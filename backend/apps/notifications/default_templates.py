"""Built-in notification templates.

These ship with the product so notifications work before an admin
customises anything. On tenant provisioning they are copied into
``NotificationTemplate`` rows the admin can then edit or disable;
``services.get_template`` also falls back to them at dispatch time if a
tenant has no row for an event.

Bodies use Django template syntax — ``{{ variable }}`` — rendered against
the context passed to ``dispatch``.
"""
from __future__ import annotations

from .enums import NotificationChannel, NotificationType

# event_key -> {name, channel, subject, body}
DEFAULT_TEMPLATES: dict[str, dict] = {
    NotificationType.WELCOME: {
        "name": "Welcome email",
        "channel": NotificationChannel.BOTH,
        "subject": "Welcome to {{ tenant_name }}",
        "body": (
            "Hi {{ recipient_name }},\n\n"
            "An account has been created for you on {{ tenant_name }}'s "
            "Bunchly workspace. You can sign in with your email address.\n"
        ),
    },
    NotificationType.PASSWORD_RESET: {
        "name": "Password reset",
        "channel": NotificationChannel.EMAIL,
        "subject": "Reset your Bunchly password",
        "body": (
            "Hi {{ recipient_name }},\n\n"
            "Use the following details to reset your password:\n"
            "uid: {{ uid }}\ntoken: {{ token }}\n\n"
            "If you did not request this, you can ignore this email.\n"
        ),
    },
    NotificationType.LEAVE_SUBMITTED: {
        "name": "Leave request submitted",
        "channel": NotificationChannel.BOTH,
        "subject": "Leave request — {{ employee_name }}",
        "body": (
            "{{ employee_name }} submitted a {{ leave_type }} request from "
            "{{ start_date }} to {{ end_date }} ({{ total_days }} day(s)).\n"
            "It is awaiting your approval.\n"
        ),
    },
    NotificationType.LEAVE_STAGE_ADVANCED: {
        "name": "Leave advanced a stage",
        "channel": NotificationChannel.BOTH,
        "subject": "Leave request advanced — {{ employee_name }}",
        "body": (
            "The {{ leave_type }} request for {{ employee_name }} "
            "({{ start_date }} – {{ end_date }}) advanced to the "
            "{{ stage }} stage.\n"
        ),
    },
    NotificationType.LEAVE_APPROVED: {
        "name": "Leave approved",
        "channel": NotificationChannel.BOTH,
        "subject": "Leave approved — {{ employee_name }}",
        "body": (
            "The {{ leave_type }} request for {{ employee_name }} from "
            "{{ start_date }} to {{ end_date }} has been approved.\n"
        ),
    },
    NotificationType.LEAVE_REJECTED: {
        "name": "Leave rejected",
        "channel": NotificationChannel.BOTH,
        "subject": "Leave rejected — {{ employee_name }}",
        "body": (
            "The {{ leave_type }} request for {{ employee_name }} "
            "({{ start_date }} – {{ end_date }}) was rejected.\n"
            "{{ note }}\n"
        ),
    },
    NotificationType.LEAVE_CANCELLED: {
        "name": "Leave cancelled",
        "channel": NotificationChannel.BOTH,
        "subject": "Leave cancelled — {{ employee_name }}",
        "body": (
            "The {{ leave_type }} request for {{ employee_name }} "
            "({{ start_date }} – {{ end_date }}) was cancelled.\n"
        ),
    },
    NotificationType.LEAVE_PENDING_REMINDER: {
        "name": "Leave awaiting approval",
        "channel": NotificationChannel.BOTH,
        "subject": "Reminder: leave awaiting your approval",
        "body": (
            "The {{ leave_type }} request for {{ employee_name }} "
            "({{ start_date }} – {{ end_date }}) has been awaiting approval "
            "since {{ submitted_date }}.\n"
        ),
    },
    NotificationType.LEAVE_FINANCE_NOTICE: {
        "name": "Leave finance notice",
        "channel": NotificationChannel.EMAIL,
        "subject": "Approved leave — {{ employee_name }}",
        "body": (
            "{{ employee_name }} has approved {{ leave_type }} from "
            "{{ start_date }} to {{ end_date }} ({{ total_days }} day(s)).\n"
        ),
    },
    NotificationType.DOCUMENT_APPROVED: {
        "name": "Document approved",
        "channel": NotificationChannel.BOTH,
        "subject": "Document approved — {{ document_title }}",
        "body": "Your document '{{ document_title }}' was approved.\n",
    },
    NotificationType.DOCUMENT_REJECTED: {
        "name": "Document rejected",
        "channel": NotificationChannel.BOTH,
        "subject": "Document rejected — {{ document_title }}",
        "body": (
            "Your document '{{ document_title }}' was rejected.\n"
            "{{ note }}\n"
        ),
    },
    NotificationType.DOCUMENT_EXPIRING: {
        "name": "Document expiring",
        "channel": NotificationChannel.BOTH,
        "subject": "Document expiring — {{ document_title }}",
        "body": (
            "The document '{{ document_title }}' for {{ employee_name }} "
            "expires on {{ expiry_date }}.\n"
        ),
    },
    NotificationType.DOCUMENT_MISSING: {
        "name": "Missing required document",
        "channel": NotificationChannel.BOTH,
        "subject": "Missing required document",
        "body": (
            "{{ employee_name }} has no document on file for the required "
            "category '{{ category_name }}'.\n"
        ),
    },
    NotificationType.PAYSLIP_PUBLISHED: {
        "name": "Payslip published",
        "channel": NotificationChannel.BOTH,
        "subject": "Your payslip for {{ period }} is available",
        "body": (
            "Your payslip for {{ period }} has been published.\n"
            "Net pay: {{ net_pay }}.\n"
            "Log in to Bunchly to view the full breakdown.\n"
        ),
    },
    NotificationType.EDUCATION_CLAIM_SUBMITTED: {
        "name": "Education claim submitted",
        "channel": NotificationChannel.BOTH,
        "subject": "Education claim {{ reference }} — {{ employee_name }}",
        "body": (
            "{{ employee_name }} submitted an education-assistance claim "
            "({{ reference }}) for {{ dependant_name }} — {{ amount }}.\n"
            "It is awaiting HR review.\n"
        ),
    },
    NotificationType.EDUCATION_CLAIM_APPROVED: {
        "name": "Education claim approved",
        "channel": NotificationChannel.BOTH,
        "subject": "Education claim {{ reference }} approved",
        "body": (
            "Your education-assistance claim {{ reference }} for "
            "{{ dependant_name }} was approved for {{ amount }} and is "
            "now with Finance for payment.\n{{ note }}\n"
        ),
    },
    NotificationType.EDUCATION_CLAIM_REJECTED: {
        "name": "Education claim rejected",
        "channel": NotificationChannel.BOTH,
        "subject": "Education claim {{ reference }} rejected",
        "body": (
            "Your education-assistance claim {{ reference }} for "
            "{{ dependant_name }} was rejected.\n{{ note }}\n"
        ),
    },
    NotificationType.EDUCATION_CLAIM_INFO_REQUESTED: {
        "name": "Education claim needs more information",
        "channel": NotificationChannel.BOTH,
        "subject": "Education claim {{ reference }} — more information needed",
        "body": (
            "More information is needed for education-assistance claim "
            "{{ reference }}.\n{{ note }}\n"
        ),
    },
    NotificationType.EDUCATION_CLAIM_PAID: {
        "name": "Education claim paid",
        "channel": NotificationChannel.BOTH,
        "subject": "Education claim {{ reference }} paid",
        "body": (
            "Your education-assistance claim {{ reference }} for "
            "{{ dependant_name }} has been paid — {{ amount }}.\n"
            "Payment reference: {{ payment_reference }}.\n"
        ),
    },
    NotificationType.WORKFLOW_SUBMITTED: {
        "name": "Workflow item awaiting you",
        "channel": NotificationChannel.BOTH,
        "subject": "Approval needed — {{ subject }}",
        "body": (
            "'{{ subject }}' is awaiting your decision at the "
            "{{ stage }} stage.\n"
        ),
    },
    NotificationType.WORKFLOW_APPROVED: {
        "name": "Workflow item approved",
        "channel": NotificationChannel.BOTH,
        "subject": "Approved — {{ subject }}",
        "body": (
            "'{{ subject }}' was approved by {{ actor_name }}.\n"
            "{{ comment }}\n"
        ),
    },
    NotificationType.WORKFLOW_REJECTED: {
        "name": "Workflow item rejected",
        "channel": NotificationChannel.BOTH,
        "subject": "Rejected — {{ subject }}",
        "body": (
            "'{{ subject }}' was rejected by {{ actor_name }}.\n"
            "{{ comment }}\n"
        ),
    },
    NotificationType.WORKFLOW_INFO_REQUESTED: {
        "name": "Workflow needs more information",
        "channel": NotificationChannel.BOTH,
        "subject": "More information needed — {{ subject }}",
        "body": (
            "{{ actor_name }} has requested more information on "
            "'{{ subject }}'.\n{{ comment }}\n"
        ),
    },
    NotificationType.WORKFLOW_ESCALATED: {
        "name": "Workflow item escalated",
        "channel": NotificationChannel.BOTH,
        "subject": "Escalation: {{ subject }} is overdue",
        "body": (
            "'{{ subject }}' has been awaiting a decision at the "
            "{{ stage }} stage beyond its {{ sla_days }}-day SLA.\n"
        ),
    },
    NotificationType.WORKFLOW_COMPLETED: {
        "name": "Workflow completed",
        "channel": NotificationChannel.BOTH,
        "subject": "Completed — {{ subject }}",
        "body": "The workflow '{{ subject }}' has completed.\n",
    },
    NotificationType.POLICY_ASSIGNED: {
        "name": "Policy assigned",
        "channel": NotificationChannel.BOTH,
        "subject": "Action required — please acknowledge {{ policy_title }}",
        "body": (
            "You have been assigned the policy '{{ policy_title }}' "
            "({{ policy_version }}). Please review and acknowledge it"
            "{% if due_date %} by {{ due_date }}{% endif %}.\n"
        ),
    },
    NotificationType.POLICY_PUBLISHED: {
        "name": "Policy version published",
        "channel": NotificationChannel.BOTH,
        "subject": "New version published — {{ policy_title }} {{ policy_version }}",
        "body": (
            "A new version of '{{ policy_title }}' ({{ policy_version }}) "
            "has been published. Please re-read and re-acknowledge it.\n"
        ),
    },
    NotificationType.POLICY_ACK_REMINDER: {
        "name": "Policy acknowledgement reminder",
        "channel": NotificationChannel.BOTH,
        "subject": "Reminder — please acknowledge {{ policy_title }}",
        "body": (
            "This is a reminder that '{{ policy_title }}' "
            "({{ policy_version }}) is awaiting your acknowledgement"
            "{% if due_date %}; due {{ due_date }}{% endif %}.\n"
        ),
    },
    NotificationType.BIRTHDAY: {
        "name": "Employee birthday",
        "channel": NotificationChannel.BOTH,
        "subject": "Birthday today — {{ employee_name }}",
        "body": "{{ employee_name }} celebrates a birthday today.\n",
    },
    NotificationType.CONTRACT_EXPIRY: {
        "name": "Contract expiry reminder",
        "channel": NotificationChannel.BOTH,
        "subject": "Contract expiring — {{ employee_name }}",
        "body": (
            "The contract for {{ employee_name }} expires on "
            "{{ expiry_date }} ({{ days_remaining }} day(s) away).\n"
        ),
    },
    NotificationType.PROBATION_ENDING: {
        "name": "Probation ending reminder",
        "channel": NotificationChannel.BOTH,
        "subject": "Probation ending — {{ employee_name }}",
        "body": (
            "The probation period for {{ employee_name }} ends on "
            "{{ probation_end_date }} ({{ days_remaining }} day(s) away).\n"
        ),
    },
    NotificationType.RETIREMENT_REMINDER: {
        "name": "Retirement approaching",
        "channel": NotificationChannel.BOTH,
        "subject": "Retirement approaching — {{ employee_name }}",
        "body": (
            "{{ employee_name }} is due to retire on {{ retirement_date }} "
            "({{ days_remaining }} day(s) away).\n"
        ),
    },
    NotificationType.GENERAL: {
        "name": "General notification",
        "channel": NotificationChannel.IN_APP,
        "subject": "{{ subject }}",
        "body": "{{ message }}",
    },
}
