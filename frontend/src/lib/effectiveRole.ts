/* Derives the prototype's "hr | manager | employee" view from the
   current user's real permissions.

   This drives shape/layout decisions only ("am I viewing the HR
   overview or my own dashboard?"). Hard authorisation gates use real
   permission codes via useAuth.hasPerm — never this role string.

   Order matters:
   1) Platform admins (cross-tenant superusers) get the HR layout.
   2) Holders of HR-wide perms (employees.view_employee or RBAC admin
      perms or tenant-settings perms) get the HR layout.
   3) Holders of team-scoped perms (employees.view_team or any leave
      approval/configuration perm) get the manager layout.
   4) Everyone else gets the employee layout. */

export type EffectiveRole = "hr" | "manager" | "employee";

interface UserLike {
  is_platform_admin?: boolean;
}

const HR_PERMS = [
  "employees.view_employee",
  "accounts.manage_users",
  "accounts.manage_roles",
  "tenant.manage_settings",
  "organisation.manage",
];

const MANAGER_PERMS = [
  "employees.view_team",
  "leave.approve",
  "leave.confirm",
  "performance.review",
];

function hasAny(set: Set<string>, codes: string[]) {
  return codes.some((c) => set.has(c));
}

export function effectiveRoleFrom(
  user: UserLike | null,
  permissions: Set<string>,
): EffectiveRole {
  if (!user) return "employee";
  if (user.is_platform_admin) return "hr";
  if (hasAny(permissions, HR_PERMS)) return "hr";
  if (hasAny(permissions, MANAGER_PERMS)) return "manager";
  return "employee";
}
