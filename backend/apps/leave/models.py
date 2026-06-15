"""Leave & absence models (spec §9.8).

Four tenant-owned models:

``LeaveType``      configurable leave categories with accrual / carry-forward
                   / approval rules.
``LeaveBalance``   an employee's balance for one leave type in one year.
``LeaveRequest``   an application for time off.
``LeaveApproval``  one row per stage of a request's configurable approval
                   chain (manager -> HR -> optional extra stage).

Balance arithmetic and the approval workflow live in ``services.py`` so
the models stay declarative.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    AccrualMethod,
    ApprovalStage,
    ApprovalStatus,
    DayPortion,
    GenderEligibility,
    LeaveCategory,
    LeaveRequestStatus,
)

ZERO = Decimal("0.00")


class LeaveType(TenantOwnedModel):
    """A configurable category of leave for a tenant.

    Every rule a tenant might want to vary — entitlement, accrual,
    carry-forward, notice, documentation and the approval chain — is a
    field here. Nothing about leave behaviour is hard-coded elsewhere.
    """

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    category = models.CharField(
        max_length=20, choices=LeaveCategory.choices, default=LeaveCategory.CUSTOM
    )
    description = models.TextField(blank=True)
    colour = models.CharField(
        max_length=9, default="#2563eb", help_text="Hex colour for calendar display."
    )

    # --- Entitlement & accrual -------------------------------------------
    is_paid = models.BooleanField(default=True)
    default_annual_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=ZERO,
        help_text="Yearly entitlement granted to a new balance.",
    )
    accrual_method = models.CharField(
        max_length=20, choices=AccrualMethod.choices, default=AccrualMethod.ANNUAL_LUMP
    )
    allow_carry_forward = models.BooleanField(default=False)
    max_carry_forward_days = models.DecimalField(
        max_digits=6, decimal_places=2, default=ZERO
    )

    # --- Application rules -----------------------------------------------
    requires_approval = models.BooleanField(default=True)
    requires_hr_confirmation = models.BooleanField(
        default=True, help_text="Adds an HR confirmation stage after the manager."
    )
    extra_approval_stage = models.BooleanField(
        default=False, help_text="Adds a final PVC/Admin/Finance approval stage."
    )
    extra_approval_label = models.CharField(
        max_length=80, blank=True, help_text="Label for the extra approval stage."
    )
    notify_finance = models.BooleanField(
        default=False,
        help_text="Email the configured Accounts/Finance recipients on approval.",
    )
    requires_documentation = models.BooleanField(
        default=False, help_text="A supporting document must be attached."
    )
    min_notice_days = models.PositiveIntegerField(
        default=0, help_text="Minimum days between application and start date."
    )
    max_consecutive_days = models.PositiveIntegerField(
        default=0, help_text="0 = unlimited."
    )
    allow_negative_balance = models.BooleanField(default=False)
    gender_eligibility = models.CharField(
        max_length=10, choices=GenderEligibility.choices, default=GenderEligibility.ANY
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_leavetype_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class LeaveBalance(TenantOwnedModel):
    """An employee's leave balance for one leave type in one year.

    The available figure is derived, never stored, so it can never drift
    from its components::

        available = entitled + carried_forward + adjustment
                    - taken - pending
    """

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="leave_balances"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="balances"
    )
    year = models.PositiveIntegerField(db_index=True)

    entitled_days = models.DecimalField(max_digits=7, decimal_places=2, default=ZERO)
    carried_forward_days = models.DecimalField(
        max_digits=7, decimal_places=2, default=ZERO
    )
    taken_days = models.DecimalField(max_digits=7, decimal_places=2, default=ZERO)
    pending_days = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=ZERO,
        help_text="Days reserved by requests awaiting approval.",
    )
    adjustment_days = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=ZERO,
        help_text="Manual correction (may be negative).",
    )
    adjustment_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-year", "leave_type__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "employee", "leave_type", "year"],
                name="uniq_leavebalance_per_employee_type_year",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "employee", "year"]),
            models.Index(fields=["tenant", "leave_type", "year"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} — {self.leave_type.code} {self.year}: {self.available_days}"

    @property
    def entitlement_total(self) -> Decimal:
        """Total days an employee is entitled to before any are used."""
        return self.entitled_days + self.carried_forward_days + self.adjustment_days

    @property
    def available_days(self) -> Decimal:
        """Days still bookable — entitlement minus taken and pending."""
        return self.entitlement_total - self.taken_days - self.pending_days


class LeaveRequest(TenantOwnedModel):
    """An application for time off, moving through a configurable approval chain.

    Lifecycle: ``draft`` -> ``pending`` -> ``approved`` / ``rejected``.
    ``cancelled`` / ``withdrawn`` are terminal owner-initiated exits.
    ``total_days`` is the working-day cost computed by ``services``.
    """

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="requests"
    )

    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    start_portion = models.CharField(
        max_length=12, choices=DayPortion.choices, default=DayPortion.FULL
    )
    end_portion = models.CharField(
        max_length=12, choices=DayPortion.choices, default=DayPortion.FULL
    )
    total_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=ZERO,
        help_text="Working-day cost of the request (computed).",
    )

    reason = models.TextField(blank=True)
    contact_during_leave = models.CharField(max_length=160, blank=True)
    supporting_document = models.FileField(
        upload_to="leave-documents/", null=True, blank=True
    )

    status = models.CharField(
        max_length=12,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.DRAFT,
        db_index=True,
    )
    current_stage = models.CharField(
        max_length=10,
        choices=ApprovalStage.choices,
        blank=True,
        help_text="Approval stage currently awaiting a decision.",
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)

    # The balance the request draws on (set when the year is known).
    balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "status", "start_date"]),
            models.Index(fields=["tenant", "leave_type", "start_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} — {self.leave_type.code} {self.start_date}→{self.end_date}"

    @property
    def is_editable(self) -> bool:
        """Only drafts may be edited or deleted by the applicant."""
        return self.status == LeaveRequestStatus.DRAFT

    @property
    def is_active(self) -> bool:
        """True while the request reserves or consumes balance."""
        return self.status in {
            LeaveRequestStatus.PENDING,
            LeaveRequestStatus.APPROVED,
        }


class LeaveApproval(TenantOwnedModel):
    """One stage of a leave request's approval chain.

    Stages are created when a request is submitted, in ``sequence`` order.
    The default chain is manager -> HR; an extra stage is appended when
    the leave type enables ``extra_approval_stage``.
    """

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="approvals"
    )
    stage = models.CharField(max_length=10, choices=ApprovalStage.choices)
    sequence = models.PositiveSmallIntegerField(
        help_text="Order within the chain — lower decides first."
    )
    label = models.CharField(max_length=80, blank=True)
    status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING
    )

    decided_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["leave_request", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["leave_request", "sequence"],
                name="uniq_leaveapproval_sequence_per_request",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "stage", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_stage_display()} — {self.get_status_display()}"
