"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";

type Rule = {
  rule_id: string;
  jurisdiction: string;
  regulator: string;
  rule_type: string;
  rule_text: string;
  rule_parameters: Record<string, any>;
  severity: string;
  is_active: boolean;
  effective_date: string;
  created_at: string;
  updated_at: string;
};

type RulesResponse = {
  data: Rule[];
  total: number;
  page: number;
  limit: number;
};

export default function RulesPage() {
  const router = useRouter();
  const [items, setItems] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  useEffect(() => {
    if (!isLoggedIn()) return;
    
    const fetchRules = async () => {
      try {
        setLoading(true);
        const res = await fetch("/api/rules");
        if (!res.ok) throw new Error('Failed to fetch rules');
        const data = await res.json() as RulesResponse;
        setItems(data.data);
      } catch (error) {
        console.error('Error fetching rules:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRules();
  }, [isLoggedIn]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Rules</h1>
      {loading ? (
        <div className="h-24 animate-pulse rounded bg-zinc-100 dark:bg-zinc-900" />
      ) : (
        <ul className="divide-y rounded border">
          {items.map((r) => (
            <li key={r.rule_id} className="flex items-center justify-between p-3 text-sm">
              <div>
                <div className="font-medium">{r.rule_id}</div>
                <div className="text-xs text-zinc-500">
                  {r.regulator} • {r.rule_type} • {r.is_active ? 'Active' : 'Inactive'}
                </div>
                <div className="mt-1 text-sm">{r.rule_text}</div>
              </div>
              <div className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800">
                {r.severity}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

