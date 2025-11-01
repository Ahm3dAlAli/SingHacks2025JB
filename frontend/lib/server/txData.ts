import { promises as fs } from "fs";
import path from "path";
import { Transaction } from "@/types/transaction";
import { parseTransactionsWithZodFromText } from "@/lib/parseTransactions";

let cache: { rows: Transaction[]; byId: Map<string, Transaction>; loadedAt: number } | null = null;

const CANDIDATE_PATHS = [
  path.join(process.cwd(), "public", "data", "transactions_mock_1000_for_participants.csv"),
  path.join(process.cwd(), "public", "data", "transactions.csv"),
];

export async function loadTransactions(): Promise<{ rows: Transaction[]; byId: Map<string, Transaction> }> {
  if (cache && Date.now() - cache.loadedAt < 60_000) return cache; // simple 60s cache
  let text: string | null = null;
  for (const p of CANDIDATE_PATHS) {
    try {
      text = await fs.readFile(p, "utf8");
      break;
    } catch {}
  }
  if (!text) return { rows: [], byId: new Map() };
  const { rows } = parseTransactionsWithZodFromText(text);
  const byId = new Map<string, Transaction>();
  for (const r of rows) byId.set(r.transaction_id, r);
  cache = { rows, byId, loadedAt: Date.now() };
  return cache;
}

export function computeSeverity(tx: Transaction): "low" | "medium" | "high" | "critical" {
  const sanc = (tx.sanctions_screening ?? "").toString().toUpperCase();
  if (sanc === "HIT") return "critical";
  if (sanc === "POTENTIAL_MATCH") return "high";
  const risk = tx.aml_risk_score ?? 0;
  if (risk >= 80) return "high";
  if (risk >= 50) return "medium";
  return "low";
}

export function computeRisk(tx: Transaction): number {
  const sanc = (tx.sanctions_screening ?? "").toString().toUpperCase();
  let score = Math.min(100, Math.max(0, Math.round((tx.aml_risk_score ?? 0))));
  if (sanc === "HIT") score = Math.max(score, 95);
  else if (sanc === "POTENTIAL_MATCH") score = Math.max(score, 75);
  const amt = Math.abs(tx.amount);
  if (amt > 100_000) score = Math.max(score, 70);
  return Math.min(100, score);
}

export function computeRuleHits(tx: Transaction): { id: string; name: string; score: number }[] {
  const hits: { id: string; name: string; score: number }[] = [];
  const sanc = (tx.sanctions_screening ?? "").toString().toUpperCase();
  if (sanc === "HIT") hits.push({ id: "rule-sanctions-hit", name: "Sanctions HIT", score: 50 });
  else if (sanc === "POTENTIAL_MATCH") hits.push({ id: "rule-sanctions-pm", name: "Sanctions potential match", score: 30 });
  if ((tx.aml_risk_score ?? 0) >= 80) hits.push({ id: "rule-aml-high", name: "High AML risk score", score: 25 });
  if (Math.abs(tx.amount) > 100_000) hits.push({ id: "rule-amount-high", name: "High amount", score: 20 });
  if (tx.pep_flag || tx.customer_is_pep) hits.push({ id: "rule-pep", name: "PEP flag", score: 30 });
  // Travel rule & VA
  if (tx.product_has_va_exposure && tx.va_disclosure_provided === false) hits.push({ id: "rule-va-disclosure-missing", name: "VA exposure without disclosure", score: 20 });
  if (tx.travel_rule_complete === false) hits.push({ id: "rule-travel-incomplete", name: "Travel rule incomplete", score: 20 });
  // SWIFT MT data quality when message present
  if (tx.swift_mt) {
    if (!tx.swift_f50_present) hits.push({ id: "rule-swift-missing-f50", name: "SWIFT missing F50 (Ordering Customer)", score: 15 });
    if (!tx.swift_f59_present) hits.push({ id: "rule-swift-missing-f59", name: "SWIFT missing F59 (Beneficiary Customer)", score: 15 });
    if (!tx.swift_f70_purpose) hits.push({ id: "rule-swift-missing-f70", name: "SWIFT missing F70 (Purpose)", score: 10 });
    if (!tx.swift_f71_charges) hits.push({ id: "rule-swift-missing-f71", name: "SWIFT missing F71 (Charges)", score: 10 });
  }
  // KYC / EDD
  const today = new Date();
  const due = tx.kyc_due_date ? new Date(tx.kyc_due_date + "T00:00:00+08:00") : null;
  if (due && !isNaN(due.getTime()) && due.getTime() < today.getTime()) hits.push({ id: "rule-kyc-overdue", name: "KYC overdue", score: 25 });
  if (tx.edd_required && !tx.edd_performed) hits.push({ id: "rule-edd-missing", name: "EDD required but not performed", score: 25 });
  if (tx.sow_documented === false) hits.push({ id: "rule-sow-missing", name: "Source of wealth not documented", score: 15 });
  // FX anomalies
  if (tx.fx_indicator) {
    const spread = tx.fx_spread_bps ?? 0;
    if (spread > 50) hits.push({ id: "rule-fx-wide-spread", name: "FX spread high", score: 15 });
  }
  // Cash risks
  if ((tx.daily_cash_total_customer ?? 0) > 50_000) hits.push({ id: "rule-cash-volume-high", name: "High cash volume (daily)", score: 15 });
  if ((tx.daily_cash_txn_count ?? 0) >= 10) hits.push({ id: "rule-cash-count-high", name: "High cash txn count (daily)", score: 10 });
  if (tx.cash_id_verified === false) hits.push({ id: "rule-cash-id-not-verified", name: "Cash ID not verified", score: 15 });
  // Timing
  try {
    const t = new Date(tx.booking_datetime);
    const hour = t.getHours();
    const day = t.getDay(); // 0 Sun ... 6 Sat
    if (!isNaN(t.getTime())) {
      if (day === 0 || day === 6) hits.push({ id: "rule-time-weekend", name: "Weekend booking time", score: 10 });
      if (hour < 7 || hour >= 20) hits.push({ id: "rule-time-out-of-hours", name: "Outside business hours", score: 10 });
    }
  } catch {}
  return hits.slice(0, 4);
}
