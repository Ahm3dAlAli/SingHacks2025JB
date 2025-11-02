"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import Link from "next/link";
import { BadgeCheck, Bell, FileText, History, ShieldAlert } from "lucide-react";
import { startWorkflow, getWorkflow, getAuditTrail, completeWorkflow, executeStep, type WorkflowSummary, type AuditEntry } from "@/lib/api/remediation";

type AlertDetail = {
  id: string;
  risk: number; // 0-100
  severity: "low" | "medium" | "high" | "critical";
  status: "new" | "acknowledged" | "in_progress" | "closed";
  entityId?: string;
  ruleHits: { id: string; name: string; score: number }[];
  transactions: { id: string; amount: number; currency: string; counterparty: string; ts: string }[];
  documents: { id: string; name: string; type: string; anomaly?: string }[];
};

type TimelineEvent = {
  id: string;
  ts: string;
  type: "created" | "ack" | "status" | "comment";
  text: string;
};

export default function AlertDetailPage() {
  const { alertId } = useParams<{ alertId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<AlertDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [person, setPerson] = useState<{ name: string; employer?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [comment, setComment] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiRecommendation, setAiRecommendation] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [wfStarting, setWfStarting] = useState(false);
  const [wfResult, setWfResult] = useState<{ id: string; message: string } | null>(null);
  const [wfId, setWfId] = useState<string | null>(null);
  const [wfInfo, setWfInfo] = useState<WorkflowSummary | null>(null);
  const [wfLoading, setWfLoading] = useState(false);
  const [wfError, setWfError] = useState<string | null>(null);
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);
  const [completeRunning, setCompleteRunning] = useState(false);
  const [stepRunning, setStepRunning] = useState<string | null>(null);
  const [stepError, setStepError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  const severityColor = useMemo(() => {
    switch (detail?.severity) {
      case "critical":
        return "bg-red-600 text-white";
      case "high":
        return "bg-orange-600 text-white";
      case "medium":
        return "bg-amber-500 text-white";
      default:
        return "bg-emerald-600 text-white";
    }
  }, [detail?.severity]);

  async function fetchAll() {
    try {
      setLoading(true);
      setError(null);
      const [dRes, tRes] = await Promise.all([
        fetch(`/api/v1/alerts/${alertId}`),
        fetch(`/api/v1/alerts/${alertId}/timeline`),
      ]);
      if (!dRes.ok) throw new Error("Failed to load alert");
      if (!tRes.ok) throw new Error("Failed to load timeline");
      const d = (await dRes.json()) as AlertDetail;
      const t = (await tRes.json()) as TimelineEvent[];
      setDetail(d);
      setTimeline(t);
      // Fetch person details for nicer display
      if (d.entityId) {
        try {
          const pRes = await fetch(`/api/entities/${d.entityId}`);
          if (pRes.ok) {
            const p = (await pRes.json()) as { name: string; employer?: string };
            setPerson({ name: p.name, employer: (p as any).employer });
          }
        } catch {}
      } else {
        setPerson(null);
      }
    } catch (e: any) {
      setError(e.message || "Error loading alert");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 15000); // simple polling to simulate realtime
    return () => clearInterval(id);
  }, [alertId]);

  // Load remembered workflow id for this alert (if any)
  useEffect(() => {
    try {
      const key = `wfByAlert:${alertId}`;
      const saved = typeof window !== 'undefined' ? window.localStorage.getItem(key) : null;
      if (saved) {
        setWfId(saved);
        // lazily fetch status
        void refreshWorkflowStatus(saved);
      } else {
        setWfId(null);
        setWfInfo(null);
      }
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alertId]);

  // Poll workflow status when a workflow exists
  useEffect(() => {
    if (!wfId) return;
    const id = window.setInterval(() => {
      void refreshWorkflowStatus();
    }, 10000);
    return () => window.clearInterval(id);
  }, [wfId]);

  async function ack() {
    try {
      setUpdating(true);
      await fetch(`/api/v1/alerts/${alertId}/ack`, { method: "POST" });
      await fetchAll();
    } finally {
      setUpdating(false);
    }
  }

  async function setStatus(newStatus: AlertDetail["status"]) {
    try {
      setUpdating(true);
      await fetch(`/api/v1/alerts/${alertId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      await fetchAll();
    } finally {
      setUpdating(false);
    }
  }

  async function addComment() {
    if (!comment.trim()) return;
    try {
      setUpdating(true);
      await fetch(`/api/v1/alerts/${alertId}/comment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: comment.trim() }),
      });
      setComment("");
      await fetchAll();
    } finally {
      setUpdating(false);
    }
  }

  async function summarize() {
    try {
      setAiError(null);
      setAiLoading(true);
      const res = await fetch(`/api/agent/summarize/alert/${detail!.id}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to summarize");
      const data = (await res.json()) as { summary: string; recommendation: string };
      setAiSummary(data.summary);
      setAiRecommendation(data.recommendation);
    } catch (e: any) {
      setAiError(e.message || "Error generating summary");
    } finally {
      setAiLoading(false);
    }
  }

  async function startRemediation() {
    if (!detail) return;
    try {
      setWfStarting(true);
      setWfResult(null);
      const payload = {
        alert_id: detail.id,
        risk_score: detail.risk,
        severity: detail.severity,
        customer_id: detail.entityId || "unknown",
        transaction_ids: detail.transactions.map((t) => t.id),
        triggered_rules: detail.ruleHits.map((r) => r.id),
        customer_profile: { is_pep: false },
        jurisdiction: "SG",
        alert_type: "TransactionAlert",
      } as const;
      const res = await startWorkflow(payload);
      setWfResult({ id: res.workflow_instance_id, message: res.message });
      setWfId(res.workflow_instance_id);
      try {
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(`wfByAlert:${alertId}`, res.workflow_instance_id);
        }
      } catch {}
      await refreshWorkflowStatus(res.workflow_instance_id);
    } catch (e: any) {
      setWfResult({ id: "", message: e.message || "Failed to start remediation" });
    } finally {
      setWfStarting(false);
    }
  }

  async function refreshWorkflowStatus(id?: string) {
    const wid = (id || wfId);
    if (!wid) return;
    try {
      setWfLoading(true);
      setWfError(null);
      const info = await getWorkflow(wid);
      setWfInfo(info);
    } catch (e: any) {
      setWfError(e.message || "Failed to load workflow");
    } finally {
      setWfLoading(false);
    }
  }

  async function refreshAuditTrail() {
    if (!wfId) return;
    try {
      setAuditLoading(true);
      const data = await getAuditTrail(wfId);
      setAudit(data.audit_entries || []);
    } catch (e) {
      setAudit([]);
    } finally {
      setAuditLoading(false);
    }
  }

  async function markWorkflowComplete() {
    if (!wfId) return;
    try {
      setCompleteRunning(true);
      await completeWorkflow(wfId);
      await refreshWorkflowStatus();
    } finally {
      setCompleteRunning(false);
    }
  }

  function computeNextSteps(template?: string, current?: string): string[] {
    if (!template || !current) return [];
    const map: Record<string, string[]> = {
      CRITICAL_BLOCK_WORKFLOW: ["initialize", "block_transactions", "notify_stakeholders", "investigation", "complete"],
      EDD_STANDARD_WORKFLOW: ["initialize", "request_documents", "validate_documents", "compliance_review", "complete"],
      EDD_PEP_WORKFLOW: ["initialize", "pep_verification", "senior_approval", "source_validation", "complete"],
      ENHANCED_MONITORING_WORKFLOW: ["initialize", "setup_monitoring", "periodic_review", "complete"],
    };
    const steps = map[template] || [];
    const idx = steps.indexOf(current);
    return idx >= 0 ? steps.slice(idx + 1) : steps;
  }

  async function runStep(stepName: string) {
    if (!wfId) return;
    try {
      setStepError(null);
      setStepRunning(stepName);
      await executeStep(wfId, stepName);
      await refreshWorkflowStatus();
      if (auditOpen) await refreshAuditTrail();
    } catch (e: any) {
      setStepError(e.message || "Failed to execute step");
    } finally {
      setStepRunning(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-64 animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" />
        <div className="h-40 w-full animate-pulse rounded bg-zinc-200 dark:bg-zinc-800" />
      </div>
    );
  }
  if (error || !detail) {
    return <div className="text-red-600">{error || "Not found"}</div>;
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Left: Main */}
      <div className="lg:col-span-2 space-y-6">
        <header className="rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-6 w-6 text-primary" />
              <h1 className="text-xl font-semibold">Alert {detail.id}</h1>
            </div>
            <div className="flex items-center gap-2">
              <span className={`rounded px-2 py-1 text-xs ${severityColor}`}>{detail.severity.toUpperCase()}</span>
              <span className="rounded bg-zinc-100 px-2 py-1 text-xs dark:bg-zinc-800">Status: {detail.status}</span>
              <span className="rounded bg-zinc-100 px-2 py-1 text-xs dark:bg-zinc-800">Risk: {detail.risk}</span>
            </div>
          </div>
          {person ? (
            <div className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
              Person: <span className="font-medium text-zinc-900 dark:text-zinc-50">{person.name}</span>
              {person.employer ? <> • {person.employer}</> : null}
            </div>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={ack}
              disabled={updating || detail.status !== "new"}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
            >
              Acknowledge
            </button>
            <button
              onClick={() => setStatus("in_progress")}
              disabled={updating || detail.status === "in_progress"}
              className="rounded-md border px-3 py-1.5 text-sm"
            >
              Mark In Progress
            </button>
            <button
              onClick={() => setStatus("closed")}
              disabled={updating || detail.status === "closed"}
              className="rounded-md border px-3 py-1.5 text-sm"
            >
              Close
            </button>
            <button
              onClick={startRemediation}
              disabled={wfStarting}
              className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white disabled:opacity-60"
            >
              {wfStarting ? "Starting…" : "Start Remediation"}
            </button>
            {detail.entityId && (
              <Link href={`/kyc/${detail.entityId}`} className="rounded-md border px-3 py-1.5 text-sm">
                Background Check
              </Link>
            )}
          </div>
        </header>
        {(wfResult || wfId) && (
          <div className="rounded-lg border p-3 text-sm">
            <div className="flex items-center justify-between">
              <div className="font-medium">Remediation</div>
              <div className="flex items-center gap-2">
                <button onClick={() => refreshWorkflowStatus()} className="rounded border px-2 py-1 text-xs">{wfLoading ? 'Refreshing…' : 'Refresh'}</button>
                <button onClick={() => { setAuditOpen((v)=>!v); if (!auditOpen) refreshAuditTrail(); }} className="rounded border px-2 py-1 text-xs">{auditOpen ? 'Hide Audit' : 'Show Audit'}</button>
              </div>
            </div>
            <div className="mt-1 text-zinc-600 dark:text-zinc-400">
              {wfResult && (
                wfResult.id
                  ? <>Started workflow <span className="font-mono">{wfResult.id}</span>. {wfResult.message}</>
                  : <span className="text-red-600">{wfResult.message}</span>
              )}
              {wfId && (
                <div className="mt-2">
                  <div>Workflow ID: <span className="font-mono">{wfId}</span></div>
                  {wfError ? (
                    <div className="text-red-600">{wfError}</div>
                  ) : wfInfo ? (
                    <>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">Status: {wfInfo.status}</span>
                      <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">Step: {wfInfo.current_step}</span>
                      {typeof wfInfo.progress === 'number' && (
                        <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">Progress: {Math.round(wfInfo.progress)}%</span>
                      )}
                      {wfInfo.assigned_to && (
                        <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">Assignee: {wfInfo.assigned_to}</span>
                      )}
                      <button onClick={markWorkflowComplete} disabled={completeRunning || wfInfo.status === 'completed'} className="ml-2 rounded bg-emerald-600 px-2 py-1 text-xs text-white disabled:opacity-50">
                        {completeRunning ? 'Completing…' : 'Mark Complete'}
                      </button>
                    </div>
                    
                    {wfInfo.selected_workflow && (
                      <div className="mt-2">
                        <div className="text-xs text-zinc-500">Next steps:</div>
                        <div className="mt-1 flex flex-wrap gap-2">
                          {computeNextSteps(wfInfo.selected_workflow, wfInfo.current_step).map((s) => (
                            <button
                              key={s}
                              onClick={() => runStep(s)}
                              disabled={!!stepRunning}
                              className="rounded border px-2 py-0.5 text-xs"
                              title="Execute step"
                            >
                              {stepRunning === s ? 'Running…' : s}
                            </button>
                          ))}
                        </div>
                        {stepError && <div className="mt-1 text-xs text-red-600">{stepError}</div>}
                      </div>
                    )}
                    </>
                  ) : (
                    <div className="text-xs text-zinc-500">No status loaded yet.</div>
                  )}
                </div>
              )}
            </div>

            {auditOpen && (
              <div className="mt-3 border-t pt-2">
                <div className="text-xs font-medium">Audit Trail</div>
                {auditLoading ? (
                  <div className="text-xs text-zinc-500">Loading audit…</div>
                ) : audit && audit.length > 0 ? (
                  <ul className="mt-1 space-y-1 text-xs">
                    {audit.map((a, i) => (
                      <li key={i} className="flex items-center justify-between rounded border p-1">
                        <span>{a.action.replace(/_/g, ' ')}</span>
                        <span className="text-zinc-500">{new Date(a.timestamp).toLocaleString()}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="text-xs text-zinc-500">No audit entries.</div>
                )}
              </div>
            )}
          </div>
        )}

        <section className="rounded-lg border p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <BadgeCheck className="h-4 w-4" /> Rule hits
          </h2>
          <ul className="space-y-2">
            {detail.ruleHits.map((r) => (
              <li key={r.id} className="flex items-center justify-between rounded border p-2">
                <span className="text-sm">{r.name}</span>
                <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs dark:bg-zinc-800">Score {r.score}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-lg border p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Bell className="h-4 w-4" /> Transactions
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-zinc-500">
                <tr>
                  <th className="py-1 pr-4">ID</th>
                  <th className="py-1 pr-4">Amount</th>
                  <th className="py-1 pr-4">Counterparty</th>
                  <th className="py-1 pr-4">Time</th>
                </tr>
              </thead>
              <tbody>
                {detail.transactions.map((t) => (
                  <tr key={t.id} className="border-t">
                    <td className="py-2 pr-4">{t.id}</td>
                    <td className="py-2 pr-4">{t.amount.toLocaleString()} {t.currency}</td>
                    <td className="py-2 pr-4">{t.counterparty}</td>
                    <td className="py-2 pr-4">{new Date(t.ts).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* AI Summary */}
        <section className="rounded-lg border p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Bell className="h-4 w-4" /> AI Summary & Action
          </h2>
          <div className="flex items-center gap-2">
            <button onClick={summarize} disabled={aiLoading} className="rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-60">
              {aiLoading ? "Summarizing…" : "Summarize"}
            </button>
          </div>
          <div className="mt-3 text-sm">
            {aiError ? (
              <div className="text-red-600">{aiError}</div>
            ) : aiSummary ? (
              <>
                <p>{aiSummary}</p>
                <p className="mt-1"><span className="font-medium">Recommendation:</span> {aiRecommendation}</p>
              </>
            ) : (
              <p className="text-zinc-500">No summary yet.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border p-4">
          <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <FileText className="h-4 w-4" /> Documents
          </h2>
          <ul className="space-y-2">
            {detail.documents.map((d) => (
              <li key={d.id} className="flex items-center justify-between rounded border p-2 text-sm">
                <span>{d.name}</span>
                <span className="text-xs text-zinc-500">{d.type}{d.anomaly ? ` • ${d.anomaly}` : ""}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* Right: Timeline */}
      <aside className="space-y-3">
        <div className="rounded-lg border p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <History className="h-4 w-4" /> Timeline
          </h3>
          <ol className="space-y-3 text-sm">
            {timeline.map((e) => (
              <li key={e.id} className="border-l pl-3">
                <div className="text-xs text-zinc-500">{new Date(e.ts).toLocaleString()}</div>
                <div>{e.text}</div>
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-lg border p-4">
          <h3 className="mb-2 text-sm font-semibold">Add comment</h3>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full rounded border p-2 text-sm"
            rows={3}
            placeholder="Leave a note for the case…"
          />
          <button onClick={addComment} className="mt-2 rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground">
            Comment
          </button>
        </div>
      </aside>
    </div>
  );
}
