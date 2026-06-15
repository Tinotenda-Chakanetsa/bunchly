"""Authentication & access-control routes."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .mfa import MFADisableView, MFASetupView, MFAVerifyView
from .views import (
    ChangePasswordView,
    EndImpersonationView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PermissionViewSet,
    RefreshView,
    RoleViewSet,
    SwitchTenantView,
    UserViewSet,
)

router = DefaultRouter()
router.register("roles", RoleViewSet, basename="role")
router.register("permissions", PermissionViewSet, basename="permission")
router.register("users", UserViewSet, basename="user")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("switch-tenant/", SwitchTenantView.as_view(), name="switch-tenant"),
    path("end-impersonation/", EndImpersonationView.as_view(), name="end-impersonation"),
    path("password/change/", ChangePasswordView.as_view(), name="password-change"),
    # Control #2 — Multi-factor authentication (TOTP).
    path("mfa/setup/", MFASetupView.as_view(), name="mfa-setup"),
    path("mfa/verify/", MFAVerifyView.as_view(), name="mfa-verify"),
    path("mfa/disable/", MFADisableView.as_view(), name="mfa-disable"),
    path(
        "password/reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("", include(router.urls)),
]
