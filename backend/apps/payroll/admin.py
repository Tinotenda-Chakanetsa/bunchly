from django.contrib import admin

from .models import (
    PayComponent,
    PayrollLine,
    PayrollPeriod,
    PayrollRecord,
    Payslip,
)


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "tenant", "start_date", "end_date", "status",
    )
    list_filter = ("status", "tenant")
    search_fields = ("name", "code")
    readonly_fields = ("approved_by", "approved_at", "created_at", "updated_at")


@admin.register(PayComponent)
class PayComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "component_type", "is_taxable", "is_active")
    list_filter = ("component_type", "is_taxable", "is_active", "tenant")
    search_fields = ("name", "code")


class PayrollLineInline(admin.TabularInline):
    model = PayrollLine
    extra = 0


@admin.register(PayrollRecord)
class PayrollRecordAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "period", "tenant", "basic_salary", "gross_pay",
        "net_pay", "status",
    )
    list_filter = ("status", "period", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = (
        "total_allowances", "total_deductions", "leave_without_pay_days",
        "leave_without_pay_amount", "gross_pay", "net_pay",
        "created_at", "updated_at",
    )
    inlines = [PayrollLineInline]


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "employee", "period", "tenant", "is_published",
        "published_at",
    )
    list_filter = ("is_published", "period", "tenant")
    search_fields = ("reference", "employee__first_name", "employee__last_name")
    readonly_fields = ("snapshot", "created_at", "updated_at")
