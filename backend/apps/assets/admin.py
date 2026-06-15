from django.contrib import admin

from .models import Asset, AssetAssignment, AssetCategory


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "is_active")
    list_filter = ("is_active", "tenant")
    search_fields = ("name", "code")


class AssetAssignmentInline(admin.TabularInline):
    model = AssetAssignment
    extra = 0
    readonly_fields = ("issued_by", "returned_to", "created_at")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "name", "asset_tag", "tenant", "category", "status", "condition",
    )
    list_filter = ("status", "condition", "category", "tenant")
    search_fields = ("name", "asset_tag", "serial_number")
    inlines = [AssetAssignmentInline]


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "asset", "employee", "tenant", "status", "issued_date", "returned_date",
    )
    list_filter = ("status", "tenant")
    search_fields = (
        "asset__name", "asset__asset_tag",
        "employee__first_name", "employee__last_name",
    )
    readonly_fields = ("issued_by", "returned_to", "created_at", "updated_at")
