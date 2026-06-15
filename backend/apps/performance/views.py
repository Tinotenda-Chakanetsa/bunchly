"""Viewsets for the performance-management module (spec §9.18).

Visibility scoping (as in the leave / employees modules):
- ``performance.manage`` -> sees all performance data in the tenant.
- ``performance.review`` -> sees own records + those of direct reports.
- otherwise              -> sees only their own records.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .models import (
    DevelopmentPlan,
    Goal,
    PerformanceReview,
    ReviewCycle,
    ReviewItem,
)
from .serializers import (
    DevelopmentPlanSerializer,
    GoalProgressSerializer,
    GoalSerializer,
    PerformanceReviewListSerializer,
    PerformanceReviewSerializer,
    ReviewCycleSerializer,
    ReviewItemSerializer,
)


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _has(request, code: str) -> bool:
    return request.user.has_perm_code(code, getattr(request, "tenant", None))


def _visible_employee_ids(request) -> list | None:
    """Employee ids the caller may see, or ``None`` for unrestricted."""
    if _has(request, "performance.manage"):
        return None
    own = _own_employee(request)
    if own is None:
        return []
    ids = [own.id]
    if _has(request, "performance.review"):
        tenant = getattr(request, "tenant", None)
        ids += list(
            Employee.objects.filter(tenant=tenant, line_manager=own)
            .values_list("id", flat=True)
        )
    return ids


class _ScopedViewSet(TenantModelViewSet):
    """Base viewset scoping a tenant queryset by the ``employee`` field."""

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = _visible_employee_ids(self.request)
        if visible is None:
            return queryset
        return queryset.filter(employee_id__in=visible)

    def _assert_can_edit_for(self, employee) -> None:
        """Allow managers / HR, or the employee acting on their own record."""
        if _has(self.request, "performance.manage") or _has(
            self.request, "performance.review"
        ):
            visible = _visible_employee_ids(self.request)
            if visible is None or employee.id in visible:
                return
        own = _own_employee(self.request)
        if own is None or employee.id != own.id:
            raise PermissionDenied(
                "You may only manage performance records for yourself or "
                "your direct reports."
            )


class ReviewCycleViewSet(TenantModelViewSet):
    """Performance review cycles — configured by HR."""

    queryset = ReviewCycle.objects.all()
    serializer_class = ReviewCycleSerializer
    permission_required = {
        "create": "performance.manage",
        "update": "performance.manage",
        "partial_update": "performance.manage",
        "destroy": "performance.manage",
    }
    search_fields = ["name"]
    filterset_fields = ["status"]
    ordering_fields = ["period_start", "created_at"]


class GoalViewSet(_ScopedViewSet):
    """Employee goals / KPIs / OKRs."""

    queryset = Goal.objects.select_related("employee", "cycle")
    serializer_class = GoalSerializer
    filterset_fields = ["employee", "cycle", "category", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "due_date"]

    def perform_create(self, serializer):
        employee = serializer.validated_data.get("employee")
        if employee is None:
            raise ValidationError({"employee": "An employee is required."})
        self._assert_can_edit_for(employee)
        serializer.save(tenant=self.get_tenant())

    def perform_update(self, serializer):
        self._assert_can_edit_for(serializer.instance.employee)
        serializer.save()

    @action(detail=True, methods=["post"])
    def progress(self, request, pk=None):
        """Update a goal's progress; its status follows the progress."""
        goal = self.get_object()
        self._assert_can_edit_for(goal.employee)
        payload = GoalProgressSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.apply_goal_progress(goal, payload.validated_data["progress"])
        return Response(GoalSerializer(goal, context={"request": request}).data)


class PerformanceReviewViewSet(_ScopedViewSet):
    """Performance reviews — manager, self and peer."""

    queryset = PerformanceReview.objects.select_related(
        "employee", "cycle", "reviewer"
    ).prefetch_related("items")
    permission_required = {"create": "performance.review"}
    filterset_fields = ["cycle", "employee", "review_type", "status"]
    ordering_fields = ["created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceReviewListSerializer
        return PerformanceReviewSerializer

    def perform_create(self, serializer):
        employee = serializer.validated_data.get("employee")
        if employee is None:
            raise ValidationError({"employee": "An employee is required."})
        self._assert_can_edit_for(employee)
        review = serializer.save(
            tenant=self.get_tenant(), reviewer=self.request.user
        )
        record_audit(
            AuditAction.CREATE, "performance.review", entity_id=review.pk,
            description=f"Created {review.get_review_type_display()} for {employee}",
        )

    def perform_update(self, serializer):
        services.assert_review_editable(serializer.instance)
        if serializer.instance.reviewer_id != self.request.user.id and not _has(
            self.request, "performance.manage"
        ):
            raise PermissionDenied("Only the reviewer may edit this review.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft review for the employee to acknowledge."""
        review = self.get_object()
        if review.reviewer_id != request.user.id and not _has(
            request, "performance.manage"
        ):
            raise PermissionDenied("Only the reviewer may submit this review.")
        services.submit_review(review)
        record_audit(
            AuditAction.SUBMIT, "performance.review", entity_id=review.pk,
            description=f"Submitted performance review for {review.employee}",
        )
        return Response(
            PerformanceReviewSerializer(review, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """The employee acknowledges a submitted review."""
        review = self.get_object()
        own = _own_employee(request)
        if own is None or review.employee_id != own.id:
            raise PermissionDenied(
                "Only the reviewed employee may acknowledge this review."
            )
        services.acknowledge_review(review, user=request.user)
        return Response(
            PerformanceReviewSerializer(review, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """HR closes out an acknowledged review."""
        if not _has(request, "performance.manage"):
            raise PermissionDenied("Completing a review requires performance.manage.")
        review = self.get_object()
        services.complete_review(review)
        return Response(
            PerformanceReviewSerializer(review, context={"request": request}).data
        )

    @action(detail=False)
    def history(self, request):
        """Performance history for an employee (``?employee=<id>``, or own)."""
        employee_id = request.query_params.get("employee")
        if employee_id:
            employee = Employee.objects.filter(
                tenant=getattr(request, "tenant", None), pk=employee_id
            ).first()
            if employee is None:
                raise NotFound("Employee not found.")
            visible = _visible_employee_ids(request)
            if visible is not None and employee.id not in visible:
                raise PermissionDenied("You may not view this employee's history.")
        else:
            employee = _own_employee(request)
            if employee is None:
                raise NotFound("You do not have an employee profile.")
        return Response(services.performance_history(employee))


class ReviewItemViewSet(TenantModelViewSet):
    """Per-competency rating lines within a review."""

    queryset = ReviewItem.objects.select_related("review", "review__employee")
    serializer_class = ReviewItemSerializer
    permission_required = {
        "create": "performance.review",
        "update": "performance.review",
        "partial_update": "performance.review",
        "destroy": "performance.review",
    }
    filterset_fields = ["review"]
    ordering_fields = ["sequence"]

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = _visible_employee_ids(self.request)
        if visible is None:
            return queryset
        return queryset.filter(review__employee_id__in=visible)

    def perform_create(self, serializer):
        review = serializer.validated_data["review"]
        services.assert_review_editable(review)
        serializer.save(tenant=self.get_tenant())

    def perform_update(self, serializer):
        services.assert_review_editable(serializer.instance.review)
        serializer.save()


class DevelopmentPlanViewSet(_ScopedViewSet):
    """Development plans for employees."""

    queryset = DevelopmentPlan.objects.select_related("employee", "cycle")
    serializer_class = DevelopmentPlanSerializer
    filterset_fields = ["employee", "cycle", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "target_date"]

    def perform_create(self, serializer):
        employee = serializer.validated_data.get("employee")
        if employee is None:
            raise ValidationError({"employee": "An employee is required."})
        self._assert_can_edit_for(employee)
        serializer.save(tenant=self.get_tenant())

    def perform_update(self, serializer):
        self._assert_can_edit_for(serializer.instance.employee)
        serializer.save()
