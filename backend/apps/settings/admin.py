from django.contrib import admin

from .models import SystemSetting


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = (
        "key", "tenant", "group", "value_type", "value", "is_public",
        "is_editable",
    )
    list_filter = ("group", "value_type", "is_public", "is_editable", "tenant")
    search_fields = ("key", "label")
    readonly_fields = ("created_at", "updated_at")
