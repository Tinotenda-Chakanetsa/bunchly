import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "@/layouts/AppShell";
import { useAuth } from "@/store/auth";

import RequireAuth from "./RequireAuth";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import PeopleListPage from "@/pages/PeopleListPage";
import EmployeeDetailPage from "@/pages/EmployeeDetailPage";
import LeavePage, { LeaveDetailPage } from "@/pages/LeavePage";
import DocumentsPage, { DocumentDetailPage } from "@/pages/DocumentsPage";
import EducationAssistancePage from "@/pages/EducationAssistancePage";
import BenefitsPage from "@/pages/BenefitsPage";
import OrganisationPage from "@/pages/OrganisationPage";
import RecruitmentPage, { CandidateDetailPage } from "@/pages/RecruitmentPage";
import OnboardingPage, { ProgrammeDetailPage } from "@/pages/OnboardingPage";
import PayrollPage, { PeriodDetailPage } from "@/pages/PayrollPage";
import MyPayslipsPage from "@/pages/MyPayslipsPage";
import PlatformTenantsPage from "@/pages/PlatformTenantsPage";
import PlatformDashboardPage from "@/pages/PlatformDashboardPage";
import AttendancePage from "@/pages/AttendancePage";
import PerformancePage, { ReviewDetailPage } from "@/pages/PerformancePage";
import LearningPage from "@/pages/LearningPage";
import AssetsPage from "@/pages/AssetsPage";
import {
  AuditLogsPage,
  CaseDetailPage,
  HRCasesPage,
  ImportsPage,
  PoliciesPage,
  ReportsPage,
  SettingsPage,
} from "@/pages/AdminPages";
import ComingSoonPage from "@/pages/ComingSoonPage";
import HelpSupportPage from "@/pages/HelpSupportPage";
import NotFoundPage from "@/pages/NotFoundPage";

function Stub({ title, lede }: { title: string; lede?: string }) {
  return <ComingSoonPage title={title} lede={lede} />;
}

/* Platform admins land here when they hit "/". Without impersonation
   they can't see tenant data anyway, so the regular Dashboard would be
   an empty husk for them. */
function HomeRedirect() {
  const { user, impersonating } = useAuth();
  if (user?.is_platform_admin && !impersonating) {
    return <Navigate to="/platform" replace />;
  }
  return <DashboardPage />;
}

/* Route-level guards mirror the sidebar nav permissions (layouts/nav.ts).
   Both must accept the same permission codes so that a user who can see
   the link can actually load the page (and conversely, a deep-linked
   URL still hits the empty-state for unauthorised users). */

const P = {
  people: ["employees.view_employee", "employees.view_team"],
  organisation: ["organisation.manage", "employees.view_employee"],
  onboarding: ["onboarding.view", "onboarding.manage"],
  recruitment: ["recruitment.view", "recruitment.manage"],
  leave: ["leave.view", "leave.apply", "leave.approve", "leave.confirm"],
  attendance: ["attendance.view", "attendance.manage", "attendance.clock"],
  payroll: ["payroll.view", "payroll.manage"],
  benefits: ["benefits.view", "benefits.manage", "benefits.enrol"],
  education: [
    "education.view_all_claims",
    "education.submit_claim",
    "education.review_claim",
    "education.pay_claim",
  ],
  performance: ["performance.manage", "performance.review"],
  learning: ["learning.view", "learning.manage"],
  documents: [
    "documents.view",
    "documents.upload",
    "documents.approve",
    "documents.manage",
  ],
  policies: ["policies.view", "policies.manage"],
  helpdesk: ["helpdesk.view", "helpdesk.manage"],
  assets: ["assets.view", "assets.manage"],
  imports: ["imports.run"],
  reports: ["reports.view", "reports.view_executive"],
  audit: ["audit.view"],
  settings: [
    "tenant.manage_settings",
    "accounts.manage_users",
    "accounts.manage_roles",
  ],
};

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="*"
        element={
          <RequireAuth>
            <AppShell>
              <Routes>
                <Route index element={<HomeRedirect />} />

                <Route
                  path="people"
                  element={
                    <RequireAuth permissions={P.people}>
                      <PeopleListPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="people/:id"
                  element={
                    <RequireAuth permissions={P.people}>
                      <EmployeeDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="leave"
                  element={
                    <RequireAuth permissions={P.leave}>
                      <LeavePage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="leave/:id"
                  element={
                    <RequireAuth permissions={P.leave}>
                      <LeaveDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="documents"
                  element={
                    <RequireAuth permissions={P.documents}>
                      <DocumentsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="documents/:id"
                  element={
                    <RequireAuth permissions={P.documents}>
                      <DocumentDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="education-assistance"
                  element={
                    <RequireAuth permissions={P.education}>
                      <EducationAssistancePage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="benefits"
                  element={
                    <RequireAuth permissions={P.benefits}>
                      <BenefitsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="organisation"
                  element={
                    <RequireAuth permissions={P.organisation}>
                      <OrganisationPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="recruitment"
                  element={
                    <RequireAuth permissions={P.recruitment}>
                      <RecruitmentPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="recruitment/:id"
                  element={
                    <RequireAuth permissions={P.recruitment}>
                      <CandidateDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="onboarding"
                  element={
                    <RequireAuth permissions={P.onboarding}>
                      <OnboardingPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="onboarding/:id"
                  element={
                    <RequireAuth permissions={P.onboarding}>
                      <ProgrammeDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="payroll"
                  element={
                    <RequireAuth permissions={P.payroll}>
                      <PayrollPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="payroll/:id"
                  element={
                    <RequireAuth permissions={P.payroll}>
                      <PeriodDetailPage />
                    </RequireAuth>
                  }
                />

                {/* Employee self-service — open to every tenant member with an
                    Employee profile (backend enforces own-data scoping). */}
                <Route
                  path="my-payslips"
                  element={
                    <RequireAuth>
                      <MyPayslipsPage />
                    </RequireAuth>
                  }
                />

                {/* Platform super-admin only — manage every tenant on the
                    Bunchly instance. Backend is also gated by IsPlatformAdmin. */}
                <Route
                  path="platform"
                  element={
                    <RequireAuth platformAdmin>
                      <PlatformDashboardPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="platform/tenants"
                  element={
                    <RequireAuth platformAdmin>
                      <PlatformTenantsPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="attendance"
                  element={
                    <RequireAuth permissions={P.attendance}>
                      <AttendancePage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="performance"
                  element={
                    <RequireAuth permissions={P.performance}>
                      <PerformancePage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="performance/:id"
                  element={
                    <RequireAuth permissions={P.performance}>
                      <ReviewDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="learning"
                  element={
                    <RequireAuth permissions={P.learning}>
                      <LearningPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="assets"
                  element={
                    <RequireAuth permissions={P.assets}>
                      <AssetsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="policies"
                  element={
                    <RequireAuth permissions={P.policies}>
                      <PoliciesPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="hr-cases"
                  element={
                    <RequireAuth permissions={P.helpdesk}>
                      <HRCasesPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="hr-cases/:id"
                  element={
                    <RequireAuth permissions={P.helpdesk}>
                      <CaseDetailPage />
                    </RequireAuth>
                  }
                />

                <Route
                  path="imports"
                  element={
                    <RequireAuth permissions={P.imports}>
                      <ImportsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="reports"
                  element={
                    <RequireAuth permissions={P.reports}>
                      <ReportsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="audit-logs"
                  element={
                    <RequireAuth permissions={P.audit}>
                      <AuditLogsPage />
                    </RequireAuth>
                  }
                />
                <Route
                  path="settings"
                  element={
                    <RequireAuth permissions={P.settings}>
                      <SettingsPage />
                    </RequireAuth>
                  }
                />

                <Route path="help" element={<HelpSupportPage />} />
                <Route
                  path="ai"
                  element={<Stub title="Bunchly AI" lede="Ask questions across your HR data — coming soon." />}
                />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </AppShell>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
