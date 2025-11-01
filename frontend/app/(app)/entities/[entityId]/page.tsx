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
  summary: string;
  estNetWorthUSD: number;
  reasoning: { assets: string[]; workLife: string[]; family: string[]; social: string[] };
  sources: { label: string; url: string }[];
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
        <h1 className="text-xl font-semibold">Background Check — {person.name}</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{person.occupation} • {person.employer} • {person.nationality} • DOB {person.dob}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-sm">
          <Badge>Estimated Net Worth: ${bg.estNetWorthUSD.toLocaleString()}</Badge>
          <Badge variant="outline">Relatives: {person.relatives.length}</Badge>
        </div>
      </header>

      <section className="rounded-lg border p-4">
        <h2 className="text-sm font-semibold">Summary</h2>
        <p className="mt-2 text-sm text-zinc-700 dark:text-zinc-300">{bg.summary}</p>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Assets</h3>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {bg.reasoning.assets.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Work Life</h3>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {bg.reasoning.workLife.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Family & Relatives</h3>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {bg.reasoning.family.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg border p-4">
          <h3 className="text-sm font-semibold">Social / Other Signals</h3>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {bg.reasoning.social.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-lg border p-4">
        <h3 className="text-sm font-semibold">Sources</h3>
        <ul className="mt-2 space-y-1 text-sm">
          {bg.sources.map((s, i) => (
            <li key={i}>
              <a className="underline" href={s.url} target="_blank" rel="noreferrer">{s.label}</a>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-zinc-500">Disclaimer: This background report is generated from public, non-KYC sources for demo purposes only.</p>
      </section>
    </div>
  );
}

function Badge({ children, variant = "solid" }: { children: React.ReactNode; variant?: "solid" | "outline" }) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-xs";
  if (variant === "outline") return <span className={`${base} border`}>{children}</span>;
  return <span className={`${base} bg-primary/10 text-primary`}>{children}</span>;
}

