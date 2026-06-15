"""Choice enumerations for the employees / core-HR module."""
from django.db import models


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    UNDISCLOSED = "undisclosed", "Prefer not to say"


class MaritalStatus(models.TextChoices):
    SINGLE = "single", "Single"
    MARRIED = "married", "Married"
    DIVORCED = "divorced", "Divorced"
    WIDOWED = "widowed", "Widowed"
    OTHER = "other", "Other"


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full time"
    PART_TIME = "part_time", "Part time"
    CONTRACT = "contract", "Contract"
    TEMPORARY = "temporary", "Temporary"
    INTERN = "intern", "Intern"
    CONSULTANT = "consultant", "Consultant"


class EmploymentStatus(models.TextChoices):
    PROBATION = "probation", "Probation"
    ACTIVE = "active", "Active"
    ON_LEAVE = "on_leave", "On leave"
    SUSPENDED = "suspended", "Suspended"
    NOTICE = "notice", "Serving notice"
    TERMINATED = "terminated", "Terminated"
    RESIGNED = "resigned", "Resigned"
    RETIRED = "retired", "Retired"
    ARCHIVED = "archived", "Archived"


# Statuses that mean the person has left the organisation.
EXITED_STATUSES = {
    EmploymentStatus.TERMINATED,
    EmploymentStatus.RESIGNED,
    EmploymentStatus.RETIRED,
    EmploymentStatus.ARCHIVED,
}


class ContractStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    TERMINATED = "terminated", "Terminated"
    RENEWED = "renewed", "Renewed"


class ChangeType(models.TextChoices):
    HIRE = "hire", "Hire"
    POSITION_CHANGE = "position_change", "Position change"
    DEPARTMENT_TRANSFER = "department_transfer", "Department transfer"
    SALARY_CHANGE = "salary_change", "Salary change"
    MANAGER_CHANGE = "manager_change", "Reporting line change"
    STATUS_CHANGE = "status_change", "Employment status change"
    GRADE_CHANGE = "grade_change", "Grade change"
    CONTRACT_CHANGE = "contract_change", "Contract change"
    CONFIRMATION = "confirmation", "Confirmation / probation passed"
    EXIT = "exit", "Exit / termination"
    OTHER = "other", "Other"
