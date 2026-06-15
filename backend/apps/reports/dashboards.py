"""Role-based dashboard aggregations (spec §9.16).

Each function returns a flat metrics dict for one audience. Dashboards
are tenant-scoped; the manager and employee dashboards additionally
scope to the requesting user's own employee record.
"""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.attendance.enums import ApprovalStatus, AttendanceStatus, TimesheetStatus
from apps.attendance.models import AttendanceRecord, Timesheet
from apps.documents.services import missing_required_categories
from apps.employees.enums import EXITED_STATUSES
from apps.employees.models import Employee
from apps.leave.enums import LeaveRequestStatus
from apps.leave.models import LeaveBalance, LeaveRequest
from apps.notifications.models import Notification
from apps.organisation.models import Position


def _active(tenant):
    return Employee.objects.filter(tenant=tenant).exclude(
        employment_status__in=EXITED_STATUSES
    )


def _upcoming_birthdays(employees, *, within_days=7) -> list[dict]:
    """Employees whose birthday falls within the next ``within_days``."""
    today = timezone.now().date()
    horizon = [(today + timedelta(days=n)) for n in range(within_days + 1)]
    wanted = {(d.month, d.day) for d in horizon}
    found = []
    for emp in employees:
        dob = emp.date_of_birth
        if dob and (dob.month, dob.day) in wanted:
            found.append({"name": emp.full_name, "date": dob.replace(year=today.year)})
    return sorted(found, key=lambda r: r["date"])


def hr_dashboard(tenant) -> dict:
    """The HR dashboard metric set."""
    today = timezone.now().date()
    everyone = Employee.objects.filter(tenant=tenant)
    active = _active(tenant)

    missing_docs = sum(
        1 for e in active if missing_required_categories(e)
    )
    gender_breakdown = list(
        active.values("gender").annotate(count=Count("id")).order_by()
    )
    department_breakdown = list(
        active.values("department__name").annotate(count=Count("id")).order_by()
    )
    return {
        "total_employees": everyone.count(),
        "active_employees": active.count(),
        "new_hires_30d": everyone.filter(
            start_date__gte=today - timedelta(days=30)
        ).count(),
        "exits_30d": everyone.filter(
            end_date__gte=today - timedelta(days=30), end_date__lte=today
        ).count(),
        "contracts_expiring_90d": active.filter(
            contract_end_date__gte=today,
            contract_end_date__lte=today + timedelta(days=90),
        ).count(),
        "nearing_retirement_365d": active.filter(
            retirement_date__gte=today,
            retirement_date__lte=today + timedelta(days=365),
        ).count(),
        "probation_ending_30d": active.filter(
            probation_end_date__gte=today,
            probation_end_date__lte=today + timedelta(days=30),
        ).count(),
        "missing_required_documents": missing_docs,
        "pending_leave_approvals": LeaveRequest.objects.filter(
            tenant=tenant, status=LeaveRequestStatus.PENDING
        ).count(),
        "pending_timesheet_approvals": Timesheet.objects.filter(
            tenant=tenant, status=TimesheetStatus.SUBMITTED
        ).count(),
        "attendance_exceptions_30d": AttendanceRecord.objects.filter(
            tenant=tenant, work_date__gte=today - timedelta(days=30),
        ).filter(
            Q(is_late=True)
            | Q(is_early_departure=True)
            | Q(status=AttendanceStatus.ABSENT)
            | Q(approval_status=ApprovalStatus.PENDING)
        ).count(),
        "open_vacancies": Position.objects.filter(
            tenant=tenant, is_vacant=True, is_active=True
        ).count(),
        "upcoming_birthdays": _upcoming_birthdays(active),
        "gender_breakdown": [
            {"gender": g["gender"], "count": g["count"]} for g in gender_breakdown
        ],
        "department_breakdown": [
            {"department": d["department__name"] or "(Unassigned)", "count": d["count"]}
            for d in department_breakdown
        ],
    }


def manager_dashboard(tenant, manager: Employee | None) -> dict:
    """The line-manager dashboard — scoped to the manager's direct reports."""
    if manager is None:
        return {"direct_reports": 0, "note": "No employee profile for this user."}
    today = timezone.now().date()
    reports = Employee.objects.filter(tenant=tenant, line_manager=manager)
    report_ids = list(reports.values_list("id", flat=True))

    on_leave_today = LeaveRequest.objects.filter(
        tenant=tenant,
        employee_id__in=report_ids,
        status=LeaveRequestStatus.APPROVED,
        start_date__lte=today,
        end_date__gte=today,
    ).count()
    return {
        "direct_reports": len(report_ids),
        "pending_leave_requests": LeaveRequest.objects.filter(
            tenant=tenant,
            employee_id__in=report_ids,
            status=LeaveRequestStatus.PENDING,
        ).count(),
        "team_on_leave_today": on_leave_today,
        "team_probation_ending_30d": reports.filter(
            probation_end_date__gte=today,
            probation_end_date__lte=today + timedelta(days=30),
        ).count(),
        "team_contracts_expiring_90d": reports.filter(
            contract_end_date__gte=today,
            contract_end_date__lte=today + timedelta(days=90),
        ).count(),
        "team_pending_timesheets": Timesheet.objects.filter(
            tenant=tenant,
            employee_id__in=report_ids,
            status=TimesheetStatus.SUBMITTED,
        ).count(),
    }


def employee_dashboard(tenant, employee: Employee | None, user) -> dict:
    """The employee self-service dashboard."""
    today = timezone.now().date()
    year = today.year
    unread = Notification.objects.filter(
        tenant=tenant, recipient=user, is_read=False
    ).count()
    if employee is None:
        return {
            "leave_balances": [],
            "pending_requests": 0,
            "missing_documents": 0,
            "unread_notifications": unread,
            "worked_hours_this_month": 0,
            "note": "No employee profile for this user.",
        }
    balances = LeaveBalance.objects.filter(
        tenant=tenant, employee=employee, year=year
    ).select_related("leave_type")
    month_start = today.replace(day=1)
    worked_agg = AttendanceRecord.objects.filter(
        tenant=tenant,
        employee=employee,
        work_date__gte=month_start,
        work_date__lte=today,
    ).aggregate(total=Sum("worked_minutes"))
    return {
        "leave_balances": [
            {
                "leave_type": b.leave_type.name,
                "available": b.available_days,
                "entitled": b.entitlement_total,
            }
            for b in balances
        ],
        "pending_requests": LeaveRequest.objects.filter(
            tenant=tenant, employee=employee, status=LeaveRequestStatus.PENDING
        ).count(),
        "missing_documents": len(missing_required_categories(employee)),
        "unread_notifications": unread,
        "worked_hours_this_month": round((worked_agg["total"] or 0) / 60, 1),
    }


def executive_dashboard(tenant) -> dict:
    """The executive dashboard — strategic workforce KPIs."""
    today = timezone.now().date()
    active = _active(tenant)
    active_count = active.count()
    exits_365d = Employee.objects.filter(
        tenant=tenant,
        end_date__gte=today - timedelta(days=365),
        end_date__lte=today,
    ).count()
    turnover_rate = round((exits_365d / active_count) * 100, 1) if active_count else 0.0

    distribution = list(
        active.values("employment_type").annotate(count=Count("id")).order_by()
    )
    leave_trend = list(
        LeaveRequest.objects.filter(
            tenant=tenant,
            status=LeaveRequestStatus.APPROVED,
            start_date__gte=today - timedelta(days=365),
        )
        .values("leave_type__name")
        .annotate(requests=Count("id"))
        .order_by("-requests")
    )
    return {
        "headcount": active_count,
        "exits_12m": exits_365d,
        "turnover_rate_pct": turnover_rate,
        "headcount_by_department": [
            {"department": d["department__name"] or "(Unassigned)", "count": d["count"]}
            for d in active.values("department__name").annotate(count=Count("id"))
        ],
        "workforce_distribution": [
            {"employment_type": d["employment_type"], "count": d["count"]}
            for d in distribution
        ],
        "leave_trend": [
            {"leave_type": t["leave_type__name"], "requests": t["requests"]}
            for t in leave_trend
        ],
    }
