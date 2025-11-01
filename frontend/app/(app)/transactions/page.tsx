"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type Person = { id: string; name: string };
type Tx = {
  id: string;
  entityId: string;
  amount: number;
  currency: string;
  counterparty: string;
  ts: string;
  features: { velocity: number; geoRisk: number; amountZ: number };
};
type Eval = { decision: "approve" | "hold" | "escalate"; score: number };

export default function TransactionsPage() {
  const router = useRouter();
  const [entities, setEntities] = useState<Person[]>([]);
  const [entityId, setEntityId] = useState<string>("");
  const [txs, setTxs] = useState<Tx[]>([]);
  const [evalMap, setEvalMap] = useState<Record<string, Eval>>({});
  const [loading, setLoading] = useState(false);
  const [decisionFilter, setDecisionFilter] = useState<string>("");
  const [minAmt, setMinAmt] = useState<string>("");
  const [maxAmt, setMaxAmt] = useState<string>("");

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    (async () => {
      const res = await fetch("/api/entities");
      if (res.ok) {
        const data = (await res.json()) as { items: Person[] };
        setEntities(data.items);
        if (data.items[0]) setEntityId(data.items[0].id);
      }
    })();
  }, []);

  async function load() {
    if (!entityId) return;
    try {
      setLoading(true);
      const res = await fetch(`/api/entities/${entityId}/tx`);
      if (!res.ok) throw new Error("Failed to load transactions");
      const data = (await res.json()) as { items: Tx[] };
      setTxs(data.items);
      // Evaluate all txs
      const entries = await Promise.all(
        data.items.map(async (tx) => {
          try {
            const eRes = await fetch(`/api/tx/evaluate`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(tx),
            });
            if (!eRes.ok) return [tx.id, undefined] as const;
            const e = (await eRes.json()) as Eval & { ruleHits?: any };
            return [tx.id, { decision: e.decision, score: e.score }] as const;
          } catch {
            return [tx.id, undefined] as const;
          }
        })
      );
      setEvalMap(Object.fromEntries(entries.filter(([, v]) => !!v)) as Record<string, Eval>);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Auto-load when entity changes
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityId]);

  const filtered = useMemo(() => {
    return txs.filter((t) => {
      const ev = evalMap[t.id];
      if (decisionFilter && ev && ev.decision !== decisionFilter) return false;
      const min = minAmt ? parseFloat(minAmt) : undefined;
      const max = maxAmt ? parseFloat(maxAmt) : undefined;
      if (min !== undefined && t.amount < min) return false;
      if (max !== undefined && t.amount > max) return false;
      return true;
    });
  }, [txs, evalMap, decisionFilter, minAmt, maxAmt]);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Transactions</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Select an entity to view and evaluate recent transactions.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">Entity</label>
          <select value={entityId} onChange={(e) => setEntityId(e.target.value)} className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950">
            {entities.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">Decision</label>
          <select value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value)} className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950">
            <option value="">All</option>
            <option value="approve">Approve</option>
            <option value="hold">Hold</option>
            <option value="escalate">Escalate</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">Min Amount</label>
          <input value={minAmt} onChange={(e) => setMinAmt(e.target.value)} placeholder="e.g. 1000" className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950" />
        </div>
        <div>
          <label className="mb-1 block text-xs text-zinc-600 dark:text-zinc-400">Max Amount</label>
          <input value={maxAmt} onChange={(e) => setMaxAmt(e.target.value)} placeholder="e.g. 50000" className="w-full rounded border bg-white p-2 text-sm dark:border-zinc-700 dark:bg-zinc-950" />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-zinc-500">
            <tr>
              <th className="py-2 pr-4">Tx ID</th>
              <th className="py-2 pr-4">Amount</th>
              <th className="py-2 pr-4">Counterparty</th>
              <th className="py-2 pr-4">Velocity</th>
              <th className="py-2 pr-4">Geo</th>
              <th className="py-2 pr-4">Score</th>
              <th className="py-2 pr-4">Decision</th>
              <th className="py-2 pr-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="py-6 text-center text-zinc-500">Loading…</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={8} className="py-6 text-center text-zinc-500">No transactions</td></tr>
            ) : (
              filtered.map((t) => {
                const evaln = evalMap[t.id];
                return (
                  <tr key={t.id} className="border-t">
                    <td className="py-2 pr-4 font-mono text-xs">{t.id}</td>
                    <td className="py-2 pr-4">{t.amount.toLocaleString()} {t.currency}</td>
                    <td className="py-2 pr-4">{t.counterparty}</td>
                    <td className="py-2 pr-4">{t.features.velocity.toFixed(2)}</td>
                    <td className="py-2 pr-4">{t.features.geoRisk.toFixed(2)}</td>
                    <td className="py-2 pr-4">{evaln?.score ?? "-"}</td>
                    <td className="py-2 pr-4 capitalize">{evaln?.decision ?? "-"}</td>
                    <td className="py-2 pr-4">
                      <div className="flex gap-2">
                        <Link href={`/entities/${t.entityId}`} className="rounded border px-2 py-1 text-xs">Background</Link>
                        <a href={`/api/tx/${t.id}`} target="_blank" rel="noreferrer" className="rounded border px-2 py-1 text-xs">Raw</a>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
