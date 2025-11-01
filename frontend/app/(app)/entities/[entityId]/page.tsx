"use client";

import { useEffect, useState } from "react";
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
};

export default function EntityBackgroundPage() {
  const { entityId } = useParams<{ entityId: string }>();
  const router = useRouter();
  const [person, setPerson] = useState<Person | null>(null);
  const [bg, setBg] = useState<Background | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      } catch (e: any) {
        setError(e.message || "Error");
      } finally {
        setLoading(false);
      }
    })();
  }, [entityId]);

  if (loading) return <div className="h-24 animate-pulse rounded bg-zinc-100 dark:bg-zinc-900" />;
  if (error || !person || !bg) return <div className="text-red-600">{error || "Not found"}</div>;

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
