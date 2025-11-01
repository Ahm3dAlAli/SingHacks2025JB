"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type AlertItem = {
  id: string;
  entity: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "new" | "acknowledged" | "in_progress" | "closed";
  createdAt: string;
  amount?: number;
  currency?: string;
  direction?: "IN" | "OUT";
  originator_name?: string;
  originator_account_last4?: string;
  beneficiary_name?: string;
  beneficiary_account_last4?: string;
  sanctions_screening?: string;
  channel?: string;
  product_type?: string;
  booking_jurisdiction?: string;
  regulator?: string;
};

type RuleHit = { id: string; name: string; score: number };
type RuleInfo = { ruleHits: RuleHit[]; risk: number; entityId?: string };
type ExplainData = {
  summary: string;
  rules: { id: string; name: string; contribution: number }[];
  evidence: {
    transactions: { id: string; amount: number; cp: string }[];
    documents: { id: string; name: string; anomaly: string | null }[];
  };
};

export default function AlertsManagerPage() {
  const router = useRouter();
  const [items, setItems] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [severity, setSeverity] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [entity, setEntity] = useState<string>("");
  const [ruleInfoMap, setRuleInfoMap] = useState<Record<string, RuleInfo>>({});
  const [aiMap, setAiMap] = useState<Record<string, { loading: boolean; summary?: string; recommendation?: string; error?: string }>>({});
  const [personMap, setPersonMap] = useState<Record<string, { name: string; employer?: string }>>({});
  const [explainMap, setExplainMap] = useState<Record<string, { loading: boolean; open: boolean; error?: string; data?: ExplainData }>>({});
  const [commentMap, setCommentMap] = useState<Record<string, string>>({});
  const [busyMap, setBusyMap] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(12);
  const [total, setTotal] = useState<number>(0);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (status) params.set("status", status);
    if (entity) params.set("entity", entity);
    params.set("page", String(page));
    params.set("pageSize", String(pageSize));
    return params.toString();
  }, [severity, status, entity, page, pageSize]);

  // Reset to first page when filters change
  useEffect(() => {
    setPage(1);
  }, [severity, status, entity]);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const url = query ? `/api/alerts?${query}` : "/api/alerts";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load alerts");
      const data = (await res.json()) as { items: AlertItem[]; total?: number; page?: number; pageSize?: number };
      setItems(data.items);
      setTotal(data.total ?? data.items.length);
      // After basic list loads, fetch detail per alert (for badges and AI reasoning)
      try {
        // initialize AI map as loading
        setAiMap(Object.fromEntries(data.items.map((a) => [a.id, { loading: true }])));
        setExplainMap(Object.fromEntries(data.items.map((a) => [a.id, { loading: true, open: true }])));
        const entries = await Promise.all(
          data.items.map(async (a) => {
            try {
              const dRes = await fetch(`/api/alerts/${a.id}`);
              if (!dRes.ok) return [a.id, { ruleHits: [], risk: 0 }] as const;
              const detail = (await dRes.json()) as { ruleHits?: RuleHit[]; risk?: number; entityId?: string };
              return [a.id, { ruleHits: detail.ruleHits ?? [], risk: detail.risk ?? 0, entityId: detail.entityId }] as const;
            } catch {
              return [a.id, { ruleHits: [], risk: 0 }] as const;
            }
          })
        );
        const ruleMap = Object.fromEntries(entries) as Record<string, RuleInfo>;
        setRuleInfoMap(ruleMap);

        // fetch person names for display (align entity label to person)
        const personEntries = await Promise.all(
          Object.entries(ruleMap).map(async ([alertId, info]) => {
            if (!info.entityId) return [alertId, undefined] as const;
            try {
              const pRes = await fetch(`/api/entities/${info.entityId}`);
              if (!pRes.ok) return [alertId, undefined] as const;
              const p = (await pRes.json()) as { name: string; employer?: string };
              return [alertId, { name: p.name, employer: p.employer }] as const;
            } catch {
              return [alertId, undefined] as const;
            }
          })
        );
        setPersonMap(Object.fromEntries(personEntries.filter(([, v]) => !!v)) as Record<string, { name: string; employer?: string }>);

        // fetch AI summaries automatically
        const aiEntries = await Promise.all(
          data.items.map(async (a) => {
            try {
              const sRes = await fetch(`/api/agent/summarize/alert/${a.id}`, { method: "POST" });
              if (!sRes.ok) return [a.id, { loading: false, error: "Failed to summarize" }] as const;
              const s = (await sRes.json()) as { summary: string; recommendation: string };
              return [a.id, { loading: false, summary: s.summary, recommendation: s.recommendation }] as const;
            } catch (e: any) {
              return [a.id, { loading: false, error: "Error" }] as const;
            }
          })
        );
        setAiMap(Object.fromEntries(aiEntries));
        const exEntries = await Promise.all(
          data.items.map(async (a) => {
            try {
              const eRes = await fetch(`/api/agent/explain/${a.id}`, { method: "POST" });
              if (!eRes.ok) return [a.id, { loading: false, open: true, error: "Failed to load rationale" }] as const;
              const e = (await eRes.json()) as { rationale: ExplainData };
              return [a.id, { loading: false, open: true, data: e.rationale }] as const;
            } catch {
              return [a.id, { loading: false, open: true, error: "Error" }] as const;
            }
          })
        );
        setExplainMap(Object.fromEntries(exEntries));
      } catch {}
    } catch (e: any) {
      setError(e.message || "Error loading alerts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  async function quickAction(a: AlertItem) {
    // Simple example: acknowledge new alerts, otherwise close non-closed alerts.
    const endpoint =
      a.status === "new" ? "ack" : a.status !== "closed" ? "status" : null;
    if (!endpoint) return;
    await fetch(
      `/api/alerts/${a.id}/${endpoint}` + (endpoint === "status" ? "" : ""),
      {
        method: "POST",
        headers:
          endpoint === "status"
            ? { "Content-Type": "application/json" }
            : undefined,
        body:
          endpoint === "status"
            ? JSON.stringify({ status: "closed" })
            : undefined,
      }
    );
    await load();
  }

  async function actWithDecision(a: AlertItem, decision: "approve" | "hold" | "escalate") {
    try {
      setBusyMap((m) => ({ ...m, [a.id]: true }));
      const reason = commentMap[a.id]?.trim() || undefined;
      // Record feedback regardless of status change
      await fetch(`/api/agent/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: a.id, decision, reason }),
      });
      // Map decision to alert status update
      if (decision === "approve") {
        await fetch(`/api/alerts/${a.id}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "closed" }),
        });
      } else if (decision === "hold") {
        await fetch(`/api/alerts/${a.id}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "acknowledged" }),
        });
      } else if (decision === "escalate") {
        await fetch(`/api/alerts/${a.id}/status`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: "in_progress" }),
        });
      }
      setCommentMap((m) => ({ ...m, [a.id]: "" }));
      await load();
    } finally {
      setBusyMap((m) => ({ ...m, [a.id]: false }));
    }
  }

  function severityClass(s: AlertItem["severity"]) {
    switch (s) {
      case "critical":
        return "bg-red-600 text-white";
      case "high":
        return "bg-orange-600 text-white";
      case "medium":
        return "bg-amber-500 text-white";
      default:
        return "bg-emerald-600 text-white";
    }
  }
  function severityAccent(s: AlertItem["severity"]) {
    switch (s) {
      case "critical":
        return { bg: "bg-red-50/60 dark:bg-red-950/30", border: "border-l-4 border-red-600" };
      case "high":
        return { bg: "bg-orange-50/60 dark:bg-orange-950/30", border: "border-l-4 border-orange-600" };
      case "medium":
        return { bg: "bg-amber-50/60 dark:bg-amber-950/30", border: "border-l-4 border-amber-500" };
      default:
        return { bg: "bg-emerald-50/60 dark:bg-emerald-950/30", border: "border-l-4 border-emerald-600" };
    }
  }

  function dirPill(dir?: string) {
    const color = dir === "IN" ? "bg-emerald-600" : "bg-blue-600";
    return dir ? <span className={`rounded px-2 py-0.5 text-[10px] text-white ${color}`}>{dir}</span> : null;
  }

  function sanctionsBadge(s?: string) {
    const v = (s ?? "").toString().toUpperCase();
    let cls = "bg-zinc-200 text-zinc-800";
    if (v === "CLEAR") cls = "bg-emerald-100 text-emerald-700";
    else if (v === "POTENTIAL_MATCH") cls = "bg-amber-100 text-amber-700";
    else if (v === "HIT") cls = "bg-red-100 text-red-700";
    return <span className={`rounded px-2 py-0.5 text-[10px] ${cls}`}>{v || "UNKNOWN"}</span>;
  }

  function RiskRing({ value }: { value?: number }) {
    const v = Math.max(0, Math.min(100, value ?? 0));
    const color = v >= 80 ? "#dc2626" : v >= 50 ? "#f59e0b" : "#059669";
    const bg = `conic-gradient(${color} ${v * 3.6}deg, rgba(0,0,0,0.08) 0)`;
    return (
      <div className="relative h-9 w-9">
        <div className="h-9 w-9 rounded-full" style={{ background: bg }} />
        <div className="absolute inset-1 flex items-center justify-center rounded-full bg-white text-[10px] dark:bg-zinc-950">
          {Math.round(v)}
        </div>
      </div>
    );
  }
  // Explanation panels are shown by default for every card

  // AI summaries are loaded automatically in load()

  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
            Alerts
          </h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Filter and review alerts. Click a card for details.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span>Page size</span>
          <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))} className="rounded border bg-white p-1 dark:border-zinc-700 dark:bg-zinc-950">
            {[12, 24, 36, 48].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">
            Severity
          </label>
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          >
            <option value="">All</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">
            Status
          </label>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          >
            <option value="">All</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="in_progress">In Progress</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">
            Entity
          </label>
          <input
            value={entity}
            onChange={(e) => setEntity(e.target.value)}
            placeholder="e.g. Entity-1"
            className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
      </div>

      {/* Cards */}
      {loading ? (
        <div className="grid grid-cols-1 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-28 animate-pulse rounded-lg border bg-zinc-100 dark:bg-zinc-900"
            />
          ))}
        </div>
      ) : error ? (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/40">
          {error}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-md border p-4 text-sm text-zinc-600 dark:text-zinc-400">
          No alerts found.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {items.map((a) => (
            <div
              key={a.id}
              className={`rounded-xl border p-4 shadow-sm transition hover:shadow-md ${severityAccent(a.severity).bg} ${severityAccent(a.severity).border}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
                      {(a.currency ?? "")} {a.amount?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    {dirPill(a.direction)}
                    <span className={`rounded-full px-2 py-0.5 text-[10px] ${severityClass(a.severity)}`}>{a.severity.toUpperCase()}</span>
                    <span className="rounded border bg-white/60 px-2 py-0.5 text-[10px] capitalize dark:bg-zinc-900/40">{a.status.replace("_", " ")}</span>
                  </div>
                  <div className="mt-1 truncate text-sm text-zinc-700 dark:text-zinc-300">
                    {(a.originator_name || (a.originator_account_last4 ? `****${a.originator_account_last4}` : "")) || (personMap[a.id]?.name ?? a.entity)}
                    <span className="mx-1">→</span>
                    {(a.beneficiary_name || (a.beneficiary_account_last4 ? `****${a.beneficiary_account_last4}` : "")) || a.entity}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-zinc-600 dark:text-zinc-400">
                    <span className="rounded bg-white/60 px-1.5 py-0.5 dark:bg-zinc-900/40">{new Date(a.createdAt).toLocaleString("en-SG", { timeZone: "Asia/Singapore" })}</span>
                    {a.channel ? <span className="rounded bg-white/60 px-1.5 py-0.5 dark:bg-zinc-900/40">{a.channel}</span> : null}
                    {a.product_type ? <span className="rounded bg-white/60 px-1.5 py-0.5 dark:bg-zinc-900/40">{a.product_type}</span> : null}
                    {a.booking_jurisdiction ? <span className="rounded bg-white/60 px-1.5 py-0.5 dark:bg-zinc-900/40">{a.booking_jurisdiction}</span> : null}
                    {a.regulator ? <span className="rounded bg-white/60 px-1.5 py-0.5 dark:bg-zinc-900/40">{a.regulator}</span> : null}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <RiskRing value={ruleInfoMap[a.id]?.risk} />
                  {sanctionsBadge(a.sanctions_screening)}
                </div>
              </div>
              {/* Rule Hit Badges, grouped */}
              <div className="mt-3 space-y-2">
                {(() => {
                  const hits = ruleInfoMap[a.id]?.ruleHits ?? [];
                  const regs = hits.filter((h) => h.id.startsWith("rule-sanctions") || h.id === "rule-pep");
                  const pats = hits.filter((h) => !regs.includes(h));
                  return (
                    <>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-medium text-zinc-600 dark:text-zinc-400">Flagged Patterns:</span>
                        {pats.length > 0 ? (
                          pats.slice(0, 6).map((r) => (
                            <Badge key={r.id}>{r.name} ({r.score})</Badge>
                          ))
                        ) : (
                          <span className="text-[11px] text-zinc-500">None</span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-medium text-zinc-600 dark:text-zinc-400">Regulatory Violations:</span>
                        {regs.length > 0 ? (
                          regs.slice(0, 6).map((r) => (
                            <Badge key={r.id}>{r.name} ({r.score})</Badge>
                          ))
                        ) : (
                          <span className="text-[11px] text-zinc-500">None</span>
                        )}
                      </div>
                    </>
                  );
                })()}
              </div>
              {/* Why flagged */}
              <div className="mt-2 rounded-md border bg-white/50 p-2 text-xs text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900/40">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-medium">Why flagged</span>
                  {aiMap[a.id]?.recommendation ? (
                    <span className="rounded bg-zinc-100 px-2 py-0.5 text-[10px] uppercase tracking-wide dark:bg-zinc-800">{aiMap[a.id]?.recommendation}</span>
                  ) : null}
                </div>
                {aiMap[a.id]?.loading ? (
                  <span className="text-zinc-500">Summarizing…</span>
                ) : aiMap[a.id]?.error ? (
                  <span className="text-red-600">{aiMap[a.id]?.error}</span>
                ) : aiMap[a.id]?.summary ? (
                  <>
                    <div>{aiMap[a.id]?.summary}</div>
                  </>
                ) : (
                  <span className="text-zinc-500">No summary yet.</span>
                )}
              </div>
              <div className="mt-3 flex flex-col gap-2">
                <input
                  value={commentMap[a.id] ?? ""}
                  onChange={(e) => setCommentMap((m) => ({ ...m, [a.id]: e.target.value }))}
                  placeholder="Add comment (optional)"
                  className="w-full rounded border bg-white p-2 text-xs dark:border-zinc-700 dark:bg-zinc-950"
                />
                <div className="flex items-center gap-2">
                <Link
                  href={`/alerts/${a.id}`}
                  className="rounded bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground shadow hover:opacity-90"
                >
                  View
                </Link>
                {ruleInfoMap[a.id]?.entityId && (
                  <Link
                    href={`/kyc/${ruleInfoMap[a.id]!.entityId}`}
                    className="rounded border px-3 py-1.5 text-xs"
                  >
                    Background
                  </Link>
                )}
                <button
                  disabled={busyMap[a.id]}
                  onClick={() => actWithDecision(a, "approve")}
                  className="rounded border bg-white/60 px-3 py-1.5 text-xs shadow-sm disabled:opacity-60 dark:bg-zinc-900/40"
                >
                  Approve
                </button>
                <button
                  disabled={busyMap[a.id]}
                  onClick={() => actWithDecision(a, "hold")}
                  className="rounded border bg-white/60 px-3 py-1.5 text-xs shadow-sm disabled:opacity-60 dark:bg-zinc-900/40"
                >
                  Hold
                </button>
                <button
                  disabled={busyMap[a.id]}
                  onClick={() => actWithDecision(a, "escalate")}
                  className="rounded border bg-white/60 px-3 py-1.5 text-xs shadow-sm disabled:opacity-60 dark:bg-zinc-900/40"
                >
                  Escalate
                </button>
                </div>
              </div>
              <div className="mt-3 rounded-md border bg-white/60 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-900/40">
                {explainMap[a.id]?.loading ? (
                  <div className="text-zinc-500">Loading rationale…</div>
                ) : explainMap[a.id]?.error ? (
                  <div className="text-red-600">{explainMap[a.id]?.error}</div>
                ) : explainMap[a.id]?.data ? (
                  <div className="space-y-2">
                    <div>
                      <span className="font-medium">Rules:</span>
                      <div className="mt-1 flex flex-wrap gap-2">
                        {explainMap[a.id]!.data!.rules.map((r) => (
                          <span key={r.id} className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] dark:bg-zinc-800">
                            {r.name} ({r.contribution})
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <span className="font-medium">Evidence:</span>
                      <div className="mt-1 grid grid-cols-1 gap-2 sm:grid-cols-2">
                        <div>
                          <div className="text-[11px] text-zinc-500">Transactions</div>
                          <ul className="mt-1 space-y-1">
                            {explainMap[a.id]!.data!.evidence.transactions.map((t) => (
                              <li key={t.id} className="flex justify-between">
                                <span className="font-mono">{t.id}</span>
                                <span>
                                  {t.amount.toLocaleString()} • {t.cp}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <div className="text-[11px] text-zinc-500">Documents</div>
                          <ul className="mt-1 space-y-1">
                            {explainMap[a.id]!.data!.evidence.documents.map((d) => (
                              <li key={d.id} className="flex items-center justify-between">
                                <span>{d.name}</span>
                                {d.anomaly ? (
                                  <span className="rounded bg-red-600 px-1.5 py-0.5 text-[10px] text-white">{d.anomaly}</span>
                                ) : (
                                  <span className="text-[10px] text-zinc-500">ok</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
      {/* Pagination Controls */}
      {!loading && items.length > 0 ? (
        <div className="mt-4 flex items-center justify-between text-xs text-zinc-600 dark:text-zinc-400">
          <div>
            {(() => {
              const start = (page - 1) * pageSize + 1;
              const end = Math.min(page * pageSize, total);
              const pages = Math.max(1, Math.ceil(total / pageSize));
              return <span>Showing {start}-{end} of {total} • Page {page} / {pages}</span>;
            })()}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="rounded border px-2 py-1 disabled:opacity-60">Prev</button>
            <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="rounded border px-2 py-1 disabled:opacity-60">Next</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
      {children}
    </span>
  );
}
