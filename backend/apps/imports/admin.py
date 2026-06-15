from django.contrib import admin

from .models import ImportBatch, ImportError


class ImportErrorInline(admin.TabularInline):
    model = ImportError
    extra = 0
    readonly_fields = ("row_number", "field", "error", "created_at")
    can_delete = False


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "entity_type", "tenant", "status", "total_rows", "valid_rows",
        "error_rows", "committed_rows", "created_at",
    )
    list_filter = ("entity_type", "status", "tenant")
    search_fields = ("original_filename",)
    readonly_fields = (
        "tenant", "entity_type", "original_filename", "total_rows",
        "valid_rows", "error_rows", "committed_rows", "committed_at",
        "created_by", "updated_by", "created_at", "updated_at",
    )
    inlines = [ImportErrorInline]


@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = ("batch", "row_number", "field", "error")
    search_fields = ("error", "field")
