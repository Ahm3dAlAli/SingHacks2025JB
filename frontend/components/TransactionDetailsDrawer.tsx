"use client";

import { useState } from "react";
import { Transaction } from "@/types/transaction";
import { maskAccount } from "@/lib/parseTransactions";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from "@/components/ui/sheet";

export function TransactionDetailsDrawer({ open, onOpenChange, tx }: { open: boolean; onOpenChange: (o: boolean) => void; tx?: Transaction | null }) {
  const [revealPII, setRevealPII] = useState(false);
  if (!tx) return null;
  function maskMaybe(v?: string) {
    if (!v) return "";
    return revealPII ? v : maskAccount(v);
  }
  function fmtAmount(n: number, ccy: string) {
    return new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n) + (ccy ? ` ${ccy}` : "");
  }
  function fmtDT(iso?: string | null) {
    if (!iso) return "";
    const d = new Date(iso);
    return new Intl.DateTimeFormat("en-SG", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Singapore" }).format(d);
  }
  function fmtDateOnly(s?: string) {
    if (!s) return "";
    try {
      const parts = s.split("-");
      if (parts.length === 3) {
        const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
        return new Intl.DateTimeFormat("en-SG", { dateStyle: "medium" }).format(d);
      }
    } catch {}
    return s;
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[440px] sm:max-w-[520px]">
        <SheetHeader>
          <SheetTitle>Transaction {tx.transaction_id}</SheetTitle>
          <SheetDescription>Full details and narrative</SheetDescription>
        </SheetHeader>
        <div className="mt-3 space-y-4">
          <div className="flex items-center justify-between rounded border p-2 text-xs">
            <div className="text-zinc-600 dark:text-zinc-400">Reveal PII (names, accounts)</div>
            <label className="inline-flex cursor-pointer items-center gap-2">
              <input type="checkbox" checked={revealPII} onChange={(e) => setRevealPII(e.target.checked)} />
              <span className="text-xs">{revealPII ? "Shown" : "Hidden"}</span>
            </label>
          </div>

          <Section title="Core">
            <Field label="Booking Date/Time" value={fmtDT(tx.booking_datetime)} />
            <Field label="Value Date" value={tx.value_date} />
            <Field label="Transaction ID" value={tx.transaction_id} mono />
            <Field label="Amount" value={fmtAmount(tx.amount, tx.currency)} />
            <Field label="Currency" value={tx.currency} />
            <Field label="Channel" value={tx.channel} />
            <Field label="Product Type" value={tx.product_type} />
            <Field label="Jurisdiction" value={tx.booking_jurisdiction} />
            <Field label="Regulator" value={tx.regulator} />
          </Section>

          <Section title="Originator">
            <Field label="Name" value={tx.originator_name} />
            <Field label="Account" value={maskMaybe(tx.originator_account)} mono />
            <Field label="Country" value={tx.originator_country} />
          </Section>

          <Section title="Beneficiary">
            <Field label="Name" value={tx.beneficiary_name} />
            <Field label="Account" value={maskMaybe(tx.beneficiary_account)} mono />
            <Field label="Country" value={tx.beneficiary_country} />
          </Section>

          <Section title="Compliance">
            <Field label="KYC Completed" value={boolStr(tx.kyc_completed)} />
            <Field label="PEP" value={boolStr(tx.customer_is_pep ?? tx.pep_flag)} />
            <Field label="AML Risk Score" value={tx.aml_risk_score?.toString() ?? ""} />
            <Field label="Sanctions Screening" value={String(tx.sanctions_screening ?? "")} />
            <Field label="Suitability Assessed" value={boolStr(tx.suitability_assessed)} />
            <Field label="Suitability Result" value={tx.suitability_result ?? ""} />
            <Field label="VA Disclosure Provided" value={boolStr(tx.va_disclosure_provided)} />
            <Field label="Product has VA Exposure" value={boolStr(tx.product_has_va_exposure)} />
            <Field label="Is Advised" value={boolStr(tx.is_advised)} />
            <Field label="Product Complex" value={boolStr(tx.product_complex)} />
            <Field label="Client Risk Profile" value={tx.client_risk_profile ?? ""} />
          </Section>

          <Section title="Cash Thresholds">
            <Field label="Daily Cash Total (Customer)" value={tx.daily_cash_total_customer?.toString() ?? ""} />
            <Field label="Daily Cash Txn Count" value={tx.daily_cash_txn_count?.toString() ?? ""} />
            <Field label="Cash ID Verified" value={boolStr(tx.cash_id_verified)} />
          </Section>

          <Section title="Investigations">
            <Field label="Suspicion Determined" value={fmtDT(tx.suspicion_determined_datetime)} />
            <Field label="STR Filed" value={fmtDT(tx.str_filed_datetime)} />
          </Section>

          <Section title="SWIFT & Messaging">
            <Field label="SWIFT MT" value={tx.swift_mt ?? ""} />
            <Field label="Ordering Inst. BIC" value={tx.ordering_institution_bic ?? ""} />
            <Field label="Beneficiary Inst. BIC" value={tx.beneficiary_institution_bic ?? ""} />
            <Field label="F50 (Ordering Customer)" value={boolStr(tx.swift_f50_present)} />
            <Field label="F59 (Beneficiary Customer)" value={boolStr(tx.swift_f59_present)} />
            <Field label="Purpose (F70)" value={tx.swift_f70_purpose ?? ""} />
            <Field label="Charges (F71)" value={tx.swift_f71_charges ?? ""} />
            <Field label="Travel Rule Complete" value={boolStr(tx.travel_rule_complete)} />
          </Section>

          <Section title="FX Details">
            <Field label="FX Involved" value={boolStr(tx.fx_indicator)} />
            <Field label="Base CCY" value={tx.fx_base_ccy ?? ""} />
            <Field label="Quote CCY" value={tx.fx_quote_ccy ?? ""} />
            <Field label="Applied Rate" value={tx.fx_applied_rate?.toString() ?? ""} />
            <Field label="Market Rate" value={tx.fx_market_rate?.toString() ?? ""} />
            <Field label="Spread (bps)" value={tx.fx_spread_bps?.toString() ?? ""} />
            <Field label="FX Counterparty" value={tx.fx_counterparty ?? ""} />
          </Section>

          <Section title="Customer & KYC">
            <Field label="Customer ID" value={tx.customer_id ?? ""} />
            <Field label="Customer Type" value={tx.customer_type ?? ""} />
            <Field label="Risk Rating" value={tx.customer_risk_rating ?? ""} />
            <Field label="KYC Last Completed" value={fmtDateOnly(tx.kyc_last_completed)} />
            <Field label="KYC Due Date" value={fmtDateOnly(tx.kyc_due_date)} />
            <Field label="EDD Required" value={boolStr(tx.edd_required)} />
            <Field label="EDD Performed" value={boolStr(tx.edd_performed)} />
            <Field label="Source of Wealth Documented" value={boolStr(tx.sow_documented)} />
          </Section>

          {tx.narrative ? (
            <div>
              <div className="mb-1 text-xs font-medium text-zinc-600 dark:text-zinc-400">Narrative</div>
              <div className="rounded border p-2 text-sm whitespace-pre-wrap">{tx.narrative}</div>
            </div>
          ) : null}

          <div className="pt-2">
            <SheetClose className="rounded border px-3 py-1.5 text-sm">Close</SheetClose>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function boolStr(v?: boolean) {
  return v === undefined ? "" : v ? "Yes" : "No";
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold text-zinc-700 dark:text-zinc-300">{title}</h3>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {children}
      </div>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="text-xs">
      <div className="text-zinc-500">{label}</div>
      <div className={mono ? "font-mono" : ""}>{value}</div>
    </div>
  );
}
