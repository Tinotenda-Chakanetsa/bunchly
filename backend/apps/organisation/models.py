"""Organisation-structure models (spec §9.2).

Departments, teams, locations, job titles, positions, grades and cost
centres. All are tenant-owned, soft-deletable and uniquely coded within
their tenant. Employee-to-position and manager hierarchy links live in
the ``employees`` module; ``Position.reports_to`` provides structural
reporting lines independent of who currently fills a seat.
"""
from __future__ import annotations

from django.db import models

from apps.common.models import TenantOwnedModel


class CostCentre(TenantOwnedModel):
    """A budget/cost allocation bucket departments roll up to."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_costcentre_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Location(TenantOwnedModel):
    """A physical work location / office."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    postal_code = models.CharField(max_length=40, blank=True)
    country = models.CharField(max_length=80, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_location_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return self.name


class Grade(TenantOwnedModel):
    """A job grade / band. Salary ranges are intentionally NOT stored here —
    compensation data lives in the restricted compensation module."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    level = models.PositiveIntegerField(
        default=1, help_text="Numeric seniority — higher is more senior."
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["level", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_grade_code_per_tenant"
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Department(TenantOwnedModel):
    """An organisational department. Self-referencing for sub-departments."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    cost_centre = models.ForeignKey(
        CostCentre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departments",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="departments",
    )
    # The employee who heads the department (org-chart leadership link).
    head = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_department_code_per_tenant"
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
            models.Index(fields=["tenant", "parent"]),
        ]

    def __str__(self) -> str:
        return self.name


class Team(TenantOwnedModel):
    """A team within a department."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="teams"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_team_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "department"])]

    def __str__(self) -> str:
        return self.name


class JobTitle(TenantOwnedModel):
    """A reusable job title (e.g. 'Software Engineer')."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_jobtitle_code_per_tenant"
            )
        ]

    def __str__(self) -> str:
        return self.name


class Position(TenantOwnedModel):
    """A budgeted seat in the organisation — a job title within a department.

    ``reports_to`` defines the structural reporting line. ``headcount`` is
    the budgeted number of employees for this seat; ``is_vacant`` supports
    vacant-position and headcount-planning reports (spec §9.2).
    """

    name = models.CharField(
        max_length=200, blank=True, help_text="Optional label; defaults to the job title."
    )
    job_title = models.ForeignKey(
        JobTitle, on_delete=models.PROTECT, related_name="positions"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="positions"
    )
    grade = models.ForeignKey(
        Grade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
    )
    reports_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_positions",
    )
    headcount = models.PositiveIntegerField(default=1)
    is_vacant = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["department__name", "job_title__name"]
        indexes = [
            models.Index(fields=["tenant", "department"]),
            models.Index(fields=["tenant", "is_vacant"]),
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name or self.job_title.name
