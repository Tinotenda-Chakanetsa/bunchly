from django.contrib import admin

from .models import LeaveApproval, LeaveBalance, LeaveRequest, LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "tenant", "category", "is_paid",
        "default_annual_days", "is_active",
    )
    list_filter = ("category", "is_paid", "is_active", "tenant")
    search_fields = ("name", "code")


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "leave_type", "year", "entitled_days",
        "taken_days", "pending_days", "available_days",
    )
    list_filter = ("year", "leave_type", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = ("created_at", "updated_at")


class LeaveApprovalInline(admin.TabularInline):
    model = LeaveApproval
    extra = 0
    readonly_fields = ("stage", "sequence", "label", "decided_by", "decided_at")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "leave_type", "start_date", "end_date",
        "total_days", "status", "current_stage",
    )
    list_filter = ("status", "current_stage", "leave_type", "tenant")
    search_fields = (
        "employee__first_name", "employee__last_name", "reason",
    )
    readonly_fields = ("total_days", "submitted_at", "decided_at", "created_at", "updated_at")
    inlines = [LeaveApprovalInline]


@admin.register(LeaveApproval)
class LeaveApprovalAdmin(admin.ModelAdmin):
    list_display = ("leave_request", "stage", "sequence", "status", "decided_by", "decided_at")
    list_filter = ("stage", "status")
