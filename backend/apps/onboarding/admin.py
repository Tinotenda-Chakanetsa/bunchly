from django.contrib import admin

from .models import (
    ChecklistTaskTemplate,
    ChecklistTemplate,
    OnboardingProgramme,
    OnboardingTask,
)


class ChecklistTaskTemplateInline(admin.TabularInline):
    model = ChecklistTaskTemplate
    extra = 0


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "programme_type", "is_default", "is_active")
    list_filter = ("programme_type", "is_default", "is_active", "tenant")
    search_fields = ("name",)
    inlines = [ChecklistTaskTemplateInline]


class OnboardingTaskInline(admin.TabularInline):
    model = OnboardingTask
    extra = 0


@admin.register(OnboardingProgramme)
class OnboardingProgrammeAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "tenant", "programme_type", "status", "start_date",
        "target_completion_date",
    )
    list_filter = ("programme_type", "status", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = ("completed_at", "created_at", "updated_at")
    inlines = [OnboardingTaskInline]


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = (
        "title", "programme", "tenant", "owner_role", "status", "due_date",
    )
    list_filter = ("owner_role", "status", "tenant")
    search_fields = ("title",)
