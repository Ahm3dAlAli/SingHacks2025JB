"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type Person = {
  id: string;
  name: string;
  nationality: string;
  dob: string;
  occupation: string;
  employer: string;
  relatives: { relation: string; name: string }[];
};

type Background = {
  entityId: string;
  name: string;
  summary: string;
  totals: { inflow: number; outflow: number; net: number };
  counts: { txns: number; counterparties: number; currencies: number; daysActive: number };
  lastSeen: string | null;
  topCounterparties: { name: string; count: number; amount: number }[];
  currencies: { code: string; amount: number }[];
  channels: { channel: string; count: number }[];
  sanctions: { clear: number; potential: number; hit: number; unknown: number };
  flags: string[];
  adverseMedia?: {
    count: number;
    risk: "low" | "medium" | "high";
    categories: string[];
    items?: { id: string; title: string; summary: string; source: string; url: string; date: string; category: string; severity: "low" | "medium" | "high" }[];
  };
  kyc?: {
    type: string;
    pep: boolean;
    adverseInformation: boolean;
    adverseMedia: boolean;
    reputationalRisk: "low" | "medium" | "high";
    insiderFlag: boolean;
    reasonPurpose: string | null;
    education: string | null;
    familyBackground: string | null;
    currentOccupation: string | null;
    businessActivities: string[];
    sourceOfWealth: string;
    assetBreakdown: { label: string; amount: number }[];
    sourceOfIncome: string | null;
  };
};

export default function EntityBackgroundPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const router = useRouter();
  const [person, setPerson] = useState<Person | null>(null);
  const [bg, setBg] = useState<Background | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docs, setDocs] = useState<{ id: string; title: string; filePath: string; status: string; uploadedAt: string }[]>([]);
  const [showAllAdverse, setShowAllAdverse] = useState(false);
  const [adverseTab, setAdverseTab] = useState<"overview" | "internet">("internet");
  type AdverseItem = { id: string; title: string; summary: string; source: string; url: string; date: string; category: string; severity: "low" | "medium" | "high" };
  const [searching, setSearching] = useState(false);
  const [searchStep, setSearchStep] = useState<string>("");
  const [searchItems, setSearchItems] = useState<(AdverseItem & { subject: string; subjectType: 'client' | 'counterparty' })[]>([]);
  const searchTimers = useRef<number[]>([]);
  const [filterCats, setFilterCats] = useState<string[]>([]);
  const [searchText, setSearchText] = useState<string>("");
  const [includeCounterparties, setIncludeCounterparties] = useState<boolean>(false);
  const [adverseReady, setAdverseReady] = useState<boolean>(false);
  const [overviewItems, setOverviewItems] = useState<AdverseItem[]>([]);

  function summarize(items: AdverseItem[]) {
    const count = items.length;
    const categories = Array.from(new Set(items.map((i) => i.category)));
    let risk: 'low' | 'medium' | 'high' = 'low';
    if (items.some((x) => x.severity === 'high') || count >= 3) risk = 'high';
    else if (items.some((x) => x.severity === 'medium') || count >= 2) risk = 'medium';
    return { count, categories, risk };
  }

  // No tab persistence — default to Internet Search until results are generated

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const [pRes, bRes] = await Promise.all([
          fetch(`/api/entities/${entityId}`),
          fetch(`/api/agent/background/${entityId}`, { method: "POST" }),
        ]);
        if (!pRes.ok) throw new Error("Failed to load person");
        const p = (await pRes.json()) as Person;
        setPerson(p);
        if (!bRes.ok) throw new Error("Failed to load background report");
        const report = (await bRes.json()) as Background;
        setBg(report);
        try {
          const dRes = await fetch(`/api/docs/by-entity/${entityId}`);
          if (dRes.ok) {
            const dj = (await dRes.json()) as { items: any[] };
            setDocs(dj.items.map((x) => ({ id: x.id, title: x.title, filePath: x.filePath, status: x.status, uploadedAt: x.uploadedAt })));
          }
        } catch {}
      } catch (e: any) {
        setError(e.message || "Error");
      } finally {
        setLoading(false);
      }
    })();
  }, [entityId]);

  if (loading) return <div className="h-24 animate-pulse rounded bg-zinc-100 dark:bg-zinc-900" />;
  if (error || !person || !bg) return <div className="text-red-600">{error || "Not found"}</div>;

  function startInternetSearch() {
    if (!bg?.adverseMedia) return;
    // reset state
    setSearchItems([]);
    setSearchStep("Initializing search...");
    setSearching(true);
    // clear previous timers
    searchTimers.current.forEach((t) => clearTimeout(t));
    searchTimers.current = [];
    const items = ((bg?.adverseMedia?.items || []) as AdverseItem[]).map((it) => ({ ...it, subject: bg?.name || '', subjectType: 'client' as const }));
    const steps = [
      { t: 400, msg: "Searching news sources..." },
      { t: 900, msg: "Scanning watchlists and regulatory updates..." },
      { t: 1400, msg: "Summarizing mentions..." },
    ];
    steps.forEach((s) => {
      const id = window.setTimeout(() => setSearchStep(s.msg), s.t);
      searchTimers.current.push(id);
    });
    // Stream items one-by-one
    let delay = 1800;
    // Optionally include counterparties
    let pool = items as (AdverseItem & { subject: string; subjectType: 'client' | 'counterparty' })[];
    async function fetchCounterpartyMentions() {
      if (!bg) return; // Exit early if bg is null
      try {
        const cps = (bg?.topCounterparties || []).slice(0, 5).map((c) => c.name).filter(Boolean);
        const results = await Promise.all(
          cps.map(async (n) => {
            const res = await fetch(`/api/agent/adverse-media/by-name?name=${encodeURIComponent(n)}`);
            if (!res.ok) return null;
            const data = (await res.json()) as { name: string; items?: AdverseItem[] };
            const items = (data.items || []).map((it) => ({ ...it, subject: data.name, subjectType: 'counterparty' as const }));
            return items;
          })
        );
        const extra = results.flat().filter(Boolean) as (AdverseItem & { subject: string; subjectType: 'client' | 'counterparty' })[];
        pool = [...pool, ...extra];
      } catch {}
    }

    if (includeCounterparties) {
      setSearchStep("Gathering counterparties...");
      // Fetch counterparties then continue streaming
      fetchCounterpartyMentions().then(stream);
    } else {
      stream();
    }

    function stream() {
      // Basic ordering: by date desc
      pool.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      if (pool.length === 0) {
        const id = window.setTimeout(() => {
          setSearchStep("No mentions found.");
          setSearching(false);
        }, delay);
        searchTimers.current.push(id);
      } else {
        // Save overview data (client-only and counterparty too) for Overview tab
        const clientOnly = pool.filter((p) => p.subjectType === 'client');
        setOverviewItems(clientOnly);
        pool.forEach((it, idx) => {
          const id = window.setTimeout(() => {
            setSearchItems((prev) => [...prev, it]);
            if (idx === pool.length - 1) {
              setSearchStep("Search complete.");
              setSearching(false);
              setAdverseReady(true);
            }
          }, delay);
          searchTimers.current.push(id);
          delay += 650;
        });
      }
    }
  }
  function resetInternetSearch() {
    searchTimers.current.forEach((t) => clearTimeout(t));
    searchTimers.current = [];
    setSearching(false);
    setSearchStep("");
    setSearchItems([]);
  }

  return (
    <div className="space-y-6">
      <header className="rounded-lg border p-4">
        <h1 className="text-xl font-semibold">{person.name}</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{person.nationality || "—"}</p>
        <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
          <Metric label="Inflow" value={bg.totals.inflow} />
          <Metric label="Outflow" value={bg.totals.outflow} />
          <Metric label="Net" value={bg.totals.net} />
          <div className="rounded border p-2 text-center">
            <div className="text-[10px] uppercase text-zinc-500">Transactions</div>
            <div className="text-sm font-semibold">{bg.counts.txns}</div>
          </div>
        </div>
        {bg.flags.length > 0 ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {bg.flags.map((f, i) => (
              <Badge key={i}>{f}</Badge>
            ))}
          </div>
        ) : null}
      </header>

      <section className="rounded-lg border p-4">
        <h2 className="text-sm font-semibold">Summary</h2>
        <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-300">{bg.summary}</p>
        <p className="mt-1 text-xs text-zinc-500">Last seen: {bg.lastSeen ? new Date(bg.lastSeen).toLocaleString("en-SG", { timeZone: "Asia/Singapore" }) : "—"}</p>
      </section>

      {/* Adverse Media section with tabs and View All modal */}
      <section id="adverse-media" className="rounded-lg border p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Adverse Media</h2>
          <div className="flex items-center gap-1 text-xs">
            <button
              className={`rounded px-2 py-1 ${adverseTab === 'overview' ? 'border bg-white dark:bg-zinc-900' : 'opacity-70'}`}
              onClick={() => setAdverseTab('overview')}
            >Overview</button>
            <button
              className={`rounded px-2 py-1 ${adverseTab === 'internet' ? 'border bg-white dark:bg-zinc-900' : 'opacity-70'}`}
              onClick={() => { setAdverseTab('internet'); resetInternetSearch(); }}
            >Internet Search</button>
          </div>
        </div>

        {adverseTab === 'overview' ? (
          adverseReady ? (
            (() => {
              const s = summarize(overviewItems);
              return (
                <div className="mt-2 space-y-2 text-sm">
                  <div className="flex items-center justify-between text-xs text-zinc-600 dark:text-zinc-400">
                    <div>
                      {s.count} mention{s.count !== 1 ? 's' : ''} across {s.categories.length} topic{s.categories.length !== 1 ? 's' : ''} • risk: {s.risk}
                    </div>
                    {overviewItems.length > 5 ? (
                      <button onClick={() => setShowAllAdverse(true)} className="rounded border px-2 py-1">View all</button>
                    ) : null}
                  </div>
                  <ul className="space-y-2">
                    {overviewItems.slice(0, 5).map((i, idx) => (
                      <li key={`${i.title}-${idx}`} className="rounded border p-2">
                        <div className="flex items-center justify-between gap-2">
                          <div className="font-medium">{i.title}</div>
                          <span className={`rounded px-2 py-0.5 text-xs ${i.severity === 'high' ? 'bg-red-100 text-red-700' : i.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{i.severity}</span>
                        </div>
                        <div className="text-xs text-zinc-600 dark:text-zinc-400">{i.source} • {new Date(i.date).toLocaleDateString('en-SG')} • {i.category}</div>
                        <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">{i.summary}</p>
                        <a href={i.url} className="mt-1 inline-block text-xs text-primary underline" target="_blank">Open source</a>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })()
          ) : (
            <div className="mt-2 flex items-center justify-end text-xs text-zinc-600 dark:text-zinc-400">
              <button onClick={() => { setAdverseTab('internet'); resetInternetSearch(); }} className="rounded border px-2 py-1">Start Internet Search</button>
            </div>
          )
        ) : (
          <div className="mt-2 text-sm">
            {searchItems.length === 0 && !searching ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-xs text-zinc-600 dark:text-zinc-400">
                  <p>Simulated internet search across news sources and watchlists.</p>
                  <label className="inline-flex items-center gap-1">
                    <input type="checkbox" checked={includeCounterparties} onChange={(e) => setIncludeCounterparties(e.target.checked)} />
                    <span>Include counterparties (top {(bg.topCounterparties || []).slice(0,5).length})</span>
                  </label>
                </div>
                <button onClick={startInternetSearch} className="rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground">Start search</button>
              </div>
            ) : null}
            {(searching || searchItems.length > 0) ? (
              <div>
                <div className="mb-2 flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400">
                  <div className={`h-3 w-3 rounded-full border-2 border-zinc-300 border-t-primary ${searching ? 'animate-spin' : ''}`} />
                  <span>{searchStep || (searching ? 'Searching...' : 'Search complete.')}</span>
                  <div className="ml-auto flex items-center gap-2">
                    <button onClick={resetInternetSearch} className="rounded border px-2 py-0.5">Reset</button>
                    {!searching && <button onClick={startInternetSearch} className="rounded border px-2 py-0.5">Run again</button>}
                  </div>
                </div>
                <ul className="space-y-2">
                  {searchItems.map((i, idx) => (
                    <li key={i.id} className="rounded border p-2 opacity-0 animate-fade-in-up" style={{ animationDelay: `${idx * 60}ms` }}>
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium">{i.title}</div>
                        <span className={`rounded px-2 py-0.5 text-xs ${i.severity === 'high' ? 'bg-red-100 text-red-700' : i.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{i.severity}</span>
                      </div>
                      <div className="text-xs text-zinc-600 dark:text-zinc-400">{i.source} • {new Date(i.date).toLocaleDateString('en-SG')} • {i.category} • Subject: {i.subjectType === 'counterparty' ? `Counterparty — ${i.subject}` : 'Client'}</div>
                      <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">{i.summary}</p>
                      <a href={i.url} className="mt-1 inline-block text-xs text-primary underline" target="_blank">Open source</a>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        )}
      </section>

      

      <section className="rounded-lg border p-4">
        <h2 className="text-sm font-semibold">KYC Profile</h2>
        <div className="mt-2 grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
          <KycRow label="Type" value={bg.kyc?.type || "—"} />
          <KycRow label="PEP" value={bg.kyc?.pep ? "Yes" : "No"} />
          <KycRow
            label="Adverse Signals"
            value={(() => {
              if (!adverseReady) {
                return (
                  <span>
                    Not yet searched
                    <button
                      onClick={() => {
                        setAdverseTab('internet');
                        const el = document.getElementById('adverse-media');
                        el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }}
                      className="ml-2 inline-flex rounded border px-1.5 py-0.5 text-[10px]"
                    >
                      Run Internet Search
                    </button>
                  </span>
                );
              }
              const s = summarize(overviewItems);
              return (
                <span>
                  {s.count} mention{s.count !== 1 ? 's' : ''} • risk: {s.risk}
                  <button
                    onClick={() => {
                      setAdverseTab('overview');
                      const el = document.getElementById('adverse-media');
                      el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }}
                    className="ml-2 inline-flex rounded border px-1.5 py-0.5 text-[10px]"
                  >
                    View details
                  </button>
                </span>
              );
            })()}
          />
          <KycRow label="Reputational Risk" value={bg.kyc?.reputationalRisk || "—"} />
          <KycRow label="Insider Flag" value={bg.kyc?.insiderFlag ? "Yes" : "No"} />
          <KycRow label="Reason & Purpose" value={bg.kyc?.reasonPurpose || "—"} />
          <KycRow label="Current Occupation" value={bg.kyc?.currentOccupation || person.occupation || "—"} />
          <KycRow label="Business Activities" value={(bg.kyc?.businessActivities || []).join(", ") || "—"} />
          <KycRow label="Source of Wealth" value={bg.kyc?.sourceOfWealth || "—"} />
          <KycRow label="Source of Income" value={bg.kyc?.sourceOfIncome || "—"} />
          <div>
            <div className="text-xs text-zinc-600 dark:text-zinc-400">Asset Breakdown</div>
            <ul className="mt-1 text-sm">
              {(bg.kyc?.assetBreakdown || []).map((a, i) => (
                <li key={i} className="flex justify-between"><span>{a.label}</span><span className="text-zinc-600">{a.amount.toLocaleString()}</span></li>
              ))}
              {(bg.kyc?.assetBreakdown || []).length === 0 ? <li className="text-zinc-500">—</li> : null}
            </ul>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Top Counterparties</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {bg.topCounterparties.length === 0 ? <li className="text-zinc-500">None</li> : bg.topCounterparties.map((c) => (
              <li key={c.name} className="flex justify-between">
                <span className="truncate pr-2">{c.name}</span>
                <span className="text-zinc-600">{c.count} • {c.amount.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Currencies</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {bg.currencies.length === 0 ? <li className="text-zinc-500">None</li> : bg.currencies.map((c) => (
              <li key={c.code} className="flex justify-between">
                <span>{c.code}</span>
                <span className="text-zinc-600">{c.amount.toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Channels</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {bg.channels.length === 0 ? <li className="text-zinc-500">None</li> : bg.channels.map((c) => (
              <li key={c.channel} className="flex justify-between">
                <span className="truncate pr-2">{c.channel}</span>
                <span className="text-zinc-600">{c.count}</span>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Sanctions</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
            <Badge variant="outline">CLEAR: {bg.sanctions.clear}</Badge>
            <Badge variant="outline">POTENTIAL_MATCH: {bg.sanctions.potential}</Badge>
            <Badge variant="outline">HIT: {bg.sanctions.hit}</Badge>
            <Badge variant="outline">UNKNOWN: {bg.sanctions.unknown}</Badge>
          </div>
        </section>
      </div>

      <section className="rounded-lg border p-4">
        <h2 className="text-sm font-semibold">Documents</h2>
        {docs.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">No documents linked to this client.</p>
        ) : (
          <ul className="mt-2 space-y-2 text-sm">
            {docs.map((d) => (
              <li key={d.id} className="flex items-center justify-between rounded border p-2">
                <div>
                  <div className="font-medium">{d.title}</div>
                  <div className="text-xs text-zinc-500">Uploaded {new Date(d.uploadedAt).toLocaleString("en-SG", { timeZone: "Asia/Singapore" })}</div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={d.status} />
                  <a href={d.filePath} target="_blank" className="rounded border px-2 py-1 text-xs">Open</a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Removed: Adverse Media here (moved above KYC Profile) */}

      {showAllAdverse && bg.adverseMedia ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowAllAdverse(false)} />
          <div className="relative z-10 max-h-[80vh] w-[90vw] max-w-4xl overflow-auto rounded-lg border bg-white p-4 dark:bg-zinc-950">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold">Adverse Media — {bg.name}</div>
              <div className="flex items-center gap-2 text-xs">
                <input
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  placeholder="Search title/source/category"
                  className="rounded border bg-white px-2 py-1 dark:border-zinc-700 dark:bg-zinc-950"
                />
                <button onClick={() => { setFilterCats([]); setSearchText(""); }} className="rounded border px-2 py-1">Clear</button>
                <button onClick={() => setShowAllAdverse(false)} className="rounded border px-2 py-1">Close</button>
              </div>
            </div>
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
              {(bg.adverseMedia.categories || []).map((c) => {
                const active = filterCats.includes(c);
                return (
                  <button
                    key={c}
                    onClick={() => setFilterCats((prev) => active ? prev.filter((x) => x !== c) : [...prev, c])}
                    className={`rounded px-2 py-0.5 ${active ? 'bg-primary text-primary-foreground' : 'border'}`}
                    title={active ? 'Click to remove filter' : 'Click to filter'}
                  >{c}</button>
                );
              })}
              {bg.adverseMedia.categories && bg.adverseMedia.categories.length > 0 ? (
                <button onClick={() => setFilterCats([])} className="rounded border px-2 py-0.5">All</button>
              ) : null}
            </div>
            <ul className="mt-1 space-y-2 text-sm">
              {((bg.adverseMedia.items || []) as any[])
                .filter((i) => filterCats.length === 0 || filterCats.includes(i.category))
                .filter((i) => {
                  const t = searchText.trim().toLowerCase();
                  if (!t) return true;
                  return (
                    i.title.toLowerCase().includes(t) ||
                    i.source.toLowerCase().includes(t) ||
                    i.category.toLowerCase().includes(t)
                  );
                })
                .map((i, idx) => (
                <li key={i.id} className="rounded border p-2 opacity-0 animate-fade-in-up" style={{ animationDelay: `${idx * 40}ms` }}>
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium">{i.title}</div>
                    <span className={`rounded px-2 py-0.5 text-xs ${i.severity === 'high' ? 'bg-red-100 text-red-700' : i.severity === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{i.severity}</span>
                  </div>
                  <div className="text-xs text-zinc-600 dark:text-zinc-400">{i.source} • {new Date(i.date).toLocaleDateString('en-SG')} • {i.category}</div>
                  <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">{i.summary}</p>
                  <a href={i.url} className="mt-1 inline-block text-xs text-primary underline" target="_blank">Open source</a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Badge({ children, variant = "solid" }: { children: React.ReactNode; variant?: "solid" | "outline" }) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-xs";
  if (variant === "outline") return <span className={`${base} border`}>{children}</span>;
  return <span className={`${base} bg-primary/10 text-primary`}>{children}</span>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border p-2 text-center">
      <div className="text-[10px] uppercase text-zinc-500">{label}</div>
      <div className="text-sm font-semibold">{value.toLocaleString()}</div>
    </div>
  );
}

function KycRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between rounded border p-2">
      <div className="text-xs text-zinc-500">{label}</div>
      <div className="text-sm">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const m: Record<string, { text: string; cls: string }> = {
    pending_compliance: { text: "Pending — Compliance", cls: "bg-amber-100 text-amber-700" },
    pending_legal: { text: "Pending — Legal", cls: "bg-orange-100 text-orange-700" },
    approved: { text: "Approved", cls: "bg-emerald-100 text-emerald-700" },
    rejected: { text: "Rejected", cls: "bg-red-100 text-red-700" },
  };
  const v = m[status] || { text: status, cls: "bg-zinc-100 text-zinc-700" };
  return <span className={`rounded px-2 py-0.5 text-[10px] ${v.cls}`}>{v.text}</span>;
}
