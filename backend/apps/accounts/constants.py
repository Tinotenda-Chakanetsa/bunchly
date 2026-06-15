"""RBAC catalogue: permission codenames and default role definitions.

These are *templates*. On tenant provisioning the system roles below are
copied into the tenant so each organisation can customise them without
affecting others. Nothing here is hard-coded into business logic — code
only ever checks a codename string via ``user.has_perm_code``.
"""
from __future__ import annotations

# --- Permission catalogue --------------------------------------------------
# (code, human name, module)
PERMISSIONS: list[tuple[str, str, str]] = [
    # Organisation & access control
    ("tenant.manage_settings", "Manage organisation settings", "organisation"),
    ("accounts.manage_users", "Manage users & invitations", "accounts"),
    ("accounts.manage_roles", "Manage roles & permissions", "accounts"),
    # Employees / core HR
    ("employees.view_employee", "View employee records", "employees"),
    ("employees.view_own", "View own employee profile", "employees"),
    ("employees.add_employee", "Create employee records", "employees"),
    ("employees.change_employee", "Edit employee records", "employees"),
    ("employees.archive_employee", "Archive/terminate employees", "employees"),
    ("employees.view_salary", "View salary & bank details", "employees"),
    ("employees.view_team", "View direct reports", "employees"),
    # Organisation structure
    ("organisation.manage", "Manage departments, positions, structure", "organisation"),
    # Leave
    ("leave.view", "View leave records", "leave"),
    ("leave.apply", "Apply for leave", "leave"),
    ("leave.approve", "Approve/reject leave (manager)", "leave"),
    ("leave.confirm", "Confirm leave (HR)", "leave"),
    ("leave.configure", "Configure leave types & rules", "leave"),
    # Workflows / approvals
    ("workflows.configure", "Configure approval workflows", "workflows"),
    ("workflows.view", "View all workflow instances", "workflows"),
    ("workflows.act", "Act on assigned workflow items", "workflows"),
    # Benefits
    ("benefits.view", "View benefit types & enrolments", "benefits"),
    ("benefits.manage", "Configure benefits & approve enrolments", "benefits"),
    ("benefits.enrol", "Enrol in benefits", "benefits"),
    # Onboarding / offboarding
    ("onboarding.view", "View onboarding & offboarding programmes", "onboarding"),
    ("onboarding.manage", "Configure & run onboarding/offboarding", "onboarding"),
    # Performance management
    ("performance.manage", "Configure cycles & manage all performance data", "performance"),
    ("performance.review", "Conduct performance reviews", "performance"),
    # Learning & development
    ("learning.view", "View training courses & records", "learning"),
    ("learning.manage", "Manage courses, assignments & records", "learning"),
    # Asset management
    ("assets.view", "View assets & assignments", "assets"),
    ("assets.manage", "Manage assets & assignments", "assets"),
    # HR helpdesk / case management
    ("helpdesk.view", "View all HR cases", "helpdesk"),
    ("helpdesk.manage", "Handle & resolve HR cases", "helpdesk"),
    # Time & attendance
    ("attendance.view", "View all attendance & timesheets", "attendance"),
    ("attendance.manage", "Manage shifts, attendance & timesheets", "attendance"),
    ("attendance.clock", "Clock in/out & record own attendance", "attendance"),
    # Policies & acknowledgements
    ("policies.view", "View policies & assignments", "policies"),
    ("policies.manage", "Manage policies, versions & assignments", "policies"),
    # Documents
    ("documents.view", "View employee documents", "documents"),
    ("documents.upload", "Upload documents", "documents"),
    ("documents.approve", "Approve uploaded documents", "documents"),
    ("documents.manage", "Manage document categories", "documents"),
    # Education assistance
    ("education.view_rules", "View education assistance rules", "education"),
    ("education.configure", "Configure education assistance rules", "education"),
    ("education.submit_claim", "Submit education claims", "education"),
    ("education.review_claim", "Review education claims (HR)", "education"),
    ("education.pay_claim", "Mark education claims as paid (Finance)", "education"),
    ("education.view_all_claims", "View all education claims", "education"),
    # Imports
    ("imports.run", "Run bulk data imports", "imports"),
    # Reports & analytics
    ("reports.view", "View & export reports", "reports"),
    ("reports.view_executive", "View executive dashboards", "reports"),
    # Notifications
    ("notifications.configure", "Configure notification engine", "notifications"),
    # Audit
    ("audit.view", "View audit logs", "audit"),
    # Payroll
    ("payroll.view", "View payroll data", "payroll"),
    ("payroll.manage", "Manage payroll & payslips", "payroll"),
    # Recruitment
    ("recruitment.view", "View recruitment & candidates", "recruitment"),
    ("recruitment.manage", "Manage recruitment & candidates", "recruitment"),
]

ALL_PERMISSION_CODES = [code for code, _, _ in PERMISSIONS]

# Self-service permissions every member of a tenant gets by default,
# regardless of their administrative role. Rationale: an HR Admin,
# Finance Officer, or Auditor is *also* an employee of the organisation
# and needs to apply for their own leave, clock in, upload their own
# documents, submit their own school-fees claim, and so on.
SELF_SERVICE_PERMISSIONS = [
    "employees.view_own",
    "leave.apply",
    "attendance.clock",
    "documents.upload",
    "education.submit_claim",
    "benefits.view",
    "benefits.enrol",
    "onboarding.view",
    "learning.view",
    "assets.view",
    "policies.view",
]


# --- Default (system) roles ------------------------------------------------
# "*" grants the wildcard — every permission within the tenant.
DEFAULT_ROLES: dict[str, dict] = {
    "Organisation Administrator": {
        "description": "Full access within the organisation.",
        "permissions": ["*"],
    },
    "HR Administrator": {
        "description": "Manages employee records, leave, documents and claims.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "employees.view_employee", "employees.add_employee",
            "employees.change_employee", "employees.archive_employee",
            "employees.view_team", "organisation.manage",
            "leave.view", "leave.confirm", "leave.configure",
            "workflows.configure", "workflows.view", "workflows.act",
            "benefits.manage",
            "documents.view", "documents.approve", "documents.manage",
            "education.view_rules", "education.configure",
            "education.review_claim", "education.view_all_claims",
            "recruitment.view", "recruitment.manage",
            "onboarding.manage",
            "performance.manage", "performance.review",
            "learning.manage",
            "assets.manage",
            "helpdesk.view", "helpdesk.manage",
            "attendance.view", "attendance.manage",
            "policies.manage",
            "imports.run", "reports.view", "notifications.configure",
        ],
    },
    "Line Manager": {
        "description": "Manages and approves for direct reports.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "employees.view_team", "leave.view", "leave.approve",
            "workflows.act", "documents.view", "reports.view",
            "performance.review",
        ],
    },
    "Employee": {
        "description": "Self-service access to own records.",
        "permissions": SELF_SERVICE_PERMISSIONS,
    },
    "Accounts / Finance Officer": {
        "description": "Processes approved claims and payments.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "education.view_all_claims", "education.pay_claim",
            "reports.view", "payroll.view",
        ],
    },
    "Executive / Head of HR": {
        "description": "Strategic dashboards and workforce analytics.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "employees.view_employee", "reports.view",
            "reports.view_executive", "education.view_all_claims",
            "attendance.view",
        ],
    },
    "Recruiter": {
        "description": "Manages job postings, candidates and interviews.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "recruitment.view", "recruitment.manage", "employees.view_employee",
        ],
    },
    "Payroll Officer": {
        "description": "Manages payroll data, payslips and exports.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "payroll.view", "payroll.manage", "employees.view_salary",
            "reports.view", "attendance.view",
        ],
    },
    "Auditor": {
        "description": "Read-only compliance and audit access.",
        "permissions": SELF_SERVICE_PERMISSIONS + [
            "audit.view", "reports.view", "employees.view_employee",
        ],
    },
}
