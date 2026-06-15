import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { I } from "@/components/icons";
import { Badge, Button, Modal, useToast } from "@/components/ui";
import {
  generateContractDocument,
  getContractTemplateTokens,
  previewContractTemplate,
  type EmploymentContract,
} from "@/api/employees";
import { downloadBlob } from "@/lib/export";

interface Props {
  contract: EmploymentContract | null;
  /** Empty = use backend's resolved default (or built-in layout). */
  templateId: string;
  templateName: string;
  onClose: () => void;
  onSuccess?: () => void;
}

/** ``supervisor_email`` → ``Supervisor email``. */
function humanise(token: string): string {
  const s = token.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Tokens that deserve a textarea instead of an input. */
const LONG_TOKENS = new Set([
  "special_clause",
  "additional_terms",
  "custom_clause",
  "notes",
  "benefits_paragraph",
  "tenure_paragraph",
  "annual_leave_text",
  "sick_leave_text",
  "notice_text",
  "working_hours_text",
]);

export function GenerateContractModal({
  contract,
  templateId,
  templateName,
  onClose,
  onSuccess,
}: Props) {
  const open = Boolean(contract);
  const toast = useToast();
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoTriggered, setAutoTriggered] = useState(false);

  // Reset whenever the modal re-opens for a different contract.
  useEffect(() => {
    if (!open) {
      setValues({});
      setError(null);
      setAutoTriggered(false);
    }
  }, [open]);

  const tokensQuery = useQuery({
    queryKey: ["contract-template", templateId, "tokens"],
    queryFn: () => getContractTemplateTokens(templateId),
    enabled: open && Boolean(templateId),
    retry: false,
  });

  // Pre-resolve the template's auto-filled values for THIS employee so the
  // "Auto-filled" details panel actually shows the merged values, and any
  // auto token the user wants to override comes pre-populated.
  const previewQuery = useQuery({
    queryKey: ["contract-template", templateId, "preview", contract?.employee],
    queryFn: () =>
      previewContractTemplate(templateId, {
        employee: contract!.employee,
        contract_type: contract!.contract_type,
        start_date: contract!.start_date,
        end_date: contract!.end_date ?? undefined,
      }),
    enabled: open && Boolean(templateId && contract),
    retry: false,
  });

  const manualTokens = useMemo(
    () => tokensQuery.data?.manual ?? [],
    [tokensQuery.data],
  );
  const autoTokens = useMemo(
    () => tokensQuery.data?.auto ?? [],
    [tokensQuery.data],
  );
  const previewValues = previewQuery.data?.values ?? {};

  // Seed the input map once we know which tokens the user has to fill in.
  useEffect(() => {
    if (manualTokens.length === 0) return;
    setValues((prev) => {
      const seed: Record<string, string> = { ...prev };
      manualTokens.forEach((t) => {
        if (!(t in seed)) seed[t] = "";
      });
      return seed;
    });
  }, [manualTokens]);

  const noManualPrompts =
    !templateId || (tokensQuery.isFetched && manualTokens.length === 0);

  async function generate(extra: Record<string, string> = {}) {
    if (!contract) return;
    setError(null);
    setBusy(true);
    try {
      const payload: Record<string, unknown> = { ...values, ...extra };
      if (templateId) payload.template_id = templateId;
      const { blob, filename } = await generateContractDocument(
        contract.id,
        payload,
      );
      downloadBlob(blob, filename);
      toast.push("Contract generated and downloaded", "success");
      onSuccess?.();
      onClose();
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not generate the contract.";
      setError(detail);
    } finally {
      setBusy(false);
    }
  }

  // Fast path: nothing to fill → generate immediately on open.
  useEffect(() => {
    if (open && noManualPrompts && !autoTriggered && !busy && tokensQuery.isFetched !== false) {
      setAutoTriggered(true);
      generate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, noManualPrompts, autoTriggered, tokensQuery.isFetched]);

  if (!contract) return null;

  if (noManualPrompts) {
    return (
      <Modal open={open} onClose={onClose} title="Generating contract…">
        <p style={{ fontSize: 13, color: "var(--text-3)" }}>
          {templateId
            ? "Your template has no template-specific fields to fill — generating the document now."
            : "Using the built-in contract layout — generating the document now."}
        </p>
        {error && (
          <div
            style={{
              marginTop: 12,
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
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      width={680}
      title={`Fill in template fields${templateName ? ` — ${templateName}` : ""}`}
      sub="The .docx downloads the moment you click Generate."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => generate()}
            disabled={busy}
            leftIcon={<I.download size={13} />}
          >
            {busy ? "Generating…" : "Generate .docx"}
          </Button>
        </>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <p style={{ fontSize: 13, color: "var(--text-3)", margin: 0 }}>
          Your template needs the following fields that aren't in the employee
          record. Fill them in once and the document downloads immediately.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {manualTokens.map((token) => {
            const isLong = LONG_TOKENS.has(token);
            return (
              <div className="field" key={token}>
                <label>{humanise(token)}</label>
                {isLong ? (
                  <textarea
                    className="textarea"
                    rows={3}
                    value={values[token] ?? ""}
                    onChange={(e) =>
                      setValues((v) => ({ ...v, [token]: e.target.value }))
                    }
                  />
                ) : (
                  <input
                    className="input"
                    value={values[token] ?? ""}
                    onChange={(e) =>
                      setValues((v) => ({ ...v, [token]: e.target.value }))
                    }
                  />
                )}
              </div>
            );
          })}
        </div>

        {autoTokens.length > 0 && (
          <details
            style={{
              border: "1px solid var(--hairline)",
              borderRadius: 10,
              padding: 12,
              fontSize: 12,
              background: "var(--card-2)",
            }}
          >
            <summary
              style={{ cursor: "pointer", fontWeight: 600, color: "var(--ink-3)" }}
            >
              Auto-filled from system ({autoTokens.length})
            </summary>
            <p style={{ marginTop: 8, color: "var(--text-3)" }}>
              These come from the employee, contract and tenant records
              automatically — no input needed.
            </p>
            <div
              style={{
                marginTop: 8,
                display: "flex",
                flexWrap: "wrap",
                gap: 4,
                fontFamily: "var(--mono)",
              }}
            >
              {autoTokens.map((t) => (
                <Badge key={t} tone="outline">
                  {t}
                  {previewValues[t] ? (
                    <span style={{ color: "var(--text-3)", marginLeft: 6 }}>
                      → {previewValues[t].slice(0, 24)}
                      {previewValues[t].length > 24 ? "…" : ""}
                    </span>
                  ) : null}
                </Badge>
              ))}
            </div>
          </details>
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
      </div>
    </Modal>
  );
}
