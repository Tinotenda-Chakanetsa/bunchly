from django.contrib import admin

from .models import SavedReport


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ("name", "report_key", "tenant", "owner", "is_shared", "created_at")
    list_filter = ("report_key", "is_shared", "tenant")
    search_fields = ("name", "owner__email")
    readonly_fields = ("created_at", "updated_at")
