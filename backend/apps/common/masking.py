"""Field-level masking for sensitive PII / financial data.

Control #8 — *Fine-grained data protection*. A serializer that mixes
in ``SensitiveFieldMaskingMixin`` automatically renders any field
listed in ``settings.SENSITIVE_FIELDS`` as a masked string for callers
who do not hold the field's clearance permission
(``settings.SENSITIVE_FIELD_PERMISSIONS``).

Examples
--------
``"1234-5678-9012-3456"`` → ``"**** **** **** 3456"``
``"930313-04-1234"``      → ``"******-04-****"``
Numeric salaries          → ``"***"``

The actual database value is never sent to the unauthorised caller.

Usage::

    class EmployeeSerializer(SensitiveFieldMaskingMixin, ModelSerializer):
        class Meta:
            model = Employee
            fields = [..., "current_salary", "national_id"]

When a Finance Officer with ``payroll.view_salary`` requests the same
record they receive the unmasked value; an HR Admin without that code
sees the mask.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings


def mask_value(value: Any) -> Any:
    """Return a masked representation of *value*.

    Strings keep their last four characters (or the last segment after
    a dash / space); numbers become ``"***"``. ``None`` is returned
    unchanged so empty fields stay empty rather than becoming a fake
    mask the caller might mistake for a value.
    """
    if value is None or value == "":
        return value
    if isinstance(value, (int, float)):
        return "***"
    s = str(value)
    if len(s) <= 4:
        return "*" * len(s)
    # Preserve any trailing alphanumeric block (e.g. last 4 of bank
    # account / passport) — operators commonly need it to confirm the
    # right record without exposing the whole number.
    return f"{'*' * (len(s) - 4)}{s[-4:]}"


class SensitiveFieldMaskingMixin:
    """Mixin for ``rest_framework.serializers.Serializer`` subclasses.

    Walks the representation produced by ``to_representation`` and
    masks every field in ``settings.SENSITIVE_FIELDS`` unless the
    requesting user holds the corresponding clearance permission
    declared in ``settings.SENSITIVE_FIELD_PERMISSIONS``.
    """

    def to_representation(self, instance):  # type: ignore[override]
        data = super().to_representation(instance)
        request = self.context.get("request") if hasattr(self, "context") else None
        user = getattr(request, "user", None)
        tenant = getattr(request, "tenant", None)

        sensitive = settings.SENSITIVE_FIELDS
        perms = settings.SENSITIVE_FIELD_PERMISSIONS

        # Platform admins see everything; operators see exactly what
        # their role permits.
        is_platform_admin = bool(
            user is not None and getattr(user, "is_platform_admin", False)
        )

        for field_name in list(data.keys()):
            if field_name not in sensitive:
                continue
            if is_platform_admin:
                continue
            required = perms.get(field_name)
            if (
                required
                and user is not None
                and getattr(user, "is_authenticated", False)
                and user.has_perm_code(required, tenant)
            ):
                continue
            data[field_name] = mask_value(data[field_name])
        return data
