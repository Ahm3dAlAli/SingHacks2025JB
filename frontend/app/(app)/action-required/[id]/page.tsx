"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import DiffView from "@/components/DiffView";

type Suggestion = {
  id: string;
  updateId: string;
  ruleId: string | null;
  title: string;
  rationale: string;
  confidence: number;
  impact: { estimatedHits: number; note?: string } | null;
  suggestedDsl: string;
  currentDsl?: string | null;
  unifiedDiff: string;
  structuredDiff: { path: string; from?: string | number; to?: string | number; note?: string }[];
  status: "needs_review" | "approved" | "rejected" | "promoted";
  createdAt: string;
  createdVersionId?: string;
  compileArtifact?: string;
  promotedAt?: string;
};

type RuleDetail = { rule: { id: string; name: string; dsl: string }; history: { versionId: string; dsl: string; createdAt: string }[] } | null;

export default function SuggestionDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [s, setS] = useState<Suggestion | null>(null);
  const [msg, setMsg] = useState<string>("");
  const [validation, setValidation] = useState<{ ok: boolean; warnings?: string[] } | null>(null);
  const [replay, setReplay] = useState<{ ok: boolean; evaluated?: number; regressions?: number; improvements?: number } | null>(null);
  const [ruleDetail, setRuleDetail] = useState<RuleDetail>(null);

  useEffect(() => { if (!isLoggedIn()) router.replace("/login"); }, [router]);

  async function load() {
    const res = await fetch(`/api/rules/suggestions/${id}`);
    if (!res.ok) { setS(null); setMsg("Suggestion not found"); return; }
    const data = await res.json();
    if ((data as any).error) { setS(null); setMsg("Suggestion not found"); return; }
    setS(data);
    if (data.ruleId) {
      const rr = await fetch(`/api/rules/${data.ruleId}`);
      if (rr.ok) setRuleDetail(await rr.json());
    } else setRuleDetail(null);
  }

  useEffect(() => { load(); }, [id]);

  async function action(kind: "validate" | "replay" | "approve" | "reject" | "promote") {
    setMsg("");
    const res = await fetch(`/api/rules/suggestions/${id}/${kind}`, { method: "POST" });
    const data = await res.json();
    if (kind === "validate") { setValidation(data); setMsg(data.ok ? "Validation OK" : "Validation failed"); }
    else if (kind === "replay") { setReplay(data); setMsg(data.ok ? "Replay complete" : "Replay failed"); }
    else { await load(); setMsg(kind === "approve" ? "Approved" : kind === "reject" ? "Rejected" : "Promoted"); }
  }

  const headerBadge = useMemo(() => {
    if (!s || typeof (s as any).status !== "string") return null;
    const status = (s as any).status as string;
    const color = status === "needs_review" ? "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200"
      : status === "approved" ? "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200"
      : status === "rejected" ? "bg-rose-100 text-rose-900 dark:bg-rose-900/30 dark:text-rose-200"
      : "bg-blue-100 text-blue-900 dark:bg-blue-900/30 dark:text-blue-200";
    return <span className={`rounded px-2 py-0.5 text-[10px] ${color}`}>{status.replace("_"," ")}</span>;
  }, [s]);

  if (!s) return <div className="rounded-md border p-4 text-sm">Loading…</div>;

  return (
    <div className="space-y-6">
      <div>
        <a href="/regulatory-updates" className="text-xs text-zinc-500 underline">← Back to Regulatory Updates</a>
      </div>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-zinc-500">{new Date(s.createdAt).toLocaleString()} • confidence {(s.confidence * 100).toFixed(0)}%</div>
          <h1 className="mt-1 text-xl font-semibold text-zinc-900 dark:text-zinc-50">{s.title}</h1>
        </div>
        {headerBadge}
      </div>

      {msg ? <div className="rounded border bg-zinc-50 p-2 text-sm dark:bg-zinc-900">{msg}</div> : null}

      <div className="flex flex-wrap gap-2 text-sm">
        <button onClick={() => action("validate")} className="rounded border px-2 py-1">Validate</button>
        <button onClick={() => action("replay")} className="rounded border px-2 py-1">Replay</button>
        {s.status === "needs_review" && <button onClick={() => action("approve")} className="rounded bg-primary px-3 py-1 text-primary-foreground">Approve</button>}
        {s.status === "needs_review" && <button onClick={() => action("reject")} className="rounded border px-2 py-1">Reject</button>}
        {s.status === "approved" && <button onClick={() => action("promote")} className="rounded bg-blue-600 px-3 py-1 text-white dark:bg-blue-500">Promote</button>}
      </div>

      {/* Full Rule (Current) */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Full Rule (Current)</h2>
        {ruleDetail ? (
          <div className="space-y-2">
            <div className="text-xs text-zinc-500">{ruleDetail.rule.name} • {ruleDetail.rule.id}</div>
            <pre className="overflow-auto rounded bg-zinc-50 p-2 text-xs dark:bg-zinc-900"><code>{ruleDetail.rule.dsl}</code></pre>
          </div>
        ) : (
          <div className="text-sm text-zinc-600 dark:text-zinc-400">No existing rule (new).</div>
        )}
      </section>

      {/* Current vs Suggested */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Proposed Change</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <div className="mb-1 text-xs text-zinc-500">Current (baseline)</div>
            <pre className="overflow-auto rounded bg-zinc-50 p-2 text-xs dark:bg-zinc-900"><code>{s.currentDsl || ruleDetail?.rule.dsl || "(none)"}</code></pre>
          </div>
          <div>
            <div className="mb-1 text-xs text-zinc-500">Suggested</div>
            <pre className="overflow-auto rounded bg-zinc-50 p-2 text-xs dark:bg-zinc-900"><code>{s.suggestedDsl}</code></pre>
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs text-zinc-500">Unified Diff</div>
          <DiffView diff={s.unifiedDiff} />
        </div>
        <div>
          <div className="mb-1 text-xs text-zinc-500">Structured Changes</div>
          <ul className="list-disc pl-6 text-sm">
            {s.structuredDiff.map((d, i) => (
              <li key={i}><span className="font-mono">{d.path}</span>: {String(d.from ?? "")} → {String(d.to ?? "")} {d.note ? `• ${d.note}`: ""}</li>
            ))}
          </ul>
        </div>
        {s.createdVersionId && (
          <div className="text-sm">
            New version created: <a className="underline" href={`/api/rules/versions/${s.createdVersionId}/diff`} target="_blank" rel="noreferrer">view diff summary</a>
          </div>
        )}
      </section>

      {/* Impact */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Impact</h2>
        <div className="text-sm">
          <div>Estimated hits: {s.impact?.estimatedHits ?? "–"}</div>
          <div className="text-zinc-600 dark:text-zinc-400">{s.impact?.note}</div>
          {replay && replay.ok && (
            <div className="mt-3 rounded border p-3">
              Replay evaluated {replay.evaluated} items • regressions {replay.regressions} • improvements {replay.improvements}
            </div>
          )}
        </div>
      </section>

      {/* Validation */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Validation</h2>
        <div className="text-sm">
          {validation ? (
            <div>
              <div>OK: {String(validation.ok)}</div>
              {validation.warnings?.length ? (
                <ul className="mt-2 list-disc pl-6">
                  {validation.warnings.map((w, i) => (<li key={i}>{w}</li>))}
                </ul>
              ) : <div className="text-zinc-600 dark:text-zinc-400">No warnings</div>}
            </div>
          ) : <div className="text-zinc-600 dark:text-zinc-400">Run Validate to see results.</div>}
        </div>
      </section>

      {/* Rationale */}
      <section className="space-y-2">
        <h2 className="text-sm font-semibold">Rationale</h2>
        <div className="space-y-1 text-sm">
          <div>{s.rationale}</div>
          <div className="text-xs text-zinc-500">Update: {s.updateId} • Rule: {s.ruleId ?? "(new)"}</div>
          {s.promotedAt && (
            <div className="text-xs">Promoted at {new Date(s.promotedAt).toLocaleString()} with artifact {s.compileArtifact}</div>
          )}
        </div>
      </section>
    </div>
  );
}
