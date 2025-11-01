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
};

type RuleHit = { id: string; name: string; score: number };
type RuleInfo = { ruleHits: RuleHit[]; risk: number };
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
  const [explainMap, setExplainMap] = useState<Record<string, { loading: boolean; open: boolean; error?: string; data?: ExplainData }>>({});

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (status) params.set("status", status);
    if (entity) params.set("entity", entity);
    return params.toString();
  }, [severity, status, entity]);

  async function load() {
    try {
      setLoading(true);
      setError(null);
      const url = query ? `/api/alerts?${query}` : "/api/alerts";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to load alerts");
      const data = (await res.json()) as { items: AlertItem[] };
      setItems(data.items);
      // After basic list loads, fetch detail per alert (for badges and AI reasoning)
      try {
        // initialize AI map as loading
        setAiMap(Object.fromEntries(data.items.map((a) => [a.id, { loading: true }])));
        setExplainMap(Object.fromEntries(data.items.map((a) => [a.id, { loading: true, open: false }])));
        const entries = await Promise.all(
          data.items.map(async (a) => {
            try {
              const dRes = await fetch(`/api/alerts/${a.id}`);
              if (!dRes.ok) return [a.id, { ruleHits: [], risk: 0 }] as const;
              const detail = (await dRes.json()) as { ruleHits?: RuleHit[]; risk?: number };
              return [a.id, { ruleHits: detail.ruleHits ?? [], risk: detail.risk ?? 0 }] as const;
            } catch {
              return [a.id, { ruleHits: [], risk: 0 }] as const;
            }
          })
        );
        setRuleInfoMap(Object.fromEntries(entries));

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
              if (!eRes.ok) return [a.id, { loading: false, open: false, error: "Failed to load rationale" }] as const;
              const e = (await eRes.json()) as { rationale: ExplainData };
              return [a.id, { loading: false, open: false, data: e.rationale }] as const;
            } catch {
              return [a.id, { loading: false, open: false, error: "Error" }] as const;
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
  function toggleExplain(id: string) {
    setExplainMap((m) => ({ ...m, [id]: { ...(m[id] ?? { loading: false, open: false }), open: !(m[id]?.open ?? false) } }));
  }

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
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
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
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((a) => (
            <div key={a.id} className="rounded-lg border p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs">{a.id}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] ${severityClass(
                        a.severity
                      )}`}
                    >
                      {a.severity.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                    {a.entity}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {new Date(a.createdAt).toLocaleString()}
                  </div>
                </div>
                <span className="rounded border px-2 py-0.5 text-[10px] capitalize">
                  {a.status.replace("_", " ")}
                </span>
              </div>
              {/* Rule Hit Badges */}
              <div className="mt-3 flex flex-wrap gap-2">
                {(ruleInfoMap[a.id]?.ruleHits && ruleInfoMap[a.id].ruleHits.length > 0
                  ? ruleInfoMap[a.id].ruleHits.slice(0, 3)
                  : []
                ).map((r) => (
                  <Badge key={r.id}>
                    {r.name} ({r.score})
                  </Badge>
                ))}
                {(!ruleInfoMap[a.id] || ruleInfoMap[a.id].ruleHits.length === 0) && (
                  <span className="text-xs text-zinc-500">No patterns</span>
                )}
              </div>
              {/* AI Summary */}
              <div className="mt-2 text-xs text-zinc-700 dark:text-zinc-300">
                {aiMap[a.id]?.loading ? (
                  <span className="text-zinc-500">Summarizing…</span>
                ) : aiMap[a.id]?.error ? (
                  <span className="text-red-600">{aiMap[a.id]?.error}</span>
                ) : aiMap[a.id]?.summary ? (
                  <>
                    <div>{aiMap[a.id]?.summary}</div>
                    <div>
                      <span className="font-medium">Recommendation:</span> {aiMap[a.id]?.recommendation}
                    </div>
                  </>
                ) : (
                  <span className="text-zinc-500">No summary yet.</span>
                )}
              </div>
              <div className="mt-3 flex items-center gap-2">
                <Link
                  href={`/alerts/${a.id}`}
                  className="rounded bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90"
                >
                  View
                </Link>
                {(a.status === "new" || a.status !== "closed") && (
                  <button
                    onClick={() => quickAction(a)}
                    className="rounded border px-3 py-1.5 text-xs"
                  >
                    {a.status === "new"
                      ? "Acknowledge"
                      : a.status !== "closed"
                      ? "Close"
                      : ""}
                  </button>
                )}
                <button onClick={() => toggleExplain(a.id)} className="rounded border px-3 py-1.5 text-xs">
                  {explainMap[a.id]?.open ? "Hide" : "See more"}
                </button>
              </div>
              {explainMap[a.id]?.open && (
                <div className="mt-3 rounded-md border bg-zinc-50 p-3 text-xs dark:border-zinc-800 dark:bg-zinc-900/50">
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
              )}
            </div>
          ))}
        </div>
      )}
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
