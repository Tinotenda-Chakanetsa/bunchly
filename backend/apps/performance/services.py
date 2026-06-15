"""Performance-management business logic (spec §9.18).

Covers the review lifecycle (draft → submitted → acknowledged →
completed), goal status derivation from progress and the performance-
history view.
"""
from __future__ import annotations

from django.db.models import Avg
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .enums import (
    GoalStatus,
    LOCKED_REVIEW_STATUSES,
    ReviewStatus,
)
from .models import Goal, PerformanceReview


# --------------------------------------------------------------------------
# Goals
# --------------------------------------------------------------------------
def apply_goal_progress(goal: Goal, progress: int) -> Goal:
    """Set a goal's progress and derive its status from it.

    A manually set terminal status (achieved / cancelled etc.) is left
    alone; otherwise status tracks progress.
    """
    progress = max(0, min(100, int(progress)))
    goal.progress = progress
    if goal.status not in {
        GoalStatus.ACHIEVED, GoalStatus.PARTIALLY_ACHIEVED,
        GoalStatus.NOT_ACHIEVED, GoalStatus.CANCELLED,
    }:
        if progress >= 100:
            goal.status = GoalStatus.ACHIEVED
        elif progress > 0:
            goal.status = GoalStatus.IN_PROGRESS
        else:
            goal.status = GoalStatus.NOT_STARTED
    goal.save(update_fields=["progress", "status", "updated_at"])
    return goal


# --------------------------------------------------------------------------
# Review lifecycle
# --------------------------------------------------------------------------
def submit_review(review: PerformanceReview) -> PerformanceReview:
    """Submit a draft review for the employee to acknowledge."""
    if review.status != ReviewStatus.DRAFT:
        raise ValidationError("Only a draft review can be submitted.")
    if review.overall_rating is None:
        raise ValidationError(
            {"overall_rating": "An overall rating is required before submitting."}
        )
    review.status = ReviewStatus.SUBMITTED
    review.submitted_at = timezone.now()
    review.save(update_fields=["status", "submitted_at", "updated_at"])
    return review


def acknowledge_review(review: PerformanceReview, *, user) -> PerformanceReview:
    """Record the employee acknowledging a submitted review."""
    if review.status != ReviewStatus.SUBMITTED:
        raise ValidationError("Only a submitted review can be acknowledged.")
    review.status = ReviewStatus.ACKNOWLEDGED
    review.acknowledged_at = timezone.now()
    review.acknowledged_by = user
    review.save(update_fields=[
        "status", "acknowledged_at", "acknowledged_by", "updated_at",
    ])
    return review


def complete_review(review: PerformanceReview) -> PerformanceReview:
    """Mark an acknowledged review as completed (HR close-out)."""
    if review.status != ReviewStatus.ACKNOWLEDGED:
        raise ValidationError("Only an acknowledged review can be completed.")
    review.status = ReviewStatus.COMPLETED
    review.save(update_fields=["status", "updated_at"])
    return review


def assert_review_editable(review: PerformanceReview) -> None:
    """Raise if a review is past the editable point of its lifecycle."""
    if review.status in LOCKED_REVIEW_STATUSES:
        raise ValidationError(
            "This review is acknowledged/completed and can no longer be edited."
        )


# --------------------------------------------------------------------------
# Performance history
# --------------------------------------------------------------------------
def performance_history(employee) -> dict:
    """An employee's review ratings and goal-achievement summary."""
    reviews = PerformanceReview.objects.filter(
        tenant=employee.tenant, employee=employee
    ).select_related("cycle").order_by("-created_at")
    goals = Goal.objects.filter(tenant=employee.tenant, employee=employee)

    average_rating = reviews.filter(overall_rating__isnull=False).aggregate(
        avg=Avg("overall_rating")
    )["avg"]
    return {
        "employee": str(employee.pk),
        "review_count": reviews.count(),
        "average_overall_rating": (
            round(average_rating, 2) if average_rating is not None else None
        ),
        "goals_total": goals.count(),
        "goals_achieved": goals.filter(status=GoalStatus.ACHIEVED).count(),
        "reviews": [
            {
                "id": str(r.id),
                "cycle": r.cycle.name,
                "review_type": r.review_type,
                "overall_rating": r.overall_rating,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in reviews[:50]
        ],
    }
