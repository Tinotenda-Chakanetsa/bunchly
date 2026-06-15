from django.contrib import admin

from .models import (
    Candidate,
    CandidateDocument,
    Interview,
    JobPosting,
    JobRequisition,
    Offer,
)


@admin.register(JobRequisition)
class JobRequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "title", "tenant", "department", "headcount", "status",
    )
    list_filter = ("status", "employment_type", "tenant")
    search_fields = ("reference", "title")
    readonly_fields = ("reference", "approved_by", "approved_at")


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = (
        "title", "tenant", "status", "is_internal", "posted_date", "closing_date",
    )
    list_filter = ("status", "is_internal", "tenant")
    search_fields = ("title",)


class CandidateDocumentInline(admin.TabularInline):
    model = CandidateDocument
    extra = 0


class InterviewInline(admin.TabularInline):
    model = Interview
    extra = 0


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "posting", "tenant", "stage", "rating", "linked_employee",
    )
    list_filter = ("stage", "tenant")
    search_fields = ("first_name", "last_name", "email")
    inlines = [CandidateDocumentInline, InterviewInline]


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ("candidate", "tenant", "scheduled_at", "mode", "status", "score")
    list_filter = ("status", "mode", "tenant")
    search_fields = ("candidate__first_name", "candidate__last_name")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("candidate", "tenant", "job_title", "salary", "status")
    list_filter = ("status", "tenant")
    search_fields = ("candidate__first_name", "candidate__last_name", "job_title")
    readonly_fields = ("approved_by", "approved_at", "sent_at", "decided_at")
