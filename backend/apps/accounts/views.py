"""Authentication, RBAC and user-management APIs."""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.common.context import get_context
from apps.common.permissions import HasModulePermission, HasTenant
from apps.tenants.models import TenantUserMembership

from .models import Permission, Role, User
from .serializers import (
    InviteUserSerializer,
    LoginSerializer,
    MembershipBriefSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PermissionSerializer,
    RoleSerializer,
    UserSerializer,
)
from .tokens import tokens_for_user

logger = logging.getLogger("bunchly.auth")


def _resolve_tenant(user, tenant_slug: str | None):
    """Pick the membership/tenant for a login or tenant switch."""
    memberships = user.memberships.filter(is_active=True).select_related("tenant")
    if tenant_slug:
        membership = memberships.filter(tenant__slug=tenant_slug).first()
    else:
        membership = memberships.filter(is_default=True).first() or memberships.first()
    return membership


class LoginView(APIView):
    """Email/password login with account lockout and rate limiting."""

    # Skip JWT authentication so a stale Authorization header (e.g. an
    # expired token in the client's localStorage) can't poison the login
    # request — SimpleJWT raises InvalidToken before permission_classes
    # runs, which would surface as "Given token not valid for any token
    # type" to the user even though this endpoint is public.
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]
        ctx = get_context()

        user = User.objects.filter(email=email).first()

        # Generic failure — never reveal whether the email exists.
        invalid = Response(
            {"detail": "Invalid email or password."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

        if user is None:
            logger.info("login.failed", extra={"reason": "unknown_email"})
            return invalid

        if user.is_locked:
            logger.warning("login.locked", extra={"user_id": str(user.id)})
            return Response(
                {"detail": "Account temporarily locked. Try again later."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        authenticated = authenticate(request, username=email, password=password)
        if authenticated is None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                user.locked_until = timezone.now() + timezone.timedelta(
                    minutes=settings.LOGIN_LOCKOUT_MINUTES
                )
                logger.warning("login.lockout_triggered", extra={"user_id": str(user.id)})
            user.save(update_fields=["failed_login_attempts", "locked_until"])
            logger.info("login.failed", extra={"reason": "bad_password"})
            return invalid

        # Success — reset lockout counters.
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = timezone.now()
        user.last_login_ip = ctx.ip_address
        user.save(
            update_fields=[
                "failed_login_attempts",
                "locked_until",
                "last_login",
                "last_login_ip",
            ]
        )

        membership = _resolve_tenant(
            user, serializer.validated_data.get("tenant_slug")
        )
        tenant = membership.tenant if membership else None
        if tenant is None and not user.is_platform_admin:
            return Response(
                {"detail": "Your account is not linked to any organisation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tokens = tokens_for_user(user, tenant)
        logger.info(
            "login.success",
            extra={
                "user_id": str(user.id),
                "tenant_id": str(tenant.id) if tenant else None,
            },
        )
        memberships = user.memberships.filter(is_active=True).select_related("tenant")
        return Response(
            {
                **tokens,
                "user": UserSerializer(user).data,
                "active_tenant_id": str(tenant.id) if tenant else None,
                "memberships": MembershipBriefSerializer(memberships, many=True).data,
            }
        )


class RefreshView(TokenRefreshView):
    """Rotates the access token; tenant claim is preserved automatically."""

    # Refresh takes the refresh token in the body; never authenticate
    # from the Authorization header here.
    authentication_classes: list = []
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """Blacklists the supplied refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response(
                {"detail": "A refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(token).blacklist()
        except TokenError:
            pass  # already invalid — treat logout as idempotent
        return Response({"detail": "Signed out."})


class MeView(APIView):
    """Current user: profile, memberships and active-tenant permissions."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        tenant = getattr(request, "tenant", None)
        memberships = user.memberships.filter(is_active=True).select_related("tenant")
        # The `impersonating` claim is set when a platform admin entered
        # this tenant via the audited impersonation flow. Frontend uses
        # it to render the banner + Exit-impersonation control.
        token_payload = getattr(request, "auth", None)
        impersonating = bool(
            token_payload and token_payload.get("impersonating") is True
        )
        return Response(
            {
                "user": UserSerializer(user).data,
                "memberships": MembershipBriefSerializer(memberships, many=True).data,
                "active_tenant_id": str(tenant.id) if tenant else None,
                "permissions": sorted(user.permission_codes(tenant)),
                "impersonating": impersonating,
                "active_tenant_name": tenant.name if tenant else None,
                "active_tenant_slug": tenant.slug if tenant else None,
            }
        )


class SwitchTenantView(APIView):
    """Issues a fresh token pair bound to a different organisation."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        slug = request.data.get("tenant_slug")
        membership = _resolve_tenant(request.user, slug)
        if membership is None:
            return Response(
                {"detail": "You are not a member of that organisation."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tokens = tokens_for_user(request.user, membership.tenant)
        return Response(
            {**tokens, "active_tenant_id": str(membership.tenant.id)}
        )


class EndImpersonationView(APIView):
    """Exit an impersonation session and return to the pure platform-admin token.

    Records the end of the impersonation in the audit trail so the audit
    log shows a matched start/end pair per session.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.audit.models import AuditAction
        from apps.audit.services import record_audit

        if not request.user.is_platform_admin:
            return Response(
                {"detail": "Only platform admins can end impersonation."},
                status=status.HTTP_403_FORBIDDEN,
            )
        tenant = getattr(request, "tenant", None)
        token_payload = getattr(request, "auth", None)
        was_impersonating = bool(
            token_payload and token_payload.get("impersonating") is True
        )
        if not was_impersonating:
            return Response(
                {"detail": "Not currently impersonating a tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if tenant is not None:
            record_audit(
                AuditAction.IMPERSONATE_END,
                "tenant",
                entity_id=tenant.pk,
                description=(
                    f"Platform admin {request.user.email} exited tenant "
                    f"{tenant.slug}"
                ),
                tenant=tenant,
                actor=request.user,
            )
        # Re-issue a tenant-less token — back to the platform overview.
        tokens = tokens_for_user(request.user)
        return Response({**tokens, "active_tenant_id": None, "impersonating": False})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated."})


class PasswordResetRequestView(APIView):
    """Starts the password-reset flow. Always returns 200 (no enumeration)."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email=serializer.validated_data["email"].lower(), is_active=True
        ).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            # Routed through the notification engine, which resolves the
            # user's tenant and renders the configured template.
            from apps.notifications.services import notify_user

            notify_user(
                user,
                "password_reset",
                context={
                    "recipient_name": user.full_name or user.email,
                    "uid": uid,
                    "token": token,
                },
            )
        return Response(
            {"detail": "If the account exists, reset instructions were sent."}
        )


class PasswordResetConfirmView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(
            user, data["token"]
        ):
            return Response(
                {"detail": "Invalid or expired reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(data["new_password"])
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["password", "failed_login_attempts", "locked_until"])
        return Response({"detail": "Password has been reset."})


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only RBAC permission catalogue."""

    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["module"]
    search_fields = ["code", "name"]


class RoleViewSet(viewsets.ModelViewSet):
    """Tenant-scoped role management."""

    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = {
        "list": "accounts.manage_roles",
        "retrieve": "accounts.manage_roles",
        "default": "accounts.manage_roles",
    }
    search_fields = ["name"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return (
            Role.objects.filter(tenant=tenant)
            .prefetch_related("permissions")
            .order_by("name")
        )

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

    def perform_destroy(self, instance):
        if instance.is_system:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("System roles cannot be deleted.")
        instance.delete()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Lists users within the current tenant; supports inviting new ones."""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = {
        "list": "accounts.manage_users",
        "retrieve": "accounts.manage_users",
        "invite": "accounts.manage_users",
        "default": "accounts.manage_users",
    }
    search_fields = ["email", "first_name", "last_name"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return User.objects.filter(
            memberships__tenant=tenant, memberships__is_active=True
        ).distinct()

    @action(detail=False, methods=["post"], throttle_classes=[ScopedRateThrottle])
    def invite(self, request):
        self.throttle_scope = "invitation"
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tenant = request.tenant

        user, created = User.objects.get_or_create(
            email=data["email"].lower(),
            defaults={
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])

        membership, _ = TenantUserMembership.objects.get_or_create(
            tenant=tenant,
            user=user,
            defaults={"invited_at": timezone.now(), "is_active": True},
        )
        membership.is_owner = data.get("is_owner", False)
        if data.get("role_ids"):
            roles = Role.objects.filter(tenant=tenant, id__in=data["role_ids"])
            membership.roles.set(roles)
        membership.save()

        return Response(
            {
                "detail": "Invitation recorded.",
                "user": UserSerializer(user).data,
                "created": created,
            },
            status=status.HTTP_201_CREATED,
        )
