"""Viewsets for the learning & development module (spec §9.19).

Courses and the skills catalogue are configured by ``learning.manage``
holders. Training records are scoped: ``learning.manage`` sees every
record; everyone else sees only their own.
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
from .models import EmployeeSkill, Skill, TrainingCourse, TrainingRecord
from .serializers import (
    AssignCourseSerializer,
    CompleteRecordSerializer,
    EmployeeSkillSerializer,
    SkillSerializer,
    TrainingCourseSerializer,
    TrainingRecordListSerializer,
    TrainingRecordSerializer,
)

_WRITE = {
    "create": "learning.manage",
    "update": "learning.manage",
    "partial_update": "learning.manage",
    "destroy": "learning.manage",
}


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _can_manage(request) -> bool:
    return request.user.has_perm_code(
        "learning.manage", getattr(request, "tenant", None)
    )


class TrainingCourseViewSet(TenantModelViewSet):
    """The training-course catalogue."""

    queryset = TrainingCourse.objects.all()
    serializer_class = TrainingCourseSerializer
    permission_required = {"default": "learning.view", **_WRITE}
    search_fields = ["name", "code", "provider"]
    filterset_fields = ["category", "delivery_mode", "is_compliance", "is_active"]
    ordering_fields = ["name", "category", "created_at"]


class SkillViewSet(TenantModelViewSet):
    """The tenant skills catalogue."""

    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_required = {"default": "learning.view", **_WRITE}
    search_fields = ["name", "category"]
    filterset_fields = ["category", "is_active"]


class TrainingRecordViewSet(TenantModelViewSet):
    """Employee training records — assignment, completion, certification."""

    queryset = TrainingRecord.objects.select_related(
        "employee", "course", "assigned_by"
    )
    permission_required = {
        "create": "learning.manage",
        "update": "learning.manage",
        "partial_update": "learning.manage",
        "destroy": "learning.manage",
        "assign": "learning.manage",
        "expiring_certifications": "learning.view",
    }
    filterset_fields = ["employee", "course", "status"]
    ordering_fields = ["created_at", "due_date", "completed_date"]

    def get_serializer_class(self):
        return (
            TrainingRecordListSerializer
            if self.action == "list"
            else TrainingRecordSerializer
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        if _can_manage(self.request):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    def _require_own_or_manage(self, record):
        if _can_manage(self.request):
            return
        own = _own_employee(self.request)
        if own is None or record.employee_id != own.id:
            raise PermissionDenied("You may only act on your own training records.")

    # --- assignment -------------------------------------------------------
    @action(detail=False, methods=["post"])
    def assign(self, request):
        """Assign a course to one or more employees."""
        payload = AssignCourseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = getattr(request, "tenant", None)
        course = TrainingCourse.objects.filter(
            tenant=tenant, pk=payload.validated_data["course"]
        ).first()
        if course is None:
            raise ValidationError({"course": "Course not found."})

        assigned, skipped = [], []
        for employee_id in payload.validated_data["employees"]:
            employee = Employee.objects.filter(
                tenant=tenant, pk=employee_id
            ).first()
            if employee is None:
                skipped.append({"employee": str(employee_id), "reason": "not found"})
                continue
            try:
                record = services.assign_course(
                    tenant=tenant, employee=employee, course=course,
                    assigned_by=request.user,
                    due_date=payload.validated_data.get("due_date"),
                )
                assigned.append(str(record.pk))
            except ValidationError as exc:
                skipped.append({"employee": str(employee_id), "reason": str(exc.detail)})
        record_audit(
            AuditAction.CREATE, "learning.training_record", entity_id=course.pk,
            description=f"Assigned '{course.name}' to {len(assigned)} employee(s)",
        )
        return Response({"assigned": assigned, "skipped": skipped}, status=201)

    # --- record lifecycle -------------------------------------------------
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Mark a training record as started."""
        record = self.get_object()
        self._require_own_or_manage(record)
        services.start_record(record)
        return Response(
            TrainingRecordSerializer(record, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete a training record (score / certification applied)."""
        record = self.get_object()
        self._require_own_or_manage(record)
        payload = CompleteRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.complete_record(
            record,
            score=payload.validated_data.get("score"),
            certificate_number=payload.validated_data.get("certificate_number", ""),
            completed_date=payload.validated_data.get("completed_date"),
        )
        record_audit(
            AuditAction.UPDATE, "learning.training_record", entity_id=record.pk,
            description=f"Completed training '{record.course.name}' for "
                        f"{record.employee}",
        )
        return Response(
            TrainingRecordSerializer(record, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel an open training record."""
        if not _can_manage(request):
            raise PermissionDenied("Cancelling a record requires learning.manage.")
        record = self.get_object()
        services.cancel_record(record)
        return Response(
            TrainingRecordSerializer(record, context={"request": request}).data
        )

    # --- self-service & compliance ---------------------------------------
    @action(detail=False, url_path="my-training")
    def my_training(self, request):
        """The requesting user's own training records."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            self.get_queryset().filter(employee=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = TrainingRecordListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, url_path="expiring-certifications")
    def expiring_certifications(self, request):
        """Completed records whose certification expires soon (``?days=N``)."""
        try:
            within = int(request.query_params.get("days", 30))
        except ValueError:
            within = 30
        records = services.expiring_certifications(
            getattr(request, "tenant", None), within_days=within
        )
        if not _can_manage(request):
            own = _own_employee(request)
            records = records.filter(employee=own) if own else records.none()
        serializer = TrainingRecordListSerializer(records, many=True)
        return Response({"days": within, "results": serializer.data})

    @action(detail=False)
    def compliance(self, request):
        """Compliance-training standing for an employee (``?employee=``, or own)."""
        employee_id = request.query_params.get("employee")
        if employee_id:
            if not _can_manage(request):
                raise PermissionDenied(
                    "You may only check your own compliance status."
                )
            employee = Employee.objects.filter(
                tenant=getattr(request, "tenant", None), pk=employee_id
            ).first()
        else:
            employee = _own_employee(request)
        if employee is None:
            raise NotFound("Employee not found.")
        return Response(services.compliance_status(employee))


class EmployeeSkillViewSet(TenantModelViewSet):
    """Skills held by employees."""

    queryset = EmployeeSkill.objects.select_related(
        "employee", "skill", "training_record"
    )
    serializer_class = EmployeeSkillSerializer
    permission_required = {
        "create": "learning.manage",
        "update": "learning.manage",
        "partial_update": "learning.manage",
        "destroy": "learning.manage",
    }
    filterset_fields = ["employee", "skill", "proficiency"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _can_manage(self.request):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()
