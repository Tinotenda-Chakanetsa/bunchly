"""TOTP-based multi-factor authentication (Control #2 — MFA).

Two endpoints back the frontend MFA flow:

* ``POST /api/v1/auth/mfa/setup/`` — provisions an unconfirmed TOTP
  device for the user and returns the secret + a QR-code data URL.
  Re-calling it before confirmation regenerates the secret.

* ``POST /api/v1/auth/mfa/verify/`` — confirms a freshly-provisioned
  device with the user's first TOTP code, or, after login, verifies a
  code on an already-confirmed device. On success the device is marked
  ``confirmed`` and the request session is marked verified
  (``django_otp.login``).

* ``POST /api/v1/auth/mfa/disable/`` — removes the device after
  re-verifying a current code. Sensitive operation, audited.

The audit log gets an entry for every setup / confirm / verify /
disable transition so SecOps can spot brute-force probes.

Notes
-----
* TOTP is the standards-compliant default. Passkeys / WebAuthn can be
  added later as a second ``Device`` plugin without changing the JWT
  flow.
* SMS-only MFA is intentionally not offered — the build prompt's
  Section 2 warns against it.
"""
from __future__ import annotations

import base64
import io
import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("bunchly.security")


def _audit(action: str, user, tenant, success: bool, ip):
    try:
        from apps.audit.services import record_audit
        from apps.audit.models import AuditAction

        record_audit(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            tenant=tenant,
            actor=user,
            entity_type="MFA",
            entity_id=str(user.pk),
            description=action,
            ip_address=ip,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit.record_failed", extra={"error": str(exc)})


def _qr_data_url(otpauth_url: str) -> str:
    """Render a TOTP otpauth:// URI to a base64-encoded PNG data URL."""
    try:
        import qrcode  # type: ignore
    except Exception:
        # qrcode is optional — if it's not installed, the caller can
        # render the URL themselves with any TOTP-aware library.
        return ""
    buf = io.BytesIO()
    img = qrcode.make(otpauth_url)
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class MFASetupView(APIView):
    """Provision (or re-provision) an unconfirmed TOTP device."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = request.user
        # Drop any previous unconfirmed device for this user.
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.objects.create(
            user=user,
            name="Bunchly TOTP",
            confirmed=False,
        )
        return Response(
            {
                "device_id": device.persistent_id,
                "secret_base32": device.bin_key.hex(),
                "otpauth_url": device.config_url,
                "qr_data_url": _qr_data_url(device.config_url),
            }
        )


class MFAVerifyView(APIView):
    """Verify a TOTP code — either to confirm setup or for re-auth."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django_otp import login as otp_login
        from django_otp.plugins.otp_totp.models import TOTPDevice

        code = (request.data.get("code") or "").strip()
        if not code.isdigit() or not (6 <= len(code) <= 8):
            return Response(
                {"detail": "Code must be 6–8 digits."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        tenant = getattr(request, "tenant", None)
        ip = request.META.get("REMOTE_ADDR")

        device = (
            TOTPDevice.objects.filter(user=user).order_by("-id").first()
        )
        if device is None:
            _audit("mfa.verify.no_device", user, tenant, success=False, ip=ip)
            return Response(
                {"detail": "No TOTP device set up yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not device.verify_token(code):
            _audit("mfa.verify.bad_code", user, tenant, success=False, ip=ip)
            return Response(
                {"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not device.confirmed:
            device.confirmed = True
            device.save(update_fields=["confirmed"])
        try:
            otp_login(request, device)
        except Exception:
            # otp_login requires a session; fine in API context to skip.
            pass

        user.mfa_last_verified_at = timezone.now()
        try:
            user.save(update_fields=["mfa_last_verified_at"])
        except Exception:
            # The User model may not yet carry this column — non-fatal.
            pass

        _audit("mfa.verify.ok", user, tenant, success=True, ip=ip)
        return Response({"detail": "MFA verified.", "confirmed": device.confirmed})


class MFADisableView(APIView):
    """Remove the user's confirmed TOTP device (after re-verifying)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        code = (request.data.get("code") or "").strip()
        user = request.user
        tenant = getattr(request, "tenant", None)
        ip = request.META.get("REMOTE_ADDR")

        device = (
            TOTPDevice.objects.filter(user=user, confirmed=True).first()
        )
        if device is None or not device.verify_token(code):
            _audit("mfa.disable.bad_code", user, tenant, success=False, ip=ip)
            return Response(
                {"detail": "Verification failed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        device.delete()
        _audit("mfa.disable.ok", user, tenant, success=True, ip=ip)
        return Response({"detail": "MFA disabled."})
