from django.contrib import admin

from .models import CaseAttachment, CaseCategory, CaseComment, HRCase


@admin.register(CaseCategory)
class CaseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "tenant", "default_sla_hours", "is_active")
    list_filter = ("is_active", "tenant")
    search_fields = ("name", "code")


class CaseCommentInline(admin.TabularInline):
    model = CaseComment
    extra = 0
    readonly_fields = ("author", "created_at")


class CaseAttachmentInline(admin.TabularInline):
    model = CaseAttachment
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


@admin.register(HRCase)
class HRCaseAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "subject", "tenant", "category", "priority", "status",
        "assigned_to",
    )
    list_filter = ("status", "priority", "category", "tenant")
    search_fields = ("reference", "subject")
    readonly_fields = (
        "reference", "resolved_at", "closed_at", "created_at", "updated_at",
    )
    inlines = [CaseCommentInline, CaseAttachmentInline]


@admin.register(CaseComment)
class CaseCommentAdmin(admin.ModelAdmin):
    list_display = ("case", "author", "is_internal", "created_at")
    list_filter = ("is_internal",)
    search_fields = ("case__reference",)
