"""Serializers for the learning & development module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import EmployeeSkill, Skill, TrainingCourse, TrainingRecord


class TrainingCourseSerializer(TenantScopedModelSerializer):
    """A training-catalogue course."""

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    delivery_mode_display = serializers.CharField(
        source="get_delivery_mode_display", read_only=True
    )

    class Meta:
        model = TrainingCourse
        fields = [
            "id", "name", "code", "category", "category_display",
            "description", "delivery_mode", "delivery_mode_display",
            "provider", "duration_hours", "is_compliance",
            "provides_certification", "certification_validity_months",
            "pass_score", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_code(self, value):
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None)
        qs = TrainingCourse.all_objects.filter(tenant=tenant, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A course with this code already exists."
            )
        return value


class TrainingRecordSerializer(TenantScopedModelSerializer):
    """An employee's training record for a course."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TrainingRecord
        fields = [
            "id", "employee", "employee_name", "course", "course_name",
            "course_code", "status", "status_display", "assigned_by",
            "assigned_date", "due_date", "started_at", "completed_date",
            "score", "passed", "certificate_number",
            "certificate_expiry_date", "notes", "created_at", "updated_at",
        ]
        # Status / completion fields are owned by the service actions.
        read_only_fields = [
            "status", "assigned_by", "assigned_date", "started_at",
            "completed_date", "score", "passed", "certificate_number",
            "certificate_expiry_date", "created_at", "updated_at",
        ]


class TrainingRecordListSerializer(serializers.ModelSerializer):
    """Lightweight training-record row."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TrainingRecord
        fields = [
            "id", "employee", "employee_name", "course", "course_name",
            "status", "status_display", "due_date", "completed_date",
            "certificate_expiry_date", "created_at",
        ]


class SkillSerializer(TenantScopedModelSerializer):
    """A skills-catalogue entry."""

    class Meta:
        model = Skill
        fields = [
            "id", "name", "category", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class EmployeeSkillSerializer(TenantScopedModelSerializer):
    """A skill held by an employee."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    proficiency_display = serializers.CharField(
        source="get_proficiency_display", read_only=True
    )

    class Meta:
        model = EmployeeSkill
        fields = [
            "id", "employee", "employee_name", "skill", "skill_name",
            "proficiency", "proficiency_display", "training_record", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AssignCourseSerializer(serializers.Serializer):
    """Input for assigning a course to one or more employees."""

    course = serializers.UUIDField()
    employees = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False
    )
    due_date = serializers.DateField(required=False, allow_null=True)


class CompleteRecordSerializer(serializers.Serializer):
    """Input for completing a training record."""

    score = serializers.IntegerField(
        required=False, allow_null=True, min_value=0, max_value=100
    )
    certificate_number = serializers.CharField(
        required=False, allow_blank=True, max_length=80, default=""
    )
    completed_date = serializers.DateField(required=False, allow_null=True)
