"""Viewsets for the onboarding / offboarding module (spec §9.6, §9.7).

Checklist templates are configured by ``onboarding.manage`` holders.
Running programmes and tasks are visible to managers and HR; an
employee sees their own programmes and any task assigned to them.
"""
from __future__ import annotations

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasModulePermission, HasTenant
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .enums import ProgrammeStatus, ProgrammeType, TaskStatus
from .models import (
    ChecklistTaskTemplate,
    ChecklistTemplate,
    OnboardingProgramme,
    OnboardingTask,
)
from .serializers import (
    ChecklistTaskTemplateSerializer,
    ChecklistTemplateSerializer,
    OnboardingProgrammeListSerializer,
    OnboardingProgrammeSerializer,
    OnboardingTaskSerializer,
    StartProgrammeSerializer,
    TaskStatusSerializer,
)

_WRITE = {
    "create": "onboarding.manage",
    "update": "onboarding.manage",
    "partial_update": "onboarding.manage",
    "destroy": "onboarding.manage",
}


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


class ChecklistTemplateViewSet(TenantModelViewSet):
    """Configurable onboarding / offboarding checklist templates."""

    queryset = ChecklistTemplate.objects.prefetch_related("task_templates")
    serializer_class = ChecklistTemplateSerializer
    permission_required = {"default": "onboarding.view", **_WRITE}
    search_fields = ["name"]
    filterset_fields = ["programme_type", "is_active", "is_default"]


class ChecklistTaskTemplateViewSet(TenantModelViewSet):
    """Task lines within checklist templates."""

    queryset = ChecklistTaskTemplate.objects.select_related("template")
    serializer_class = ChecklistTaskTemplateSerializer
    permission_required = {"default": "onboarding.view", **_WRITE}
    filterset_fields = ["template", "owner_role"]
    ordering_fields = ["sequence", "created_at"]


class OnboardingProgrammeViewSet(TenantModelViewSet):
    """Running onboarding / offboarding programmes."""

    queryset = OnboardingProgramme.objects.select_related(
        "employee", "template"
    ).prefetch_related("tasks", "tasks__assigned_to")
    permission_required = {
        "create": "onboarding.manage",
        "update": "onboarding.manage",
        "partial_update": "onboarding.manage",
        "destroy": "onboarding.manage",
        "cancel": "onboarding.manage",
    }
    filterset_fields = ["employee", "programme_type", "status"]
    ordering_fields = ["created_at", "start_date"]

    def get_serializer_class(self):
        return (
            OnboardingProgrammeListSerializer
            if self.action == "list"
            else OnboardingProgrammeSerializer
        )

    def _can_manage(self) -> bool:
        return self.request.user.has_perm_code(
            "onboarding.manage", getattr(self.request, "tenant", None)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self._can_manage():
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    def create(self, request, *args, **kwargs):
        payload = StartProgrammeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = getattr(request, "tenant", None)
        data = payload.validated_data

        employee = Employee.objects.filter(
            tenant=tenant, pk=data["employee"]
        ).first()
        if employee is None:
            raise ValidationError({"employee": "Employee not found."})
        template = None
        if data.get("template"):
            template = ChecklistTemplate.objects.filter(
                tenant=tenant, pk=data["template"]
            ).first()
            if template is None:
                raise ValidationError({"template": "Checklist template not found."})

        programme = services.start_programme(
            tenant=tenant,
            employee=employee,
            programme_type=data["programme_type"],
            template=template,
            start_date=data.get("start_date"),
            notes=data.get("notes", ""),
        )
        record_audit(
            AuditAction.CREATE, "onboarding.programme", entity_id=programme.pk,
            description=f"Started {programme.get_programme_type_display()} "
                        f"for {employee}",
        )
        return Response(
            OnboardingProgrammeSerializer(
                programme, context={"request": request}
            ).data,
            status=201,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a programme that has not completed."""
        programme = self.get_object()
        services.cancel_programme(programme)
        record_audit(
            AuditAction.UPDATE, "onboarding.programme", entity_id=programme.pk,
            description=f"Cancelled {programme.get_programme_type_display()} "
                        f"for {programme.employee}",
        )
        return Response(
            OnboardingProgrammeSerializer(
                programme, context={"request": request}
            ).data
        )

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        """Task-completion statistics for a programme."""
        programme = self.get_object()
        return Response(services.programme_progress(programme))


class OnboardingTaskViewSet(TenantModelViewSet):
    """Tasks within running programmes."""

    queryset = OnboardingTask.objects.select_related(
        "programme", "programme__employee", "assigned_to"
    )
    serializer_class = OnboardingTaskSerializer
    permission_required = {
        "create": "onboarding.manage",
        "update": "onboarding.manage",
        "partial_update": "onboarding.manage",
        "destroy": "onboarding.manage",
    }
    filterset_fields = ["programme", "owner_role", "status", "assigned_to"]
    ordering_fields = ["due_date", "sequence", "created_at"]

    def _can_manage(self) -> bool:
        return self.request.user.has_perm_code(
            "onboarding.manage", getattr(self.request, "tenant", None)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self._can_manage():
            return queryset
        own = _own_employee(self.request)
        if own is None:
            return queryset.none()
        # An employee sees tasks on their own programme or assigned to them.
        return queryset.filter(programme__employee=own) | queryset.filter(
            assigned_to=own
        )

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        """Update a task's status (the task owner, assignee, or HR)."""
        task = self.get_object()
        if not self._can_manage():
            own = _own_employee(request)
            is_participant = own is not None and (
                task.programme.employee_id == own.id
                or task.assigned_to_id == own.id
            )
            if not is_participant:
                raise PermissionDenied(
                    "You may only update tasks on your own programme or "
                    "assigned to you."
                )
        payload = TaskStatusSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.set_task_status(
            task,
            payload.validated_data["status"],
            user=request.user,
            notes=payload.validated_data.get("notes", ""),
        )
        return Response(
            OnboardingTaskSerializer(task, context={"request": request}).data
        )

    @action(detail=False, url_path="my-tasks")
    def my_tasks(self, request):
        """Open tasks assigned to the requesting user."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            self.get_queryset()
            .filter(assigned_to=own)
            .exclude(status=TaskStatus.COMPLETED)
        )
        page = self.paginate_queryset(queryset)
        serializer = OnboardingTaskSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class OnboardingDashboardView(APIView):
    """Onboarding / offboarding progress dashboard (spec §9.6)."""

    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "onboarding.view"

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        programmes = OnboardingProgramme.objects.filter(tenant=tenant)
        active = programmes.filter(status=ProgrammeStatus.IN_PROGRESS)
        open_tasks = OnboardingTask.objects.filter(
            tenant=tenant,
            programme__status=ProgrammeStatus.IN_PROGRESS,
        ).exclude(status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED])
        overdue = open_tasks.filter(
            due_date__lt=timezone.now().date()
        ).count()

        return Response({
            "active_onboarding": active.filter(
                programme_type=ProgrammeType.ONBOARDING
            ).count(),
            "active_offboarding": active.filter(
                programme_type=ProgrammeType.OFFBOARDING
            ).count(),
            "completed_programmes": programmes.filter(
                status=ProgrammeStatus.COMPLETED
            ).count(),
            "open_tasks": open_tasks.count(),
            "overdue_tasks": overdue,
        })
