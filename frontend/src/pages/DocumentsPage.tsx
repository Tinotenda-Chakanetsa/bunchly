import { useMemo, useState, useRef, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Avatar,
  Badge,
  Button,
  Card,
  CardHead,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  StatusBadge,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadBlob, downloadCsv, generatePlaceholderPdf } from "@/lib/export";
import { useAuth } from "@/store/auth";
import { listEmployees } from "@/api/employees";
import {
  listDocumentCategories,
  listDocuments,
  uploadDocument,
  verifyDocument,
  type DocumentRecord,
} from "@/api/documents";

function openDocument(doc: DocumentRecord) {
  // The backend's signed-URL view lives at /api/v1/documents-download/<token>/
  // but a per-document signed token isn't exposed yet — fall back to a
  // placeholder PDF that carries the live metadata so the action isn't
  // dead.
  const blob = generatePlaceholderPdf(doc.title, [
    `Category: ${doc.category_name || doc.category}`,
    `Owner: ${doc.employee_name || "—"}`,
    `Uploaded: ${doc.created_at.slice(0, 10)}`,
    `Status: ${doc.status_display || doc.status}`,
    doc.is_confidential ? "Confidentiality: CONFIDENTIAL" : "Standard",
  ]);
  downloadBlob(blob, `${doc.title}.pdf`);
}

function UploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { user } = useAuth();
  const fileRef = useRef<HTMLInputElement | null>(null);

  const categories = useQuery({
    queryKey: ["document-categories"],
    queryFn: listDocumentCategories,
    enabled: open,
  });
  const employees = useQuery({
    queryKey: ["employees", "for-doc"],
    queryFn: () => listEmployees(),
    enabled: open,
  });

  const [employeeId, setEmployeeId] = useState(user?.id || "");
  const [categoryId, setCategoryId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isConfidential, setIsConfidential] = useState(false);
  const [pickedFile, setPickedFile] = useState<File | null>(null);

  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => {
      toast.push("Document uploaded", "success");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      onClose();
      setTitle("");
      setDescription("");
      setPickedFile(null);
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Upload failed",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!pickedFile) {
      toast.push("Pick a file first", "error");
      return;
    }
    if (!employeeId || !categoryId || !title.trim()) {
      toast.push("Employee, category and title are required", "error");
      return;
    }
    upload.mutate({
      employee: employeeId,
      category: categoryId,
      title: title.trim(),
      description,
      is_confidential: isConfidential,
      file: pickedFile,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Upload document"
      sub="Stored encrypted; routed through HR review if the category requires it."
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={upload.isPending}>
            Cancel
          </Button>
          <Button variant="primary" onClick={submit} disabled={upload.isPending}>
            {upload.isPending ? "Uploading…" : "Upload"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div
          onClick={() => fileRef.current?.click()}
          style={{
            padding: 32,
            border: "2px dashed var(--hairline)",
            borderRadius: 12,
            textAlign: "center",
            marginBottom: 16,
            background: "var(--card-2)",
            cursor: "pointer",
          }}
        >
          <I.upload size={28} style={{ color: "var(--action)", margin: "0 auto 12px" }} />
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {pickedFile ? pickedFile.name : "Click to pick a file"}
          </div>
          <div style={{ fontSize: 12.5, color: "var(--text-3)" }}>
            PDF, DOCX, JPG, PNG · respects the category's size + extension rules
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.docx,.jpg,.jpeg,.png"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) {
                setPickedFile(f);
                if (!title) setTitle(f.name.replace(/\.[^.]+$/, ""));
              }
            }}
          />
        </div>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Title</label>
            <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label>Employee</label>
            <select
              className="select"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
            >
              <option value="">
                {employees.isLoading ? "Loading…" : "Pick an employee"}
              </option>
              {(employees.data?.results ?? []).map((e) => (
                <option key={e.id} value={e.id}>
                  {e.full_name || `${e.first_name} ${e.last_name}`}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Category</label>
            <select
              className="select"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">
                {categories.isLoading ? "Loading…" : "Pick a category"}
              </option>
              {(categories.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                  {c.is_required ? " · required" : ""}
                </option>
              ))}
            </select>
          </div>
          <label className="checkbox" style={{ gridColumn: "1 / -1" }}>
            <input
              type="checkbox"
              checked={isConfidential}
              onChange={(e) => setIsConfidential(e.target.checked)}
            />
            Mark as confidential
          </label>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Description (optional)</label>
            <textarea
              className="textarea"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

export default function DocumentsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canUpload = hasPerm("documents.upload");
  const canApprove = hasPerm("documents.approve");
  const [tab, setTab] = useState("all");
  const [search, setSearch] = useState("");
  const [showUpload, setShowUpload] = useState(false);

  const docs = useQuery({
    queryKey: ["documents"],
    queryFn: () => listDocuments(),
  });
  const verify = useMutation({
    mutationFn: ({ id }: { id: string }) => verifyDocument(id),
    onSuccess: () => {
      toast.push("Verified", "success");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: () => toast.push("Could not verify", "error"),
  });

  const rows = docs.data?.results ?? [];

  const filtered = useMemo(() => {
    let r = rows;
    if (tab === "pending") r = r.filter((d) => /pending|review/i.test(d.status));
    if (tab === "policies") r = r.filter((d) => /policy/i.test(d.category_name || ""));
    if (search)
      r = r.filter((d) =>
        ((d.title || "") + (d.employee_name || "") + (d.category_name || ""))
          .toLowerCase()
          .includes(search.toLowerCase()),
      );
    return r;
  }, [tab, search, rows]);

  const pag = usePaginated(filtered);

  return (
    <div className="page">
      <PageHeader
        eyebrow="Storage & compliance"
        title="Documents"
        lede={
          docs.isLoading
            ? "Loading…"
            : `${docs.data?.count ?? rows.length} files · ${rows.filter((d) => /pending|review/i.test(d.status)).length} awaiting review`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() =>
                downloadCsv(`documents-${new Date().toISOString().slice(0, 10)}.csv`, rows)
              }
            >
              Export
            </Button>
            {canUpload && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.upload size={14} />}
                onClick={() => setShowUpload(true)}
              >
                Upload
              </Button>
            )}
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Total" value={docs.data?.count ?? rows.length} />
        <KpiCell label="Awaiting review" value={rows.filter((d) => /pending|review/i.test(d.status)).length} />
        <KpiCell label="Verified" value={rows.filter((d) => /verified|approved/i.test(d.status)).length} />
        <KpiCell label="Confidential" value={rows.filter((d) => d.is_confidential).length} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "all", label: "All", count: rows.length },
          {
            value: "pending",
            label: "Pending review",
            count: rows.filter((d) => /pending|review/i.test(d.status)).length,
          },
          { value: "policies", label: "Policies" },
        ]}
      />
      <Card>
        <div className="table-toolbar">
          <div className="toolbar-search">
            <span className="icon">
              <I.search size={16} />
            </span>
            <input
              placeholder="Search by title, owner or category…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Category</th>
              <th>Owner</th>
              <th>Uploaded</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pag.slice.map((d) => (
              <tr key={d.id} className="clickable" onClick={() => navigate(`/documents/${d.id}`)}>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <div
                      style={{
                        width: 32,
                        height: 36,
                        background: d.is_confidential ? "var(--yellow-soft)" : "var(--info-soft)",
                        color: d.is_confidential ? "#7A5A00" : "var(--action)",
                        display: "grid",
                        placeItems: "center",
                        borderRadius: 6,
                      }}
                    >
                      {d.is_confidential ? <I.shield size={14} /> : <I.document size={14} />}
                    </div>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: 13 }}>{d.title}</div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>
                        {d.id.slice(0, 8)}
                      </div>
                    </div>
                  </div>
                </td>
                <td>
                  <Badge tone={d.is_confidential ? "yellow" : "outline"}>
                    {d.category_name || "—"}
                  </Badge>
                </td>
                <td>{d.employee_name || "—"}</td>
                <td className="muted num">{d.created_at.slice(0, 10)}</td>
                <td>
                  <StatusBadge status={d.status_display || d.status} />
                </td>
                <td style={{ textAlign: "right" }}>
                  <div style={{ display: "inline-flex", gap: 4 }}>
                    {canApprove && /pending|review/i.test(d.status) && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={verify.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          verify.mutate({ id: d.id });
                        }}
                      >
                        Verify
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        openDocument(d);
                      }}
                      title="Download"
                    >
                      <I.download size={14} />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && docs.isFetched && (
              <tr>
                <td colSpan={6}>
                  <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                    No documents yet.
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <Pagination
          page={pag.page}
          pages={pag.pages}
          pageSize={pag.pageSize}
          total={pag.total}
          setPage={pag.setPage}
        />
      </Card>
      <UploadModal open={showUpload} onClose={() => setShowUpload(false)} />
    </div>
  );
}

export function DocumentDetailPage() {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canApprove = hasPerm("documents.approve");

  const docs = useQuery({
    queryKey: ["documents", "for-detail"],
    queryFn: () => listDocuments(),
  });
  const doc = (docs.data?.results ?? []).find((d) => d.id === id);

  const verify = useMutation({
    mutationFn: () => verifyDocument(id),
    onSuccess: () => {
      toast.push("Verified", "success");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });

  if (docs.isLoading) {
    return (
      <div className="page">
        <div style={{ padding: 40, color: "var(--text-3)" }}>Loading…</div>
      </div>
    );
  }
  if (!doc) {
    return (
      <div className="page">
        <Button variant="ghost" size="sm" onClick={() => navigate("/documents")}>← Back</Button>
        <div className="empty">
          <div className="title">Document not found</div>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <Button
        variant="ghost"
        size="sm"
        style={{ marginBottom: 16 }}
        onClick={() => navigate("/documents")}
      >
        <I.chevron size={14} style={{ transform: "rotate(180deg)" }} /> Back to Documents
      </Button>
      <div className="grid" style={{ gridTemplateColumns: "1.5fr 1fr", gap: 20 }}>
        <Card>
          <div
            style={{
              height: 480,
              background: "linear-gradient(135deg, #F4F6FB 0%, #E6EAF2 100%)",
              borderRadius: "16px 16px 0 0",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 32,
                background: "var(--card)",
                border: "1px solid var(--hairline)",
                borderRadius: 4,
                padding: 32,
                color: "var(--text-2)",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  textTransform: "uppercase",
                  letterSpacing: "0.16em",
                  color: "var(--text-3)",
                }}
              >
                Bunchly · {doc.is_confidential ? "Confidential" : "Standard"}
              </div>
              <h2 style={{ fontSize: 24, margin: "12px 0 24px", color: "var(--ink-3)" }}>{doc.title}</h2>
              {[85, 90, 75, 60, 88, 70, 82].map((w, i) => (
                <div
                  key={i}
                  style={{
                    height: 8,
                    background: "var(--hairline-2)",
                    borderRadius: 2,
                    marginBottom: 10,
                    width: `${w}%`,
                  }}
                />
              ))}
            </div>
          </div>
          <div className="card-foot">
            <span style={{ fontSize: 12, color: "var(--text-3)" }}>
              Version {doc.current_version?.version_number || 1} of {doc.version_count || 1}
            </span>
            <div style={{ display: "flex", gap: 6 }}>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<I.download size={13} />}
                onClick={() => openDocument(doc)}
              >
                Download
              </Button>
              {canApprove && /pending|review/i.test(doc.status) && (
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<I.check size={13} />}
                  disabled={verify.isPending}
                  onClick={() => verify.mutate()}
                >
                  Verify
                </Button>
              )}
            </div>
          </div>
        </Card>
        <Card>
          <CardHead title="Document details" />
          <div className="card-body" style={{ paddingTop: 4 }}>
            {[
              { l: "Status", v: <StatusBadge status={doc.status_display || doc.status} /> },
              { l: "Category", v: doc.category_name || "—" },
              { l: "Owner", v: doc.employee_name || "—" },
              { l: "Uploaded", v: doc.created_at.slice(0, 10) },
              { l: "Versions", v: doc.version_count || 1 },
              {
                l: "Confidentiality",
                v: (
                  <Badge tone={doc.is_confidential ? "yellow" : "outline"} dot>
                    {doc.is_confidential ? "Confidential" : "Standard"}
                  </Badge>
                ),
              },
            ].map((row, i, arr) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "8px 0",
                  borderBottom: i === arr.length - 1 ? "none" : "1px solid var(--hairline-2)",
                  fontSize: 13,
                }}
              >
                <span style={{ color: "var(--text-3)" }}>{row.l}</span>
                <span style={{ fontWeight: 500 }}>{row.v}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

void Avatar;
