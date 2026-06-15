from django.contrib import admin

from .models import BenefitEnrolmentHistory, BenefitType, EmployeeBenefit


@admin.register(BenefitType)
class BenefitTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "tenant", "category", "contribution_basis",
        "requires_approval", "is_active",
    )
    list_filter = ("category", "contribution_basis", "is_active", "tenant")
    search_fields = ("name", "code", "provider")


class BenefitEnrolmentHistoryInline(admin.TabularInline):
    model = BenefitEnrolmentHistory
    extra = 0
    readonly_fields = ("event", "note", "actor", "created_at")
    can_delete = False


@admin.register(EmployeeBenefit)
class EmployeeBenefitAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "benefit_type", "tenant", "status", "start_date",
        "employee_contribution", "employer_contribution",
    )
    list_filter = ("status", "benefit_type", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = ("approved_by", "approved_at", "created_at", "updated_at")
    inlines = [BenefitEnrolmentHistoryInline]


@admin.register(BenefitEnrolmentHistory)
class BenefitEnrolmentHistoryAdmin(admin.ModelAdmin):
    list_display = ("enrolment", "event", "actor", "created_at")
    list_filter = ("event",)
    search_fields = ("enrolment__employee__first_name",)
