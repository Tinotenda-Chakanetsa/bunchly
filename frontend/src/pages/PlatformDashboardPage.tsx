/* Platform admin home page.
 *
 * Deliberately renders ZERO tenant HR data — only counts, statuses,
 * provisioning history. The spec is explicit that platform admins
 * "Cannot casually access tenant HR data unless explicitly elevated and
 * audited" (§8.A). To see anything inside a tenant, the admin must
 * impersonate from this page, which is logged + banner-warned.
 */
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  PageHeader,
  StatusBadge,
} from "@/components/ui";
import { listTenants } from "@/api/platform";
import { useAuth } from "@/store/auth";

function fmt(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
}

export default function PlatformDashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const tenantsQ = useQuery({
    queryKey: ["platform-tenants"],
    queryFn: () => listTenants({ page: 1 } as { page?: number }),
  });

  const tenants = tenantsQ.data?.results ?? [];
  const stats = useMemo(() => {
    const active = tenants.filter((t) => t.is_active).length;
    return {
      total: tenants.length,
      active,
      inactive: tenants.length - active,
    };
  }, [tenants]);

  const recent = useMemo(() => {
    return [...tenants]
      .sort((a, b) => {
        const ta = a.onboarded_at ? new Date(a.onboarded_at).getTime() : 0;
        const tb = b.onboarded_at ? new Date(b.onboarded_at).getTime() : 0;
        return tb - ta;
      })
      .slice(0, 5);
  }, [tenants]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Platform · super-admin"
        title={`Welcome back, ${user?.first_name || "Admin"}`}
        lede={
          tenantsQ.isLoading
            ? "Loading platform stats…"
            : "Manage every organisation Bunchly hosts. No tenant data is shown here — enter a tenant to view its records."
        }
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<I.plus size={14} />}
            onClick={() => navigate("/platform/tenants")}
          >
            Provision new
          </Button>
        }
      />

      <KpiStrip cols={3} style={{ marginBottom: 20 }}>
        <KpiCell label="Total tenants" value={stats.total} sub="On this instance" />
        <KpiCell label="Active" value={stats.active} sub="Users can sign in" />
        <KpiCell label="Inactive" value={stats.inactive} sub="Sign-in blocked" />
      </KpiStrip>

      <div className="grid" style={{ gridTemplateColumns: "1.4fr 1fr", gap: 16 }}>
        <Card>
          <CardHead
            title="Recently provisioned"
            sub="Latest five tenants"
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/platform/tenants")}
              >
                See all →
              </Button>
            }
          />
          {tenantsQ.isLoading ? (
            <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
          ) : recent.length === 0 ? (
            <div className="empty" style={{ margin: 16 }}>
              <div className="title">No tenants yet</div>
              <div className="lede">
                Click <strong>Provision new</strong> to create your first
                organisation.
              </div>
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Organisation</th>
                  <th>Slug</th>
                  <th>Onboarded</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((t) => (
                  <tr
                    key={t.id}
                    className="clickable"
                    onClick={() => navigate("/platform/tenants")}
                  >
                    <td>
                      <div style={{ fontWeight: 600 }}>{t.name}</div>
                      {t.legal_name && (
                        <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                          {t.legal_name}
                        </div>
                      )}
                    </td>
                    <td className="muted">{t.slug}</td>
                    <td className="muted num">{fmt(t.onboarded_at)}</td>
                    <td>
                      <StatusBadge status={t.is_active ? "Active" : "Inactive"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <CardHead title="Platform admin reminders" />
          <div className="card-body" style={{ paddingTop: 0 }}>
            <div
              style={{
                display: "flex",
                gap: 10,
                padding: "12px 0",
                borderBottom: "1px solid var(--hairline-2)",
              }}
            >
              <I.shield size={16} style={{ color: "var(--yellow-deep)", flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>
                  Tenant data is hidden by default
                </div>
                <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
                  Enter a tenant explicitly via the Organisations page to
                  view its employees, leave or payroll. Every entry is
                  recorded in that tenant's audit log.
                </div>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                gap: 10,
                padding: "12px 0",
                borderBottom: "1px solid var(--hairline-2)",
              }}
            >
              <I.history size={16} style={{ color: "var(--text-3)", flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>
                  Impersonation is audited
                </div>
                <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
                  Start and end events are recorded. Tenant owners can review
                  who entered, when, and from where in Audit Logs.
                </div>
              </div>
            </div>
            <div
              style={{
                display: "flex",
                gap: 10,
                padding: "12px 0",
              }}
            >
              <I.info size={16} style={{ color: "var(--action)", flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>
                  Use the CLI for batch operations
                </div>
                <div style={{ fontSize: 12, color: "var(--text-3)" }}>
                  Provisioning + role-template refresh are both available as
                  management commands (<code>provision_tenant</code>,{" "}
                  <code>seed_rbac --refresh-tenants</code>).
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
