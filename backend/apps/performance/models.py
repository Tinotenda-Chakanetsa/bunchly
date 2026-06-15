"""Performance-management models (spec §9.18).

``ReviewCycle``        a configurable review period.
``Goal``               an employee objective / KPI / OKR.
``PerformanceReview``  a manager review, self-assessment or peer review.
``ReviewItem``         a per-competency rating line within a review.
``DevelopmentPlan``    a development plan for an employee.

Manager-vs-employee visibility is enforced by the viewset querysets, as
in the leave / employees modules.
"""
from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    DevelopmentPlanStatus,
    GoalCategory,
    GoalStatus,
    ReviewCycleStatus,
    ReviewStatus,
    ReviewType,
)

ZERO = Decimal("0.00")


class ReviewCycle(TenantOwnedModel):
    """A configurable performance review period (spec §9.18)."""

    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=ReviewCycleStatus.choices,
        default=ReviewCycleStatus.DRAFT,
        db_index=True,
    )

    class Meta:
        ordering = ["-period_start"]
        indexes = [models.Index(fields=["tenant", "status"])]

    def __str__(self) -> str:
        return self.name


class Goal(TenantOwnedModel):
    """An employee objective, KPI or OKR (spec §9.18)."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="goals"
    )
    cycle = models.ForeignKey(
        ReviewCycle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goals",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=12, choices=GoalCategory.choices, default=GoalCategory.OBJECTIVE
    )
    weight = models.DecimalField(
        max_digits=5, decimal_places=2, default=ZERO,
        help_text="Relative weighting of the goal (e.g. percentage).",
    )
    target = models.CharField(
        max_length=255, blank=True, help_text="Measurable target / success metric."
    )
    progress = models.PositiveSmallIntegerField(
        default=0, help_text="Percent complete, 0-100."
    )
    status = models.CharField(
        max_length=20,
        choices=GoalStatus.choices,
        default=GoalStatus.NOT_STARTED,
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "cycle"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.employee}"


class PerformanceReview(TenantOwnedModel):
    """A manager review, self-assessment or peer review (spec §9.18)."""

    cycle = models.ForeignKey(
        ReviewCycle, on_delete=models.CASCADE, related_name="reviews"
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="performance_reviews",
    )
    review_type = models.CharField(
        max_length=10, choices=ReviewType.choices, default=ReviewType.MANAGER
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="performance_reviews_given",
    )
    status = models.CharField(
        max_length=12,
        choices=ReviewStatus.choices,
        default=ReviewStatus.DRAFT,
        db_index=True,
    )
    overall_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Overall rating, 1-5."
    )
    summary = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "cycle", "employee", "review_type", "reviewer"],
                name="uniq_review_per_cycle_employee_type_reviewer",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "cycle", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_review_type_display()} — {self.employee} ({self.cycle})"


class ReviewItem(TenantOwnedModel):
    """A per-competency rating line within a performance review."""

    review = models.ForeignKey(
        PerformanceReview, on_delete=models.CASCADE, related_name="items"
    )
    competency = models.CharField(max_length=160)
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Rating for this competency, 1-5."
    )
    comment = models.TextField(blank=True)
    sequence = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["review", "sequence"]
        indexes = [models.Index(fields=["tenant", "review"])]

    def __str__(self) -> str:
        return f"{self.competency} ({self.rating})"


class DevelopmentPlan(TenantOwnedModel):
    """A development plan for an employee (spec §9.18)."""

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="development_plans",
    )
    cycle = models.ForeignKey(
        ReviewCycle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="development_plans",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    actions = models.TextField(
        blank=True, help_text="Planned development actions."
    )
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=DevelopmentPlanStatus.choices,
        default=DevelopmentPlanStatus.OPEN,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "employee", "status"])]

    def __str__(self) -> str:
        return f"{self.title} — {self.employee}"
