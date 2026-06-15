"""Serializers for the organisation-structure module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    CostCentre,
    Department,
    Grade,
    JobTitle,
    Location,
    Position,
    Team,
)


class CostCentreSerializer(TenantScopedModelSerializer):
    class Meta:
        model = CostCentre
        fields = ["id", "name", "code", "description", "is_active", "created_at"]


class LocationSerializer(TenantScopedModelSerializer):
    class Meta:
        model = Location
        fields = [
            "id", "name", "code", "address_line1", "address_line2", "city",
            "state", "postal_code", "country", "timezone", "is_active",
            "created_at",
        ]


class GradeSerializer(TenantScopedModelSerializer):
    class Meta:
        model = Grade
        fields = ["id", "name", "code", "level", "description", "is_active", "created_at"]


class DepartmentSerializer(TenantScopedModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    cost_centre_name = serializers.CharField(
        source="cost_centre.name", read_only=True, default=None
    )
    location_name = serializers.CharField(
        source="location.name", read_only=True, default=None
    )
    head_name = serializers.CharField(
        source="head.full_name", read_only=True, default=None
    )
    employee_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Department
        fields = [
            "id", "name", "code", "description", "parent", "parent_name",
            "cost_centre", "cost_centre_name", "location", "location_name",
            "head", "head_name", "is_active", "employee_count", "created_at",
        ]

    def validate_parent(self, value):
        # A department cannot be its own parent (deeper cycles are guarded
        # by the tree-building logic on read).
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("A department cannot be its own parent.")
        return value


class TeamSerializer(TenantScopedModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Team
        fields = [
            "id", "name", "code", "department", "department_name",
            "description", "is_active", "created_at",
        ]


class JobTitleSerializer(TenantScopedModelSerializer):
    class Meta:
        model = JobTitle
        fields = ["id", "name", "code", "description", "is_active", "created_at"]


class PositionSerializer(TenantScopedModelSerializer):
    job_title_name = serializers.CharField(source="job_title.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    grade_name = serializers.CharField(source="grade.name", read_only=True, default=None)
    location_name = serializers.CharField(
        source="location.name", read_only=True, default=None
    )

    class Meta:
        model = Position
        fields = [
            "id", "name", "job_title", "job_title_name", "department",
            "department_name", "grade", "grade_name", "location",
            "location_name", "reports_to", "headcount", "is_vacant",
            "is_active", "created_at",
        ]

    def validate_reports_to(self, value):
        if value and self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("A position cannot report to itself.")
        return value
