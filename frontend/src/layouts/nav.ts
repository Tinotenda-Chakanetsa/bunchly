import type { IconName } from "@/components/icons";

/* Navigation groups, gated by real backend permission codes.

   An item appears when the user holds ANY of the listed `permissions`.
   `is_platform_admin` users bypass every check (see useAuth.hasAnyPerm).

   We deliberately avoid an "effectiveRole" escape hatch here — every
   tenant-level access decision should flow through a real permission
   code defined in apps/accounts/constants.py. If a permission code
   below doesn't match what the backend grants, that is the bug, not
   a missing role check. */
export interface NavItem {
  path: string;
  label: string;
  icon: IconName;
  badge?: number;
  comingSoon?: boolean;
  permissions: string[];
  /** If true, the item is only rendered for users with is_platform_admin=true. */
  platformAdminOnly?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
  /** If true, the whole group is only rendered for platform super-admins. */
  platformAdminOnly?: boolean;
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [{ path: "/", label: "Dashboard", icon: "dashboard", permissions: [] }],
  },
  {
    label: "People",
    items: [
      {
        path: "/people",
        label: "People",
        icon: "users",
        permissions: ["employees.view_employee", "employees.view_team"],
      },
      {
        path: "/organisation",
        label: "Organisation",
        icon: "building",
        permissions: ["organisation.manage", "employees.view_employee"],
      },
      {
        path: "/onboarding",
        label: "Onboarding",
        icon: "rocket",
        permissions: ["onboarding.view", "onboarding.manage"],
      },
      {
        path: "/recruitment",
        label: "Recruitment",
        icon: "briefcase",
        permissions: ["recruitment.view", "recruitment.manage"],
      },
    ],
  },
  {
    label: "Time & Pay",
    items: [
      {
        path: "/leave",
        label: "Leave",
        icon: "calendar",
        permissions: ["leave.view", "leave.apply", "leave.approve", "leave.confirm"],
      },
      {
        path: "/attendance",
        label: "Attendance",
        icon: "clock",
        permissions: ["attendance.view", "attendance.manage", "attendance.clock"],
      },
      {
        path: "/payroll",
        label: "Payroll",
        icon: "money",
        permissions: ["payroll.view", "payroll.manage"],
      },
      {
        // Self-service — every tenant member sees their own published payslips.
        path: "/my-payslips",
        label: "My payslips",
        icon: "money",
        permissions: [],
      },
      {
        path: "/benefits",
        label: "Benefits",
        icon: "heart",
        permissions: ["benefits.view", "benefits.manage", "benefits.enrol"],
      },
      {
        path: "/education-assistance",
        label: "Education Assistance",
        icon: "book",
        permissions: [
          "education.view_all_claims",
          "education.submit_claim",
          "education.review_claim",
          "education.pay_claim",
        ],
      },
    ],
  },
  {
    label: "Develop",
    items: [
      {
        path: "/performance",
        label: "Performance",
        icon: "award",
        permissions: ["performance.manage", "performance.review"],
      },
      {
        path: "/learning",
        label: "Learning",
        icon: "book",
        permissions: ["learning.view", "learning.manage"],
      },
    ],
  },
  {
    label: "Operate",
    items: [
      {
        path: "/documents",
        label: "Documents",
        icon: "document",
        permissions: [
          "documents.view",
          "documents.upload",
          "documents.approve",
          "documents.manage",
        ],
      },
      {
        path: "/policies",
        label: "Policies",
        icon: "scroll",
        permissions: ["policies.view", "policies.manage"],
      },
      {
        path: "/hr-cases",
        label: "HR Cases",
        icon: "message",
        permissions: ["helpdesk.view", "helpdesk.manage"],
      },
      {
        path: "/assets",
        label: "Assets",
        icon: "laptop",
        permissions: ["assets.view", "assets.manage"],
      },
    ],
  },
  {
    label: "Admin",
    items: [
      {
        path: "/imports",
        label: "Imports",
        icon: "upload",
        permissions: ["imports.run"],
      },
      {
        path: "/reports",
        label: "Reports",
        icon: "chart",
        permissions: ["reports.view", "reports.view_executive"],
      },
      // Audit logs are reserved for the Auditor / Compliance role —
      // HR Admins do not get audit.view by default.
      {
        path: "/audit-logs",
        label: "Audit logs",
        icon: "history",
        permissions: ["audit.view"],
      },
      {
        path: "/settings",
        label: "Settings",
        icon: "settings",
        permissions: [
          "tenant.manage_settings",
          "accounts.manage_users",
          "accounts.manage_roles",
        ],
      },
    ],
  },
  /* Platform — only visible to is_platform_admin=true users. While a
     platform admin is impersonating a tenant the tenant-scoped groups
     also appear; otherwise these are the only groups they see. */
  {
    label: "Platform",
    platformAdminOnly: true,
    items: [
      {
        path: "/platform",
        label: "Overview",
        icon: "dashboard",
        permissions: [],
        platformAdminOnly: true,
      },
      {
        path: "/platform/tenants",
        label: "Organisations",
        icon: "globe",
        permissions: [],
        platformAdminOnly: true,
      },
    ],
  },
];
