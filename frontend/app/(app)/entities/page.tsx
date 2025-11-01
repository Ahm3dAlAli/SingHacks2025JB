"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type Person = {
  id: string;
  name: string;
  nationality: string;
  dob: string;
  occupation: string;
  employer: string;
};

export default function EntitiesPage() {
  const router = useRouter();
  const [items, setItems] = useState<Person[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [bgMap, setBgMap] = useState<Record<string, {
    type?: string;
    pep?: boolean;
    reputationalRisk?: "low" | "medium" | "high";
    lastSeen?: string | null;
    totals?: { inflow: number; outflow: number; net: number };
    sanctions?: { clear: number; potential: number; hit: number; unknown: number };
    topCounterparties?: { name: string; count: number; amount: number }[];
    txns?: number;
    reasons?: string[];
    adverse?: { count: number; risk: "low" | "medium" | "high"; categories: string[] };
  }>>({});
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const res = await fetch("/api/entities");
      const data = (await res.json()) as { items: Person[] };
      setItems(data.items);
      setLoading(false);
    })();
  }, []);

  const filtered = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (!t) return items;
    return items.filter((p) => p.name.toLowerCase().includes(t) || p.employer.toLowerCase().includes(t));
  }, [items, q]);

  // Reset page when search changes
  useEffect(() => { setPage(1); }, [q]);

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, page, pageSize]);

  // Fetch background summaries only for visible page, and cache
  useEffect(() => {
    (async () => {
      const ids = paged.map((p) => p.id).filter((id) => !bgMap[id]);
      if (ids.length === 0) return;
      try {
        const entries = await Promise.all(
          ids.map(async (id) => {
            try {
              const bRes = await fetch(`/api/agent/background/${id}`, { method: "POST" });
              if (!bRes.ok) return [id, null] as const;
              const b = await bRes.json();
              const k = b.kyc || {};
              const info = {
                type: k.type as string | undefined,
                pep: !!k.pep,
                reputationalRisk: k.reputationalRisk as any,
                lastSeen: (b.lastSeen as string) || null,
                totals: b.totals as { inflow: number; outflow: number; net: number },
                sanctions: b.sanctions as { clear: number; potential: number; hit: number; unknown: number },
                topCounterparties: (b.topCounterparties as any[])?.slice(0, 2) || [],
                txns: (b.counts?.txns as number) || 0,
                reasons: (b.reputationalReasons as string[]) || [],
                adverse: b.adverseMedia ? { count: b.adverseMedia.count as number, risk: b.adverseMedia.risk as any, categories: (b.adverseMedia.categories as string[]) || [] } : undefined,
              };
              return [id, info] as const;
            } catch {
              return [id, null] as const;
            }
          })
        );
        setBgMap((prev) => ({ ...prev, ...Object.fromEntries(entries.filter((e) => e[1] !== null) as any) }));
      } catch {}
    })();
  }, [paged, page, pageSize]);

  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Clients</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Search clients and open KYC background summaries.</p>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name or employer"
          className="w-64 rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950"
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl border bg-zinc-100 dark:bg-zinc-900" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {paged.map((p) => {
            const info = bgMap[p.id] || {};
            return (
              <div
                key={p.id}
                className={`rounded-xl border p-4 shadow-sm transition hover:shadow-md ${riskAccent(
                  info.reputationalRisk
                ).bg} ${riskAccent(info.reputationalRisk).border}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-sm font-semibold">{p.name}</div>
                    <div className="text-xs text-zinc-600 dark:text-zinc-400">{p.occupation} • {p.employer}</div>
                    <div className="text-xs text-zinc-500">{p.nationality} • DOB {p.dob}</div>
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                      {info.type ? (
                        <span className="rounded bg-white/60 px-1.5 py-0.5 text-[10px] dark:bg-zinc-900/40">
                          Client type: {info.type}
                        </span>
                      ) : null}
                      {info.pep ? (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] text-red-700">PEP (Politically Exposed Person)</span>
                      ) : null}
                      {info.reputationalRisk ? (
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] ${
                            info.reputationalRisk === 'high'
                              ? 'bg-red-600 text-white'
                              : info.reputationalRisk === 'medium'
                              ? 'bg-amber-500 text-white'
                              : 'bg-emerald-600 text-white'
                          }`}
                        >
                          {String(info.reputationalRisk).toUpperCase()}
                        </span>
                      ) : null}
                      {info.adverse && info.adverse.count > 0 ? (
                        <span className={`rounded-full px-2 py-0.5 text-[10px] ${info.adverse.risk === 'high' ? 'bg-red-100 text-red-700' : info.adverse.risk === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                          Adverse media: {info.adverse.count} mention{info.adverse.count > 1 ? 's' : ''} across {info.adverse.categories.length} topic{info.adverse.categories.length !== 1 ? 's' : ''}
                        </span>
                      ) : null}
                      {info.sanctions && (info.sanctions.hit > 0 || info.sanctions.potential > 0) ? (
                        <span className={`rounded-full px-2 py-0.5 text-[10px] ${info.sanctions.hit > 0 ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}`}>
                          Sanctions screening: {info.sanctions.hit > 0 ? 'Hit present' : 'Potential match'}
                        </span>
                      ) : null}
                      {info.lastSeen ? (
                        <span className="rounded bg-white/60 px-1.5 py-0.5 text-[10px] dark:bg-zinc-900/40">
                          Last transaction: {new Date(info.lastSeen).toLocaleDateString('en-SG')}
                        </span>
                      ) : null}
                </div>
              </div>
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <MetricMini label="Txns" value={info.txns || 0} />
                    <MetricMini label="Inflow" value={info.totals?.inflow || 0} />
                    <MetricMini label="Outflow" value={info.totals?.outflow || 0} />
                    <MetricMini label="Net" value={info.totals?.net || 0} />
                  </div>
                </div>
                {/* Explanatory reasons for risk level */}
                <div className="mt-2 text-xs text-zinc-700 dark:text-zinc-300">
                  <span className="font-medium">Why this risk level:</span>{' '}
                  {info.reasons && info.reasons.length > 0 ? info.reasons.join('; ') : 'No notable risk indicators identified.'}
                </div>
                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <div className="text-[11px] text-zinc-500">Sanctions</div>
                    <div className="mt-1 flex flex-wrap gap-2 text-[11px]">
                      {info.sanctions ? (
                        <>
                          <span className="rounded bg-red-100 px-2 py-0.5 text-red-700">HIT: {info.sanctions.hit}</span>
                          <span className="rounded bg-amber-100 px-2 py-0.5 text-amber-700">PM: {info.sanctions.potential}</span>
                          <span className="rounded bg-emerald-100 px-2 py-0.5 text-emerald-700">CLEAR: {info.sanctions.clear}</span>
                        </>
                      ) : (
                        <span className="text-zinc-500">—</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-zinc-500">Top Counterparties</div>
                    <ul className="mt-1 space-y-1 text-xs">
                      {(info.topCounterparties || []).length === 0 ? (
                        <li className="text-zinc-500">—</li>
                      ) : (
                        (info.topCounterparties || []).map((c) => (
                          <li key={c.name} className="flex justify-between"><span className="truncate pr-2">{c.name}</span><span className="text-zinc-600">{c.amount.toLocaleString()}</span></li>
                        ))
                      )}
                    </ul>
                  </div>
                </div>
                <div className="mt-3">
                  <Link href={`/kyc/${p.id}`} className="rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground">Open KYC</Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {!loading && filtered.length > 0 ? (
        <div className="mt-4 flex items-center justify-between text-xs text-zinc-600 dark:text-zinc-400">
          <div>
            {(() => {
              const start = (page - 1) * pageSize + 1;
              const end = Math.min(page * pageSize, filtered.length);
              const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
              return <span>Showing {start}-{end} of {filtered.length} • Page {page} / {pages}</span>;
            })()}
          </div>
          <div className="flex items-center gap-2">
            <span>Page size</span>
            <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))} className="rounded border bg-white p-1 dark:border-zinc-700 dark:bg-zinc-950">
              {[10, 20, 30, 40].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="rounded border px-2 py-1 disabled:opacity-60">Prev</button>
            <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= filtered.length} className="rounded border px-2 py-1 disabled:opacity-60">Next</button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MetricMini({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border bg-white/50 p-2 dark:bg-zinc-900/40">
      <div className="text-[10px] uppercase text-zinc-500">{label}</div>
      <div className="text-sm font-semibold">{value.toLocaleString()}</div>
    </div>
  );
}

function riskAccent(r?: "low" | "medium" | "high") {
  switch (r) {
    case "high":
      return { bg: "bg-red-50/60 dark:bg-red-950/30", border: "border-l-4 border-red-600" };
    case "medium":
      return { bg: "bg-amber-50/60 dark:bg-amber-950/30", border: "border-l-4 border-amber-500" };
    case "low":
      return { bg: "bg-emerald-50/60 dark:bg-emerald-950/30", border: "border-l-4 border-emerald-600" };
    default:
      return { bg: "bg-white", border: "" } as const;
  }
}
