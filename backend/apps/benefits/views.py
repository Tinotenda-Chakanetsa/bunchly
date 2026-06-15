"""Viewsets for the benefits-administration module (spec §9.11).

- ``BenefitTypeViewSet``     the configurable benefit catalogue.
- ``EmployeeBenefitViewSet`` enrolments and their lifecycle actions.

Scoping: ``benefits.manage`` holders see and act on every enrolment;
everyone else sees only their own. Enrolment is created through the
``enrol`` flow so eligibility checks and contribution snapshots apply.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .models import BenefitType, EmployeeBenefit
from .serializers import (
    BenefitTypeSerializer,
    EmployeeBenefitListSerializer,
    EmployeeBenefitSerializer,
    EnrolmentNoteSerializer,
    EnrolSerializer,
)


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


class BenefitTypeViewSet(TenantModelViewSet):
    """The configurable benefit catalogue."""

    queryset = BenefitType.objects.select_related("pay_component")
    serializer_class = BenefitTypeSerializer
    permission_required = {
        "default": "benefits.view",
        "create": "benefits.manage",
        "update": "benefits.manage",
        "partial_update": "benefits.manage",
        "destroy": "benefits.manage",
    }
    search_fields = ["name", "code", "provider"]
    filterset_fields = ["category", "is_active", "contribution_basis"]
    ordering_fields = ["name", "category", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "benefits.benefit_type",
            entity_id=serializer.instance.pk,
            description=f"Created benefit type {serializer.instance.name}",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "benefits.benefit_type",
            entity_id=serializer.instance.pk,
            description=f"Updated benefit type {serializer.instance.name}",
        )


class EmployeeBenefitViewSet(TenantModelViewSet):
    """Employee benefit enrolments and their lifecycle."""

    queryset = EmployeeBenefit.objects.select_related(
        "employee", "benefit_type", "approved_by"
    ).prefetch_related("history", "covered_dependants")
    permission_required = {
        "create": "benefits.enrol",
        "approve": "benefits.manage",
        "decline": "benefits.manage",
        "suspend": "benefits.manage",
        "resume": "benefits.manage",
        "terminate": "benefits.manage",
    }
    filterset_fields = ["employee", "benefit_type", "status"]
    ordering_fields = ["created_at", "start_date"]

    def get_serializer_class(self):
        return (
            EmployeeBenefitListSerializer
            if self.action == "list"
            else EmployeeBenefitSerializer
        )

    def _can_manage(self) -> bool:
        return self.request.user.has_perm_code(
            "benefits.manage", getattr(self.request, "tenant", None)
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self._can_manage():
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(employee=own) if own else queryset.none()

    def create(self, request, *args, **kwargs):
        payload = EnrolSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = getattr(request, "tenant", None)

        own = _own_employee(request)
        employee_id = payload.validated_data.get("employee")
        if employee_id and self._can_manage():
            employee = Employee.objects.filter(tenant=tenant, pk=employee_id).first()
            if employee is None:
                raise ValidationError({"employee": "Employee not found."})
        else:
            # A self-service enroller may only enrol themselves.
            if own is None:
                raise ValidationError(
                    {"employee": "You do not have an employee profile."}
                )
            employee = own

        benefit_type = BenefitType.objects.filter(
            tenant=tenant, pk=payload.validated_data["benefit_type"]
        ).first()
        if benefit_type is None:
            raise ValidationError({"benefit_type": "Benefit type not found."})

        enrolment = services.enrol(
            employee, benefit_type, user=request.user,
            notes=payload.validated_data.get("notes", ""),
        )
        record_audit(
            AuditAction.CREATE, "benefits.enrolment", entity_id=enrolment.pk,
            description=f"Enrolled {employee} in {benefit_type.name}",
        )
        return Response(
            EmployeeBenefitSerializer(enrolment, context={"request": request}).data,
            status=201,
        )

    # --- helpers ----------------------------------------------------------
    def _respond(self, enrolment):
        return Response(
            EmployeeBenefitSerializer(
                enrolment, context={"request": self.request}
            ).data
        )

    def _note(self, request) -> str:
        payload = EnrolmentNoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        return payload.validated_data.get("note", "")

    # --- lifecycle actions ------------------------------------------------
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending enrolment."""
        enrolment = self.get_object()
        services.approve_enrolment(enrolment, user=request.user)
        record_audit(
            AuditAction.APPROVE, "benefits.enrolment", entity_id=enrolment.pk,
            description=f"Approved benefit enrolment {enrolment.pk}",
        )
        return self._respond(enrolment)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Decline a pending enrolment."""
        enrolment = self.get_object()
        services.decline_enrolment(
            enrolment, user=request.user, note=self._note(request)
        )
        record_audit(
            AuditAction.REJECT, "benefits.enrolment", entity_id=enrolment.pk,
            description=f"Declined benefit enrolment {enrolment.pk}",
        )
        return self._respond(enrolment)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        """Suspend an active enrolment."""
        enrolment = self.get_object()
        services.suspend_enrolment(
            enrolment, user=request.user, note=self._note(request)
        )
        return self._respond(enrolment)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """Resume a suspended enrolment."""
        enrolment = self.get_object()
        services.resume_enrolment(enrolment, user=request.user)
        return self._respond(enrolment)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        """Terminate an active or suspended enrolment."""
        enrolment = self.get_object()
        services.terminate_enrolment(
            enrolment, user=request.user, note=self._note(request)
        )
        record_audit(
            AuditAction.UPDATE, "benefits.enrolment", entity_id=enrolment.pk,
            description=f"Terminated benefit enrolment {enrolment.pk}",
        )
        return self._respond(enrolment)

    @action(detail=False, url_path="my-benefits")
    def my_benefits(self, request):
        """The requesting user's own benefit enrolments."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            self.get_queryset().filter(employee=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = EmployeeBenefitListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
