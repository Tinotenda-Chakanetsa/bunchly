from django.contrib import admin

from .models import (
    Dependant,
    EducationBenefitRule,
    EducationClaim,
    EducationClaimApproval,
    EducationClaimDocument,
)


@admin.register(EducationBenefitRule)
class EducationBenefitRuleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "tenant", "max_children", "max_amount_per_child",
        "frequency", "is_active",
    )
    list_filter = ("is_active", "frequency", "tenant")
    search_fields = ("name",)


@admin.register(Dependant)
class DependantAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "employee", "tenant", "relationship",
        "education_level", "is_benefit_eligible",
    )
    list_filter = ("relationship", "education_level", "is_benefit_eligible", "tenant")
    search_fields = ("full_name", "employee__first_name", "employee__last_name")


class EducationClaimDocumentInline(admin.TabularInline):
    model = EducationClaimDocument
    extra = 0


class EducationClaimApprovalInline(admin.TabularInline):
    model = EducationClaimApproval
    extra = 0
    readonly_fields = ("stage", "decision", "actor", "comment", "created_at")
    can_delete = False


@admin.register(EducationClaim)
class EducationClaimAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "employee", "dependant", "tenant", "academic_period",
        "amount_claimed", "status",
    )
    list_filter = ("status", "education_level", "period_type", "tenant")
    search_fields = ("reference", "employee__first_name", "employee__last_name")
    readonly_fields = (
        "reference", "submitted_at", "hr_reviewed_by", "hr_reviewed_at",
        "paid_by", "paid_at", "created_at", "updated_at",
    )
    inlines = [EducationClaimDocumentInline, EducationClaimApprovalInline]


@admin.register(EducationClaimApproval)
class EducationClaimApprovalAdmin(admin.ModelAdmin):
    list_display = ("claim", "stage", "decision", "actor", "created_at")
    list_filter = ("stage", "decision")
    search_fields = ("claim__reference",)
