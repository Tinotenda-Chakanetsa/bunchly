"""Serializers for the performance-management module."""
from __future__ import annotations

from rest_framework import serializers

from apps.common.serializers import TenantScopedModelSerializer

from .models import (
    DevelopmentPlan,
    Goal,
    PerformanceReview,
    ReviewCycle,
    ReviewItem,
)


class ReviewCycleSerializer(TenantScopedModelSerializer):
    """A performance review period."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    review_count = serializers.IntegerField(source="reviews.count", read_only=True)

    class Meta:
        model = ReviewCycle
        fields = [
            "id", "name", "description", "period_start", "period_end",
            "status", "status_display", "review_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("period_start", getattr(self.instance, "period_start", None))
        end = attrs.get("period_end", getattr(self.instance, "period_end", None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {"period_end": "Period end cannot be before the start."}
            )
        return attrs


class GoalSerializer(TenantScopedModelSerializer):
    """An employee goal / KPI / OKR."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Goal
        fields = [
            "id", "employee", "employee_name", "cycle", "title", "description",
            "category", "category_display", "weight", "target", "progress",
            "status", "status_display", "due_date", "created_at", "updated_at",
        ]
        # Progress / status move together via the service action.
        read_only_fields = ["progress", "status", "created_at", "updated_at"]


class ReviewItemSerializer(TenantScopedModelSerializer):
    """A per-competency rating line within a review."""

    class Meta:
        model = ReviewItem
        fields = [
            "id", "review", "competency", "rating", "comment", "sequence",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class PerformanceReviewSerializer(TenantScopedModelSerializer):
    """A performance review with its competency items."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    cycle_name = serializers.CharField(source="cycle.name", read_only=True)
    review_type_display = serializers.CharField(
        source="get_review_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    reviewer_name = serializers.CharField(
        source="reviewer.full_name", read_only=True, default=None
    )
    items = ReviewItemSerializer(many=True, read_only=True)

    class Meta:
        model = PerformanceReview
        fields = [
            "id", "cycle", "cycle_name", "employee", "employee_name",
            "review_type", "review_type_display", "reviewer", "reviewer_name",
            "status", "status_display", "overall_rating", "summary",
            "strengths", "areas_for_improvement", "submitted_at",
            "acknowledged_at", "acknowledged_by", "items",
            "created_at", "updated_at",
        ]
        # Status / timestamps are owned by the lifecycle actions.
        read_only_fields = [
            "reviewer", "status", "submitted_at", "acknowledged_at",
            "acknowledged_by", "created_at", "updated_at",
        ]


class PerformanceReviewListSerializer(serializers.ModelSerializer):
    """Lightweight review row."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    cycle_name = serializers.CharField(source="cycle.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PerformanceReview
        fields = [
            "id", "cycle", "cycle_name", "employee", "employee_name",
            "review_type", "status", "status_display", "overall_rating",
            "created_at",
        ]


class DevelopmentPlanSerializer(TenantScopedModelSerializer):
    """A development plan for an employee."""

    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DevelopmentPlan
        fields = [
            "id", "employee", "employee_name", "cycle", "title", "description",
            "actions", "target_date", "status", "status_display",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class GoalProgressSerializer(serializers.Serializer):
    """Input for updating a goal's progress."""

    progress = serializers.IntegerField(min_value=0, max_value=100)
