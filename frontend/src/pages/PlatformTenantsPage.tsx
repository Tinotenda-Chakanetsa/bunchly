/* Platform-admin tenant directory.
 *
 * Only reachable when the signed-in user has is_platform_admin = true.
 * Backend route: /api/v1/tenants/organisations/ (TenantViewSet, gated
 * by IsPlatformAdmin). Provisioning the first user inside a new tenant
 * still requires the `provision_tenant` management command — creating
 * the tenant row from this UI gives you the shell, then you run:
 *
 *     python manage.py provision_tenant --slug <slug> \
 *       --admin-email <email> --admin-password <pw>
 *
 * to seed the first Organisation Administrator.
 */
import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/store/auth";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  StatusBadge,
  useToast,
} from "@/components/ui";
import {
  activateTenant,
  deactivateTenant,
  listTenants,
  provisionTenant,
  type PlatformTenant,
  type ProvisionTenantResponse,
} from "@/api/platform";

function fmt(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
}

function NewTenantModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();

  /* Tenant fields */
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [domain, setDomain] = useState("");
  const [legalName, setLegalName] = useState("");
  const [industry, setIndustry] = useState("");
  const [country, setCountry] = useState("");

  /* First admin fields */
  const [adminEmail, setAdminEmail] = useState("");
  const [adminFirst, setAdminFirst] = useState("");
  const [adminLast, setAdminLast] = useState("");
  const [adminPassword, setAdminPassword] = useState("");

  /* Success state (replaces the form on a clean provision). */
  const [success, setSuccess] = useState<ProvisionTenantResponse | null>(null);

  function resetAll() {
    setName("");
    setSlug("");
    setDomain("");
    setLegalName("");
    setIndustry("");
    setCountry("");
    setAdminEmail("");
    setAdminFirst("");
    setAdminLast("");
    setAdminPassword("");
    setSuccess(null);
  }

  const mutation = useMutation({
    mutationFn: () =>
      provisionTenant({
        name: name.trim(),
        slug: slug.trim() || undefined,
        domain: domain.trim() || undefined,
        legal_name: legalName.trim() || undefined,
        industry: industry.trim() || undefined,
        country: country.trim() || undefined,
        admin_email: adminEmail.trim(),
        admin_first_name: adminFirst.trim() || undefined,
        admin_last_name: adminLast.trim() || undefined,
        admin_password: adminPassword.trim() || undefined,
      }),
    onSuccess: (result) => {
      toast.push(`Tenant '${result.tenant.name}' provisioned`, "success");
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
      setSuccess(result);
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data;
      const firstKey = data && Object.keys(data)[0];
      const msg =
        firstKey && Array.isArray(data?.[firstKey])
          ? `${firstKey}: ${(data[firstKey] as string[])[0]}`
          : (data as { detail?: string })?.detail || "Could not provision tenant";
      toast.push(msg, "error");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toast.push("Organisation name is required", "error");
      return;
    }
    if (!adminEmail.trim()) {
      toast.push("Admin email is required", "error");
      return;
    }
    mutation.mutate();
  }

  function handleClose() {
    onClose();
    /* Let the close animation play out before wiping success state so
       the success block doesn't flicker back during the next open. */
    setTimeout(resetAll, 200);
  }

  /* ---------------- Success view ---------------- */
  if (success) {
    return (
      <Modal
        open={open}
        onClose={handleClose}
        width={560}
        title="Tenant ready"
        sub={`'${success.tenant.name}' is live and the first admin can sign in now.`}
        footer={
          <Button variant="primary" onClick={handleClose}>
            Done
          </Button>
        }
      >
        <div className="col" style={{ gap: 14 }}>
          <div
            style={{
              padding: 14,
              border: "1px solid var(--hairline)",
              borderRadius: 8,
              background: "var(--card-2)",
              fontSize: 13,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-3)" }}>Tenant</span>
              <span style={{ fontWeight: 600 }}>
                {success.tenant.name} · {success.tenant.slug}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: 8,
              }}
            >
              <span style={{ color: "var(--text-3)" }}>Admin email</span>
              <span style={{ fontFamily: "var(--mono)" }}>
                {success.admin.email}
              </span>
            </div>
          </div>

          {success.one_time_password ? (
            <div
              style={{
                padding: 14,
                border: "1px solid var(--yellow-deep)",
                background: "var(--yellow-soft)",
                borderRadius: 8,
                fontSize: 13,
                color: "var(--ink-3)",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 6 }}>
                One-time password — copy it now
              </div>
              <div
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 14,
                  padding: "8px 10px",
                  background: "var(--card)",
                  borderRadius: 6,
                  userSelect: "all",
                }}
              >
                {success.one_time_password}
              </div>
              <div
                style={{
                  fontSize: 11.5,
                  color: "var(--text-3)",
                  marginTop: 8,
                }}
              >
                We don't store this in clear text anywhere — once you close
                this dialog it's gone. Send it to the admin securely (1Password,
                signed email, etc.) and have them change it on first login.
              </div>
            </div>
          ) : (
            <div
              style={{
                padding: 12,
                border: "1px solid var(--hairline)",
                borderRadius: 8,
                fontSize: 12.5,
                color: "var(--text-2)",
              }}
            >
              The admin uses the password you supplied. They should change
              it on first login from Settings → Profile.
            </div>
          )}
        </div>
      </Modal>
    );
  }

  /* ---------------- Provisioning form ---------------- */
  return (
    <Modal
      open={open}
      onClose={handleClose}
      width={680}
      title="New organisation"
      sub="Creates the tenant, copies in every system role, and seeds the first Organisation Administrator — all in one step."
      footer={
        <>
          <Button variant="ghost" onClick={handleClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !name.trim() || !adminEmail.trim()}
          >
            {mutation.isPending ? "Provisioning…" : "Provision tenant"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} className="col" style={{ gap: 14 }}>
        <SectionHeading>Organisation</SectionHeading>
        <div className="field">
          <label>Display name *</label>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Holdings"
            autoFocus
          />
        </div>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <div className="field">
            <label>Slug (optional)</label>
            <input
              className="input"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="acme-holdings"
            />
          </div>
          <div className="field">
            <label>Primary domain (optional)</label>
            <input
              className="input"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="acme.bunchly.app"
            />
          </div>
        </div>
        <div className="field">
          <label>Legal name (optional)</label>
          <input
            className="input"
            value={legalName}
            onChange={(e) => setLegalName(e.target.value)}
            placeholder="Acme Holdings (Pty) Ltd"
          />
        </div>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <div className="field">
            <label>Industry (optional)</label>
            <input
              className="input"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="Software"
            />
          </div>
          <div className="field">
            <label>Country (optional)</label>
            <input
              className="input"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="ZA"
              maxLength={64}
            />
          </div>
        </div>

        <SectionHeading>First administrator</SectionHeading>
        <div className="field">
          <label>Email *</label>
          <input
            className="input"
            type="email"
            value={adminEmail}
            onChange={(e) => setAdminEmail(e.target.value)}
            placeholder="owner@acme.example"
          />
        </div>
        <div className="grid grid-2" style={{ gap: 12 }}>
          <div className="field">
            <label>First name (optional)</label>
            <input
              className="input"
              value={adminFirst}
              onChange={(e) => setAdminFirst(e.target.value)}
            />
          </div>
          <div className="field">
            <label>Last name (optional)</label>
            <input
              className="input"
              value={adminLast}
              onChange={(e) => setAdminLast(e.target.value)}
            />
          </div>
        </div>
        <div className="field">
          <label>Password (optional)</label>
          <input
            className="input"
            type="password"
            value={adminPassword}
            onChange={(e) => setAdminPassword(e.target.value)}
            placeholder="Leave blank to auto-generate a one-time password"
            minLength={8}
          />
          <div
            style={{
              fontSize: 11.5,
              color: "var(--text-3)",
              marginTop: 4,
            }}
          >
            Leaving this blank generates a secure one-time password we'll
            show you exactly once on the next screen.
          </div>
        </div>
      </form>
    </Modal>
  );
}

/* Small section header used inside the provisioning form. */
function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 11,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        fontWeight: 600,
        color: "var(--text-3)",
        marginTop: 4,
      }}
    >
      {children}
    </div>
  );
}

export default function PlatformTenantsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const { impersonateTenant } = useAuth();
  const [search, setSearch] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [enteringId, setEnteringId] = useState<string | null>(null);

  const tenantsQ = useQuery({
    queryKey: ["platform-tenants"],
    queryFn: () => listTenants({ page_size: 200 } as { page?: number }),
  });

  const tenants: PlatformTenant[] = tenantsQ.data?.results ?? [];

  const filtered = useMemo(() => {
    if (!search.trim()) return tenants;
    const q = search.trim().toLowerCase();
    return tenants.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.slug.toLowerCase().includes(q) ||
        (t.legal_name || "").toLowerCase().includes(q),
    );
  }, [search, tenants]);

  const stats = useMemo(() => {
    const active = tenants.filter((t) => t.is_active).length;
    const inactive = tenants.length - active;
    return { total: tenants.length, active, inactive };
  }, [tenants]);

  const activate = useMutation({
    mutationFn: (id: string) => activateTenant(id),
    onSuccess: () => {
      toast.push("Tenant activated", "success");
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
    },
    onError: () => toast.push("Could not activate tenant", "error"),
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => deactivateTenant(id),
    onSuccess: () => {
      toast.push("Tenant deactivated — users cannot sign in", "success");
      queryClient.invalidateQueries({ queryKey: ["platform-tenants"] });
    },
    onError: () => toast.push("Could not deactivate tenant", "error"),
  });

  function toggleActive(t: PlatformTenant) {
    if (t.is_active) {
      if (!confirm(`Deactivate ${t.name}? Users in this tenant will be blocked at login.`)) {
        return;
      }
      deactivate.mutate(t.id);
    } else {
      activate.mutate(t.id);
    }
  }

  async function enter(t: PlatformTenant) {
    if (!t.is_active) {
      toast.push("Tenant is deactivated — activate it first.", "error");
      return;
    }
    const ok = confirm(
      `Enter ${t.name} as platform admin?\n\n` +
        "Every action you take inside the tenant is recorded in that " +
        "tenant's audit log. Use this only for legitimate support tasks.",
    );
    if (!ok) return;
    setEnteringId(t.id);
    try {
      await impersonateTenant(t.id);
      toast.push(`Now viewing ${t.name}`, "success");
      navigate("/");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      toast.push(detail || "Could not enter tenant", "error");
    } finally {
      setEnteringId(null);
    }
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Platform · super-admin"
        title="Organisations"
        lede={
          tenantsQ.isLoading
            ? "Loading…"
            : `${stats.total} tenant${stats.total === 1 ? "" : "s"} · ${stats.active} active`
        }
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<I.plus size={14} />}
            onClick={() => setShowNew(true)}
          >
            New organisation
          </Button>
        }
      />

      <KpiStrip cols={3} style={{ marginBottom: 20 }}>
        <KpiCell label="Total" value={stats.total} sub="Across the platform" />
        <KpiCell label="Active" value={stats.active} sub="Users can sign in" />
        <KpiCell label="Inactive" value={stats.inactive} sub="Sign-in blocked" />
      </KpiStrip>

      <Card>
        <CardHead
          title="Organisation directory"
          sub="Manage every tenant Bunchly hosts. Activate / deactivate is immediate."
          action={
            <input
              className="input"
              placeholder="Search by name, slug, legal name…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ maxWidth: 260, height: 32 }}
            />
          }
        />
        {tenantsQ.isLoading ? (
          <div className="card-body" style={{ color: "var(--text-3)" }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="empty" style={{ margin: 16 }}>
            <div className="title">
              {search ? "No matches" : "No tenants yet"}
            </div>
            <div className="lede">
              {search
                ? "Try a different search term."
                : "Click New organisation to create your first tenant."}
            </div>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Organisation</th>
                <th>Slug</th>
                <th>Country</th>
                <th>Onboarded</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr key={t.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{t.name}</div>
                    {t.legal_name && (
                      <div style={{ fontSize: 11.5, color: "var(--text-3)" }}>
                        {t.legal_name}
                      </div>
                    )}
                  </td>
                  <td>
                    <Badge tone="outline">{t.slug}</Badge>
                  </td>
                  <td className="muted">{t.country || "—"}</td>
                  <td className="muted num">{fmt(t.onboarded_at)}</td>
                  <td>
                    <StatusBadge status={t.is_active ? "Active" : "Inactive"} />
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: 6 }}>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => enter(t)}
                        disabled={!t.is_active || enteringId === t.id}
                        title={
                          t.is_active
                            ? "Enter tenant as platform admin (audited)"
                            : "Activate the tenant first"
                        }
                      >
                        {enteringId === t.id ? "Entering…" : "Enter"}
                      </Button>
                      <Button
                        variant={t.is_active ? "outline" : "primary"}
                        size="sm"
                        onClick={() => toggleActive(t)}
                        disabled={activate.isPending || deactivate.isPending}
                      >
                        {t.is_active ? "Deactivate" : "Activate"}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <NewTenantModal open={showNew} onClose={() => setShowNew(false)} />
    </div>
  );
}
