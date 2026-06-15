from django.contrib import admin

from .models import (
    CostCentre,
    Department,
    Grade,
    JobTitle,
    Location,
    Position,
    Team,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "parent", "is_active")
    list_filter = ("is_active", "tenant")
    search_fields = ("name", "code")


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "department", "grade", "is_vacant", "is_active")
    list_filter = ("is_vacant", "is_active", "tenant")
    search_fields = ("name", "job_title__name")


for _model in (CostCentre, Location, Grade, Team, JobTitle):

    @admin.register(_model)
    class _OrgAdmin(admin.ModelAdmin):
        list_display = ("name", "code", "tenant", "is_active")
        list_filter = ("is_active", "tenant")
        search_fields = ("name", "code")
