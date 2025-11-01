import { z } from "zod";

export type ScreeningStatus = "CLEAR" | "POTENTIAL_MATCH" | "HIT" | "UNKNOWN";

export interface Transaction {
  transaction_id: string;
  booking_jurisdiction: string;
  regulator: string;
  booking_datetime: string; // ISO 8601 in UI state; parse to Date where needed
  value_date: string; // ISO date (yyyy-mm-dd)
  amount: number;
  currency: string;
  channel: string;
  product_type: string;

  originator_name: string;
  originator_account: string; // mask in UI
  originator_country: string;

  beneficiary_name: string;
  beneficiary_account: string; // mask in UI
  beneficiary_country: string;

  swift_mt?: string;
  ordering_institution_bic?: string;
  beneficiary_institution_bic?: string;
  swift_f50_present?: boolean; // Ordering customer present
  swift_f59_present?: boolean; // Beneficiary customer present
  swift_f70_purpose?: string;
  swift_f71_charges?: string; // e.g., BEN/OUR/SHA
  travel_rule_complete?: boolean;

  // compliance / KYC (extend as needed)
  kyc_completed?: boolean;
  pep_flag?: boolean;
  aml_risk_score?: number;
  sanctions_screening?: ScreeningStatus | string;
  customer_id?: string;
  customer_type?: string; // e.g., individual/corporate/domiciliary_company
  customer_risk_rating?: string; // e.g., Low/Medium/High
  customer_is_pep?: boolean;
  kyc_last_completed?: string; // date-only
  kyc_due_date?: string; // date-only
  edd_required?: boolean;
  edd_performed?: boolean;
  sow_documented?: boolean;

  // Suitability / disclosures
  suitability_assessed?: boolean;
  suitability_result?: string;
  va_disclosure_provided?: boolean;
  product_has_va_exposure?: boolean;
  client_risk_profile?: string; // e.g., Low/Balanced/High
  is_advised?: boolean;
  product_complex?: boolean;

  // Cash thresholds
  daily_cash_total_customer?: number;
  daily_cash_txn_count?: number;
  cash_id_verified?: boolean;

  // Investigations
  suspicion_determined_datetime?: string | null; // ISO or null
  str_filed_datetime?: string | null; // ISO or null

  // Free text
  narrative?: string;
  purpose_code?: string;

  // FX details
  fx_indicator?: boolean; // TRUE if FX involved
  fx_base_ccy?: string;
  fx_quote_ccy?: string;
  fx_applied_rate?: number;
  fx_market_rate?: number;
  fx_spread_bps?: number;
  fx_counterparty?: string;

  // Derived client-side fields (not in CSV)
  display_direction?: "IN" | "OUT";
  display_counterparty?: string;
}

// Full transaction shape matching backend CSV/export columns
export interface TransactionFull {
  transaction_id: string;
  booking_jurisdiction: string;
  regulator: string;
  booking_datetime: string;
  value_date: string;
  amount: number;
  currency: string;
  channel: string;
  product_type: string;
  originator_name: string;
  originator_account: string;
  originator_country: string;
  beneficiary_name: string;
  beneficiary_account: string;
  beneficiary_country: string;
  swift_mt: string | null;
  ordering_institution_bic: string | null;
  beneficiary_institution_bic: string | null;
  swift_f50_present: boolean;
  swift_f59_present: boolean;
  swift_f70_purpose: string | null;
  swift_f71_charges: string | null;
  travel_rule_complete: boolean;
  fx_indicator: boolean;
  fx_base_ccy: string | null;
  fx_quote_ccy: string | null;
  fx_applied_rate: number;
  fx_market_rate: number;
  fx_spread_bps: number;
  fx_counterparty: string | null;
  customer_id: string;
  customer_type: string;
  customer_risk_rating: string;
  customer_is_pep: boolean;
  kyc_last_completed: string;
  kyc_due_date: string;
  edd_required: boolean;
  edd_performed: boolean;
  sow_documented: boolean;
  purpose_code: string;
  narrative: string;
  is_advised: boolean;
  product_complex: boolean;
  client_risk_profile: string;
  suitability_assessed: boolean;
  suitability_result: string;
  product_has_va_exposure: boolean;
  va_disclosure_provided: boolean;
  cash_id_verified: boolean;
  daily_cash_total_customer: number;
  daily_cash_txn_count: number;
  sanctions_screening: string;
  suspicion_determined_datetime: string | null;
  str_filed_datetime: string | null;
}

export const TransactionFullSchema = z.object({
  transaction_id: z.string(),
  booking_jurisdiction: z.string(),
  regulator: z.string(),
  booking_datetime: z.string(),
  value_date: z.string(),
  amount: z.number(),
  currency: z.string(),
  channel: z.string(),
  product_type: z.string(),
  originator_name: z.string(),
  originator_account: z.string(),
  originator_country: z.string(),
  beneficiary_name: z.string(),
  beneficiary_account: z.string(),
  beneficiary_country: z.string(),
  swift_mt: z.string().nullable(),
  ordering_institution_bic: z.string().nullable(),
  beneficiary_institution_bic: z.string().nullable(),
  swift_f50_present: z.boolean(),
  swift_f59_present: z.boolean(),
  swift_f70_purpose: z.string().nullable(),
  swift_f71_charges: z.string().nullable(),
  travel_rule_complete: z.boolean(),
  fx_indicator: z.boolean(),
  fx_base_ccy: z.string().nullable(),
  fx_quote_ccy: z.string().nullable(),
  fx_applied_rate: z.number(),
  fx_market_rate: z.number(),
  fx_spread_bps: z.number(),
  fx_counterparty: z.string().nullable(),
  customer_id: z.string(),
  customer_type: z.string(),
  customer_risk_rating: z.string(),
  customer_is_pep: z.boolean(),
  kyc_last_completed: z.string(),
  kyc_due_date: z.string(),
  edd_required: z.boolean(),
  edd_performed: z.boolean(),
  sow_documented: z.boolean(),
  purpose_code: z.string(),
  narrative: z.string(),
  is_advised: z.boolean(),
  product_complex: z.boolean(),
  client_risk_profile: z.string(),
  suitability_assessed: z.boolean(),
  suitability_result: z.string(),
  product_has_va_exposure: z.boolean(),
  va_disclosure_provided: z.boolean(),
  cash_id_verified: z.boolean(),
  daily_cash_total_customer: z.number(),
  daily_cash_txn_count: z.number(),
  sanctions_screening: z.string(),
  suspicion_determined_datetime: z.string().nullable(),
  str_filed_datetime: z.string().nullable(),
});
