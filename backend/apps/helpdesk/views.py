"""Viewsets for the HR helpdesk / case-management module (spec §9.22).

Any tenant member may raise a case. ``helpdesk.view`` / ``helpdesk.manage``
holders see and handle every case; everyone else sees only the cases
they raised or are assigned to handle.
"""
from __future__ import annotations

from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .models import CaseAttachment, CaseCategory, CaseComment, HRCase
from .serializers import (
    AssignCaseSerializer,
    CaseAttachmentSerializer,
    CaseCategorySerializer,
    CaseCommentSerializer,
    CaseCreateSerializer,
    CaseStatusSerializer,
    HRCaseListSerializer,
    HRCaseSerializer,
    ResolveCaseSerializer,
)


def _own_employee(request) -> Employee | None:
    tenant = getattr(request, "tenant", None)
    return Employee.objects.filter(tenant=tenant, user=request.user).first()


def _can_manage(request) -> bool:
    tenant = getattr(request, "tenant", None)
    return request.user.has_perm_code("helpdesk.manage", tenant) or (
        request.user.has_perm_code("helpdesk.view", tenant)
    )


class CaseCategoryViewSet(TenantModelViewSet):
    """Configurable HR case categories."""

    queryset = CaseCategory.objects.all()
    serializer_class = CaseCategorySerializer
    permission_required = {
        "create": "helpdesk.manage",
        "update": "helpdesk.manage",
        "partial_update": "helpdesk.manage",
        "destroy": "helpdesk.manage",
    }
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]


class HRCaseViewSet(TenantModelViewSet):
    """HR cases — raising, handling and the resolution lifecycle."""

    queryset = HRCase.objects.select_related(
        "category", "raised_by", "assigned_to"
    ).prefetch_related("comments", "comments__author", "attachments")
    permission_required = {
        "assign": "helpdesk.manage",
        "change_status": "helpdesk.manage",
        "resolve": "helpdesk.manage",
        "close": "helpdesk.manage",
        "cancel": "helpdesk.manage",
        "reopen": "helpdesk.manage",
        "overdue": "helpdesk.view",
    }
    filterset_fields = ["status", "priority", "category", "assigned_to"]
    search_fields = ["reference", "subject", "description"]
    ordering_fields = ["created_at", "sla_due_at"]

    def get_serializer_class(self):
        return HRCaseListSerializer if self.action == "list" else HRCaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if _can_manage(self.request):
            return queryset
        own = _own_employee(self.request)
        return queryset.filter(
            Q(raised_by=own) | Q(assigned_to=self.request.user)
        ) if own else queryset.filter(assigned_to=self.request.user)

    def create(self, request, *args, **kwargs):
        payload = CaseCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        tenant = getattr(request, "tenant", None)
        data = payload.validated_data

        own = _own_employee(request)
        raised_by = own
        if data.get("employee"):
            if not _can_manage(request):
                raise PermissionDenied(
                    "You may only raise a case for yourself."
                )
            raised_by = Employee.objects.filter(
                tenant=tenant, pk=data["employee"]
            ).first()
        if raised_by is None:
            raise ValidationError(
                {"employee": "No employee profile to raise the case for."}
            )

        category = None
        if data.get("category"):
            category = CaseCategory.objects.filter(
                tenant=tenant, pk=data["category"]
            ).first()
            if category is None:
                raise ValidationError({"category": "Category not found."})

        case = services.create_case(
            tenant=tenant,
            raised_by=raised_by,
            subject=data["subject"],
            description=data.get("description", ""),
            category=category,
            priority=data.get("priority"),
        )
        record_audit(
            AuditAction.CREATE, "helpdesk.case", entity_id=case.pk,
            description=f"Raised HR case {case.reference}",
        )
        return Response(
            HRCaseSerializer(case, context={"request": request}).data, status=201
        )

    def perform_update(self, serializer):
        case = serializer.instance
        own = _own_employee(self.request)
        is_raiser = own is not None and case.raised_by_id == own.id
        if not is_raiser and not _can_manage(self.request):
            raise PermissionDenied("You may only edit a case you raised.")
        serializer.save()

    # --- helpers ----------------------------------------------------------
    def _respond(self, case):
        return Response(
            HRCaseSerializer(case, context={"request": self.request}).data
        )

    # --- lifecycle actions ------------------------------------------------
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Assign a case to an HR handler."""
        from apps.accounts.models import User

        case = self.get_object()
        payload = AssignCaseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        handler = User.objects.filter(pk=payload.validated_data["assigned_to"]).first()
        if handler is None:
            raise ValidationError({"assigned_to": "User not found."})
        services.assign_case(case, user=handler)
        record_audit(
            AuditAction.UPDATE, "helpdesk.case", entity_id=case.pk,
            description=f"Assigned HR case {case.reference}",
        )
        return self._respond(case)

    @action(detail=True, methods=["post"], url_path="change-status")
    def change_status(self, request, pk=None):
        """Move a case between the open-work statuses."""
        case = self.get_object()
        payload = CaseStatusSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.change_status(case, payload.validated_data["status"])
        return self._respond(case)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve a case, recording resolution notes."""
        case = self.get_object()
        payload = ResolveCaseSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.resolve_case(
            case, resolution_notes=payload.validated_data.get("resolution_notes", "")
        )
        record_audit(
            AuditAction.UPDATE, "helpdesk.case", entity_id=case.pk,
            description=f"Resolved HR case {case.reference}",
        )
        return self._respond(case)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close a resolved case."""
        case = self.get_object()
        services.close_case(case)
        return self._respond(case)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a case that is not yet closed."""
        case = self.get_object()
        services.cancel_case(case)
        return self._respond(case)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        """Reopen a resolved or closed case."""
        case = self.get_object()
        services.reopen_case(case)
        return self._respond(case)

    @action(detail=False, url_path="my-cases")
    def my_cases(self, request):
        """Cases raised by the requesting user."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            super().get_queryset().filter(raised_by=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = HRCaseListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False)
    def overdue(self, request):
        """Open cases whose SLA target has passed."""
        cases = services.overdue_cases(getattr(request, "tenant", None))
        page = self.paginate_queryset(cases)
        serializer = HRCaseListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CaseCommentViewSet(TenantModelViewSet):
    """Comments on HR cases."""

    queryset = CaseComment.objects.select_related("case", "case__raised_by", "author")
    serializer_class = CaseCommentSerializer
    filterset_fields = ["case", "is_internal"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _can_manage(self.request):
            return queryset
        own = _own_employee(self.request)
        # Non-HR users see comments on their own / assigned cases, minus
        # internal notes.
        visible_cases = HRCase.objects.filter(
            Q(raised_by=own) | Q(assigned_to=self.request.user)
        )
        return queryset.filter(case__in=visible_cases, is_internal=False)

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        is_internal = serializer.validated_data.get("is_internal", False)
        own = _own_employee(self.request)
        is_participant = (
            (own is not None and case.raised_by_id == own.id)
            or case.assigned_to_id == self.request.user.id
            or _can_manage(self.request)
        )
        if not is_participant:
            raise PermissionDenied("You are not a participant in this case.")
        if is_internal and not _can_manage(self.request):
            raise PermissionDenied("Only HR may add an internal note.")
        serializer.save(
            tenant=getattr(self.request, "tenant", None),
            author=self.request.user,
        )


class CaseAttachmentViewSet(TenantModelViewSet):
    """File attachments on HR cases."""

    queryset = CaseAttachment.objects.select_related("case", "case__raised_by")
    serializer_class = CaseAttachmentSerializer
    filterset_fields = ["case"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _can_manage(self.request):
            return queryset
        own = _own_employee(self.request)
        visible_cases = HRCase.objects.filter(
            Q(raised_by=own) | Q(assigned_to=self.request.user)
        )
        return queryset.filter(case__in=visible_cases)

    def perform_create(self, serializer):
        case = serializer.validated_data["case"]
        own = _own_employee(self.request)
        is_participant = (
            (own is not None and case.raised_by_id == own.id)
            or case.assigned_to_id == self.request.user.id
            or _can_manage(self.request)
        )
        if not is_participant:
            raise PermissionDenied("You are not a participant in this case.")
        serializer.save(
            tenant=getattr(self.request, "tenant", None),
            uploaded_by=self.request.user,
        )
