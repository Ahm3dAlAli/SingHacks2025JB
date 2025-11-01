"use client";

import { useEffect, useMemo, useState } from "react";
import { ScreeningStatus } from "@/types/transaction";

export type Filters = {
  dateFrom?: string;
  dateTo?: string;
  amountMin?: number;
  amountMax?: number;
  currency?: string[];
  channel?: string[];
  product_type?: string[];
  booking_jurisdiction?: string[];
  regulator?: string[];
  originator_country?: string[];
  beneficiary_country?: string[];
  sanctions_screening?: (ScreeningStatus | string)[];
  pep_flag?: boolean | null;
  fx_indicator?: boolean | null;
  client_risk_profile?: string[];
  swift_f71_charges?: string[];
  travel_rule_complete?: boolean | null;
  cash_id_verified?: boolean | null;
  product_complex?: boolean | null;
  is_advised?: boolean | null;
  kyc_completed?: boolean | null;
  suitability_assessed?: boolean | null;
  va_disclosure_provided?: boolean | null;
  query?: string;
};

export function FiltersBar({
  filters,
  onChange,
  options,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  options: Record<string, string[]>;
}) {
  const [query, setQuery] = useState(filters.query ?? "");
  useEffect(() => {
    setQuery(filters.query ?? "");
  }, [filters.query]);
  useEffect(() => {
    const t = setTimeout(() => onChange({ ...filters, query }), 250);
    return () => clearTimeout(t);
  }, [query]);

  function checkboxTristate(label: string, value: boolean | null | undefined, onUpdate: (v: boolean | null) => void) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-600 dark:text-zinc-400">{label}</span>
        <select
          value={value === null || value === undefined ? "" : value ? "true" : "false"}
          onChange={(e) => onUpdate(e.target.value === "" ? null : e.target.value === "true")}
          className="rounded border bg-white p-1 text-xs dark:border-zinc-700 dark:bg-zinc-950"
        >
          <option value="">Any</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </div>
    );
  }

  return (
    <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-3 lg:grid-cols-4">
      <div className="flex items-center gap-2">
        <label className="text-xs text-zinc-600 dark:text-zinc-400">Date From</label>
        <input type="date" value={filters.dateFrom ?? ""} onChange={(e) => onChange({ ...filters, dateFrom: e.target.value || undefined })} className="w-full rounded border p-1 text-xs" />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs text-zinc-600 dark:text-zinc-400">Date To</label>
        <input type="date" value={filters.dateTo ?? ""} onChange={(e) => onChange({ ...filters, dateTo: e.target.value || undefined })} className="w-full rounded border p-1 text-xs" />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs text-zinc-600 dark:text-zinc-400">Amt Min</label>
        <input type="number" step="0.01" value={filters.amountMin ?? ""} onChange={(e) => onChange({ ...filters, amountMin: e.target.value ? Number(e.target.value) : undefined })} className="w-full rounded border p-1 text-xs" />
      </div>
      <div className="flex items-center gap-2">
        <label className="text-xs text-zinc-600 dark:text-zinc-400">Amt Max</label>
        <input type="number" step="0.01" value={filters.amountMax ?? ""} onChange={(e) => onChange({ ...filters, amountMax: e.target.value ? Number(e.target.value) : undefined })} className="w-full rounded border p-1 text-xs" />
      </div>

      <MultiSelect label="Currency" values={filters.currency ?? []} options={options.currency ?? []} onChange={(v) => onChange({ ...filters, currency: v })} />
      <MultiSelect label="Channel" values={filters.channel ?? []} options={options.channel ?? []} onChange={(v) => onChange({ ...filters, channel: v })} />
      <MultiSelect label="Product" values={filters.product_type ?? []} options={options.product_type ?? []} onChange={(v) => onChange({ ...filters, product_type: v })} />
      <MultiSelect label="Jurisdiction" values={filters.booking_jurisdiction ?? []} options={options.booking_jurisdiction ?? []} onChange={(v) => onChange({ ...filters, booking_jurisdiction: v })} />
      <MultiSelect label="Regulator" values={filters.regulator ?? []} options={options.regulator ?? []} onChange={(v) => onChange({ ...filters, regulator: v })} />
      <MultiSelect label="Originator Country" values={filters.originator_country ?? []} options={options.originator_country ?? []} onChange={(v) => onChange({ ...filters, originator_country: v })} />
      <MultiSelect label="Beneficiary Country" values={filters.beneficiary_country ?? []} options={options.beneficiary_country ?? []} onChange={(v) => onChange({ ...filters, beneficiary_country: v })} />
      <MultiSelect label="Sanctions" values={(filters.sanctions_screening as string[] | undefined) ?? []} options={["CLEAR","POTENTIAL_MATCH","HIT","UNKNOWN"]} onChange={(v) => onChange({ ...filters, sanctions_screening: v })} />

      {checkboxTristate("PEP", filters.pep_flag ?? null, (v) => onChange({ ...filters, pep_flag: v }))}
      {checkboxTristate("FX", filters.fx_indicator ?? null, (v) => onChange({ ...filters, fx_indicator: v }))}
      <MultiSelect label="Client Risk" values={filters.client_risk_profile ?? []} options={options.client_risk_profile ?? []} onChange={(v) => onChange({ ...filters, client_risk_profile: v })} />
      <MultiSelect label="Charges (F71)" values={filters.swift_f71_charges ?? []} options={options.swift_f71_charges ?? []} onChange={(v) => onChange({ ...filters, swift_f71_charges: v })} />
      {checkboxTristate("Travel Rule", filters.travel_rule_complete ?? null, (v) => onChange({ ...filters, travel_rule_complete: v }))}
      {checkboxTristate("Cash ID Verified", filters.cash_id_verified ?? null, (v) => onChange({ ...filters, cash_id_verified: v }))}
      {checkboxTristate("Product Complex", filters.product_complex ?? null, (v) => onChange({ ...filters, product_complex: v }))}
      {checkboxTristate("Is Advised", filters.is_advised ?? null, (v) => onChange({ ...filters, is_advised: v }))}
      {checkboxTristate("KYC Completed", filters.kyc_completed ?? null, (v) => onChange({ ...filters, kyc_completed: v }))}
      {checkboxTristate("Suitability", filters.suitability_assessed ?? null, (v) => onChange({ ...filters, suitability_assessed: v }))}
      {checkboxTristate("VA Disclosure", filters.va_disclosure_provided ?? null, (v) => onChange({ ...filters, va_disclosure_provided: v }))}

      <div className="col-span-full flex items-center gap-2">
        <label className="text-xs text-zinc-600 dark:text-zinc-400">Search</label>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="ID, names, accounts, narrative"
          className="w-full rounded border p-2 text-sm"
        />
      </div>
    </div>
  );
}

function MultiSelect({ label, values, options, onChange }: { label: string; values: string[]; options: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-zinc-600 dark:text-zinc-400">{label}</label>
      <select
        multiple
        value={values}
        onChange={(e) => {
          const selected = Array.from(e.target.selectedOptions).map((o) => o.value);
          onChange(selected);
        }}
        className="w-full rounded border bg-white p-1 text-xs dark:border-zinc-700 dark:bg-zinc-950"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
