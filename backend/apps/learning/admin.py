from django.contrib import admin

from .models import EmployeeSkill, Skill, TrainingCourse, TrainingRecord


@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "tenant", "category", "delivery_mode",
        "is_compliance", "is_active",
    )
    list_filter = ("category", "delivery_mode", "is_compliance", "is_active", "tenant")
    search_fields = ("name", "code", "provider")


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "course", "tenant", "status", "completed_date",
        "certificate_expiry_date",
    )
    list_filter = ("status", "course", "tenant")
    search_fields = ("employee__first_name", "employee__last_name", "course__name")
    readonly_fields = ("assigned_by", "created_at", "updated_at")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "tenant", "is_active")
    list_filter = ("category", "is_active", "tenant")
    search_fields = ("name",)


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ("employee", "skill", "tenant", "proficiency")
    list_filter = ("proficiency", "tenant")
    search_fields = ("employee__first_name", "employee__last_name", "skill__name")
