"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import { Transaction } from "@/types/transaction";
import { parseTransactionsWithZodFromFile as parseTransactionsFromFile, parseTransactionsWithZodFromText as parseTransactionsFromText, ParseError, ParseWarning } from "@/lib/parseTransactions";
import { TransactionTable } from "@/components/TransactionTable";
import { TransactionDetailsDrawer } from "@/components/TransactionDetailsDrawer";
import { Filters, FiltersBar } from "@/components/Filters/FiltersBar";

type SortKey = "booking_datetime" | "transaction_id" | "display_direction" | "display_counterparty" | "amount" | "currency" | "product_type" | "channel" | "sanctions_screening" | "fx_indicator" | "swift_f71_charges";

export default function TransactionsPage() {
  const router = useRouter();
  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login");
  }, [router]);

  const [allRows, setAllRows] = useState<Transaction[]>([]);
  const [errors, setErrors] = useState<ParseError[]>([]);
  const [warnings, setWarnings] = useState<ParseWarning[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [sortBy, setSortBy] = useState<SortKey>("booking_datetime");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  // Keep the table simple: core columns only; full set in details drawer

  // Try loading default CSV from public if available
  useEffect(() => {
    let mounted = true;
    async function loadDefault() {
      try {
        setLoading(true);
        // Try preferred path first, then fallback
        const urls = [
          "/data/transactions_mock_1000_for_participants.csv",
          "/data/transactions.csv",
        ];
        let loaded = false;
        for (const url of urls) {
          const res = await fetch(url, { cache: "no-store" });
          if (res.ok) {
            const text = await res.text();
        const { rows, errors, warnings } = parseTransactionsFromText(text);
        if (!mounted) return;
        setAllRows(rows);
        setErrors(errors);
        setWarnings(warnings);
            loaded = true;
            break;
          }
        }
        if (!loaded) {
          // no-op if not found
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    loadDefault();
    return () => {
      mounted = false;
    };
  }, []);

  const options = useMemo(() => buildOptions(allRows), [allRows]);

  const filtered = useMemo(() => applyFilters(allRows, filters), [allRows, filters]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => compareBy(a, b, sortBy, sortDir));
    return arr;
  }, [filtered, sortBy, sortDir]);

  function onSortChange(key: SortKey) {
    if (key === sortBy) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortBy(key);
      setSortDir(key === "booking_datetime" ? "desc" : "asc");
    }
  }

  const extraColumns: any[] = [];

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    const { rows, errors, warnings } = await parseTransactionsFromFile(file);
    setAllRows(rows);
    setErrors(errors);
    setWarnings(warnings);
    setLoading(false);
  }

  function exportFiltered() {
    const csv = toCSV(sorted, filters);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transactions_export_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function downloadErrors() {
    const header = "row,message\n";
    const body = errors.map((e) => `${e.row},"${e.message.replace(/"/g, '""')}"`).join("\n");
    const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transaction_errors_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function downloadWarnings() {
    const header = "row,message\n";
    const body = warnings.map((e) => `${e.row},"${e.message.replace(/"/g, '""')}"`).join("\n");
    const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transaction_warnings_${new Date().toISOString()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Transactions</h1>
            {errors.length > 0 ? (
              <span title="Rows skipped due to validation errors" className="rounded bg-red-100 px-2 py-0.5 text-[10px] text-red-700">
                Errors: {errors.length}
              </span>
            ) : null}
            {warnings.length > 0 ? (
              <span title="Data quality hints detected" className="rounded bg-amber-100 px-2 py-0.5 text-[10px] text-amber-700">
                Warnings: {warnings.length}
              </span>
            ) : null}
          </div>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Load from CSV or upload, then filter and export.</p>
        </div>
        <div className="flex items-center gap-2">
          <input type="file" accept=".csv,text/csv" onChange={onFileChange} className="text-xs" />
          <button onClick={exportFiltered} className="rounded border px-3 py-1.5 text-xs">Export filtered</button>
          
        </div>
      </div>

      {errors.length > 0 ? (
        <div className="mb-3 flex items-center justify-between rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-800 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
          <div>{errors.length} rows skipped due to validation errors.</div>
          <button onClick={downloadErrors} className="rounded border px-2 py-1">Download report</button>
        </div>
      ) : null}

      {warnings.length > 0 ? (
        <div className="mb-3 flex items-center justify-between rounded-md border border-blue-300 bg-blue-50 p-2 text-xs text-blue-800 dark:border-blue-900/40 dark:bg-blue-950/30 dark:text-blue-200">
          <div>{warnings.length} data quality hints found (rows not skipped).</div>
          <button onClick={downloadWarnings} className="rounded border px-2 py-1">Download hints</button>
        </div>
      ) : null}

      <FiltersBar filters={filters} onChange={setFilters} options={options} />

      {loading ? (
        <div className="h-[60vh] animate-pulse rounded border bg-zinc-100 dark:bg-zinc-900" />
      ) : allRows.length === 0 ? (
        <div className="rounded border p-4 text-sm text-zinc-600 dark:text-zinc-400">Upload a CSV to begin. You can also place a file at <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">public/data/transactions_mock_1000_for_participants.csv</code> (or <code className="rounded bg-zinc-100 px-1 text-xs dark:bg-zinc-800">public/data/transactions.csv</code>) for auto-load.</div>
      ) : (
        <TransactionTable rows={sorted} onRowClick={setSelected} sortBy={sortBy} sortDir={sortDir} onSortChange={onSortChange} />
      )}

      <TransactionDetailsDrawer open={!!selected} onOpenChange={(o) => !o && setSelected(null)} tx={selected} />
    </div>
  );
}

function buildOptions(rows: Transaction[]): Record<string, string[]> {
  const pick = (k: keyof Transaction) => Array.from(new Set(rows.map((r) => (r[k] || "") as string).filter(Boolean))).sort();
  return {
    currency: pick("currency"),
    channel: pick("channel"),
    product_type: pick("product_type"),
    booking_jurisdiction: pick("booking_jurisdiction"),
    regulator: pick("regulator"),
    originator_country: pick("originator_country"),
    beneficiary_country: pick("beneficiary_country"),
    client_risk_profile: pick("client_risk_profile"),
    swift_f71_charges: pick("swift_f71_charges"),
  };
}

function applyFilters(rows: Transaction[], f: Filters): Transaction[] {
  const q = (f.query ?? "").trim().toLowerCase();
  const dateFrom = f.dateFrom ? new Date(f.dateFrom + "T00:00:00+08:00").getTime() : null;
  const dateTo = f.dateTo ? new Date(f.dateTo + "T23:59:59+08:00").getTime() : null;
  return rows.filter((r) => {
    const t = new Date(r.booking_datetime).getTime();
    if (dateFrom && t < dateFrom) return false;
    if (dateTo && t > dateTo) return false;
    if (f.amountMin !== undefined && r.amount < f.amountMin) return false;
    if (f.amountMax !== undefined && r.amount > f.amountMax) return false;
    if (f.currency && f.currency.length && !f.currency.includes(r.currency)) return false;
    if (f.channel && f.channel.length && !f.channel.includes(r.channel)) return false;
    if (f.product_type && f.product_type.length && !f.product_type.includes(r.product_type)) return false;
    if (f.booking_jurisdiction && f.booking_jurisdiction.length && !f.booking_jurisdiction.includes(r.booking_jurisdiction)) return false;
    if (f.regulator && f.regulator.length && !f.regulator.includes(r.regulator)) return false;
    if (f.originator_country && f.originator_country.length && !f.originator_country.includes(r.originator_country)) return false;
    if (f.beneficiary_country && f.beneficiary_country.length && !f.beneficiary_country.includes(r.beneficiary_country)) return false;
    if (f.sanctions_screening && f.sanctions_screening.length) {
      const v = (r.sanctions_screening ?? "").toString().toUpperCase();
      if (!f.sanctions_screening.map((x) => x.toString().toUpperCase()).includes(v)) return false;
    }
    if (f.pep_flag !== null && f.pep_flag !== undefined) {
      const pep = (r.customer_is_pep ?? r.pep_flag) ?? false;
      if (pep !== f.pep_flag) return false;
    }
    if (f.fx_indicator !== null && f.fx_indicator !== undefined && (r.fx_indicator ?? false) !== f.fx_indicator) return false;
    if (f.client_risk_profile && f.client_risk_profile.length && !f.client_risk_profile.includes(r.client_risk_profile || "")) return false;
    if (f.swift_f71_charges && f.swift_f71_charges.length && !f.swift_f71_charges.includes(r.swift_f71_charges || "")) return false;
    if (f.travel_rule_complete !== null && f.travel_rule_complete !== undefined && (r.travel_rule_complete ?? false) !== f.travel_rule_complete) return false;
    if (f.cash_id_verified !== null && f.cash_id_verified !== undefined && (r.cash_id_verified ?? false) !== f.cash_id_verified) return false;
    if (f.product_complex !== null && f.product_complex !== undefined && (r.product_complex ?? false) !== f.product_complex) return false;
    if (f.is_advised !== null && f.is_advised !== undefined && (r.is_advised ?? false) !== f.is_advised) return false;
    if (f.kyc_completed !== null && f.kyc_completed !== undefined && r.kyc_completed !== f.kyc_completed) return false;
    if (f.suitability_assessed !== null && f.suitability_assessed !== undefined && r.suitability_assessed !== f.suitability_assessed) return false;
    if (f.va_disclosure_provided !== null && f.va_disclosure_provided !== undefined && r.va_disclosure_provided !== f.va_disclosure_provided) return false;
    if (q) {
      const maskedCompare = (s?: string) => (s ?? "").toLowerCase();
      const hay = [
        r.transaction_id,
        r.originator_name,
        r.originator_account ? `****${r.originator_account.slice(-4)}` : "",
        r.beneficiary_name,
        r.beneficiary_account ? `****${r.beneficiary_account.slice(-4)}` : "",
        r.narrative ?? "",
        r.swift_f70_purpose ?? "",
      ]
        .map(maskedCompare)
        .join(" ");
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function compareBy(a: Transaction, b: Transaction, key: SortKey, dir: "asc" | "desc") {
  let avNum: number | null = null;
  let bvNum: number | null = null;
  let avStr: string | null = null;
  let bvStr: string | null = null;
  switch (key) {
    case "booking_datetime":
      avNum = new Date(a.booking_datetime).getTime();
      bvNum = new Date(b.booking_datetime).getTime();
      break;
    case "amount":
      avNum = a.amount;
      bvNum = b.amount;
      break;
    case "transaction_id":
      avStr = a.transaction_id;
      bvStr = b.transaction_id;
      break;
    case "display_direction":
      avStr = a.display_direction ?? "";
      bvStr = b.display_direction ?? "";
      break;
    case "display_counterparty":
      avStr = a.display_counterparty ?? "";
      bvStr = b.display_counterparty ?? "";
      break;
    case "currency":
      avStr = a.currency;
      bvStr = b.currency;
      break;
    case "product_type":
      avStr = a.product_type;
      bvStr = b.product_type;
      break;
    case "channel":
      avStr = a.channel;
      bvStr = b.channel;
      break;
    case "sanctions_screening":
      avStr = (a.sanctions_screening ?? "").toString();
      bvStr = (b.sanctions_screening ?? "").toString();
      break;
    case "fx_indicator":
      avNum = (a.fx_indicator ? 1 : 0);
      bvNum = (b.fx_indicator ? 1 : 0);
      break;
    case "swift_f71_charges":
      avStr = a.swift_f71_charges ?? "";
      bvStr = b.swift_f71_charges ?? "";
      break;
  }
  let cmp = 0;
  if (avNum !== null && bvNum !== null) cmp = avNum - bvNum;
  else {
    const as = (avStr ?? "");
    const bs = (bvStr ?? "");
    cmp = as.localeCompare(bs);
  }
  return dir === "asc" ? cmp : -cmp;
}

function toCSV(rows: Transaction[], filters: Filters): string {
  const meta = `# export_time_utc,${new Date().toISOString()}\n# filters,${encodeURIComponent(JSON.stringify(filters))}\n`;
  const cols: (keyof Transaction)[] = [
    "booking_datetime",
    "transaction_id",
    "display_direction",
    "display_counterparty",
    "amount",
    "currency",
    "product_type",
    "channel",
    "sanctions_screening",
  ];
  const header = cols.join(",") + "\n";
  const body = rows
    .map((r) =>
      cols
        .map((k) => {
          let v: string | number | boolean | undefined | null;
          switch (k) {
            case "booking_datetime": v = r.booking_datetime; break;
            case "transaction_id": v = r.transaction_id; break;
            case "display_direction": v = r.display_direction ?? ""; break;
            case "display_counterparty": v = r.display_counterparty ?? ""; break;
            case "amount": v = r.amount; break;
            case "currency": v = r.currency; break;
            case "product_type": v = r.product_type; break;
            case "channel": v = r.channel; break;
            case "sanctions_screening": v = r.sanctions_screening ?? ""; break;
            default: v = "";
          }
          const s = v === undefined || v === null ? "" : String(v);
          if (s.includes(",") || s.includes("\n") || s.includes('"')) return '"' + s.replace(/"/g, '""') + '"';
          return s;
        })
        .join(",")
    )
    .join("\n");
  return meta + header + body + "\n";
}

// Advanced column selector removed for simplicity; all fields remain in the details drawer
