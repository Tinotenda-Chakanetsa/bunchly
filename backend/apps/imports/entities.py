"""Importable-entity definitions (spec §9.14).

Each entity declares its canonical columns, required columns, a row
validator and a row applier. Adding a new entity is purely additive —
register a new :class:`EntityDefinition` in :data:`REGISTRY` (and a
matching value in :class:`~apps.imports.enums.ImportEntityType`) — the
parser / validate / commit services stay generic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from apps.employees.enums import EmploymentStatus
from apps.employees.models import Employee
from apps.organisation.models import (
    CostCentre,
    Department,
    Grade,
    JobTitle,
    Location,
)


@dataclass(frozen=True)
class EntityDefinition:
    """Everything the import pipeline needs to handle one entity type."""

    columns: list[str]
    required: set[str]
    template_help: dict[str, str]
    validate_row: Callable[[object, dict, int], list[tuple[str, str]]]
    apply_row: Callable[[object, dict], object]


# --- shared helpers --------------------------------------------------------

def _resolve_by_code(model, tenant, code):
    """Look up a tenant-scoped reference by its ``code`` column."""
    if not code:
        return None
    return model.objects.filter(tenant=tenant, code=code).first()


def _parse_date(value):
    """Tolerant ISO date parser. Returns ``None`` for empty / invalid input."""
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return None


# --- employees -------------------------------------------------------------

_EMPLOYEE_REF_COLUMNS = [
    ("department_code", Department, "Department"),
    ("job_title_code", JobTitle, "Job title"),
    ("grade_code", Grade, "Grade"),
    ("cost_centre_code", CostCentre, "Cost centre"),
    ("work_location_code", Location, "Location"),
]


def _employees_validate(tenant, row, row_index):
    errors: list[tuple[str, str]] = []
    if not row.get("employee_number"):
        errors.append(("employee_number", "Required."))
    if not row.get("first_name"):
        errors.append(("first_name", "Required."))
    if not row.get("last_name"):
        errors.append(("last_name", "Required."))

    # Tenant-scoped uniqueness (employee_number + national_id).
    employee_number = row.get("employee_number")
    if employee_number and Employee.all_objects.filter(
        tenant=tenant, employee_number=employee_number, is_deleted=False
    ).exists():
        errors.append(("employee_number", "Already in use in this tenant."))

    national_id = row.get("national_id")
    if national_id and Employee.all_objects.filter(
        tenant=tenant, national_id=national_id, is_deleted=False
    ).exists():
        errors.append(("national_id", "Already in use in this tenant."))

    # Reference-FK lookups — every referenced code must exist.
    for code_field, model, label in _EMPLOYEE_REF_COLUMNS:
        code = row.get(code_field)
        if code and _resolve_by_code(model, tenant, code) is None:
            errors.append(
                (code_field, f"{label} with code '{code}' not found.")
            )

    # Employment status (uses Employee enum; default 'active' if blank).
    raw_status = (row.get("employment_status") or "").strip()
    if raw_status and raw_status not in {s.value for s in EmploymentStatus}:
        errors.append(
            ("employment_status", f"Unknown employment status '{raw_status}'.")
        )

    # Start date must be parseable when provided.
    if row.get("start_date") and _parse_date(row["start_date"]) is None:
        errors.append(("start_date", "Use ISO date format YYYY-MM-DD."))

    return errors


def _employees_apply(tenant, row):
    status = (row.get("employment_status") or EmploymentStatus.ACTIVE).strip()
    return Employee.objects.create(
        tenant=tenant,
        employee_number=row["employee_number"].strip(),
        first_name=row["first_name"].strip(),
        last_name=row["last_name"].strip(),
        preferred_name=(row.get("preferred_name") or "").strip(),
        work_email=(row.get("work_email") or "").strip(),
        personal_email=(row.get("personal_email") or "").strip(),
        phone=(row.get("phone") or "").strip(),
        national_id=(row.get("national_id") or "").strip(),
        department=_resolve_by_code(Department, tenant, row.get("department_code")),
        job_title=_resolve_by_code(JobTitle, tenant, row.get("job_title_code")),
        grade=_resolve_by_code(Grade, tenant, row.get("grade_code")),
        cost_centre=_resolve_by_code(CostCentre, tenant, row.get("cost_centre_code")),
        work_location=_resolve_by_code(Location, tenant, row.get("work_location_code")),
        employment_status=status,
        start_date=_parse_date(row.get("start_date")),
    )


# --- registry --------------------------------------------------------------

REGISTRY: dict[str, EntityDefinition] = {
    "employees": EntityDefinition(
        columns=[
            "employee_number", "first_name", "last_name", "preferred_name",
            "work_email", "personal_email", "phone", "national_id",
            "department_code", "job_title_code", "grade_code",
            "cost_centre_code", "work_location_code", "employment_status",
            "start_date",
        ],
        required={"employee_number", "first_name", "last_name"},
        template_help={
            "employee_number": "Required. Unique per tenant (e.g. EMP-001).",
            "first_name": "Required.",
            "last_name": "Required.",
            "work_email": "Optional. Used for notifications.",
            "national_id": "Optional. Unique per tenant when supplied.",
            "department_code": (
                "Optional. Must match an existing Department code."
            ),
            "job_title_code": "Optional. Must match an existing Job title code.",
            "grade_code": "Optional. Must match an existing Grade code.",
            "cost_centre_code": (
                "Optional. Must match an existing Cost centre code."
            ),
            "work_location_code": (
                "Optional. Must match an existing Location code."
            ),
            "employment_status": (
                "Optional. One of: active, probation, on_leave, terminated, "
                "resigned, retired. Defaults to 'active'."
            ),
            "start_date": "Optional. ISO date — YYYY-MM-DD.",
        },
        validate_row=_employees_validate,
        apply_row=_employees_apply,
    ),
}


def get_definition(entity_type: str) -> EntityDefinition:
    """Look up an entity definition or raise ``KeyError``."""
    return REGISTRY[entity_type]
