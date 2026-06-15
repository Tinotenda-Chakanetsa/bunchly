"""Learning & development models (spec §9.19).

``TrainingCourse``  a tenant-configurable training catalogue entry.
``TrainingRecord``  an employee's assignment / completion of a course,
                    including certification tracking.
``Skill``           a tenant skills catalogue.
``EmployeeSkill``   a skill held by an employee, at a proficiency level.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TenantOwnedModel

from .enums import (
    CourseCategory,
    DeliveryMode,
    RecordStatus,
    SkillProficiency,
)


class TrainingCourse(TenantOwnedModel):
    """A configurable training course (spec §9.19)."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=40)
    category = models.CharField(
        max_length=16, choices=CourseCategory.choices, default=CourseCategory.OTHER
    )
    description = models.TextField(blank=True)
    delivery_mode = models.CharField(
        max_length=12, choices=DeliveryMode.choices, default=DeliveryMode.ONLINE
    )
    provider = models.CharField(max_length=160, blank=True)
    duration_hours = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text="Nominal course duration in hours.",
    )
    is_compliance = models.BooleanField(
        default=False, help_text="A mandatory compliance course."
    )
    provides_certification = models.BooleanField(default=False)
    certification_validity_months = models.PositiveSmallIntegerField(
        default=0, help_text="Months a certification stays valid; 0 = no expiry.",
    )
    pass_score = models.PositiveSmallIntegerField(
        default=0, help_text="Minimum score to pass; 0 = no score required.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"], name="uniq_trainingcourse_code_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active", "is_compliance"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class TrainingRecord(TenantOwnedModel):
    """An employee's assignment / completion of a training course."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="training_records"
    )
    course = models.ForeignKey(
        TrainingCourse, on_delete=models.PROTECT, related_name="records"
    )
    status = models.CharField(
        max_length=12,
        choices=RecordStatus.choices,
        default=RecordStatus.ASSIGNED,
        db_index=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    assigned_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    started_at = models.DateField(null=True, blank=True)
    completed_date = models.DateField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    passed = models.BooleanField(default=False)

    # Certification tracking.
    certificate_number = models.CharField(max_length=80, blank=True)
    certificate_expiry_date = models.DateField(null=True, blank=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "employee", "status"]),
            models.Index(fields=["tenant", "course", "status"]),
            models.Index(fields=["tenant", "certificate_expiry_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee} — {self.course.name} ({self.get_status_display()})"


class Skill(TenantOwnedModel):
    """A tenant skills-catalogue entry (spec §9.19 — skills tracking)."""

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["category", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name"], name="uniq_skill_name_per_tenant"
            )
        ]
        indexes = [models.Index(fields=["tenant", "is_active"])]

    def __str__(self) -> str:
        return self.name


class EmployeeSkill(TenantOwnedModel):
    """A skill held by an employee, at a proficiency level."""

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="skills"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.CASCADE, related_name="employee_skills"
    )
    proficiency = models.CharField(
        max_length=14,
        choices=SkillProficiency.choices,
        default=SkillProficiency.BEGINNER,
    )
    # Optionally evidenced by a completed training record.
    training_record = models.ForeignKey(
        TrainingRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skills_evidenced",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["skill__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "employee", "skill"],
                name="uniq_employeeskill_per_employee",
            )
        ]
        indexes = [models.Index(fields=["tenant", "employee"])]

    def __str__(self) -> str:
        return f"{self.employee} — {self.skill} ({self.get_proficiency_display()})"
