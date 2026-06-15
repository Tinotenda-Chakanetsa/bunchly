"""System-settings business logic — typed casting, get/set, seeding."""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from .defaults import DEFAULT_SETTINGS
from .enums import SettingValueType
from .models import SystemSetting

_TRUE = {"true", "1", "yes", "on"}


def cast_value(value: str, value_type: str):
    """Cast a raw text setting value to its Python type."""
    if value is None or value == "":
        return None
    if value_type == SettingValueType.INTEGER:
        return int(value)
    if value_type == SettingValueType.BOOLEAN:
        return str(value).strip().lower() in _TRUE
    if value_type == SettingValueType.DECIMAL:
        return Decimal(value)
    if value_type == SettingValueType.JSON:
        return json.loads(value)
    return value


def validate_value(value: str, value_type: str) -> None:
    """Raise ``ValidationError`` if a raw value cannot be cast to its type."""
    try:
        cast_value(value, value_type)
    except (ValueError, InvalidOperation, json.JSONDecodeError):
        raise ValidationError(
            {"value": f"Value is not valid for type '{value_type}'."}
        )


def get_setting(tenant, key: str, default=None):
    """Return a tenant setting's cast value, or ``default`` if absent."""
    setting = SystemSetting.objects.filter(tenant=tenant, key=key).first()
    if setting is None:
        return default
    cast = cast_value(setting.value, setting.value_type)
    return default if cast is None else cast


def set_setting(tenant, key: str, value) -> SystemSetting:
    """Create or update a tenant setting, storing the value as text."""
    setting = SystemSetting.objects.filter(tenant=tenant, key=key).first()
    if setting is None:
        spec = DEFAULT_SETTINGS.get(key, {})
        setting = SystemSetting(
            tenant=tenant,
            key=key,
            group=spec.get("group", ""),
            label=spec.get("label", ""),
            value_type=spec.get("value_type", SettingValueType.STRING),
            is_public=spec.get("is_public", False),
        )
    if not setting.is_editable and setting.pk is not None:
        raise ValidationError(f"Setting '{key}' is locked and cannot be changed.")
    raw = _to_raw(value, setting.value_type)
    validate_value(raw, setting.value_type)
    setting.value = raw
    setting.save()
    return setting


def _to_raw(value, value_type: str) -> str:
    """Serialise a Python value to its stored text form."""
    if value is None:
        return ""
    if value_type == SettingValueType.JSON and not isinstance(value, str):
        return json.dumps(value)
    if value_type == SettingValueType.BOOLEAN and isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def seed_defaults(tenant) -> int:
    """Create any missing catalogue settings for a tenant. Returns the count."""
    created = 0
    for key, spec in DEFAULT_SETTINGS.items():
        _, was_created = SystemSetting.objects.get_or_create(
            tenant=tenant,
            key=key,
            defaults={
                "group": spec["group"],
                "label": spec["label"],
                "value_type": spec["value_type"],
                "value": spec["value"],
                "is_public": spec["is_public"],
            },
        )
        created += int(was_created)
    return created
