import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  KpiCell,
  KpiStrip,
  Modal,
  PageHeader,
  Pagination,
  PersonCell,
  Tabs,
  useToast,
  usePaginated,
} from "@/components/ui";
import { downloadCsv } from "@/lib/export";
import { useAuth } from "@/store/auth";
import { listEmployees } from "@/api/employees";
import {
  assignAssetAction,
  listAssetAssignments,
  listAssetCategories,
  listAssets,
  registerAsset,
  returnAssetAction,
  type Asset,
} from "@/api/hr";

const CONDITIONS = [
  { value: "new", label: "New" },
  { value: "good", label: "Good" },
  { value: "fair", label: "Fair" },
  { value: "poor", label: "Poor" },
  { value: "damaged", label: "Damaged" },
];

function CategoryIcon({ name, size = 16 }: { name?: string; size?: number }) {
  const n = (name || "").toLowerCase();
  if (n.includes("laptop")) return <I.laptop size={size} />;
  if (n.includes("phone") || n.includes("mobile")) return <I.phone size={size} />;
  if (n.includes("monitor") || n.includes("display")) return <I.dashboard size={size} />;
  return <I.briefcase size={size} />;
}

function RegisterAssetModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const categories = useQuery({
    queryKey: ["asset-categories"],
    queryFn: listAssetCategories,
    enabled: open,
  });
  const [name, setName] = useState("");
  const [assetTag, setAssetTag] = useState("");
  const [serial, setSerial] = useState("");
  const [category, setCategory] = useState<string>("");
  const [condition, setCondition] = useState("new");
  const [location, setLocation] = useState("");

  const create = useMutation({
    mutationFn: registerAsset,
    onSuccess: (rec) => {
      toast.push(`${rec.asset_tag} registered`, "success");
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      onClose();
      setName("");
      setAssetTag("");
      setSerial("");
      setLocation("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not register asset",
        "error",
      ),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !assetTag.trim() || !serial.trim()) {
      toast.push("Name, tag and serial are required", "error");
      return;
    }
    create.mutate({
      name: name.trim(),
      asset_tag: assetTag.trim(),
      serial_number: serial.trim(),
      condition,
      category: category || undefined,
      location: location.trim() || undefined,
    });
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Register asset"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={create.isPending}>
            {create.isPending ? "Registering…" : "Register"}
          </Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <div className="grid grid-2" style={{ gap: 14 }}>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Asset name / model</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder='MacBook Pro 14" M3'
              autoFocus
            />
          </div>
          <div className="field">
            <label>Asset tag</label>
            <input
              className="input"
              value={assetTag}
              onChange={(e) => setAssetTag(e.target.value)}
              placeholder="AST-0123"
            />
          </div>
          <div className="field">
            <label>Serial number</label>
            <input
              className="input"
              value={serial}
              onChange={(e) => setSerial(e.target.value)}
              placeholder="C02XX…"
            />
          </div>
          <div className="field">
            <label>Category</label>
            <select className="select" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">{categories.isLoading ? "Loading…" : "No category"}</option>
              {(categories.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Condition</label>
            <select className="select" value={condition} onChange={(e) => setCondition(e.target.value)}>
              {CONDITIONS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ gridColumn: "1 / -1" }}>
            <label>Location</label>
            <input
              className="input"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="HQ store-room"
            />
          </div>
        </div>
      </form>
    </Modal>
  );
}

function AssignModal({
  open,
  onClose,
  asset,
}: {
  open: boolean;
  onClose: () => void;
  asset: Asset | null;
}) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const employees = useQuery({
    queryKey: ["employees", "for-assets"],
    queryFn: () => listEmployees(),
    enabled: open,
  });
  const [employeeId, setEmployeeId] = useState("");

  const assign = useMutation({
    mutationFn: () =>
      assignAssetAction({
        assetId: asset!.id,
        employee: employeeId,
      }),
    onSuccess: () => {
      toast.push("Asset assigned", "success");
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["asset-assignments"] });
      onClose();
      setEmployeeId("");
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not assign",
        "error",
      ),
  });

  function submit() {
    if (!asset || !employeeId) {
      toast.push("Pick an employee", "error");
      return;
    }
    assign.mutate();
  }

  return (
    <Modal
      open={open && !!asset}
      onClose={onClose}
      title={asset ? `Assign ${asset.name}` : "Assign asset"}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={assign.isPending}>
            {assign.isPending ? "Assigning…" : "Assign"}
          </Button>
        </>
      }
    >
      <div className="field">
        <label>Assign to</label>
        <select className="select" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
          <option value="">{employees.isLoading ? "Loading…" : "Pick an employee"}</option>
          {(employees.data?.results ?? []).map((e) => (
            <option key={e.id} value={e.id}>
              {e.full_name || `${e.first_name} ${e.last_name}`}
            </option>
          ))}
        </select>
      </div>
    </Modal>
  );
}

export default function AssetsPage() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const { hasPerm } = useAuth();
  const canManage = hasPerm("assets.manage");
  const [tab, setTab] = useState("all");
  const [showRegister, setShowRegister] = useState(false);
  const [assignAsset, setAssignAsset] = useState<Asset | null>(null);

  const assets = useQuery({ queryKey: ["assets"], queryFn: () => listAssets() });
  const assignments = useQuery({
    queryKey: ["asset-assignments"],
    queryFn: () => listAssetAssignments({ status: "issued" }),
  });

  const rows = assets.data?.results ?? [];
  const issued = assignments.data ?? [];
  const issuedByAssetId = useMemo(() => {
    const m = new Map<string, typeof issued[number]>();
    for (const a of issued) m.set(a.asset, a);
    return m;
  }, [issued]);

  const filtered = useMemo(
    () =>
      rows.filter((a) =>
        tab === "assigned"
          ? a.status === "assigned"
          : tab === "stock"
            ? a.status === "available"
            : true,
      ),
    [rows, tab],
  );
  const pag = usePaginated(filtered);

  const ret = useMutation({
    mutationFn: (assignmentId: string) =>
      returnAssetAction({ assignmentId, return_condition: "good" }),
    onSuccess: () => {
      toast.push("Asset returned to stock", "success");
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["asset-assignments"] });
    },
    onError: (err: unknown) =>
      toast.push(
        (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail || "Could not return",
        "error",
      ),
  });

  const conditionTone = (c?: string) => {
    if (c === "new" || c === "good") return "green";
    if (c === "fair") return "blue";
    return "yellow";
  };

  return (
    <div className="page">
      <PageHeader
        eyebrow="Company property"
        title="Assets"
        lede={
          assets.isLoading
            ? "Loading…"
            : `${rows.length} assets · ${rows.filter((a) => a.status === "available").length} available`
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<I.download size={14} />}
              onClick={() => downloadCsv("assets.csv", rows)}
            >
              Export
            </Button>
            {canManage && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<I.plus size={14} />}
                onClick={() => setShowRegister(true)}
              >
                Register asset
              </Button>
            )}
          </>
        }
      />
      <KpiStrip cols={4} style={{ marginBottom: 20 }}>
        <KpiCell label="Total" value={rows.length} />
        <KpiCell label="Assigned" value={rows.filter((a) => a.status === "assigned").length} />
        <KpiCell label="Available" value={rows.filter((a) => a.status === "available").length} />
        <KpiCell label="In repair" value={rows.filter((a) => a.status === "in_repair").length} />
      </KpiStrip>
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { value: "all", label: "All assets", count: rows.length },
          { value: "assigned", label: "Assigned", count: rows.filter((a) => a.status === "assigned").length },
          { value: "stock", label: "In stock", count: rows.filter((a) => a.status === "available").length },
        ]}
      />
      <Card>
        <table className="table">
          <thead>
            <tr>
              <th>Asset</th>
              <th>Category</th>
              <th>Serial</th>
              <th>Assigned to</th>
              <th>Issued</th>
              <th>Condition</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pag.slice.map((a) => {
              const asg = issuedByAssetId.get(a.id);
              return (
                <tr key={a.id}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div
                        style={{
                          width: 36,
                          height: 36,
                          borderRadius: 10,
                          background: "var(--info-soft)",
                          color: "var(--action)",
                          display: "grid",
                          placeItems: "center",
                        }}
                      >
                        <CategoryIcon name={a.category_name} />
                      </div>
                      <div>
                        <div style={{ fontWeight: 500 }}>{a.name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--mono)" }}>
                          {a.asset_tag}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Badge tone="outline">{a.category_name || "—"}</Badge>
                  </td>
                  <td className="num" style={{ fontSize: 12, color: "var(--text-3)" }}>
                    {a.serial_number}
                  </td>
                  <td>
                    {asg ? (
                      <PersonCell name={asg.employee_name || "—"} />
                    ) : a.status === "assigned" ? (
                      <span className="muted">—</span>
                    ) : (
                      <Badge tone="yellow" dot>
                        Unassigned
                      </Badge>
                    )}
                  </td>
                  <td className="muted num">{asg?.issued_date || "—"}</td>
                  <td>
                    <Badge tone={conditionTone(a.condition)} dot>
                      {a.condition_display || a.condition}
                    </Badge>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {asg ? (
                      canManage ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={ret.isPending}
                          onClick={() => ret.mutate(asg.id)}
                        >
                          {ret.isPending ? "…" : "Return"}
                        </Button>
                      ) : (
                        <span className="muted" style={{ fontSize: 11 }}>Issued</span>
                      )
                    ) : a.status === "available" ? (
                      canManage ? (
                        <Button variant="primary" size="sm" onClick={() => setAssignAsset(a)}>
                          Assign
                        </Button>
                      ) : (
                        <Badge tone="yellow" dot>Unassigned</Badge>
                      )
                    ) : (
                      <span className="muted" style={{ fontSize: 11 }}>
                        {a.status_display || a.status}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && assets.isFetched && (
              <tr>
                <td colSpan={7}>
                  <div style={{ padding: 28, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
                    No assets yet.
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

      <RegisterAssetModal open={showRegister} onClose={() => setShowRegister(false)} />
      <AssignModal
        open={!!assignAsset}
        onClose={() => setAssignAsset(null)}
        asset={assignAsset}
      />
    </div>
  );
}
