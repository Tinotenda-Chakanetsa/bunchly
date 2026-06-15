"""Report registry — the aggregate queries behind every report (spec §9.17).

Each report is a function ``(tenant, filters) -> ReportResult`` registered
under a :class:`~apps.reports.enums.ReportKey`. The module is read-only:
it queries the other domain modules and shapes the result into columns /
rows / summary so the view layer and exporters stay generic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.attendance.enums import AttendanceStatus
from apps.attendance.models import AttendanceRecord
from apps.audit.models import AuditLog
from apps.documents.enums import DocumentStatus
from apps.documents.models import Document
from apps.documents.services import missing_required_categories
from apps.employees.enums import EXITED_STATUSES
from apps.employees.models import Employee
from apps.leave.enums import LeaveRequestStatus
from apps.leave.models import LeaveBalance, LeaveRequest
from apps.workflows.models import WorkflowInstance

from .enums import ReportKey


@dataclass
class ReportResult:
    """A rendered report: column metadata, data rows and headline summary."""

    columns: list[dict] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# key -> {"label", "description", "fn"}
_REGISTRY: dict[str, dict] = {}


def report(key: str, label: str, description: str = ""):
    """Register a report function under a :class:`ReportKey`."""

    def decorator(fn: Callable):
        _REGISTRY[key] = {"label": label, "description": description, "fn": fn}
        return fn

    return decorator


def report_catalogue() -> list[dict]:
    """The list of available reports, for the catalogue endpoint."""
    return [
        {"key": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in _REGISTRY.items()
    ]


def run_report(report_key: str, tenant, filters: dict) -> ReportResult:
    """Execute a registered report. Raises ``KeyError`` for an unknown key."""
    meta = _REGISTRY[report_key]
    return meta["fn"](tenant, filters or {})


# --------------------------------------------------------------------------
# Filter helpers
# --------------------------------------------------------------------------
def _date_window(filters: dict, *, default_days_back=90, default_days_fwd=0):
    """Resolve (date_from, date_to) from filters, applying sensible defaults."""
    today = timezone.now().date()
    date_from = filters.get("date_from") or (today - timedelta(days=default_days_back))
    date_to = filters.get("date_to") or (today + timedelta(days=default_days_fwd))
    return date_from, date_to


def _employees(tenant, filters: dict):
    """Base employee queryset with an optional department filter applied."""
    qs = Employee.objects.filter(tenant=tenant).select_related(
        "department", "job_title", "line_manager"
    )
    department = filters.get("department")
    if department:
        qs = qs.filter(department_id=department)
    return qs


# --------------------------------------------------------------------------
# Workforce reports
# --------------------------------------------------------------------------
@report(ReportKey.EMPLOYEE_LIST, "Employee list", "Full employee directory.")
def _employee_list(tenant, filters) -> ReportResult:
    employees = _employees(tenant, filters).order_by("first_name", "last_name")
    rows = [
        {
            "employee_number": e.employee_number,
            "name": e.full_name,
            "department": e.department.name if e.department else "",
            "job_title": e.job_title.name if e.job_title else "",
            "status": e.get_employment_status_display(),
            "start_date": e.start_date,
        }
        for e in employees
    ]
    active = sum(
        1 for e in employees if e.employment_status not in EXITED_STATUSES
    )
    return ReportResult(
        columns=[
            {"key": "employee_number", "label": "Employee #"},
            {"key": "name", "label": "Name"},
            {"key": "department", "label": "Department"},
            {"key": "job_title", "label": "Job title"},
            {"key": "status", "label": "Status"},
            {"key": "start_date", "label": "Start date"},
        ],
        rows=rows,
        summary={"total": len(rows), "active": active},
    )


@report(
    ReportKey.HEADCOUNT_BY_DEPARTMENT,
    "Headcount by department",
    "Active employee counts grouped by department.",
)
def _headcount_by_department(tenant, filters) -> ReportResult:
    grouped = (
        _employees(tenant, filters)
        .exclude(employment_status__in=EXITED_STATUSES)
        .values("department__name")
        .annotate(headcount=Count("id"))
        .order_by("-headcount")
    )
    rows = [
        {
            "department": g["department__name"] or "(Unassigned)",
            "headcount": g["headcount"],
        }
        for g in grouped
    ]
    return ReportResult(
        columns=[
            {"key": "department", "label": "Department"},
            {"key": "headcount", "label": "Headcount"},
        ],
        rows=rows,
        summary={
            "departments": len(rows),
            "total_headcount": sum(r["headcount"] for r in rows),
        },
    )


@report(ReportKey.NEW_HIRES, "New hires", "Employees hired within the date range.")
def _new_hires(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=90)
    employees = _employees(tenant, filters).filter(
        start_date__gte=date_from, start_date__lte=date_to
    ).order_by("-start_date")
    rows = [
        {
            "employee_number": e.employee_number,
            "name": e.full_name,
            "department": e.department.name if e.department else "",
            "start_date": e.start_date,
        }
        for e in employees
    ]
    return ReportResult(
        columns=[
            {"key": "employee_number", "label": "Employee #"},
            {"key": "name", "label": "Name"},
            {"key": "department", "label": "Department"},
            {"key": "start_date", "label": "Start date"},
        ],
        rows=rows,
        summary={"total": len(rows), "from": date_from, "to": date_to},
    )


@report(ReportKey.EXITS, "Exits", "Employees who left within the date range.")
def _exits(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=90)
    employees = _employees(tenant, filters).filter(
        end_date__gte=date_from, end_date__lte=date_to
    ).order_by("-end_date")
    rows = [
        {
            "employee_number": e.employee_number,
            "name": e.full_name,
            "department": e.department.name if e.department else "",
            "end_date": e.end_date,
            "status": e.get_employment_status_display(),
            "exit_reason": e.exit_reason,
        }
        for e in employees
    ]
    return ReportResult(
        columns=[
            {"key": "employee_number", "label": "Employee #"},
            {"key": "name", "label": "Name"},
            {"key": "department", "label": "Department"},
            {"key": "end_date", "label": "Exit date"},
            {"key": "status", "label": "Status"},
            {"key": "exit_reason", "label": "Reason"},
        ],
        rows=rows,
        summary={"total": len(rows), "from": date_from, "to": date_to},
    )


def _date_field_report(tenant, filters, *, field_name, label, default_fwd):
    """Shared body for the contract / probation / retirement reports."""
    today = timezone.now().date()
    date_from = filters.get("date_from") or today
    date_to = filters.get("date_to") or (today + timedelta(days=default_fwd))
    lookup = {
        f"{field_name}__gte": date_from,
        f"{field_name}__lte": date_to,
    }
    employees = (
        _employees(tenant, filters)
        .exclude(employment_status__in=EXITED_STATUSES)
        .filter(**lookup)
        .order_by(field_name)
    )
    rows = [
        {
            "employee_number": e.employee_number,
            "name": e.full_name,
            "department": e.department.name if e.department else "",
            "date": getattr(e, field_name),
            "days_remaining": (getattr(e, field_name) - today).days,
        }
        for e in employees
    ]
    return ReportResult(
        columns=[
            {"key": "employee_number", "label": "Employee #"},
            {"key": "name", "label": "Name"},
            {"key": "department", "label": "Department"},
            {"key": "date", "label": label},
            {"key": "days_remaining", "label": "Days remaining"},
        ],
        rows=rows,
        summary={"total": len(rows), "from": date_from, "to": date_to},
    )


@report(ReportKey.CONTRACT_EXPIRY, "Contract expiry", "Contracts ending soon.")
def _contract_expiry(tenant, filters) -> ReportResult:
    return _date_field_report(
        tenant, filters, field_name="contract_end_date",
        label="Contract end", default_fwd=90,
    )


@report(ReportKey.PROBATION_ENDING, "Probation ending", "Probations ending soon.")
def _probation_ending(tenant, filters) -> ReportResult:
    return _date_field_report(
        tenant, filters, field_name="probation_end_date",
        label="Probation end", default_fwd=30,
    )


@report(
    ReportKey.RETIREMENT_APPROACHING,
    "Retirement approaching",
    "Employees due to retire soon.",
)
def _retirement_approaching(tenant, filters) -> ReportResult:
    return _date_field_report(
        tenant, filters, field_name="retirement_date",
        label="Retirement date", default_fwd=365,
    )


# --------------------------------------------------------------------------
# Leave reports
# --------------------------------------------------------------------------
@report(ReportKey.LEAVE_BALANCES, "Leave balances", "Current leave balances.")
def _leave_balances(tenant, filters) -> ReportResult:
    year = filters.get("year") or timezone.now().year
    balances = LeaveBalance.objects.filter(
        tenant=tenant, year=year
    ).select_related("employee", "leave_type")
    department = filters.get("department")
    if department:
        balances = balances.filter(employee__department_id=department)
    rows = [
        {
            "employee": b.employee.full_name,
            "leave_type": b.leave_type.name,
            "year": b.year,
            "entitled": b.entitlement_total,
            "taken": b.taken_days,
            "pending": b.pending_days,
            "available": b.available_days,
        }
        for b in balances.order_by("employee__first_name", "leave_type__name")
    ]
    return ReportResult(
        columns=[
            {"key": "employee", "label": "Employee"},
            {"key": "leave_type", "label": "Leave type"},
            {"key": "year", "label": "Year"},
            {"key": "entitled", "label": "Entitled"},
            {"key": "taken", "label": "Taken"},
            {"key": "pending", "label": "Pending"},
            {"key": "available", "label": "Available"},
        ],
        rows=rows,
        summary={"total": len(rows), "year": year},
    )


@report(ReportKey.LEAVE_TAKEN, "Leave taken", "Approved leave within the date range.")
def _leave_taken(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=180)
    requests = LeaveRequest.objects.filter(
        tenant=tenant,
        status=LeaveRequestStatus.APPROVED,
        start_date__gte=date_from,
        start_date__lte=date_to,
    ).select_related("employee", "leave_type")
    department = filters.get("department")
    if department:
        requests = requests.filter(employee__department_id=department)
    rows = [
        {
            "employee": r.employee.full_name,
            "leave_type": r.leave_type.name,
            "start_date": r.start_date,
            "end_date": r.end_date,
            "days": r.total_days,
        }
        for r in requests.order_by("-start_date")
    ]
    return ReportResult(
        columns=[
            {"key": "employee", "label": "Employee"},
            {"key": "leave_type", "label": "Leave type"},
            {"key": "start_date", "label": "Start"},
            {"key": "end_date", "label": "End"},
            {"key": "days", "label": "Days"},
        ],
        rows=rows,
        summary={
            "total_requests": len(rows),
            "total_days": float(sum(r["days"] for r in rows)),
        },
    )


@report(ReportKey.LEAVE_TRENDS, "Leave trends", "Approved leave grouped by type.")
def _leave_trends(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=365)
    grouped = (
        LeaveRequest.objects.filter(
            tenant=tenant,
            status=LeaveRequestStatus.APPROVED,
            start_date__gte=date_from,
            start_date__lte=date_to,
        )
        .values("leave_type__name")
        .annotate(requests=Count("id"), days=Sum("total_days"))
        .order_by("-days")
    )
    rows = [
        {
            "leave_type": g["leave_type__name"],
            "requests": g["requests"],
            "days": float(g["days"] or 0),
        }
        for g in grouped
    ]
    return ReportResult(
        columns=[
            {"key": "leave_type", "label": "Leave type"},
            {"key": "requests", "label": "Requests"},
            {"key": "days", "label": "Total days"},
        ],
        rows=rows,
        summary={
            "total_days": sum(r["days"] for r in rows),
            "from": date_from, "to": date_to,
        },
    )


# --------------------------------------------------------------------------
# Document reports
# --------------------------------------------------------------------------
@report(
    ReportKey.MISSING_DOCUMENTS,
    "Missing required documents",
    "Employees missing one or more required documents.",
)
def _missing_documents(tenant, filters) -> ReportResult:
    rows = []
    for employee in _employees(tenant, filters).exclude(
        employment_status__in=EXITED_STATUSES
    ):
        missing = missing_required_categories(employee)
        if missing:
            rows.append({
                "employee": employee.full_name,
                "department": employee.department.name if employee.department else "",
                "missing": ", ".join(c.name for c in missing),
                "missing_count": len(missing),
            })
    return ReportResult(
        columns=[
            {"key": "employee", "label": "Employee"},
            {"key": "department", "label": "Department"},
            {"key": "missing", "label": "Missing categories"},
            {"key": "missing_count", "label": "Count"},
        ],
        rows=rows,
        summary={"employees_with_gaps": len(rows)},
    )


@report(
    ReportKey.DOCUMENT_AUDIT,
    "Document upload audit",
    "Documents uploaded within the date range.",
)
def _document_audit(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=90)
    documents = Document.objects.filter(
        tenant=tenant,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).select_related("employee", "category")
    rows = [
        {
            "employee": d.employee.full_name,
            "category": d.category.name,
            "title": d.title,
            "status": d.get_status_display(),
            "uploaded_at": d.created_at.date(),
        }
        for d in documents.order_by("-created_at")
    ]
    approved = sum(1 for d in documents if d.status == DocumentStatus.APPROVED)
    return ReportResult(
        columns=[
            {"key": "employee", "label": "Employee"},
            {"key": "category", "label": "Category"},
            {"key": "title", "label": "Title"},
            {"key": "status", "label": "Status"},
            {"key": "uploaded_at", "label": "Uploaded"},
        ],
        rows=rows,
        summary={"total": len(rows), "approved": approved},
    )


# --------------------------------------------------------------------------
# Time & attendance reports
# --------------------------------------------------------------------------
def _attendance_records(tenant, filters, date_from, date_to):
    """Attendance records in a window, with an optional department filter."""
    records = AttendanceRecord.objects.filter(
        tenant=tenant, work_date__gte=date_from, work_date__lte=date_to
    )
    department = filters.get("department")
    if department:
        records = records.filter(employee__department_id=department)
    return records


@report(
    ReportKey.ATTENDANCE_SUMMARY,
    "Attendance summary",
    "Worked hours, overtime and exceptions per employee.",
)
def _attendance_summary(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=30)
    grouped = (
        _attendance_records(tenant, filters, date_from, date_to)
        .values("employee__first_name", "employee__last_name")
        .annotate(
            days=Count("id"),
            worked_minutes=Sum("worked_minutes"),
            overtime_minutes=Sum("overtime_minutes"),
            late_days=Count("id", filter=Q(is_late=True)),
            absent_days=Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
        )
        .order_by("employee__first_name", "employee__last_name")
    )
    rows = [
        {
            "employee": f"{g['employee__first_name']} {g['employee__last_name']}",
            "days": g["days"],
            "worked_hours": round((g["worked_minutes"] or 0) / 60, 2),
            "overtime_hours": round((g["overtime_minutes"] or 0) / 60, 2),
            "late_days": g["late_days"],
            "absent_days": g["absent_days"],
        }
        for g in grouped
    ]
    return ReportResult(
        columns=[
            {"key": "employee", "label": "Employee"},
            {"key": "days", "label": "Days recorded"},
            {"key": "worked_hours", "label": "Worked hours"},
            {"key": "overtime_hours", "label": "Overtime hours"},
            {"key": "late_days", "label": "Late days"},
            {"key": "absent_days", "label": "Absent days"},
        ],
        rows=rows,
        summary={
            "employees": len(rows),
            "total_worked_hours": round(sum(r["worked_hours"] for r in rows), 2),
            "total_overtime_hours": round(
                sum(r["overtime_hours"] for r in rows), 2
            ),
            "from": date_from, "to": date_to,
        },
    )


@report(
    ReportKey.OVERTIME_BY_DEPARTMENT,
    "Overtime by department",
    "Overtime hours grouped by department.",
)
def _overtime_by_department(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=30)
    grouped = (
        _attendance_records(tenant, filters, date_from, date_to)
        .values("employee__department__name")
        .annotate(
            overtime_minutes=Sum("overtime_minutes"),
            worked_minutes=Sum("worked_minutes"),
        )
        .order_by("-overtime_minutes")
    )
    rows = [
        {
            "department": g["employee__department__name"] or "(Unassigned)",
            "overtime_hours": round((g["overtime_minutes"] or 0) / 60, 2),
            "worked_hours": round((g["worked_minutes"] or 0) / 60, 2),
        }
        for g in grouped
    ]
    return ReportResult(
        columns=[
            {"key": "department", "label": "Department"},
            {"key": "overtime_hours", "label": "Overtime hours"},
            {"key": "worked_hours", "label": "Worked hours"},
        ],
        rows=rows,
        summary={
            "departments": len(rows),
            "total_overtime_hours": round(
                sum(r["overtime_hours"] for r in rows), 2
            ),
            "from": date_from, "to": date_to,
        },
    )


# --------------------------------------------------------------------------
# Workflow & audit reports
# --------------------------------------------------------------------------
@report(
    ReportKey.WORKFLOW_THROUGHPUT,
    "Workflow throughput",
    "Workflow instances grouped by status.",
)
def _workflow_throughput(tenant, filters) -> ReportResult:
    grouped = (
        WorkflowInstance.objects.filter(tenant=tenant)
        .values("workflow__name", "status")
        .annotate(count=Count("id"))
        .order_by("workflow__name", "status")
    )
    rows = [
        {
            "workflow": g["workflow__name"],
            "status": g["status"],
            "count": g["count"],
        }
        for g in grouped
    ]
    return ReportResult(
        columns=[
            {"key": "workflow", "label": "Workflow"},
            {"key": "status", "label": "Status"},
            {"key": "count", "label": "Count"},
        ],
        rows=rows,
        summary={"total_instances": sum(r["count"] for r in rows)},
    )


@report(ReportKey.AUDIT_LOGS, "Audit logs", "Audit-trail entries within the range.")
def _audit_logs(tenant, filters) -> ReportResult:
    date_from, date_to = _date_window(filters, default_days_back=30)
    logs = AuditLog.objects.filter(
        tenant=tenant,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).select_related("actor").order_by("-created_at")[:1000]
    rows = [
        {
            "timestamp": log.created_at,
            "actor": log.actor.full_name if log.actor else "(system)",
            "action": log.action,
            "entity_type": log.entity_type,
            "description": log.description,
        }
        for log in logs
    ]
    return ReportResult(
        columns=[
            {"key": "timestamp", "label": "Timestamp"},
            {"key": "actor", "label": "Actor"},
            {"key": "action", "label": "Action"},
            {"key": "entity_type", "label": "Entity"},
            {"key": "description", "label": "Description"},
        ],
        rows=rows,
        summary={"total": len(rows), "from": date_from, "to": date_to},
    )
