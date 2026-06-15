from django.contrib import admin

from .models import Document, DocumentCategory, DocumentVersion


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "tenant", "is_required", "requires_approval",
        "is_sensitive", "tracks_expiry", "is_active",
    )
    list_filter = (
        "is_required", "requires_approval", "is_sensitive", "is_active", "tenant",
    )
    search_fields = ("name", "code")


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = (
        "version_number", "file", "original_filename", "file_size",
        "content_type", "is_current",
    )


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title", "employee", "category", "status", "is_confidential",
        "expiry_date", "created_at",
    )
    list_filter = ("status", "category", "is_confidential", "tenant")
    search_fields = ("title", "employee__first_name", "employee__last_name")
    readonly_fields = ("reviewed_by", "reviewed_at", "created_at", "updated_at")
    inlines = [DocumentVersionInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        "document", "version_number", "is_current", "file_size", "created_at",
    )
    list_filter = ("is_current",)
    search_fields = ("document__title", "original_filename")
