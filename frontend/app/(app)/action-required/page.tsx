"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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
};

export default function ActionRequiredPage() {
  const router = useRouter();
  const [items, setItems] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  async function load() {
    setLoading(true);
    const res = await fetch("/api/rules/suggestions?status=needs_review");
    const data = (await res.json()) as { items: Suggestion[] };
    setItems(data.items);
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function act(id: string, action: "validate" | "replay" | "approve" | "reject") {
    setMessage("");
    const res = await fetch(`/api/rules/suggestions/${id}/${action}`, { method: "POST" });
    const data = await res.json();
    if (action === "validate") setMessage(data.ok ? `Validation ok${data.warnings?.length ? `, warnings: ${data.warnings.join(", ")}` : ""}` : "Validation failed");
    else if (action === "replay") setMessage(data.ok ? `Replay: ${data.evaluated} eval, regressions ${data.regressions}, improvements ${data.improvements}` : "Replay failed");
    else {
      await load();
      setMessage(action === "approve" ? "Approved" : "Rejected");
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Action Required</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">Review rule change suggestions generated from regulatory updates.</p>
      </div>
      {message ? <div className="rounded border bg-emerald-50 p-2 text-sm text-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-200">{message}</div> : null}
      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-lg border bg-zinc-100 dark:bg-zinc-900" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-md border p-4 text-sm text-zinc-600 dark:text-zinc-400">No pending suggestions.</div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {items.map((s) => (
            <article key={s.id} className="rounded-lg border p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs text-zinc-500">{new Date(s.createdAt).toLocaleString()} • confidence {(s.confidence * 100).toFixed(0)}%</div>
                  <h2 className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-50">{s.title}</h2>
                </div>
                <span className="rounded bg-amber-100 px-2 py-0.5 text-[10px] text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">Needs review</span>
              </div>
              <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-300">{s.rationale}</p>
              {s.impact ? (
                <div className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">Impact: ~{s.impact.estimatedHits} alerts/day • {s.impact.note}</div>
              ) : null}
              <div className="mt-3">
                <DiffView diff={s.unifiedDiff} compact />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-sm">
                <a href={`/action-required/${s.id}`} className="rounded border px-2 py-1">Review</a>
                <button onClick={() => act(s.id, "validate")} className="rounded border px-2 py-1">Validate</button>
                <button onClick={() => act(s.id, "replay")} className="rounded border px-2 py-1">Replay</button>
                <button onClick={() => act(s.id, "approve")} className="rounded bg-primary px-3 py-1 text-primary-foreground">Approve</button>
                <button onClick={() => act(s.id, "reject")} className="rounded border px-2 py-1">Reject</button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
