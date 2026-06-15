"""Choice enumerations for the workflow engine (spec §10)."""
from django.db import models


class WorkflowEntity(models.TextChoices):
    """The kinds of domain object a workflow can govern."""

    LEAVE_REQUEST = "leave_request", "Leave request"
    DOCUMENT = "document", "Document approval"
    EDUCATION_CLAIM = "education_claim", "Education assistance claim"
    ONBOARDING = "onboarding", "Onboarding task"
    OFFBOARDING = "offboarding", "Offboarding task"
    SALARY_CHANGE = "salary_change", "Salary change"
    RECRUITMENT_OFFER = "recruitment_offer", "Recruitment offer"
    PAYROLL = "payroll", "Payroll approval"
    HR_CASE = "hr_case", "HR case"
    GENERAL = "general", "General approval"


class ApproverType(models.TextChoices):
    """How a stage's approvers are resolved at run time."""

    ROLE = "role", "Anyone holding a role"
    NAMED_USER = "named_user", "A specific named user"
    LINE_MANAGER = "line_manager", "The subject's line manager"
    DEPARTMENT_HEAD = "department_head", "The subject's department head"


class WorkflowStatus(models.TextChoices):
    """Lifecycle of a workflow instance (spec §10 default statuses)."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    PENDING_REVIEW = "pending_review", "Pending review"
    PENDING_APPROVAL = "pending_approval", "Pending approval"
    MORE_INFO = "more_info", "More information required"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


# Statuses where the instance is still moving through its chain.
OPEN_STATUSES = {
    WorkflowStatus.SUBMITTED,
    WorkflowStatus.PENDING_REVIEW,
    WorkflowStatus.PENDING_APPROVAL,
    WorkflowStatus.MORE_INFO,
}
# Statuses where the workflow has finished.
TERMINAL_STATUSES = {
    WorkflowStatus.APPROVED,
    WorkflowStatus.REJECTED,
    WorkflowStatus.PAID,
    WorkflowStatus.CANCELLED,
    WorkflowStatus.COMPLETED,
}


class WorkflowActionType(models.TextChoices):
    """An entry in a workflow instance's action log."""

    SUBMIT = "submit", "Submitted"
    APPROVE = "approve", "Approved"
    REJECT = "reject", "Rejected"
    REQUEST_INFO = "request_info", "Requested more information"
    PROVIDE_INFO = "provide_info", "Provided information"
    COMMENT = "comment", "Commented"
    ESCALATE = "escalate", "Escalated"
    CANCEL = "cancel", "Cancelled"
    COMPLETE = "complete", "Completed"
