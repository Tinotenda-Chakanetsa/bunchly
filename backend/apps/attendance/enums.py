"""Choice enumerations for the time & attendance module (spec §9.9)."""
from django.db import models


class AttendanceStatus(models.TextChoices):
    """How a working day resolved for an employee."""

    PRESENT = "present", "Present"
    REMOTE = "remote", "Worked remotely"
    ABSENT = "absent", "Absent"
    ON_LEAVE = "on_leave", "On leave"
    HOLIDAY = "holiday", "Public holiday"
    REST_DAY = "rest_day", "Rest day"


# Statuses on which no work is expected — lateness / overtime do not apply.
NON_WORKING_STATUSES = {
    AttendanceStatus.ABSENT,
    AttendanceStatus.ON_LEAVE,
    AttendanceStatus.HOLIDAY,
    AttendanceStatus.REST_DAY,
}


class EntryType(models.TextChoices):
    """How an attendance record was captured."""

    CLOCK = "clock", "Clock in / out"
    MANUAL = "manual", "Manual entry"


class ApprovalStatus(models.TextChoices):
    """Review state of an attendance record (manual entries need approval)."""

    PENDING = "pending", "Pending approval"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class TimesheetStatus(models.TextChoices):
    """Lifecycle of a per-employee timesheet period."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    EXPORTED = "exported", "Exported to payroll"
