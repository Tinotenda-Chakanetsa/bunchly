from django.contrib import admin

from .models import Policy, PolicyAssignment, PolicyVersion


class PolicyVersionInline(admin.TabularInline):
    model = PolicyVersion
    fk_name = "policy"
    extra = 0
    readonly_fields = ("published_at", "published_by", "created_at")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "tenant", "category", "is_active")
    list_filter = ("category", "is_active", "tenant")
    search_fields = ("title", "code")
    inlines = [PolicyVersionInline]


@admin.register(PolicyVersion)
class PolicyVersionAdmin(admin.ModelAdmin):
    list_display = ("policy", "version", "tenant", "published_at", "effective_date")
    list_filter = ("tenant", "published_at")
    search_fields = ("policy__title", "version")
    readonly_fields = ("published_at", "published_by", "created_at", "updated_at")


@admin.register(PolicyAssignment)
class PolicyAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "policy", "tenant", "acknowledged_at", "due_date",
    )
    list_filter = ("tenant", "policy")
    search_fields = (
        "employee__first_name", "employee__last_name", "policy__title",
    )
    readonly_fields = (
        "acknowledged_at", "acknowledged_version", "assigned_by",
        "created_at", "updated_at",
    )
