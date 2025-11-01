# Transactions Data Model & Validation

This app ingests transactions from CSV, validates them with Zod, and maps them to a UI-friendly shape for filtering and display.

## Types

- `TransactionFull` (canonical): Matches CSV/backend columns. Strict and fully typed; nullable fields use explicit `null` in CSV.
- `Transaction` (UI): Light, optional-friendly shape used by components. Adds derived fields used in tables/filters.

Key differences
- Validation: `TransactionFull` has `TransactionFullSchema` (Zod). `Transaction` has no schema.
- Nullability: `TransactionFull` uses `null` for empty optional columns; `Transaction` uses `undefined` for optional UI fields.
- Derived fields: `Transaction` includes `display_direction` and `display_counterparty`.

## Ingest Pipeline

Client (`/transactions`)
- Load CSV from `public/data/transactions_mock_1000_for_participants.csv` (or `public/data/transactions.csv`) or via file upload.
- Validate each row against `TransactionFullSchema`.
- Map to `Transaction` (adds derived direction/counterparty) for UI.
- Non-blocking “hints” warnings are generated for SWIFT completeness when `swift_mt` is present.

Server (`lib/server/txData.ts`)
- Reads CSV from `public/data`.
- Validates with the same Zod schema and maps to `Transaction`.
- Caches results for 60s.

API
- `GET /api/v1/transactions` → `{ items: TransactionFull[], errors, warnings }` (server-validated).

## Dates & Normalization
- `booking_datetime`: normalized to Asia/Singapore offset (`+08:00`). Invalid values are rejected with a parse error.
- `value_date` and KYC dates: normalized to `YYYY-MM-DD` when possible; empty becomes `""` (UI treats empty as unset).

## Rule Hits & Severity (Alerts)

Severity (`computeSeverity`)
- Sanctions HIT → `critical`
- Sanctions POTENTIAL_MATCH → `high`
- AML risk score ≥ 80 → `high`; ≥ 50 → `medium`

Rule hits (`computeRuleHits`)
- Sanctions: HIT / POTENTIAL_MATCH
- Amount: high value
- PEP: `pep_flag` or `customer_is_pep`
- Travel rule: `travel_rule_complete === false`
- VA exposure: `product_has_va_exposure` and `va_disclosure_provided === false`
- SWIFT: missing `F50/F59/F70/F71` when `swift_mt` present; missing BICs shown as hints in UI
- KYC/EDD: overdue `kyc_due_date`, `edd_required` without `edd_performed`, `sow_documented === false`
- FX: wide `fx_spread_bps`
- Cash: high `daily_cash_total_customer`, high `daily_cash_txn_count`, `cash_id_verified === false`
- Timing: weekend or out-of-business-hours `booking_datetime`

Note: thresholds are demo defaults (e.g., amount > 100k, FX spread > 50 bps) and can be tuned.

## Adjusting Validation
- Edit `types/transaction.ts` to change `TransactionFull` and `TransactionFullSchema`.
- If the CSV omits some columns you want to accept, relax those schema fields using `.optional()` or allow `null`.

## Mapping to UI
- `toClientTransaction(f: TransactionFull): Transaction` handles `null`→`undefined` and computes:
  - `display_direction`: `IN` if `amount >= 0`, else `OUT`.
  - `display_counterparty`: originator or beneficiary depending on direction; falls back to masked account.
## KYC Profile (derived)
- Fields are inferred from transactions on `/api/agent/background/{id}`:
  - type: "Private Individual" vs "Corporate" (name heuristic)
  - pep: true if any transaction flagged PEP
  - adverseMedia / adverseInformation: true if sanctions HIT or POTENTIAL_MATCH present
  - reputationalRisk: low/medium/high (based on sanctions/AML score)
  - reasonPurpose: most frequent `swift_f70_purpose`/`purpose_code` or first `narrative`
  - businessActivities: top channels
  - sourceOfWealth: "Documented" if any `sow_documented`; else "Not documented"
  - assetBreakdown: totals by currency
  - sourceOfIncome: unknown in MVP

