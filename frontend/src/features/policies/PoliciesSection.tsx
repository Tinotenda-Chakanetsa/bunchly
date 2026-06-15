/* Policies — backend-driven. Re-exported from AdminPages.tsx so the
   rest of the admin file (Imports, Reports, Settings, Audit Logs) can
   be migrated incrementally. */
import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  KpiCell,
  KpiStrip,
  Meter,
  Modal,
  PageHeader,
  useToast,
} from "@/components/ui";
import {
  bulkAssignPolicy,
  createPolicy,
  listPolicies,
  listMyPolicyAssignments,
  acknowledgePolicy,
  type Policy,
} from "@/api/hr";
import { listEmployees } from "@/api/employees";
import { useAuth } from "@/store/auth";

const CATEGORIES: Array<{ value: string; label: string; tone: "red" | "yellow" | "blue" | "soft" }> = [
  { value: "hr_policy", label: "HR policy", tone: "blue" },
  { value: "health_safety", label: "Health & safety", tone: "yellow" },
  { value: "it_acceptable_use", label: "IT / acceptable use", tone: "yellow" },
  { value: "code_of_conduct", label: "Code of conduct", tone: "red" },
  { value: "privacy", label: "Privacy / data protection", tone: "blue" },
  { value: "compliance", label: "Regulatory / compliance", tone: "blue" },
  { value: "other", label: "Other", tone: "soft" },
];

function categoryTone(code: string) {
  return CATEGORIES.find((c) => c.value === code)?.tone || "soft";
}

function NewPolicyModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [code, setCode] = useState("");
  const [category, setCategory] = useState("hr_policy");
  const [description, setDescription] = useState("");
  const [mandatory, setMandatory] = useState(true);

  const create = useMutation({
    mutationFn: createPolicy,
    onSuccess: (p) => {
      toast.push(`Policy '${p.title}' published`, "success");
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      onClose();
      setTitle("");
      setCode("");
      setDescription("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not publish policy",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || !code.trim()) {
      toast.push("Title and code are required", "error");
      return;
    }
    create.mutate({
      title: title.trim(),
      code: code.trim(),
      category,
      description: description.trim(),
      requires_acknowledgement: mandatory,
    });
  }
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Publish new policy"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Publishing…" : "Publish"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Title</label>
            <input
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Acceptable Use Policy"
              autoFocus
            />
          </div>
          <div className="field">
            <label>Code</label>
            <input
              className="input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="POL-AUP"
            />
          </div>
          <div className="field">
            <label>Category</label>
            <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Description</label>
            <textarea
              className="textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What the policy covers and who it applies to."
            />
          </div>
          <label className="checkbox" style={{ gridColumn: "1 / -1" }}>
            <input
              type="checkbox"
              checked={mandatory}
              onChange={(e) => setMandatory(e.target.checked)}
            />
            Mandatory acknowledgement
          </label>
        </div>
      </form>
    </Modal>
  );
}

function PolicyRow({
  policy,
  myAssignmentId,
  canAcknowledge,
}: {
  policy: Policy;
  myAssignmentId?: string;
  canAcknowledge: boolean;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const total = policy.assignment_count ?? 0;
  const pending = policy.pending_count ?? 0;
  const acknowledged = Math.max(0, total - pending);
  const pct = total === 0 ? 0 : Math.round((acknowledged / total) * 100);
  const done = total > 0 && pct === 100;
  const ver = policy.current_version_detail?.version || "—";
  const effective = policy.current_version_detail?.effective_date || "—";

  const assignAll = useMutation({
    mutationFn: async () => {
      // The backend's bulk-assign requires an explicit, non-empty list
      // of employee UUIDs (there's no `assign_all` flag).
      const allEmployees = await listEmployees({ page: 1 });
      const ids = (allEmployees.results ?? []).map((e) => e.id);
      if (ids.length === 0) {
        throw new Error("No employees to assign this policy to.");
      }
      return bulkAssignPolicy(policy.id, { employees: ids });
    },
    onSuccess: (data) => {
      toast.push(`Assigned to ${data.assigned} employees`, "success");
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      queryClient.invalidateQueries({ queryKey: ["my-policy-assignments"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail
          || (err as Error)?.message
          || "Could not assign",
        "error",
      ),
  });

  const ack = useMutation({
    mutationFn: () => acknowledgePolicy(myAssignmentId || ""),
    onSuccess: () => {
      toast.push("Policy acknowledged", "success");
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      queryClient.invalidateQueries({ queryKey: ["my-policy-assignments"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not acknowledge",
        "error",
      ),
  });

  return (
    <div className="list-row" style={{ alignItems: "center" }}>
      <div className="row-icon" style={{ background: "var(--mist)", color: "var(--ink-3)" }}>
        <I.scroll size={16} />
      </div>
      <div className="row-main">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
          <span className="row-title">{policy.title}</span>
          <Badge tone={categoryTone(policy.category)}>
            {policy.category_display || policy.category}
          </Badge>
          {policy.requires_acknowledgement && <Badge tone="outline">Mandatory</Badge>}
        </div>
        <div className="row-sub">
          <span style={{ fontFamily: "var(--mono)" }}>{policy.code}</span> · v{ver} · Effective{" "}
          {effective} · {acknowledged} of {total} acknowledged
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 180 }}>
        <div style={{ flex: 1 }}>
          <Meter
            value={acknowledged}
            max={Math.max(total, 1)}
            color={done ? "var(--positive)" : "var(--action)"}
            thin
          />
        </div>
        <span
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: done ? "var(--positive)" : "var(--ink-3)",
            minWidth: 36,
            textAlign: "right",
          }}
        >
          {total === 0 ? "—" : `${pct}%`}
        </span>
      </div>
      {canAcknowledge && myAssignmentId && (
        <Button
          variant="outline"
          size="sm"
          disabled={ack.isPending}
          onClick={() => ack.mutate()}
        >
          {ack.isPending ? "…" : "Acknowledge"}
        </Button>
      )}
      <Button
        variant="ghost"
        size="sm"
        disabled={assignAll.isPending}
        onClick={() => assignAll.mutate()}
      >
        {assignAll.isPending ? "…" : "Assign to all"}
      </Button>
    </div>
  );
}

export function PoliciesPage() {
  const { effectiveRole } = useAuth();
  const [showNew, setShowNew] = useState(false);

  const policies = useQuery({
    queryKey: ["policies"],
    queryFn: () => listPolicies(),
  });
  const myAssignments = useQuery({
    queryKey: ["my-policy-assignments"],
    queryFn: listMyPolicyAssignments,
  });

  const rows = policies.data?.results ?? [];
  const totalAssignments = rows.reduce((a, p) => a + (p.assignment_count ?? 0), 0);
  const totalPending = rows.reduce((a, p) => a + (p.pending_count ?? 0), 0);
  const totalAck = Math.max(0, totalAssignments - totalPending);

  const myPendingByPolicyId = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of myAssignments.data ?? []) {
      if (!a.is_acknowledged) map.set(a.policy, a.id);
    }
    return map;
  }, [myAssignments.data]);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Compliance & governance"
        title="Policies"
        lede={
          policies.isLoading
            ? "Loading…"
            : `${rows.length} policies · ${totalPending} acknowledgements outstanding`
        }
        actions={
          effectiveRole !== "hr" ? undefined : (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<I.plus size={14} />}
              onClick={() => setShowNew(true)}
            >
              New policy
            </Button>
          )
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Policies" value={rows.length} />
        <KpiCell label="Assignments" value={totalAssignments} />
        <KpiCell label="Acknowledged" value={totalAck} />
        <KpiCell label="Pending" value={totalPending} />
      </KpiStrip>
      <Card>
        <div className="list">
          {rows.map((p) => (
            <PolicyRow
              key={p.id}
              policy={p}
              myAssignmentId={myPendingByPolicyId.get(p.id)}
              canAcknowledge={effectiveRole !== "hr"}
            />
          ))}
          {rows.length === 0 && policies.isFetched && (
            <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
              No policies yet.
            </div>
          )}
        </div>
      </Card>
      <NewPolicyModal open={showNew} onClose={() => setShowNew(false)} />
    </div>
  );
}
