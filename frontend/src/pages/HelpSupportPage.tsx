/* Help & Support — the user-facing entry point for getting help.

   Backend integration: a submitted contact form raises a real HRCase via
   POST /hr-cases/, the same lifecycle the HR team works on every day.
   "My recent tickets" is a filtered view of /hr-cases/ scoped to cases
   the current user raised. The FAQ section is in-memory — the questions
   are common-knowledge, not data the backend tracks. */
import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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
  listCaseCategories,
  listHRCases,
  raiseHRCase,
} from "@/api/hr";
import { useAuth } from "@/store/auth";

interface Faq {
  q: string;
  a: string;
  category: "leave" | "documents" | "performance" | "policies" | "account" | "payroll";
}

const FAQS: Faq[] = [
  {
    category: "leave",
    q: "How do I request leave?",
    a: "Open the Leave page from the sidebar, click \"Request leave\", pick a leave type and date range, and submit. Your line manager will receive the approval task; if HR confirmation is required for the leave type, it goes to HR after the manager approves.",
  },
  {
    category: "leave",
    q: "When does my leave balance refresh?",
    a: "Balances accrue according to the leave type. Annual leave accrues monthly; sick leave is granted as an annual lump on Jan 1. Carry-forward (where allowed) happens automatically and is capped per the leave type's rules.",
  },
  {
    category: "documents",
    q: "What document types can I upload?",
    a: "By default: PDF, DOCX, JPG, JPEG and PNG up to 15 MB. Your organisation may have customised this — if your upload is rejected, check the message for the allowed list.",
  },
  {
    category: "documents",
    q: "Why does my document show \"Awaiting review\"?",
    a: "Some categories (bank details, contracts, medical certificates) require HR approval before they're considered verified. They stay in \"Awaiting review\" until an HR Administrator approves or rejects them.",
  },
  {
    category: "performance",
    q: "When can I see my performance review?",
    a: "Reviews become visible after your reviewer submits the draft. You then acknowledge it, and it's finalised when complete. The Performance page lists every review you're involved in.",
  },
  {
    category: "policies",
    q: "I see policy assignments — what do they mean?",
    a: "When HR publishes a policy with \"Mandatory acknowledgement\", every employee is asked to read and acknowledge it. Until you click Acknowledge, the assignment shows as pending in the Policies page.",
  },
  {
    category: "account",
    q: "I can't see a sidebar item I expected to see.",
    a: "Bunchly hides items you don't have permission for. If a feature you need is missing, ask your HR Administrator (or Organisation Administrator) to grant the matching role.",
  },
  {
    category: "account",
    q: "How do I switch between organisations?",
    a: "If you belong to more than one Bunchly tenant, your profile menu in the top-right has a tenant switcher. Switching reloads your permissions for the new tenant.",
  },
  {
    category: "payroll",
    q: "Why don't I see Payroll in my sidebar?",
    a: "Payroll is restricted to users with the Payroll Officer or Organisation Administrator role. If you should be seeing it, ask HR to assign you the right role.",
  },
];

const FAQ_CATEGORIES: Array<{ value: Faq["category"] | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "leave", label: "Leave" },
  { value: "documents", label: "Documents" },
  { value: "performance", label: "Performance" },
  { value: "policies", label: "Policies" },
  { value: "payroll", label: "Payroll" },
  { value: "account", label: "Account" },
];

function FaqItem({ faq }: { faq: Faq }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      style={{
        borderBottom: "1px solid var(--hairline-2)",
        padding: "14px 0",
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          width: "100%",
          alignItems: "center",
          gap: 12,
          background: "transparent",
          border: "none",
          padding: 0,
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <I.chevron
          size={14}
          style={{
            color: "var(--text-3)",
            transform: open ? "rotate(90deg)" : "rotate(0deg)",
            transition: "transform 0.15s",
          }}
        />
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--ink-3)", flex: 1 }}>
          {faq.q}
        </span>
        <Badge tone="outline">{faq.category}</Badge>
      </button>
      {open && (
        <div
          style={{
            marginLeft: 26,
            marginTop: 8,
            fontSize: 13,
            color: "var(--text-2)",
            lineHeight: 1.6,
          }}
        >
          {faq.a}
        </div>
      )}
    </div>
  );
}

function ContactModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const categories = useQuery({
    queryKey: ["case-categories"],
    queryFn: listCaseCategories,
    enabled: open,
  });
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");

  const raise = useMutation({
    mutationFn: raiseHRCase,
    onSuccess: (rec) => {
      toast.push(
        `We've got it — case ${rec.case_number || rec.id.slice(0, 8)} created.`,
        "success",
      );
      queryClient.invalidateQueries({ queryKey: ["hr-cases"] });
      queryClient.invalidateQueries({ queryKey: ["my-cases"] });
      onClose();
      setSubject("");
      setDescription("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not submit your question",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) {
      toast.push("Please add a subject and details", "error");
      return;
    }
    raise.mutate({
      category: category || undefined,
      subject: subject.trim(),
      description: description.trim(),
      priority,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Contact support"
      sub="Your message lands as an HR case. We'll respond by the SLA on the case."
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={raise.isPending}>
            {raise.isPending ? "Sending…" : "Send"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="field" style={{ marginBottom: 12 }}>
          <label>Subject</label>
          <input
            className="input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Short summary of what you need"
            autoFocus
          />
        </div>
        <div className="grid grid-2" style={{ marginBottom: 12 }}>
          <div className="field">
            <label>Topic</label>
            <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">{categories.isLoading ? "Loading…" : "General"}</option>
              {(categories.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Priority</label>
            <select
              className="select"
              value={priority}
              onChange={(e) =>
                setPriority(e.target.value as "low" | "medium" | "high" | "urgent")
              }
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
          </div>
        </div>
        <div className="field">
          <label>Details</label>
          <textarea
            className="textarea"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Walk us through it — error messages, steps you've tried, anything useful."
            rows={6}
          />
        </div>
      </form>
    </Modal>
  );
}

export default function HelpSupportPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Faq["category"] | "all">("all");
  const [showContact, setShowContact] = useState(false);

  const cases = useQuery({
    queryKey: ["my-cases"],
    queryFn: () => listHRCases(),
  });
  const myCases = cases.data?.results ?? [];

  const faqs = useMemo(() => {
    let r = FAQS;
    if (category !== "all") r = r.filter((f) => f.category === category);
    if (query) {
      const s = query.toLowerCase();
      r = r.filter((f) => (f.q + f.a).toLowerCase().includes(s));
    }
    return r;
  }, [query, category]);

  const openCount = myCases.filter((c) => c.status === "open").length;
  const resolvedCount = myCases.filter((c) => c.status === "resolved").length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="We're here to help"
        title="Help & support"
        lede={
          user
            ? `Hi ${user.first_name || user.full_name?.split(" ")[0] || "there"} — search our help library or open a support case.`
            : "Search our help library or open a support case."
        }
        actions={
          <Button
            variant="primary"
            size="sm"
            leftIcon={<I.message size={14} />}
            onClick={() => setShowContact(true)}
          >
            Contact support
          </Button>
        }
      />

      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Articles" value={FAQS.length} sub="In help library" />
        <KpiCell label="My open cases" value={openCount} />
        <KpiCell label="My resolved cases" value={resolvedCount} />
        <KpiCell label="Response SLA" value="≤ 72h" sub="Per case category" />
      </KpiStrip>

      <div className="grid" style={{ gridTemplateColumns: "1.5fr 1fr", gap: 20 }}>
        <div className="col" style={{ gap: 20 }}>
          <Card>
            <CardHead title="Search the help library" />
            <div className="card-body">
              <div className="toolbar-search" style={{ width: "100%", marginBottom: 12 }}>
                <span className="icon"><I.search size={16} /></span>
                <input
                  placeholder="Try 'leave balance' or 'document expiry'…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 4 }}>
                {FAQ_CATEGORIES.map((c) => {
                  const active = c.value === category;
                  return (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setCategory(c.value)}
                      className={active ? "btn-ink" : ""}
                      style={{
                        background: active ? undefined : "var(--mist)",
                        color: active ? undefined : "var(--text-2)",
                        border: "none",
                        padding: "5px 12px",
                        borderRadius: 999,
                        fontSize: 12,
                        cursor: "pointer",
                        fontWeight: 500,
                        height: "auto",
                      }}
                    >
                      {c.label}
                    </button>
                  );
                })}
              </div>
              <div style={{ marginTop: 12 }}>
                {faqs.length === 0 ? (
                  <div className="empty" style={{ padding: 28 }}>
                    <div className="title">No articles match</div>
                    <div className="lede">
                      Try a different search, or{" "}
                      <button
                        type="button"
                        onClick={() => setShowContact(true)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "var(--action)",
                          cursor: "pointer",
                          padding: 0,
                          fontSize: 13,
                          textDecoration: "underline",
                        }}
                      >
                        contact support
                      </button>
                      .
                    </div>
                  </div>
                ) : (
                  faqs.map((f, i) => <FaqItem key={i} faq={f} />)
                )}
              </div>
            </div>
          </Card>

          <Card>
            <CardHead
              title="My support cases"
              sub="Tickets you've raised — newest first"
              action={
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate("/hr-cases")}
                >
                  View all
                </Button>
              }
            />
            <div className="card-body" style={{ paddingTop: 0 }}>
              {cases.isLoading ? (
                <div style={{ padding: 20, color: "var(--text-3)" }}>Loading…</div>
              ) : myCases.length === 0 ? (
                <div className="empty" style={{ padding: 24 }}>
                  <div className="title">No cases yet</div>
                  <div className="lede">
                    Open a case from the button above and we'll get back to you.
                  </div>
                </div>
              ) : (
                myCases.slice(0, 5).map((c) => (
                  <div
                    key={c.id}
                    onClick={() => navigate(`/hr-cases/${c.id}`)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "12px 0",
                      borderBottom: "1px solid var(--hairline-2)",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-3)" }}>
                        {c.subject}
                      </div>
                      <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>
                        <span style={{ fontFamily: "var(--mono)" }}>
                          {c.case_number || c.id.slice(0, 8)}
                        </span>
                        {" · "}
                        {c.category_name || "General"}
                        {" · "}
                        Opened {c.created_at.slice(0, 10)}
                      </div>
                    </div>
                    <StatusBadge status={c.status_display || c.status} />
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        <div className="col" style={{ gap: 20 }}>
          <Card>
            <CardHead title="Quick actions" />
            <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <Button
                variant="outline"
                onClick={() => setShowContact(true)}
                leftIcon={<I.message size={14} />}
              >
                Contact support
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate("/hr-cases")}
                leftIcon={<I.history size={14} />}
              >
                View all my cases
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate("/leave")}
                leftIcon={<I.calendar size={14} />}
              >
                Request leave
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate("/documents")}
                leftIcon={<I.document size={14} />}
              >
                My documents
              </Button>
              <Button
                variant="ghost"
                onClick={() => navigate("/policies")}
                leftIcon={<I.scroll size={14} />}
              >
                Acknowledge policies
              </Button>
            </div>
          </Card>

          <Card>
            <CardHead title="Reach us directly" />
            <div className="card-body" style={{ fontSize: 13, color: "var(--text-2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0" }}>
                <I.mail size={14} style={{ color: "var(--text-3)" }} />
                <a
                  href="mailto:hr@bunchly.local"
                  style={{ color: "var(--action)", textDecoration: "none" }}
                >
                  hr@bunchly.local
                </a>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0" }}>
                <I.clock size={14} style={{ color: "var(--text-3)" }} />
                Mon–Fri · 09:00–17:30 (local time)
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0" }}>
                <I.shield size={14} style={{ color: "var(--text-3)" }} />
                Sensitive issues are kept confidential to HR
              </div>
            </div>
          </Card>

          <Card>
            <CardHead title="System info" />
            <div className="card-body" style={{ fontSize: 12.5, color: "var(--text-3)" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "6px 0",
                  borderBottom: "1px solid var(--hairline-2)",
                }}
              >
                <span>Version</span>
                <span style={{ fontFamily: "var(--mono)", color: "var(--ink-3)" }}>
                  Bunchly 1.0
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "6px 0",
                  borderBottom: "1px solid var(--hairline-2)",
                }}
              >
                <span>Signed in as</span>
                <span style={{ color: "var(--ink-3)" }}>
                  {user?.email || "—"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0" }}>
                <span>Status</span>
                <Badge tone="green" dot>All systems normal</Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <ContactModal open={showContact} onClose={() => setShowContact(false)} />
    </div>
  );
}
