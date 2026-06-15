from django.contrib import admin

from .models import (
    Employee,
    EmployeeHistory,
    EmergencyContact,
    EmploymentContract,
)


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


class EmploymentContractInline(admin.TabularInline):
    model = EmploymentContract
    extra = 0


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "employee_number", "full_name", "tenant", "department",
        "employment_status", "start_date",
    )
    list_filter = ("employment_status", "employment_type", "tenant")
    search_fields = ("employee_number", "first_name", "last_name", "work_email")
    autocomplete_fields = ("user", "line_manager")
    inlines = [EmergencyContactInline, EmploymentContractInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(EmployeeHistory)
class EmployeeHistoryAdmin(admin.ModelAdmin):
    list_display = ("employee", "change_type", "field_changed", "effective_date", "created_at")
    list_filter = ("change_type",)
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = [f.name for f in EmployeeHistory._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(EmploymentContract)
class EmploymentContractAdmin(admin.ModelAdmin):
    list_display = ("__str__", "employee", "status", "start_date", "end_date")
    list_filter = ("status", "contract_type")
    search_fields = ("reference", "employee__first_name", "employee__last_name")
