from django.contrib import admin

from .models import Workflow, WorkflowAction, WorkflowInstance, WorkflowStage


class WorkflowStageInline(admin.TabularInline):
    model = WorkflowStage
    extra = 0


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "entity_type", "is_default", "is_active")
    list_filter = ("entity_type", "is_default", "is_active", "tenant")
    search_fields = ("name", "code")
    inlines = [WorkflowStageInline]


@admin.register(WorkflowStage)
class WorkflowStageAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow", "sequence", "approver_type", "sla_days")
    list_filter = ("approver_type", "tenant")
    search_fields = ("name", "workflow__name")


class WorkflowActionInline(admin.TabularInline):
    model = WorkflowAction
    extra = 0
    readonly_fields = ("action", "stage", "actor", "comment", "created_at")
    can_delete = False


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "subject", "workflow", "tenant", "status", "current_stage",
        "initiated_by", "created_at",
    )
    list_filter = ("status", "workflow", "tenant")
    search_fields = ("subject", "entity_id")
    readonly_fields = (
        "submitted_at", "completed_at", "stage_entered_at",
        "created_at", "updated_at",
    )
    inlines = [WorkflowActionInline]


@admin.register(WorkflowAction)
class WorkflowActionAdmin(admin.ModelAdmin):
    list_display = ("instance", "action", "stage", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("instance__subject",)
