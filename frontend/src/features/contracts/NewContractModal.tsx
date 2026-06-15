import { useEffect, useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Badge, Button, Modal, useToast } from "@/components/ui";
import {
  createContract,
  generateContractDocument,
  previewContractTemplate,
} from "@/api/employees";
import { downloadBlob } from "@/lib/export";

const CONTRACT_TYPES = [
  { value: "full_time", label: "Full-time (permanent)" },
  { value: "fixed_term", label: "Fixed-term" },
  { value: "part_time", label: "Part-time" },
  { value: "contractor", label: "Contractor" },
  { value: "internship", label: "Internship" },
];

interface Props {
  open: boolean;
  employeeId: string;
  /** Currently picked template id, "" = use built-in layout. */
  templateId: string;
  /** Display name of the picked template. */
  templateName: string;
  /** Every placeholder the template uses, sourced from the templates list.
      This is the source of truth for which fields to render — preview is
      only used to seed their initial values. */
  templateTokens: string[];
  onClose: () => void;
  onSuccess?: () => void;
}

/** ``employer_address`` → ``Employer address``. */
function humanise(token: string): string {
  const s = token.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Fields that benefit from a textarea rather than a single-line input. */
const LONG_HINTS = ["address", "paragraph", "text", "clause", "notes", "summary"];
function isLongToken(token: string): boolean {
  return LONG_HINTS.some((h) => token.toLowerCase().includes(h));
}

/**
 * New-contract dialog. When a template is selected the dialog also
 * lists every placeholder the template uses, pre-filled with the
 * system-derived value so HR can see — and override — everything that
 * will land in the generated .docx before saving.
 *
 * Submit creates the contract row AND generates the .docx in one go.
 */
export function NewContractModal({
  open,
  employeeId,
  templateId,
  templateName,
  templateTokens,
  onClose,
  onSuccess,
}: Props) {
  const queryClient = useQueryClient();
  const toast = useToast();

  // Contract metadata fields.
  const [contractType, setContractType] = useState("full_time");
  const [reference, setReference] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState("");
  const [notes, setNotes] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Tokens come from the template itself (always available) — preview
  // only seeds values. So we still render every field even when the
  // preview endpoint can't resolve the employee (e.g. demo IDs).
  const tokens = templateTokens;
  const [values, setValues] = useState<Record<string, string>>({});
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  /* Try to pre-resolve the template's placeholders against the employee
     and the form's current contract metadata. Refreshes when type /
     dates / job title change so dynamic tokens (``formatted_*``,
     ``tenure_paragraph``, etc.) stay in step with what the user types.

     Failure here is non-fatal — we still render every token from
     ``templateTokens`` so HR can fill them in manually. This is the
     case when the route's ``employeeId`` is a demo string like
     ``E-0205`` that the backend can't look up. */
  useEffect(() => {
    if (!open || !templateId) {
      setValues({});
      setPreviewError(null);
      return;
    }
    let cancelled = false;
    setPreviewBusy(true);
    setPreviewError(null);
    previewContractTemplate(templateId, {
      employee: employeeId,
      contract_type: contractType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      job_title: jobTitle || undefined,
    })
      .then((data) => {
        if (cancelled) return;
        setValues((current) => {
          // Seed only tokens the user hasn't touched yet — never clobber
          // an in-progress override when the preview re-runs.
          const next: Record<string, string> = { ...current };
          for (const tok of templateTokens) {
            if (!(tok in current)) next[tok] = data.values[tok] ?? "";
          }
          return next;
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const detail = (err as { response?: { data?: { detail?: string }; status?: number } }).response;
        if (detail?.status === 404) {
          setPreviewError(
            "Auto-fill from the system isn't available for this employee — fill the fields manually below.",
          );
        } else {
          setPreviewError(
            "Couldn't pre-fill from the system — fill the fields manually below.",
          );
        }
        // Still seed the inputs with empty strings so the form renders.
        setValues((current) => {
          const next: Record<string, string> = { ...current };
          for (const tok of templateTokens) if (!(tok in current)) next[tok] = "";
          return next;
        });
      })
      .finally(() => {
        if (!cancelled) setPreviewBusy(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    open,
    templateId,
    employeeId,
    contractType,
    startDate,
    endDate,
    jobTitle,
    templateTokens,
  ]);

  // Reset everything when the dialog closes so a fresh open gets fresh state.
  useEffect(() => {
    if (open) return;
    setContractType("full_time");
    setReference("");
    setJobTitle("");
    setStartDate(new Date().toISOString().slice(0, 10));
    setEndDate("");
    setNotes("");
    setError(null);
    setValues({});
    setPreviewError(null);
  }, [open]);

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    setError(null);
    if (!startDate) {
      setError("Start date is required.");
      return;
    }
    setBusy(true);
    try {
      const created = await createContract({
        employee: employeeId,
        contract_type: contractType,
        reference: reference || undefined,
        job_title: jobTitle || undefined,
        start_date: startDate,
        end_date: endDate || null,
        notes: notes || undefined,
      });
      // Generate the .docx in the same flow — the user typed everything
      // they need on this form, no second prompt needed.
      try {
        const overrides: Record<string, string> = { ...values };
        if (templateId) overrides.template_id = templateId;
        const { blob, filename } = await generateContractDocument(
          created.id,
          overrides,
        );
        downloadBlob(blob, filename);
        toast.push("Contract created and downloaded", "success");
      } catch (err) {
        const detail =
          (err as { response?: { data?: { detail?: string } } }).response?.data
            ?.detail ||
          "Contract was saved but the .docx could not be generated. Use Generate .docx on the row to retry.";
        setError(detail);
        // Refresh so the new row appears even on partial success.
        await queryClient.invalidateQueries({
          queryKey: ["employee-contracts", employeeId],
        });
        onSuccess?.();
        return;
      }
      await queryClient.invalidateQueries({
        queryKey: ["employee-contracts", employeeId],
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      const detail =
        (err as { response?: { data?: unknown } }).response?.data ||
        "Could not create the contract.";
      setError(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setBusy(false);
    }
  }

  const showTemplateSection = Boolean(templateId) && tokens.length > 0;
  const subtitle = templateName
    ? `Using template "${templateName}" — every field below lands in the generated .docx.`
    : "No template selected — the contract uses the built-in layout.";

  return (
    <Modal
      open={open}
      onClose={onClose}
      width={760}
      title="New contract"
      sub={subtitle}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="primary" onClick={() => submit()} disabled={busy}>
            {busy ? "Creating…" : "Create & generate"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {/* --- Contract metadata --- */}
        <div>
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            Contract metadata
          </div>
          <div className="grid grid-2" style={{ gap: 12 }}>
            <div className="field">
              <label>Type</label>
              <select
                className="select"
                value={contractType}
                onChange={(e) => setContractType(e.target.value)}
              >
                {CONTRACT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Reference (optional)</label>
              <input
                className="input"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="CTR-2026-001"
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>Job title snapshot</label>
              <input
                className="input"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                placeholder="Leave blank to use the employee's current title"
              />
            </div>
            <div className="field">
              <label>Start date</label>
              <input
                className="input"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="field">
              <label>End date (optional)</label>
              <input
                className="input"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>Notes</label>
              <textarea
                className="textarea"
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* --- Template-driven placeholder fields --- */}
        {showTemplateSection && (
          <div
            style={{
              borderTop: "1px solid var(--hairline-2)",
              paddingTop: 16,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <div className="eyebrow">Document fields ({tokens.length})</div>
              {previewBusy && <Badge tone="default">Refreshing preview…</Badge>}
            </div>
            <p
              style={{
                fontSize: 12,
                color: "var(--text-3)",
                margin: "0 0 12px",
              }}
            >
              Pre-filled from the employee and tenant settings. Edit any value
              before generating — fields you leave blank fall back to the
              system value.
            </p>
            <div className="grid grid-2" style={{ gap: 12 }}>
              {tokens.map((tok) => {
                const long = isLongToken(tok);
                const v = values[tok] ?? "";
                const onChange = (
                  e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
                ) =>
                  setValues((prev) => ({ ...prev, [tok]: e.target.value }));
                return long ? (
                  <div key={tok} className="field" style={{ gridColumn: "1 / -1" }}>
                    <label>{humanise(tok)}</label>
                    <textarea
                      className="textarea"
                      rows={3}
                      value={v}
                      onChange={onChange}
                    />
                  </div>
                ) : (
                  <div key={tok} className="field">
                    <label>{humanise(tok)}</label>
                    <input className="input" value={v} onChange={onChange} />
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Surface a non-fatal preview failure inline so HR knows the
            system couldn't pre-fill but the fields are still editable. */}
        {previewError && (
          <div
            style={{
              padding: "10px 12px",
              background: "var(--yellow-soft)",
              borderRadius: 8,
              fontSize: 12.5,
              color: "var(--yellow-deep)",
            }}
          >
            {previewError}
          </div>
        )}

        {/* Only show the no-extras banner when the picked template really
            has zero placeholders (HR uploaded a static-text document). */}
        {templateId && tokens.length === 0 && !previewBusy && !previewError && (
          <div
            style={{
              padding: "10px 12px",
              background: "var(--info-soft)",
              borderRadius: 8,
              fontSize: 12.5,
              color: "var(--action-deep)",
            }}
          >
            This template has no extra placeholders beyond the contract
            metadata above — the .docx will be generated as-is on submit.
          </div>
        )}

        {error && (
          <div
            style={{
              padding: "10px 12px",
              background: "var(--danger-soft)",
              color: "var(--danger)",
              borderRadius: 8,
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}
      </form>
    </Modal>
  );
}
