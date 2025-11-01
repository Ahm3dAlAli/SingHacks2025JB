"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type RegUpdate = {
  id: string;
  authority: string;
  date: string;
  title: string;
  summary: string;
  url: string;
  tags: string[];
};

type Suggestion = {
  id: string;
  title: string;
  createdAt: string;
  promotedAt?: string;
  unifiedDiff: string;
  status: "needs_review" | "approved" | "rejected" | "promoted";
};

const AUTHORITIES = ["", "MAS", "HKMA", "FINMA", "FCA", "AUSTRAC"];

export default function RegulatoryUpdatesPage() {
  const router = useRouter();
  const [items, setItems] = useState<RegUpdate[]>([]);
  const [authority, setAuthority] = useState<string>("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [newSugs, setNewSugs] = useState<Suggestion[]>([]);
  const [appliedSugs, setAppliedSugs] = useState<Suggestion[]>([]);
  const [byUpdate, setByUpdate] = useState<Record<string, { pending?: Suggestion; applied?: Suggestion }>>({});

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  async function load() {
    setLoading(true);
    const qs = new URLSearchParams();
    if (authority) qs.set("authority", authority);
    if (q.trim()) qs.set("q", q.trim());
    const res = await fetch(`/api/regulatory/updates${qs.toString() ? `?${qs.toString()}` : ""}`);
    const data = (await res.json()) as { items: RegUpdate[] };
    setItems(data.items);
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authority]);

  useEffect(() => {
    let mounted = true;
    async function loadSugs() {
      try {
        const [nr, pr] = await Promise.all([
          fetch(`/api/rules/suggestions?status=needs_review`).then((r) => r.json()),
          fetch(`/api/rules/suggestions?status=promoted`).then((r) => r.json()),
        ]);
        if (!mounted) return;
        setNewSugs(nr.items ?? []);
        setAppliedSugs((pr.items ?? []).slice(0, 4));
        const map: Record<string, { pending?: Suggestion; applied?: Suggestion }> = {};
        for (const s of nr.items ?? []) {
          map[s.updateId] = { ...(map[s.updateId] || {}), pending: s } as any;
        }
        // choose most recent applied per update
        for (const s of (pr.items ?? []) as Suggestion[]) {
          const existing = map[s.updateId]?.applied;
          if (!existing || new Date(s.promotedAt || s.createdAt) > new Date(existing.promotedAt || existing.createdAt)) {
            map[s.updateId] = { ...(map[s.updateId] || {}), applied: s } as any;
          }
        }
        setByUpdate(map);
      } catch {}
    }
    loadSugs();
    const t = setInterval(loadSugs, 10000);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  function countAddsDels(diff: string) {
    let adds = 0, dels = 0;
    for (const l of (diff || "").split(/\r?\n/)) {
      if (l.startsWith("+++ ") || l.startsWith("--- ")) continue;
      if (l.startsWith("+")) adds++;
      else if (l.startsWith("-")) dels++;
    }
    return { adds, dels };
  }

  const filtered = useMemo(() => items, [items]);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Regulatory Updates</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Latest guidance and notices from MAS, HKMA, FINMA, and others (mock).</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <section className="rounded-lg border p-3">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold">What’s New</h2>
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">{newSugs.length} pending</span>
          </div>
          {newSugs.length === 0 ? (
            <div className="text-xs text-zinc-500">No pending suggestions yet. Use “Propose Rule Change” on an update.</div>
          ) : (
            <ul className="space-y-2">
              {newSugs.slice(0, 4).map((s) => {
                const { adds, dels } = countAddsDels(s.unifiedDiff);
                return (
                  <li key={s.id} className="flex items-center justify-between gap-2 rounded border p-2 text-sm">
                    <div>
                      <div className="font-medium text-zinc-900 dark:text-zinc-50">{s.title}</div>
                      <div className="text-xs text-zinc-500">{new Date(s.createdAt).toLocaleString()}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200">+{adds}</span>
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] text-rose-900 dark:bg-rose-900/30 dark:text-rose-200">-{dels}</span>
                      <button onClick={() => router.push(`/action-required/${s.id}`)} className="rounded border px-2 py-1 text-xs">Review</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <section className="rounded-lg border p-3">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recently Applied</h2>
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200">{appliedSugs.length}</span>
          </div>
          {appliedSugs.length === 0 ? (
            <div className="text-xs text-zinc-500">No applied suggestions yet.</div>
          ) : (
            <ul className="space-y-2">
              {appliedSugs.map((s) => {
                const { adds, dels } = countAddsDels(s.unifiedDiff);
                return (
                  <li key={s.id} className="flex items-center justify-between gap-2 rounded border p-2 text-sm">
                    <div>
                      <div className="font-medium text-zinc-900 dark:text-zinc-50">{s.title}</div>
                      <div className="text-xs text-zinc-500">Applied {s.promotedAt ? new Date(s.promotedAt).toLocaleString() : new Date(s.createdAt).toLocaleString()}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200">+{adds}</span>
                      <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] text-rose-900 dark:bg-rose-900/30 dark:text-rose-200">-{dels}</span>
                      <button onClick={() => router.push(`/action-required/${s.id}`)} className="rounded border px-2 py-1 text-xs">View</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">Authority</label>
          <select value={authority} onChange={(e) => setAuthority(e.target.value)} className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950">
            {AUTHORITIES.map((a) => (
              <option key={a || "all"} value={a}>{a || "All"}</option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">Search</label>
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Query in title/summary" className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950" />
            <button onClick={load} className="rounded bg-primary px-3 py-2 text-sm text-primary-foreground">Search</button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg border bg-zinc-100 dark:bg-zinc-900" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-md border p-4 text-sm text-zinc-600 dark:text-zinc-400">No updates found.</div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {filtered.map((u) => {
            const status = byUpdate[u.id];
            const hasPending = !!status?.pending;
            const hasApplied = !!status?.applied;
            return (
            <article key={u.id} className="rounded-lg border p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs text-zinc-500">{u.authority} • {new Date(u.date).toLocaleDateString()}</div>
                  <h2 className="mt-1 text-sm font-semibold text-zinc-900 dark:text-zinc-50">{u.title}</h2>
                </div>
                <div className="flex items-center gap-2">
                  {hasPending ? (
                    <button onClick={() => router.push(`/action-required/${status!.pending!.id}`)} className="rounded bg-amber-600 px-2 py-1 text-xs text-white">Review Proposal</button>
                  ) : hasApplied ? (
                    <button onClick={() => router.push(`/action-required/${status!.applied!.id}`)} className="rounded bg-emerald-600 px-2 py-1 text-xs text-white">View Applied</button>
                  ) : (
                    <button
                      onClick={async () => {
                        const res = await fetch(`/api/rules/suggestions/from-update/${u.id}`, { method: "POST" });
                        if (res.ok) {
                          const s = await res.json();
                          router.push(`/action-required/${s.id}`);
                        }
                      }}
                      className="rounded bg-primary px-2 py-1 text-xs text-primary-foreground"
                    >
                      Propose Rule Change
                    </button>
                  )}
                  <a href={u.url} target="_blank" rel="noreferrer" className="rounded border px-2 py-1 text-xs">Source</a>
                </div>
              </div>
              <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-300">{u.summary}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {u.tags.map((t) => (
                  <span key={t} className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] dark:bg-zinc-800">{t}</span>
                ))}
                {hasPending && <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">Proposed</span>}
                {hasApplied && <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200">Applied</span>}
              </div>
            </article>
          );})}
        </div>
      )}
    </div>
  );
}
