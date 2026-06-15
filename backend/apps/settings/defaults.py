"""Built-in catalogue of operational system settings.

These are *operational* defaults that do not belong to a specific
domain module. Branding, email identity and module on/off flags live on
``tenants.TenantSettings``; module-specific configuration lives on its
own model (``LeaveType``, ``EducationBenefitRule`` …). Keep this
catalogue for cross-cutting, tenant-tunable values.

Each entry: key -> (group, label, value_type, default value, is_public).
"""
from __future__ import annotations

from .enums import SettingValueType

DEFAULT_SETTINGS: dict[str, dict] = {
    "general.date_format": {
        "group": "general",
        "label": "Date display format",
        "value_type": SettingValueType.STRING,
        "value": "DD/MM/YYYY",
        "is_public": True,
    },
    "general.fiscal_year_start_month": {
        "group": "general",
        "label": "Fiscal year start month",
        "value_type": SettingValueType.INTEGER,
        "value": "1",
        "is_public": True,
    },
    "general.week_start_day": {
        "group": "general",
        "label": "First day of the week (0=Mon)",
        "value_type": SettingValueType.INTEGER,
        "value": "0",
        "is_public": True,
    },
    "dashboard.show_birthdays": {
        "group": "dashboard",
        "label": "Show upcoming birthdays on dashboards",
        "value_type": SettingValueType.BOOLEAN,
        "value": "true",
        "is_public": True,
    },
    "dashboard.alert_horizon_days": {
        "group": "dashboard",
        "label": "Days ahead to surface expiry / probation alerts",
        "value_type": SettingValueType.INTEGER,
        "value": "30",
        "is_public": True,
    },
    "selfservice.allow_profile_edit": {
        "group": "self_service",
        "label": "Allow employees to edit their own profile",
        "value_type": SettingValueType.BOOLEAN,
        "value": "false",
        "is_public": True,
    },
    "security.session_timeout_minutes": {
        "group": "security",
        "label": "Idle session timeout (minutes)",
        "value_type": SettingValueType.INTEGER,
        "value": "60",
        "is_public": False,
    },
    "support.contact_email": {
        "group": "support",
        "label": "Internal HR support contact email",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": True,
    },
    # --- Contract template ------------------------------------------------
    # Used by the DOCX contract generator. Every field is optional; the
    # generator falls back to sensible defaults when blank.
    "contract.employer_address": {
        "group": "contract",
        "label": "Employer postal address (on contracts)",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.employer_telephone": {
        "group": "contract",
        "label": "Employer telephone (on contracts)",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.working_hours_text": {
        "group": "contract",
        "label": "Working-hours paragraph for new contracts",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.annual_leave_text": {
        "group": "contract",
        "label": "Annual-leave paragraph for new contracts",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.sick_leave_text": {
        "group": "contract",
        "label": "Sick-leave paragraph for new contracts",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.notice_text": {
        "group": "contract",
        "label": "Termination-notice paragraph for new contracts",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.witness_title": {
        "group": "contract",
        "label": "Default witness title on contract signature page",
        "value_type": SettingValueType.STRING,
        "value": "Human Resources Officer",
        "is_public": False,
    },
    "contract.bonus_enabled": {
        "group": "contract",
        "label": "Include a bonus clause by default",
        "value_type": SettingValueType.BOOLEAN,
        "value": "false",
        "is_public": False,
    },
    "contract.medical_aid_enabled": {
        "group": "contract",
        "label": "Include a medical-aid clause by default",
        "value_type": SettingValueType.BOOLEAN,
        "value": "false",
        "is_public": False,
    },
    "contract.transport_allowance": {
        "group": "contract",
        "label": "Default monthly transport allowance (blank to omit)",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
    "contract.housing_allowance": {
        "group": "contract",
        "label": "Default monthly housing allowance (blank to omit)",
        "value_type": SettingValueType.STRING,
        "value": "",
        "is_public": False,
    },
}
