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

  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Entities</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Search people and open background reports.</p>
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
            <div key={i} className="h-28 animate-pulse rounded-lg border bg-zinc-100 dark:bg-zinc-900" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <div key={p.id} className="rounded-lg border p-4">
              <div className="text-sm font-semibold">{p.name}</div>
              <div className="text-xs text-zinc-600 dark:text-zinc-400">{p.occupation} • {p.employer}</div>
              <div className="text-xs text-zinc-500">{p.nationality} • DOB {p.dob}</div>
              <div className="mt-3 flex gap-2">
                <Link href={`/entities/${p.id}`} className="rounded bg-primary px-3 py-1.5 text-xs text-primary-foreground">Background Check</Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

