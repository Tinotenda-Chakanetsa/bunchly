"""Choice enumerations for the notification engine (spec §6, §9.15)."""
from django.db import models


class NotificationType(models.TextChoices):
    """Catalogue of notification events the system can raise.

    The string value is the stable ``event_key`` used to look up a
    tenant's template and to toggle a notification on/off.
    """

    # Account lifecycle
    WELCOME = "welcome", "Welcome email"
    PASSWORD_RESET = "password_reset", "Password reset"
    # Leave
    LEAVE_SUBMITTED = "leave_submitted", "Leave request submitted"
    LEAVE_STAGE_ADVANCED = "leave_stage_advanced", "Leave advanced a stage"
    LEAVE_APPROVED = "leave_approved", "Leave approved"
    LEAVE_REJECTED = "leave_rejected", "Leave rejected"
    LEAVE_CANCELLED = "leave_cancelled", "Leave cancelled"
    LEAVE_PENDING_REMINDER = "leave_pending_reminder", "Leave awaiting approval"
    LEAVE_FINANCE_NOTICE = "leave_finance_notice", "Leave finance notice"
    # Documents
    DOCUMENT_APPROVED = "document_approved", "Document approved"
    DOCUMENT_REJECTED = "document_rejected", "Document rejected"
    DOCUMENT_EXPIRING = "document_expiring", "Document expiring"
    DOCUMENT_MISSING = "document_missing", "Missing required document"
    # Payroll
    PAYSLIP_PUBLISHED = "payslip_published", "Payslip published"
    # Education assistance
    EDUCATION_CLAIM_SUBMITTED = "education_claim_submitted", "Education claim submitted"
    EDUCATION_CLAIM_APPROVED = "education_claim_approved", "Education claim approved"
    EDUCATION_CLAIM_REJECTED = "education_claim_rejected", "Education claim rejected"
    EDUCATION_CLAIM_INFO_REQUESTED = (
        "education_claim_info_requested", "Education claim needs more info"
    )
    EDUCATION_CLAIM_PAID = "education_claim_paid", "Education claim paid"
    # Workflow engine
    WORKFLOW_SUBMITTED = "workflow_submitted", "Workflow item awaiting you"
    WORKFLOW_APPROVED = "workflow_approved", "Workflow item approved"
    WORKFLOW_REJECTED = "workflow_rejected", "Workflow item rejected"
    WORKFLOW_INFO_REQUESTED = "workflow_info_requested", "Workflow needs more info"
    WORKFLOW_ESCALATED = "workflow_escalated", "Workflow item escalated"
    WORKFLOW_COMPLETED = "workflow_completed", "Workflow completed"
    # Policies & acknowledgements
    POLICY_ASSIGNED = "policy_assigned", "Policy assigned for acknowledgement"
    POLICY_PUBLISHED = "policy_published", "Policy version published"
    POLICY_ACK_REMINDER = "policy_ack_reminder", "Policy acknowledgement reminder"
    # Date-triggered HR alerts
    BIRTHDAY = "birthday", "Employee birthday"
    CONTRACT_EXPIRY = "contract_expiry", "Contract expiry reminder"
    PROBATION_ENDING = "probation_ending", "Probation ending reminder"
    RETIREMENT_REMINDER = "retirement_reminder", "Retirement approaching"
    # Catch-all
    GENERAL = "general", "General notification"


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email only"
    IN_APP = "in_app", "In-app only"
    BOTH = "both", "Email and in-app"


class NotificationLevel(models.TextChoices):
    INFO = "info", "Information"
    SUCCESS = "success", "Success"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"


class EmailStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class InboundEmailStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed / matched"
    UNMATCHED = "unmatched", "Unmatched"
    FAILED = "failed", "Processing failed"
