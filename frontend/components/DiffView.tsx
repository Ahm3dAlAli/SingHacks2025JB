"use client";

import React, { useMemo } from "react";

type Props = {
  diff: string;
  className?: string;
  compact?: boolean;
  showHeader?: boolean;
};

export default function DiffView({ diff, className = "", compact = false, showHeader = true }: Props) {
  const lines = useMemo(() => (diff || "").split(/\r?\n/), [diff]);
  const counts = useMemo(() => {
    let adds = 0, dels = 0;
    for (const l of lines) {
      if (l.startsWith("+++ ") || l.startsWith("--- ")) continue;
      if (l.startsWith("+")) adds++;
      else if (l.startsWith("-")) dels++;
    }
    return { adds, dels };
  }, [lines]);

  return (
    <div className={`overflow-auto rounded border ${compact ? "max-h-48" : ""} ${className}`}>
      {showHeader && (
        <div className="flex items-center justify-between border-b bg-zinc-50 px-2 py-1 text-[11px] dark:bg-zinc-900">
          <div className="flex items-center gap-2">
            <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200">+{counts.adds}</span>
            <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-900 dark:bg-rose-900/30 dark:text-rose-200">-{counts.dels}</span>
          </div>
          <div className="text-zinc-500">Unified diff</div>
        </div>
      )}
      <pre className="m-0 whitespace-pre-wrap break-words p-0 text-xs">
        {lines.map((line, i) => {
          const ch = line[0] || " ";
          let style = "";
          if (line.startsWith("@@")) style = "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300";
          else if (line.startsWith("+++ ") || line.startsWith("--- ")) style = "text-zinc-500";
          else if (ch === "+") style = "bg-emerald-50 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-300 border-l-4 border-emerald-400/60 dark:border-emerald-700";
          else if (ch === "-") style = "bg-rose-50 text-rose-800 dark:bg-rose-900/20 dark:text-rose-300 border-l-4 border-rose-400/60 dark:border-rose-700";
          else style = "text-zinc-800 dark:text-zinc-200";
          return (
            <div key={i} className={`px-2 py-0.5 font-mono ${style}`}>{line || "\u00A0"}</div>
          );
        })}
      </pre>
    </div>
  );
}
