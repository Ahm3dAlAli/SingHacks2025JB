"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type Rule = { id: string; name: string; status: string; versionId: string; createdAt: string };

export default function RulesPage() {
  const router = useRouter();
  const [items, setItems] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const res = await fetch("/api/rules");
      const data = (await res.json()) as { items: Rule[] };
      setItems(data.items);
      setLoading(false);
    })();
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Rules</h1>
      {loading ? (
        <div className="h-24 animate-pulse rounded bg-zinc-100 dark:bg-zinc-900" />
      ) : (
        <ul className="divide-y rounded border">
          {items.map((r) => (
            <li key={r.id} className="flex items-center justify-between p-3 text-sm">
              <div>
                <div className="font-medium">{r.name}</div>
                <div className="text-xs text-zinc-500">{r.status} • {new Date(r.createdAt).toLocaleString()}</div>
              </div>
              <Link href={`/api/rules/${r.id}`} target="_blank" className="rounded border px-2 py-1 text-xs">View API</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

