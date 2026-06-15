from django.contrib import admin

from .models import (
    DevelopmentPlan,
    Goal,
    PerformanceReview,
    ReviewCycle,
    ReviewItem,
)


@admin.register(ReviewCycle)
class ReviewCycleAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "period_start", "period_end", "status")
    list_filter = ("status", "tenant")
    search_fields = ("name",)


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        "title", "employee", "tenant", "category", "progress", "status",
    )
    list_filter = ("category", "status", "tenant")
    search_fields = ("title", "employee__first_name", "employee__last_name")


class ReviewItemInline(admin.TabularInline):
    model = ReviewItem
    extra = 0


@admin.register(PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = (
        "employee", "cycle", "tenant", "review_type", "status", "overall_rating",
    )
    list_filter = ("review_type", "status", "cycle", "tenant")
    search_fields = ("employee__first_name", "employee__last_name")
    readonly_fields = (
        "submitted_at", "acknowledged_at", "acknowledged_by",
        "created_at", "updated_at",
    )
    inlines = [ReviewItemInline]


@admin.register(DevelopmentPlan)
class DevelopmentPlanAdmin(admin.ModelAdmin):
    list_display = ("title", "employee", "tenant", "status", "target_date")
    list_filter = ("status", "tenant")
    search_fields = ("title", "employee__first_name", "employee__last_name")
