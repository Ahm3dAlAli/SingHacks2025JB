import { Transaction, ScreeningStatus, TransactionFull, TransactionFullSchema } from "@/types/transaction";

export type ParseError = { row: number; message: string };
export type ParseWarning = { row: number; message: string };

// Minimal CSV parser supporting quotes, commas, newlines, and escaped quotes.
function parseCSV(text: string): { headers: string[]; rows: string[][] } {
  const rows: string[][] = [];
  let i = 0;
  const len = text.length;
  let cur: string[] = [];
  let field = "";
  let inQuotes = false;

  function pushField() {
    cur.push(field);
    field = "";
  }
  function pushRow() {
    rows.push(cur);
    cur = [];
  }

  while (i < len) {
    const ch = text[i];
    if (inQuotes) {
      if (ch === '"') {
        const next = text[i + 1];
        if (next === '"') {
          field += '"';
          i += 2;
          continue;
        } else {
          inQuotes = false;
          i++;
          continue;
        }
      } else {
        field += ch;
        i++;
        continue;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
        i++;
        continue;
      }
      if (ch === ",") {
        pushField();
        i++;
        continue;
      }
      if (ch === "\n") {
        pushField();
        pushRow();
        i++;
        // handle CRLF (if any previous CR)
        continue;
      }
      if (ch === "\r") {
        // consume optional \n
        pushField();
        pushRow();
        i++;
        if (text[i] === "\n") i++;
        continue;
      }
      field += ch;
      i++;
    }
  }
  // flush last field/row
  pushField();
  pushRow();

  if (rows.length === 0) return { headers: [], rows: [] };
  const headers = rows[0].map((h) => h.trim());
  const dataRows = rows.slice(1);
  return { headers, rows: dataRows };
}

const REQUIRED_COLUMNS = [
  "transaction_id",
  "booking_datetime",
  "amount",
  "currency",
  "originator_name",
  "beneficiary_name",
];

export async function parseTransactionsFromFile(file: File): Promise<{ rows: Transaction[]; errors: ParseError[]; warnings: ParseWarning[]; missingColumns?: string[] }> {
  const text = await file.text();
  return parseTransactionsFromText(text);
}

export function parseTransactionsFromText(text: string): { rows: Transaction[]; errors: ParseError[]; warnings: ParseWarning[]; missingColumns?: string[] } {
  const { headers, rows } = parseCSV(text);
  if (!headers || headers.length === 0) {
    return { rows: [], errors: [{ row: 0, message: "Couldn't parse file. Expected a header row." }], warnings: [] };
  }
  const headerSet = new Set(headers);
  const missing = REQUIRED_COLUMNS.filter((c) => !headerSet.has(c));
  if (missing.length) {
    return { rows: [], errors: [{ row: 0, message: `Missing required columns: ${missing.join(", ")}` }], missingColumns: missing, warnings: [] };
  }

  const data: Transaction[] = [];
  const errors: ParseError[] = [];
  const warnings: ParseWarning[] = [];

  const idx: Record<string, number> = Object.fromEntries(headers.map((h, i) => [h, i]));

  rows.forEach((cols, r) => {
    const rowNum = r + 2; // account for header
    function val(name: string): string {
      const i = idx[name];
      return i !== undefined ? (cols[i] ?? "").trim() : "";
    }
    function num(name: string): number | undefined {
      const v = val(name);
      if (v === "") return undefined;
      const n = Number(v.replace(/,/g, ""));
      return Number.isFinite(n) ? n : undefined;
    }
    function int(name: string): number | undefined {
      const n = num(name);
      return n !== undefined ? Math.trunc(n) : undefined;
    }

    // Required checks
    const transaction_id = val("transaction_id");
    const booking_datetime_raw = val("booking_datetime");
    const amountRaw = val("amount");
    const currency = val("currency");
    const originator_name = val("originator_name");
    const beneficiary_name = val("beneficiary_name");
    if (!transaction_id || !booking_datetime_raw || !amountRaw || !currency || !originator_name || !beneficiary_name) {
      errors.push({ row: rowNum, message: "Missing required fields" });
      return;
    }
    const amount = Number(amountRaw.replace(/,/g, ""));
    if (!Number.isFinite(amount)) {
      errors.push({ row: rowNum, message: "Invalid amount" });
      return;
    }

    const booking_datetime = toSingaporeISO(booking_datetime_raw);
    if (!booking_datetime) {
      errors.push({ row: rowNum, message: "Invalid booking_datetime" });
      return;
    }

    const value_date_raw = val("value_date");
    const value_date = normalizeDateOnly(value_date_raw);

    const tx: Transaction = {
      transaction_id,
      booking_jurisdiction: val("booking_jurisdiction"),
      regulator: val("regulator"),
      booking_datetime,
      value_date,
      amount,
      currency,
      channel: val("channel"),
      product_type: val("product_type"),
      originator_name,
      originator_account: val("originator_account"),
      originator_country: val("originator_country"),
      beneficiary_name,
      beneficiary_account: val("beneficiary_account"),
      beneficiary_country: val("beneficiary_country"),
      swift_mt: val("swift_mt") || undefined,
      ordering_institution_bic: val("ordering_institution_bic") || undefined,
      beneficiary_institution_bic: val("beneficiary_institution_bic") || undefined,
      swift_f50_present: toBool(val("swift_f50_present")),
      swift_f59_present: toBool(val("swift_f59_present")),
      swift_f70_purpose: val("swift_f70_purpose") || undefined,
      swift_f71_charges: val("swift_f71_charges") || undefined,
      travel_rule_complete: toBool(val("travel_rule_complete")),
      kyc_completed: toBool(val("kyc_completed")),
      pep_flag: toBool(val("pep_flag")),
      aml_risk_score: num("aml_risk_score"),
      sanctions_screening: normalizeSanctions(val("sanctions_screening")),
      customer_id: val("customer_id") || undefined,
      customer_type: val("customer_type") || undefined,
      customer_risk_rating: val("customer_risk_rating") || undefined,
      customer_is_pep: toBool(val("customer_is_pep")),
      kyc_last_completed: normalizeDateOnly(val("kyc_last_completed")) || undefined,
      kyc_due_date: normalizeDateOnly(val("kyc_due_date")) || undefined,
      edd_required: toBool(val("edd_required")),
      edd_performed: toBool(val("edd_performed")),
      sow_documented: toBool(val("sow_documented")),
      suitability_assessed: toBool(val("suitability_assessed")),
      suitability_result: val("suitability_result") || undefined,
      va_disclosure_provided: toBool(val("va_disclosure_provided")),
      product_has_va_exposure: toBool(val("product_has_va_exposure")),
      client_risk_profile: val("client_risk_profile") || undefined,
      is_advised: toBool(val("is_advised")),
      product_complex: toBool(val("product_complex")),
      daily_cash_total_customer: num("daily_cash_total_customer"),
      daily_cash_txn_count: int("daily_cash_txn_count"),
      cash_id_verified: toBool(val("cash_id_verified")),
      suspicion_determined_datetime: nullableISO(val("suspicion_determined_datetime")),
      str_filed_datetime: nullableISO(val("str_filed_datetime")),
      narrative: val("narrative") || undefined,
      purpose_code: val("purpose_code") || undefined,
      fx_indicator: toBool(val("fx_indicator")),
      fx_base_ccy: val("fx_base_ccy") || undefined,
      fx_quote_ccy: val("fx_quote_ccy") || undefined,
      fx_applied_rate: num("fx_applied_rate"),
      fx_market_rate: num("fx_market_rate"),
      fx_spread_bps: num("fx_spread_bps"),
      fx_counterparty: val("fx_counterparty") || undefined,
    };

    // Derived
    tx.display_direction = amount >= 0 ? "IN" : "OUT";
    tx.display_counterparty = tx.display_direction === "OUT"
      ? (tx.beneficiary_name || maskAccount(tx.beneficiary_account))
      : (tx.originator_name || maskAccount(tx.originator_account));

    data.push(tx);

    // Non-blocking validation hints for SWIFT scenarios
    if (tx.swift_mt) {
      const missingFields: string[] = [];
      if (!tx.swift_f50_present) missingFields.push("swift_f50_present (Ordering Customer)");
      if (!tx.swift_f59_present) missingFields.push("swift_f59_present (Beneficiary Customer)");
      if (!tx.swift_f70_purpose) missingFields.push("swift_f70_purpose (Purpose)");
      if (!tx.swift_f71_charges) missingFields.push("swift_f71_charges (Charges)");
      if (!tx.ordering_institution_bic) missingFields.push("ordering_institution_bic");
      if (!tx.beneficiary_institution_bic) missingFields.push("beneficiary_institution_bic");
      if (missingFields.length) {
        warnings.push({ row: rowNum, message: `SWIFT MT present but missing: ${missingFields.join(", ")}` });
      }
    }
  });

  return { rows: data, errors, warnings };
}

export function toBool(v: any): boolean | undefined {
  const s = String(v ?? "").trim().toUpperCase();
  if (!s) return undefined;
  if (["TRUE", "1", "Y", "YES"].includes(s)) return true;
  if (["FALSE", "0", "N", "NO"].includes(s)) return false;
  return undefined;
}

export function maskAccount(v?: string): string {
  if (!v) return "";
  const last4 = v.slice(-4);
  return `****${last4}`;
}

export function normalizeSanctions(v?: string): ScreeningStatus | string | undefined {
  if (!v) return undefined;
  const s = v.trim().toUpperCase();
  if (["CLEAR", "POTENTIAL_MATCH", "HIT", "UNKNOWN"].includes(s)) return s as ScreeningStatus;
  if (["POTENTIAL MATCH", "MATCH", "POSSIBLE", "POSSIBLE_MATCH", "POTENTIAL"].includes(s)) return "POTENTIAL_MATCH";
  if (["NONE", "NO_MATCH", "NEGATIVE"].includes(s)) return "CLEAR";
  return s;
}

export function toSingaporeISO(v?: string): string | null {
  if (!v) return null;
  const s = v.trim();
  if (!s) return null;
  // If already ISO with timezone, return as-is
  if (/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s) && /[Zz]|[+\-]\d{2}:?\d{2}$/.test(s)) {
    try {
      const d = new Date(s);
      if (isNaN(d.getTime())) return null;
      // Convert to +08:00 string
      const iso = toTZOffsetISO(d, 8);
      return iso;
    } catch {
      return null;
    }
  }
  // If looks like date time without tz, treat as Asia/Singapore
  // Accept "YYYY-MM-DD HH:mm[:ss]" or "YYYY-MM-DDTHH:mm[:ss]"
  const m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)/);
  if (m) {
    const date = m[1];
    const time = m[2].length === 5 ? m[2] + ":00" : m[2];
    return `${date}T${time}+08:00`;
  }
  // Fallback: try Date parse and convert to +08:00
  try {
    const d = new Date(s);
    if (isNaN(d.getTime())) return null;
    return toTZOffsetISO(d, 8);
  } catch {
    return null;
  }
}

function toTZOffsetISO(d: Date, tzOffsetHours: number): string {
  // Convert UTC time to target offset
  const utc = d.getTime() + d.getTimezoneOffset() * 60_000;
  const target = new Date(utc + tzOffsetHours * 3600_000);
  const yyyy = target.getUTCFullYear();
  const mm = String(target.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(target.getUTCDate()).padStart(2, "0");
  const HH = String(target.getUTCHours()).padStart(2, "0");
  const MM = String(target.getUTCMinutes()).padStart(2, "0");
  const SS = String(target.getUTCSeconds()).padStart(2, "0");
  const offset = (tzOffsetHours >= 0 ? "+" : "-") + String(Math.abs(tzOffsetHours)).padStart(2, "0") + ":00";
  return `${yyyy}-${mm}-${dd}T${HH}:${MM}:${SS}${offset}`;
}

function normalizeDateOnly(v?: string): string {
  if (!v) return "";
  const s = v.trim();
  // yyyy-mm-dd or yyyy/mm/dd
  let m = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/);
  if (m) return `${m[1]}-${m[2].padStart(2, "0")}-${m[3].padStart(2, "0")}`;
  // dd/mm/yyyy or d/m/yyyy
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  // try parse
  const d = new Date(s);
  if (isNaN(d.getTime())) return "";
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function nullableISO(v?: string): string | null {
  const s = (v ?? "").trim();
  if (!s) return null;
  const iso = toSingaporeISO(s);
  return iso;
}

// Parse CSV into TransactionFull and validate each row using Zod.
export function parseTransactionsFullFromText(text: string): { rows: TransactionFull[]; errors: ParseError[]; warnings: ParseWarning[] } {
  const { headers, rows } = parseCSV(text);
  if (!headers || headers.length === 0) {
    return { rows: [], errors: [{ row: 0, message: "Couldn't parse file. Expected a header row." }], warnings: [] };
  }
  const idx: Record<string, number> = Object.fromEntries(headers.map((h, i) => [h, i]));
  const data: TransactionFull[] = [];
  const errors: ParseError[] = [];
  const warnings: ParseWarning[] = [];

  function get(cols: string[], name: string): string {
    const i = idx[name];
    return i !== undefined ? (cols[i] ?? "").trim() : "";
  }
  function getOrNull(cols: string[], name: string): string | null {
    const v = get(cols, name);
    return v === "" ? null : v;
  }
  function getNumber(cols: string[], name: string): number {
    const v = get(cols, name);
    const n = Number(v.replace(/,/g, ""));
    return n;
  }
  function getNumberOrNull(cols: string[], name: string): number | null {
    const v = get(cols, name);
    if (!v) return null;
    const n = Number(v.replace(/,/g, ""));
    return Number.isFinite(n) ? n : NaN;
  }
  function getBool(cols: string[], name: string): boolean {
    const v = get(cols, name).toUpperCase();
    if (["TRUE", "1", "Y", "YES"].includes(v)) return true;
    if (["FALSE", "0", "N", "NO"].includes(v)) return false;
    // Default to false if unspecified
    return false;
  }

  rows.forEach((cols, r) => {
    const rowNum = r + 2;
    // Build a raw object from CSV strings, coercing types where appropriate
    const bookingIso = toSingaporeISO(get(cols, "booking_datetime"));
    if (!bookingIso) {
      errors.push({ row: rowNum, message: "Invalid booking_datetime" });
      return;
    }
    const candidate = {
      transaction_id: get(cols, "transaction_id"),
      booking_jurisdiction: get(cols, "booking_jurisdiction"),
      regulator: get(cols, "regulator"),
      booking_datetime: bookingIso,
      value_date: normalizeDateOnly(get(cols, "value_date")),
      amount: getNumber(cols, "amount"),
      currency: get(cols, "currency"),
      channel: get(cols, "channel"),
      product_type: get(cols, "product_type"),
      originator_name: get(cols, "originator_name"),
      originator_account: get(cols, "originator_account"),
      originator_country: get(cols, "originator_country"),
      beneficiary_name: get(cols, "beneficiary_name"),
      beneficiary_account: get(cols, "beneficiary_account"),
      beneficiary_country: get(cols, "beneficiary_country"),
      swift_mt: getOrNull(cols, "swift_mt"),
      ordering_institution_bic: getOrNull(cols, "ordering_institution_bic"),
      beneficiary_institution_bic: getOrNull(cols, "beneficiary_institution_bic"),
      swift_f50_present: getBool(cols, "swift_f50_present"),
      swift_f59_present: getBool(cols, "swift_f59_present"),
      swift_f70_purpose: getOrNull(cols, "swift_f70_purpose"),
      swift_f71_charges: getOrNull(cols, "swift_f71_charges"),
      travel_rule_complete: getBool(cols, "travel_rule_complete"),
      fx_indicator: getBool(cols, "fx_indicator"),
      fx_base_ccy: getOrNull(cols, "fx_base_ccy"),
      fx_quote_ccy: getOrNull(cols, "fx_quote_ccy"),
      fx_applied_rate: getNumber(cols, "fx_applied_rate"),
      fx_market_rate: getNumber(cols, "fx_market_rate"),
      fx_spread_bps: getNumber(cols, "fx_spread_bps"),
      fx_counterparty: getOrNull(cols, "fx_counterparty"),
      customer_id: get(cols, "customer_id"),
      customer_type: get(cols, "customer_type"),
      customer_risk_rating: get(cols, "customer_risk_rating"),
      customer_is_pep: getBool(cols, "customer_is_pep"),
      kyc_last_completed: normalizeDateOnly(get(cols, "kyc_last_completed")),
      kyc_due_date: normalizeDateOnly(get(cols, "kyc_due_date")),
      edd_required: getBool(cols, "edd_required"),
      edd_performed: getBool(cols, "edd_performed"),
      sow_documented: getBool(cols, "sow_documented"),
      purpose_code: get(cols, "purpose_code"),
      narrative: get(cols, "narrative"),
      is_advised: getBool(cols, "is_advised"),
      product_complex: getBool(cols, "product_complex"),
      client_risk_profile: get(cols, "client_risk_profile"),
      suitability_assessed: getBool(cols, "suitability_assessed"),
      suitability_result: get(cols, "suitability_result"),
      product_has_va_exposure: getBool(cols, "product_has_va_exposure"),
      va_disclosure_provided: getBool(cols, "va_disclosure_provided"),
      cash_id_verified: getBool(cols, "cash_id_verified"),
      daily_cash_total_customer: getNumber(cols, "daily_cash_total_customer"),
      daily_cash_txn_count: getNumber(cols, "daily_cash_txn_count"),
      sanctions_screening: get(cols, "sanctions_screening"),
      suspicion_determined_datetime: toSingaporeISO(get(cols, "suspicion_determined_datetime")),
      str_filed_datetime: toSingaporeISO(get(cols, "str_filed_datetime")),
    } as unknown;

    const parsed = TransactionFullSchema.safeParse(candidate);
    if (!parsed.success) {
      const issues = parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
      errors.push({ row: rowNum, message: `Schema validation failed: ${issues}` });
      return;
    }
    data.push(parsed.data);
  });

  return { rows: data, errors, warnings };
}

export async function parseTransactionsFullFromFile(file: File): Promise<{ rows: TransactionFull[]; errors: ParseError[]; warnings: ParseWarning[] }> {
  const text = await file.text();
  return parseTransactionsFullFromText(text);
}

export function toClientTransaction(f: TransactionFull): Transaction {
  const t: Transaction = {
    transaction_id: f.transaction_id,
    booking_jurisdiction: f.booking_jurisdiction,
    regulator: f.regulator,
    booking_datetime: f.booking_datetime,
    value_date: f.value_date,
    amount: f.amount,
    currency: f.currency,
    channel: f.channel,
    product_type: f.product_type,
    originator_name: f.originator_name,
    originator_account: f.originator_account,
    originator_country: f.originator_country,
    beneficiary_name: f.beneficiary_name,
    beneficiary_account: f.beneficiary_account,
    beneficiary_country: f.beneficiary_country,
    swift_mt: f.swift_mt || undefined,
    ordering_institution_bic: f.ordering_institution_bic || undefined,
    beneficiary_institution_bic: f.beneficiary_institution_bic || undefined,
    swift_f50_present: f.swift_f50_present,
    swift_f59_present: f.swift_f59_present,
    swift_f70_purpose: f.swift_f70_purpose || undefined,
    swift_f71_charges: f.swift_f71_charges || undefined,
    travel_rule_complete: f.travel_rule_complete,
    sanctions_screening: f.sanctions_screening,
    customer_id: f.customer_id,
    customer_type: f.customer_type,
    customer_risk_rating: f.customer_risk_rating,
    customer_is_pep: f.customer_is_pep,
    kyc_last_completed: f.kyc_last_completed,
    kyc_due_date: f.kyc_due_date,
    edd_required: f.edd_required,
    edd_performed: f.edd_performed,
    sow_documented: f.sow_documented,
    suitability_assessed: f.suitability_assessed,
    suitability_result: f.suitability_result,
    va_disclosure_provided: f.va_disclosure_provided,
    product_has_va_exposure: f.product_has_va_exposure,
    client_risk_profile: f.client_risk_profile,
    is_advised: f.is_advised,
    product_complex: f.product_complex,
    daily_cash_total_customer: f.daily_cash_total_customer,
    daily_cash_txn_count: f.daily_cash_txn_count,
    cash_id_verified: f.cash_id_verified,
    narrative: f.narrative,
    purpose_code: f.purpose_code,
    fx_indicator: f.fx_indicator,
    fx_base_ccy: f.fx_base_ccy || undefined,
    fx_quote_ccy: f.fx_quote_ccy || undefined,
    fx_applied_rate: f.fx_applied_rate,
    fx_market_rate: f.fx_market_rate,
    fx_spread_bps: f.fx_spread_bps,
    fx_counterparty: f.fx_counterparty || undefined,
  };
  // Derived display fields
  t.display_direction = t.amount >= 0 ? "IN" : "OUT";
  t.display_counterparty = t.display_direction === "OUT"
    ? (t.beneficiary_name || maskAccount(t.beneficiary_account))
    : (t.originator_name || maskAccount(t.originator_account));
  return t;
}

export function parseTransactionsWithZodFromText(text: string): { rows: Transaction[]; errors: ParseError[]; warnings: ParseWarning[] } {
  const full = parseTransactionsFullFromText(text);
  const rows = full.rows.map(toClientTransaction);
  // Non-blocking SWIFT hints similar to lightweight parser
  const warnings = [...full.warnings];
  rows.forEach((tx, i) => {
    if (tx.swift_mt) {
      const missingFields: string[] = [];
      if (!tx.swift_f50_present) missingFields.push("swift_f50_present (Ordering Customer)");
      if (!tx.swift_f59_present) missingFields.push("swift_f59_present (Beneficiary Customer)");
      if (!tx.swift_f70_purpose) missingFields.push("swift_f70_purpose (Purpose)");
      if (!tx.swift_f71_charges) missingFields.push("swift_f71_charges (Charges)");
      if (!tx.ordering_institution_bic) missingFields.push("ordering_institution_bic");
      if (!tx.beneficiary_institution_bic) missingFields.push("beneficiary_institution_bic");
      if (missingFields.length) warnings.push({ row: i + 2, message: `SWIFT MT present but missing: ${missingFields.join(", ")}` });
    }
  });
  return { rows, errors: full.errors, warnings };
}

export async function parseTransactionsWithZodFromFile(file: File): Promise<{ rows: Transaction[]; errors: ParseError[]; warnings: ParseWarning[] }> {
  const text = await file.text();
  return parseTransactionsWithZodFromText(text);
}
