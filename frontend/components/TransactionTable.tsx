"use client";

import { Transaction, ScreeningStatus } from "@/types/transaction";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type SortDir = "asc" | "desc";

export type ColumnKey =
  | "booking_datetime"
  | "transaction_id"
  | "display_direction"
  | "display_counterparty"
  | "amount"
  | "currency"
  | "product_type"
  | "channel"
  | "sanctions_screening"
  | "fx_indicator"
  | "swift_f71_charges";

export function TransactionTable({
  rows,
  onRowClick,
  sortBy,
  sortDir,
  onSortChange,
  extraColumns = [],
}: {
  rows: Transaction[];
  onRowClick: (tx: Transaction) => void;
  sortBy: ColumnKey;
  sortDir: SortDir;
  onSortChange: (key: ColumnKey) => void;
  extraColumns?: { key: string; label: string; widthClass?: string; render: (tx: Transaction) => React.ReactNode }[];
}) {
  function sortIndicator(key: ColumnKey) {
    if (sortBy !== key) return null;
    return <span className="ml-1 text-[10px]">{sortDir === "asc" ? "▲" : "▼"}</span>;
  }
  function header(key: ColumnKey, label: string, widthClass?: string) {
    return (
      <TableHead key={key} className={`sticky top-0 bg-white dark:bg-zinc-950 ${widthClass ?? ""}`}>
        <button className="flex items-center" onClick={() => onSortChange(key)} aria-label={`Sort by ${label}`}>
          {label}
          {sortIndicator(key)}
        </button>
      </TableHead>
    );
  }

  return (
    <div className="rounded border">
      <Table className="min-w-[1000px]">
        <TableHeader>
          <TableRow>
            {header("booking_datetime", "Booking Date/Time", "w-[160px]")}
            {header("transaction_id", "Transaction ID", "w-[160px]")}
            {header("display_direction", "Direction", "w-[72px]")}
            {header("display_counterparty", "Counterparty")}
            {header("amount", "Amount", "w-[120px]")}
            {header("currency", "Currency", "w-[72px]")}
            {header("product_type", "Product Type", "w-[140px]")}
            {header("channel", "Channel", "w-[120px]")}
            {header("sanctions_screening", "Sanctions", "w-[100px]")}
            {header("fx_indicator", "FX", "w-[60px]")}
            {header("swift_f71_charges", "Charges (F71)", "w-[120px]")}
            <TableHead className="w-[140px]">Compliance</TableHead>
            {extraColumns.map((c) => (
              <TableHead key={c.key} className={c.widthClass}>{c.label}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((tx) => (
            <TableRow key={tx.transaction_id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50 cursor-pointer" onClick={() => onRowClick(tx)}>
              <TableCell className="text-zinc-700 dark:text-zinc-300 w-[160px]">{fmtDT(tx.booking_datetime)}</TableCell>
              <TableCell className="font-mono w-[160px]">
                <div className="flex items-center gap-2 truncate" title={tx.transaction_id}>
                  <span className="truncate">{tx.transaction_id}</span>
                </div>
              </TableCell>
              <TableCell className="w-[72px]">{dirPill(tx.display_direction)}</TableCell>
              <TableCell className="truncate" title={tx.display_counterparty}>{tx.display_counterparty}</TableCell>
              <TableCell className="text-right w-[120px]">{fmtAmt(tx.amount)}</TableCell>
              <TableCell className="w-[72px]"><span className="rounded bg-zinc-100 px-2 py-0.5 text-[10px] dark:bg-zinc-800">{tx.currency}</span></TableCell>
              <TableCell className="w-[140px]">{tx.product_type}</TableCell>
              <TableCell className="w-[120px]">{tx.channel}</TableCell>
              <TableCell className="w-[100px]">{sanctionsBadge(tx.sanctions_screening)}</TableCell>
              <TableCell className="w-[60px]">{tx.fx_indicator ? <span className="rounded bg-blue-100 px-2 py-0.5 text-[10px] text-blue-700">FX</span> : <span className="text-[10px] text-zinc-500">—</span>}</TableCell>
              <TableCell className="w-[120px]">{(tx.swift_f71_charges ?? "").toUpperCase()}</TableCell>
              <TableCell className="w-[140px]">
                {tx.customer_is_pep || tx.pep_flag ? (
                  <span className="mr-1 rounded bg-red-100 px-2 py-0.5 text-[10px] text-red-700">PEP</span>
                ) : null}
                {tx.travel_rule_complete !== undefined ? (
                  <span className={`rounded px-2 py-0.5 text-[10px] ${tx.travel_rule_complete ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    TR{tx.travel_rule_complete ? "" : " (incomplete)"}
                  </span>
                ) : null}
              </TableCell>
              {extraColumns.map((c) => (
                <TableCell key={c.key} className={c.widthClass}>{c.render(tx)}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function fmtDT(iso: string) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const f = new Intl.DateTimeFormat("en-SG", {
    timeZone: "Asia/Singapore",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return f.format(d);
}
function fmtAmt(n: number) {
  return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}
function dirPill(dir?: string) {
  const color = dir === "IN" ? "bg-emerald-600" : "bg-blue-600";
  return dir ? <span className={`rounded px-2 py-0.5 text-[10px] text-white ${color}`}>{dir}</span> : null;
}
function sanctionsBadge(s?: ScreeningStatus | string) {
  const v = (s ?? "").toString().toUpperCase();
  let cls = "bg-zinc-200 text-zinc-800";
  if (v === "CLEAR") cls = "bg-emerald-100 text-emerald-700";
  else if (v === "POTENTIAL_MATCH") cls = "bg-amber-100 text-amber-700";
  else if (v === "HIT") cls = "bg-red-100 text-red-700";
  return <span className={`rounded px-2 py-0.5 text-[10px] ${cls}`}>{v || "UNKNOWN"}</span>;
}
