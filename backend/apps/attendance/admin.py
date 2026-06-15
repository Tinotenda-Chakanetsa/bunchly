from django.contrib import admin

from .models import AttendanceRecord, Shift, Timesheet


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "start_time", "end_time", "is_active")
    list_filter = ("is_active", "tenant")
    search_fields = ("name", "code")


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    fk_name = "timesheet"
    extra = 0
    readonly_fields = ("worked_minutes", "overtime_minutes", "created_at")


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "tenant", "period_start", "period_end", "status",
    )
    list_filter = ("status", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = ("decided_by", "decided_at", "created_at", "updated_at")
    inlines = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "tenant", "work_date", "status", "entry_type",
        "worked_minutes", "is_late", "approval_status",
    )
    list_filter = ("status", "entry_type", "approval_status", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = (
        "worked_minutes", "overtime_minutes", "is_late", "late_minutes",
        "is_early_departure", "early_departure_minutes", "decided_by",
        "decided_at", "created_at", "updated_at",
    )
