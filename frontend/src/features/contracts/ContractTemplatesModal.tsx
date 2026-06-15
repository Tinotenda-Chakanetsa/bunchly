import { useMemo, useRef, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Empty,
  Modal,
  useToast,
} from "@/components/ui";
import {
  deleteContractTemplate,
  getPlaceholderCatalogue,
  listContractTemplates,
  updateContractTemplate,
  uploadContractTemplate,
} from "@/api/employees";

interface Props {
  open: boolean;
  onClose: () => void;
  onChanged?: () => void;
}

/**
 * Manage tenant contract templates: list, upload a new .docx, set
 * default, deactivate. The catalogue button at the bottom shows every
 * ``{{ token }}`` HR can drop into their template.
 */
export function ContractTemplatesModal({ open, onClose, onChanged }: Props) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [pickedFile, setPickedFile] = useState<File | null>(null);
  const [showCatalogue, setShowCatalogue] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const templates = useQuery({
    queryKey: ["contract-templates"],
    queryFn: listContractTemplates,
    enabled: open,
  });

  const catalogue = useQuery({
    queryKey: ["contract-template-placeholders"],
    queryFn: getPlaceholderCatalogue,
    enabled: open && showCatalogue,
  });

  function resetForm() {
    setName("");
    setCode("");
    setDescription("");
    setIsDefault(false);
    setPickedFile(null);
    setError(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!pickedFile) {
      setError("Pick a .docx template file first.");
      return;
    }
    if (!name.trim() || !code.trim()) {
      setError("Name and code are required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await uploadContractTemplate({
        name: name.trim(),
        code: code.trim().toLowerCase().replace(/\s+/g, "_"),
        description,
        file: pickedFile,
        is_default: isDefault,
      });
      toast.push(`Template '${name}' uploaded`, "success");
      resetForm();
      await templates.refetch();
      onChanged?.();
    } catch (err) {
      const detail =
        (err as { response?: { data?: unknown } }).response?.data ||
        "Upload failed.";
      setError(typeof detail === "string" ? detail : JSON.stringify(detail));
    } finally {
      setBusy(false);
    }
  }

  async function setAsDefault(id: string) {
    try {
      await updateContractTemplate(id, { is_default: true });
      toast.push("Default template updated", "success");
      await templates.refetch();
      onChanged?.();
    } catch {
      toast.push("Could not change default template", "error");
    }
  }

  async function deactivate(id: string) {
    try {
      await updateContractTemplate(id, { is_active: false });
      await templates.refetch();
      onChanged?.();
    } catch {
      toast.push("Could not deactivate template", "error");
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this template? This cannot be undone.")) return;
    try {
      await deleteContractTemplate(id);
      await templates.refetch();
      onChanged?.();
      toast.push("Template deleted", "success");
    } catch {
      toast.push("Could not delete template", "error");
    }
  }

  const rows = useMemo(() => templates.data ?? [], [templates.data]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      width={760}
      title="Contract templates"
      sub="Upload your tenant-branded .docx templates with {{ placeholders }}."
      footer={
        <Button variant="primary" onClick={onClose}>
          Done
        </Button>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        {/* Upload form */}
        <form
          onSubmit={submit}
          style={{
            padding: 16,
            border: "1px solid var(--hairline)",
            borderRadius: 12,
            background: "var(--card-2)",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 600, fontSize: 13.5 }}>Upload a new template</div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowCatalogue((v) => !v)}
              leftIcon={<I.list size={13} />}
            >
              {showCatalogue ? "Hide" : "Show"} placeholder catalogue
            </Button>
          </div>

          <div className="grid grid-2" style={{ gap: 12 }}>
            <div className="field">
              <label>Name</label>
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Standard employment contract"
              />
            </div>
            <div className="field">
              <label>Code</label>
              <input
                className="input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="standard_employment"
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>Description (optional)</label>
              <input
                className="input"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>.docx template</label>
              <div
                onClick={() => fileRef.current?.click()}
                style={{
                  padding: 16,
                  border: "2px dashed var(--hairline)",
                  borderRadius: 10,
                  textAlign: "center",
                  cursor: "pointer",
                  background: "var(--card)",
                }}
              >
                <I.upload size={20} style={{ color: "var(--action)", margin: "0 auto 8px" }} />
                <div style={{ fontWeight: 500, fontSize: 13 }}>
                  {pickedFile ? pickedFile.name : "Click to pick a .docx file"}
                </div>
                <div style={{ fontSize: 11.5, color: "var(--text-3)", marginTop: 2 }}>
                  Word documents with{" "}
                  <code style={{ fontFamily: "var(--mono)" }}>{`{{ token }}`}</code>{" "}
                  placeholders
                </div>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  style={{ display: "none" }}
                  onChange={(e) => setPickedFile(e.target.files?.[0] ?? null)}
                />
              </div>
            </div>
            <label className="checkbox" style={{ gridColumn: "1 / -1" }}>
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
              />
              Set as tenant default
            </label>
          </div>

          {error && (
            <div
              style={{
                padding: "8px 12px",
                background: "var(--danger-soft)",
                color: "var(--danger)",
                borderRadius: 8,
                fontSize: 12.5,
              }}
            >
              {error}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 6 }}>
            <Button type="button" variant="ghost" onClick={resetForm} disabled={busy}>
              Reset
            </Button>
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Uploading…" : "Upload template"}
            </Button>
          </div>
        </form>

        {/* Existing templates */}
        <div>
          <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 8 }}>
            Your templates ({rows.length})
          </div>
          {templates.isLoading ? (
            <div style={{ fontSize: 13, color: "var(--text-3)" }}>Loading…</div>
          ) : rows.length === 0 ? (
            <Empty
              icon="document"
              title="No templates yet"
              lede="Upload a Word document with placeholders to brand every generated contract."
            />
          ) : (
            <div className="list">
              {rows.map((t) => (
                <div key={t.id} className="list-row" style={{ alignItems: "center" }}>
                  <div className="row-icon">
                    <I.document size={16} />
                  </div>
                  <div className="row-main">
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span className="row-title">{t.name}</span>
                      {t.is_default && <Badge tone="yellow" dot>Default</Badge>}
                      {!t.is_active && <Badge tone="default">Inactive</Badge>}
                    </div>
                    <div className="row-sub" style={{ fontFamily: "var(--mono)" }}>
                      {t.code} · {t.discovered_placeholders.length} placeholder
                      {t.discovered_placeholders.length === 1 ? "" : "s"}
                    </div>
                  </div>
                  {!t.is_default && t.is_active && (
                    <Button variant="outline" size="sm" onClick={() => setAsDefault(t.id)}>
                      Make default
                    </Button>
                  )}
                  {t.is_active && (
                    <Button variant="ghost" size="sm" onClick={() => deactivate(t.id)}>
                      Deactivate
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(t.id)}
                    title="Delete template"
                  >
                    <I.trash size={14} />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {showCatalogue && (
          <div
            style={{
              padding: 14,
              border: "1px solid var(--hairline)",
              borderRadius: 12,
              background: "var(--card-2)",
            }}
          >
            <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 8 }}>
              Auto-fillable placeholders
            </div>
            <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 10 }}>
              Drop any of these into your Word document — Bunchly will fill
              them at generation time from the tenant, employee and contract
              records. Anything you use that isn't on this list becomes a
              manual field HR fills in the Generate dialog.
            </div>
            {catalogue.isLoading ? (
              <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>Loading…</div>
            ) : (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {(catalogue.data ?? []).map((tok) => (
                  <Badge
                    key={tok}
                    tone="outline"
                    style={{ fontFamily: "var(--mono)" }}
                  >
                    {`{{ ${tok} }}`}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
