import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { I } from "@/components/icons";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHead,
  Empty,
  Skeleton,
} from "@/components/ui";
import {
  listContractTemplates,
  listEmployeeContracts,
  type EmploymentContract,
} from "@/api/employees";
import { useAuth } from "@/store/auth";
import { fmtDate } from "@/lib/format";

import { ContractTemplatesModal } from "./ContractTemplatesModal";
import { GenerateContractModal } from "./GenerateContractModal";
import { NewContractModal } from "./NewContractModal";

const STATUS_TONE: Record<string, "default" | "blue" | "yellow" | "green" | "red"> = {
  draft: "default",
  active: "green",
  expired: "yellow",
  terminated: "red",
  renewed: "blue",
};

interface Props {
  employeeId: string;
}

/**
 * Contracts panel for the Employee detail page.
 *
 * – Lists this employee's contracts (live from the backend)
 * – New Contract modal (POST /contracts/)
 * – Templates modal (GET/POST/PATCH/DELETE /contract-templates/)
 * – Template picker for the next .docx generation
 * – Generate dialog that fetches the template's manual tokens and only
 *   asks for those (skips straight to download otherwise)
 */
export function ContractsPanel({ employeeId }: Props) {
  const { hasPerm } = useAuth();
  const canManage = hasPerm("employees.change_employee");
  const [creating, setCreating] = useState(false);
  const [managingTemplates, setManagingTemplates] = useState(false);
  const [templateId, setTemplateId] = useState<string>("");
  const [generatingContract, setGeneratingContract] =
    useState<EmploymentContract | null>(null);

  const contractsQuery = useQuery({
    queryKey: ["employee-contracts", employeeId],
    queryFn: () => listEmployeeContracts(employeeId),
    enabled: Boolean(employeeId),
  });

  const templatesQuery = useQuery({
    queryKey: ["contract-templates"],
    queryFn: listContractTemplates,
  });

  const activeTemplates = useMemo(
    () => (templatesQuery.data ?? []).filter((t) => t.is_active),
    [templatesQuery.data],
  );
  const resolvedDefault = useMemo(() => {
    const flagged = activeTemplates.find((t) => t.is_default);
    if (flagged) return flagged;
    return (
      [...activeTemplates].sort((a, b) =>
        b.created_at.localeCompare(a.created_at),
      )[0] ?? null
    );
  }, [activeTemplates]);

  const effectiveTemplate = useMemo(() => {
    if (templateId) return activeTemplates.find((t) => t.id === templateId) ?? null;
    return resolvedDefault;
  }, [activeTemplates, templateId, resolvedDefault]);
  const effectiveTemplateId = effectiveTemplate?.id ?? "";
  const effectiveTemplateName = effectiveTemplate?.name ?? "";
  const effectiveTemplateTokens = effectiveTemplate?.discovered_placeholders ?? [];

  const contracts = contractsQuery.data?.results ?? [];

  return (
    <>
      <Card style={{ marginTop: 16 }}>
        <CardHead
          title="Contracts & documents"
          sub="Pick a template and click Generate — Bunchly auto-fills what it can and only asks for what it can't."
          action={
            canManage ? (
              <div style={{ display: "flex", gap: 6 }}>
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<I.settings size={13} />}
                  onClick={() => setManagingTemplates(true)}
                >
                  Templates
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  leftIcon={<I.plus size={13} />}
                  onClick={() => setCreating(true)}
                >
                  New contract
                </Button>
              </div>
            ) : null
          }
        />

        {canManage && activeTemplates.length > 0 && (
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--hairline-2)" }}>
            <div className="field" style={{ maxWidth: 420 }}>
              <label>Template for the next .docx generation</label>
              <select
                className="select"
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
              >
                <option value="">
                  {resolvedDefault
                    ? `Use ${resolvedDefault.name}${resolvedDefault.is_default ? " (default)" : ""}`
                    : "Use built-in layout"}
                </option>
                {activeTemplates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        <CardBody style={{ padding: 0 }}>
          {contractsQuery.isLoading ? (
            <div style={{ padding: 18 }}>
              <Skeleton height={20} width={240} />
            </div>
          ) : contractsQuery.isError ? (
            <Empty
              icon="warn"
              title="Could not load contracts"
              lede="Check your backend connection — the contracts endpoint returned an error."
            />
          ) : contracts.length === 0 ? (
            <Empty
              icon="document"
              title="No contracts on file yet"
              lede={
                canManage
                  ? "Click New contract to add the first one for this employee."
                  : "Ask HR to register an employment contract."
              }
            />
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Type</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {contracts.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>
                        {(c as EmploymentContract & { reference?: string }).reference ||
                          `Contract ${c.id.slice(0, 8)}`}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-3)" }}>{c.id.slice(0, 8)}</div>
                    </td>
                    <td>{c.contract_type.replace(/_/g, " ")}</td>
                    <td>{fmtDate(c.start_date)}</td>
                    <td>{c.end_date ? fmtDate(c.end_date) : "Indefinite"}</td>
                    <td>
                      <Badge tone={STATUS_TONE[c.status || "draft"] || "default"}>
                        {c.status || "—"}
                      </Badge>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      {canManage && (
                        <Button
                          variant="outline"
                          size="sm"
                          leftIcon={<I.download size={13} />}
                          onClick={() => setGeneratingContract(c)}
                        >
                          Generate .docx
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      <NewContractModal
        open={creating}
        employeeId={employeeId}
        templateId={effectiveTemplateId}
        templateName={effectiveTemplateName}
        templateTokens={effectiveTemplateTokens}
        onClose={() => setCreating(false)}
        onSuccess={() => contractsQuery.refetch()}
      />
      <ContractTemplatesModal
        open={managingTemplates}
        onClose={() => setManagingTemplates(false)}
        onChanged={() => templatesQuery.refetch()}
      />
      <GenerateContractModal
        contract={generatingContract}
        templateId={effectiveTemplateId}
        templateName={effectiveTemplateName}
        onClose={() => setGeneratingContract(null)}
        onSuccess={() => contractsQuery.refetch()}
      />
    </>
  );
}
