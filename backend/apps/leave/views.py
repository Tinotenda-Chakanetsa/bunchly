"""Viewsets for the leave & absence module (spec §9.8).

Access scoping mirrors the employees module:
- ``leave.view``     -> sees every employee's leave in the tenant.
- ``leave.approve``  -> sees own + direct reports' leave.
- otherwise          -> sees only their own leave (self-service).

All state changes go through ``services`` so balances, the approval
chain and notifications stay consistent; every change is audited.
"""
from __future__ import annotations

from datetime import date

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.common.permissions import HasModulePermission, HasTenant
from apps.common.viewsets import TenantModelViewSet
from apps.employees.models import Employee

from . import services
from .enums import ApprovalStage, LeaveRequestStatus
from .models import LeaveApproval, LeaveBalance, LeaveRequest, LeaveType
from .serializers import (
    LeaveApprovalSerializer,
    LeaveBalanceAdjustSerializer,
    LeaveBalanceSerializer,
    LeaveDecisionSerializer,
    LeaveRequestListSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)


def _own_employee(request) -> Employee | None:
    """The employee record of the requesting user, if any."""
    tenant = getattr(request, "tenant", None)
    return (
        Employee.objects.filter(tenant=tenant, user=request.user)
        .select_related("department", "line_manager")
        .first()
    )


def _scoped_employee_ids(request):
    """Employee ids the caller may see leave for, or ``None`` for 'all'."""
    user = request.user
    tenant = getattr(request, "tenant", None)
    if user.has_perm_code("leave.view", tenant):
        return None  # unrestricted

    self_emp = _own_employee(request)
    if self_emp is None:
        return []
    if user.has_perm_code("leave.approve", tenant):
        # Manager: own record plus direct reports.
        report_ids = list(
            Employee.objects.filter(tenant=tenant, line_manager=self_emp)
            .values_list("id", flat=True)
        )
        return [self_emp.id, *report_ids]
    return [self_emp.id]


class LeaveTypeViewSet(TenantModelViewSet):
    """Configurable leave types. Reading is open; configuring is gated."""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_required = {
        "create": "leave.configure",
        "update": "leave.configure",
        "partial_update": "leave.configure",
        "destroy": "leave.configure",
    }
    search_fields = ["name", "code"]
    filterset_fields = ["is_active", "category", "is_paid"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        super().perform_create(serializer)
        record_audit(
            AuditAction.CREATE, "leave.leave_type",
            entity_id=serializer.instance.pk,
            description=f"Created leave type {serializer.instance.name}",
        )

    def perform_update(self, serializer):
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "leave.leave_type",
            entity_id=serializer.instance.pk,
            description=f"Updated leave type {serializer.instance.name}",
        )

    def perform_destroy(self, instance):
        pk, name = instance.pk, instance.name
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE, "leave.leave_type",
            entity_id=pk, description=f"Archived leave type {name}",
        )


class LeaveBalanceViewSet(TenantModelViewSet):
    """Leave balances — role-scoped; HR adjusts via the ``adjust`` action."""

    queryset = LeaveBalance.objects.select_related(
        "employee", "leave_type", "employee__line_manager"
    )
    serializer_class = LeaveBalanceSerializer
    permission_required = {
        "create": "leave.configure",
        "update": "leave.configure",
        "partial_update": "leave.configure",
        "destroy": "leave.configure",
        "adjust": "leave.configure",
    }
    filterset_fields = ["employee", "leave_type", "year"]
    ordering_fields = ["year", "created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        allowed = _scoped_employee_ids(self.request)
        if allowed is None:
            return queryset
        return queryset.filter(employee_id__in=allowed)

    @action(detail=False, url_path="my-balances")
    def my_balances(self, request):
        """The requesting user's own leave balances."""
        employee = _own_employee(request)
        if employee is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        year = request.query_params.get("year")
        balances = LeaveBalance.objects.filter(
            tenant=getattr(request, "tenant", None), employee=employee
        ).select_related("leave_type")
        if year:
            balances = balances.filter(year=year)
        serializer = self.get_serializer(balances, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        """Apply a manual (signed) correction to a balance — HR only."""
        balance = self.get_object()
        payload = LeaveBalanceAdjustSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        delta = payload.validated_data["adjustment_days"]
        reason = payload.validated_data["reason"]

        before = balance.adjustment_days
        balance.adjustment_days = before + delta
        balance.adjustment_reason = reason
        balance.save(
            update_fields=["adjustment_days", "adjustment_reason", "updated_at"]
        )
        record_audit(
            AuditAction.UPDATE, "leave.leave_balance", entity_id=balance.pk,
            description=f"Adjusted leave balance for {balance.employee}",
            before={"adjustment_days": str(before)},
            after={"adjustment_days": str(balance.adjustment_days)},
            reason=reason,
        )
        return Response(self.get_serializer(balance).data)


class LeaveRequestViewSet(TenantModelViewSet):
    """Leave requests — application, lifecycle actions and calendars."""

    queryset = LeaveRequest.objects.select_related(
        "employee", "employee__line_manager", "leave_type", "balance"
    ).prefetch_related("approvals")
    permission_required = {"create": "leave.apply"}
    filterset_fields = ["employee", "leave_type", "status", "current_stage"]
    search_fields = ["employee__first_name", "employee__last_name", "reason"]
    ordering_fields = ["start_date", "end_date", "submitted_at", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return LeaveRequestListSerializer
        return LeaveRequestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        allowed = _scoped_employee_ids(self.request)
        if allowed is None:
            return queryset
        return queryset.filter(employee_id__in=allowed)

    # --- create / edit guards --------------------------------------------
    def perform_create(self, serializer):
        request = self.request
        tenant = getattr(request, "tenant", None)
        user = request.user
        target = serializer.validated_data.get("employee")
        own = _own_employee(request)

        can_apply_for_others = user.has_perm_code(
            "leave.view", tenant
        ) or user.has_perm_code("leave.approve", tenant)
        if target is None:
            if own is None:
                raise ValidationError(
                    {"employee": "You do not have an employee profile; "
                                 "specify an employee to apply for."}
                )
            target = own
        elif target != own and not can_apply_for_others:
            raise PermissionDenied("You may only apply for your own leave.")

        instance = serializer.save(
            tenant=tenant, employee=target, status=LeaveRequestStatus.DRAFT
        )
        record_audit(
            AuditAction.CREATE, "leave.leave_request", entity_id=instance.pk,
            description=f"Drafted leave request for {instance.employee}",
        )

    def perform_update(self, serializer):
        if not serializer.instance.is_editable:
            raise PermissionDenied("Only a draft request can be edited.")
        serializer.save()
        record_audit(
            AuditAction.UPDATE, "leave.leave_request",
            entity_id=serializer.instance.pk,
            description=f"Updated leave request for {serializer.instance.employee}",
        )

    def perform_destroy(self, instance):
        if not instance.is_editable:
            raise PermissionDenied(
                "Only a draft request can be deleted — cancel it instead."
            )
        pk = instance.pk
        super().perform_destroy(instance)
        record_audit(
            AuditAction.DELETE, "leave.leave_request", entity_id=pk,
            description="Deleted draft leave request",
        )

    # --- decision authority ----------------------------------------------
    def _can_decide(self, leave_request) -> bool:
        """Whether the requesting user may decide the request's current stage."""
        user = self.request.user
        tenant = getattr(self.request, "tenant", None)
        if getattr(user, "is_platform_admin", False):
            return True
        stage = leave_request.current_stage
        if stage == ApprovalStage.MANAGER:
            if not user.has_perm_code("leave.approve", tenant):
                return False
            if user.has_perm_code("leave.view", tenant):
                return True  # HR / org-wide approver
            own = _own_employee(self.request)
            return own is not None and leave_request.employee.line_manager_id == own.id
        if stage in {ApprovalStage.HR, ApprovalStage.EXTRA}:
            return user.has_perm_code("leave.confirm", tenant)
        return False

    # --- lifecycle actions -----------------------------------------------
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """Submit a draft request into the approval workflow."""
        leave_request = self.get_object()
        own = _own_employee(request)
        is_owner = own is not None and leave_request.employee_id == own.id
        if not is_owner and not request.user.has_perm_code(
            "leave.view", getattr(request, "tenant", None)
        ):
            raise PermissionDenied("You may only submit your own leave request.")

        services.submit_request(leave_request)
        record_audit(
            AuditAction.SUBMIT, "leave.leave_request", entity_id=leave_request.pk,
            description=f"Submitted leave request for {leave_request.employee}",
        )
        return Response(
            LeaveRequestSerializer(leave_request, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve the request's current approval stage."""
        leave_request = self.get_object()
        if not self._can_decide(leave_request):
            raise PermissionDenied(
                "You are not authorised to decide this approval stage."
            )
        payload = LeaveDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        approval = services.decide_stage(
            leave_request,
            approve=True,
            user=request.user,
            comments=payload.validated_data.get("comments", ""),
        )
        record_audit(
            AuditAction.APPROVE, "leave.leave_request", entity_id=leave_request.pk,
            description=f"Approved {approval.get_stage_display()} for "
                        f"{leave_request.employee}",
        )
        return Response(
            LeaveRequestSerializer(leave_request, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject the request at its current approval stage."""
        leave_request = self.get_object()
        if not self._can_decide(leave_request):
            raise PermissionDenied(
                "You are not authorised to decide this approval stage."
            )
        payload = LeaveDecisionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        services.decide_stage(
            leave_request,
            approve=False,
            user=request.user,
            comments=payload.validated_data.get("comments", ""),
        )
        record_audit(
            AuditAction.REJECT, "leave.leave_request", entity_id=leave_request.pk,
            description=f"Rejected leave request for {leave_request.employee}",
        )
        return Response(
            LeaveRequestSerializer(leave_request, context={"request": request}).data
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel/withdraw a request and release its reserved balance."""
        leave_request = self.get_object()
        own = _own_employee(request)
        is_owner = own is not None and leave_request.employee_id == own.id
        can_manage = request.user.has_perm_code(
            "leave.view", getattr(request, "tenant", None)
        )
        if not is_owner and not can_manage:
            raise PermissionDenied("You may only cancel your own leave request.")

        services.cancel_request(leave_request, by_owner=is_owner)
        record_audit(
            AuditAction.UPDATE, "leave.leave_request", entity_id=leave_request.pk,
            description=f"Cancelled leave request for {leave_request.employee}",
        )
        return Response(
            LeaveRequestSerializer(leave_request, context={"request": request}).data
        )

    @action(detail=False)
    def mine(self, request):
        """The requesting user's own leave requests."""
        own = _own_employee(request)
        if own is None:
            raise NotFound("You do not have an employee profile in this organisation.")
        queryset = self.filter_queryset(
            self.get_queryset().filter(employee=own)
        )
        page = self.paginate_queryset(queryset)
        serializer = LeaveRequestListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, url_path="pending-approvals")
    def pending_approvals(self, request):
        """Requests awaiting a decision the caller is authorised to make."""
        queryset = self.get_queryset().filter(status=LeaveRequestStatus.PENDING)
        decidable = [r for r in queryset if self._can_decide(r)]
        page = self.paginate_queryset(decidable)
        serializer = LeaveRequestListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False)
    def calendar(self, request):
        """Active leave within a date window — for the leave calendar.

        Query params ``from`` / ``to`` (ISO dates) bound the window;
        both default to the current month-ish range if omitted.
        """
        queryset = self.get_queryset().filter(
            status__in=[LeaveRequestStatus.PENDING, LeaveRequestStatus.APPROVED]
        )
        start = _parse_date(request.query_params.get("from"))
        end = _parse_date(request.query_params.get("to"))
        if start:
            queryset = queryset.filter(end_date__gte=start)
        if end:
            queryset = queryset.filter(start_date__lte=end)
        serializer = LeaveRequestListSerializer(queryset, many=True)
        return Response({"results": serializer.data})

    @action(detail=True)
    def conflicts(self, request, pk=None):
        """Teammates whose leave overlaps this request (non-blocking warning)."""
        leave_request = self.get_object()
        clashes = services.team_conflicts(
            leave_request.employee,
            leave_request.start_date,
            leave_request.end_date,
            exclude_pk=leave_request.pk,
        )
        serializer = LeaveRequestListSerializer(clashes, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({"date": f"Invalid date '{value}' — use YYYY-MM-DD."})


class LeaveApprovalViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only view of approval-chain rows."""

    serializer_class = LeaveApprovalSerializer
    permission_classes = [IsAuthenticated, HasTenant, HasModulePermission]
    permission_required = "leave.view"
    filterset_fields = ["leave_request", "stage", "status"]
    ordering_fields = ["sequence", "decided_at"]

    def get_queryset(self):
        tenant = getattr(self.request, "tenant", None)
        return LeaveApproval.objects.filter(tenant=tenant).select_related(
            "leave_request", "leave_request__employee", "decided_by"
        )
