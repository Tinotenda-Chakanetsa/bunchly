"""Choice enumerations for the reports & analytics module (spec §9.17)."""
from django.db import models


class ReportKey(models.TextChoices):
    """The catalogue of available reports.

    The string value is the stable key used by the report registry, the
    ``run`` / ``export`` endpoints and ``SavedReport`` rows.
    """

    EMPLOYEE_LIST = "employee_list", "Employee list"
    HEADCOUNT_BY_DEPARTMENT = "headcount_by_department", "Headcount by department"
    NEW_HIRES = "new_hires", "New hires"
    EXITS = "exits", "Exits"
    CONTRACT_EXPIRY = "contract_expiry", "Contract expiry"
    PROBATION_ENDING = "probation_ending", "Probation ending"
    RETIREMENT_APPROACHING = "retirement_approaching", "Retirement approaching"
    LEAVE_BALANCES = "leave_balances", "Leave balances"
    LEAVE_TAKEN = "leave_taken", "Leave taken"
    LEAVE_TRENDS = "leave_trends", "Leave trends"
    MISSING_DOCUMENTS = "missing_documents", "Missing required documents"
    DOCUMENT_AUDIT = "document_audit", "Document upload audit"
    ATTENDANCE_SUMMARY = "attendance_summary", "Attendance summary"
    OVERTIME_BY_DEPARTMENT = "overtime_by_department", "Overtime by department"
    WORKFLOW_THROUGHPUT = "workflow_throughput", "Workflow throughput"
    AUDIT_LOGS = "audit_logs", "Audit logs"


class DashboardAudience(models.TextChoices):
    """Role-based dashboards (spec §9.16)."""

    HR = "hr", "HR dashboard"
    MANAGER = "manager", "Line manager dashboard"
    EMPLOYEE = "employee", "Employee dashboard"
    EXECUTIVE = "executive", "Executive dashboard"


class ExportFormat(models.TextChoices):
    CSV = "csv", "CSV"
    XLSX = "xlsx", "Excel (XLSX)"
