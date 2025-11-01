# Project Documentation

This frontend implements a marketing site and an authenticated app shell with a mock Alerts workflow and agentic endpoints for demos.

## Overview
- Landing: Marketing copy with blue brand palette and CTAs (`/`).
- Auth: Mock login saves a token; redirects authenticated users to `/dashboard`.
- Layouts: Route groups — `(marketing)` for site pages, `(app)` for authenticated UI with shadcn sidebar.
- Alerts Manager (`/alerts`): Card layout with severity/status, rule-hit badges, AI summary, and always-on rationale (rules + evidence). Users can Approve, Hold, or Escalate with comments; actions also post feedback.
- Alert Detail (`/alerts/[alertId]`): Summary cards, rule hits, transactions, documents, timeline, and AI summary section; links to Background Check for the entity.
- KYC (`/kyc`): Clients directory derived from transaction counterparties. One-card-per-row layout shows clear badges (Type: PI/Corporate, PEP, Reputational, Adverse media, Last seen) with mini metrics (Txns/Inflow/Outflow/Net), Sanctions summary, and top counterparties. Detail page adds a KYC Profile and linked documents.
- Transactions (`/transactions`): CSV-driven transaction list with Zod-validated ingest, filters, sorting, and export. Loads from `public/data/transactions_mock_1000_for_participants.csv` (or `public/data/transactions.csv`) or file upload.
- Regulatory Updates (`/regulatory-updates`): Filter by authority and search titles/summaries; view cards with source links and tags. Propose rule changes from an update. Top of page shows “What’s New” (pending proposals) and “Recently Applied” (promoted changes) with +/- counts and quick links.
- Suggestion Review: After you click "Propose Rule Change" on a regulatory update, you are redirected to a dedicated review page for that suggestion (deep link). The page shows the full current rule, the proposed rule, a red/green unified diff with +/- counts, structured changes, impact, validation output, and rationale; actions include Validate, Replay, Approve, Reject, and Promote.
- Rules (`/rules`): View sample rules (API-first for now). See Rules registry endpoints in API Cheatsheet.

## Routing
- Marketing: `/` (home), `/login` (mock login).
- App: `/dashboard`, `/alerts`, `/alerts/[alertId]`, `/kyc`, `/kyc/[entityId]`, `/transactions`, `/regulatory-updates`, `/rules`.

## Mock APIs
- Alerts: `GET /api/alerts`, `POST /api/alerts`, `GET /api/alerts/{id}`, `POST /api/alerts/{id}/ack`, `POST /api/alerts/{id}/status`, `POST /api/alerts/{id}/assign`, `POST /api/alerts/{id}/comment`, `GET /api/alerts/{id}/timeline`.
- Clients/KYC: `GET /api/entities`, `GET /api/entities/{id}`.
- Agent orchestration: `POST /api/agent/summarize/alert/{id}`, `POST /api/agent/auto-triage`, `POST /api/agent/learn`, `POST /api/agent/explain/{id}`, `POST /api/agent/feedback`, `POST /api/agent/tune`, `POST /api/agent/background/{id}`.
- Regulatory ingestion: `GET /api/ingestion/sources`, `POST /api/ingestion/sources/scan`, `POST /api/ingestion/webhooks/{source}`, `GET /api/ingestion/items`, `GET /api/ingestion/items/{itemId}`, `POST /api/ingestion/items/{itemId}/parse`, `GET /api/ingestion/parses/{parseId}`.
- Rules registry: `GET /api/rules`, `POST /api/rules`, `POST /api/rules/validate`, `POST /api/rules/compile`, `POST /api/rules/promote`, `GET /api/rules/{ruleId}`, `GET /api/rules/versions/{versionId}/diff`, `POST /api/rules/replay`.
 - Transactions (validated): `GET /api/v1/transactions` → parses server-side CSV with Zod and returns validated `TransactionFull[]` with `errors` and `warnings`.
 - Documentation Review: `POST /api/docs/upload`, `GET /api/docs/review?role=…`, `GET/POST /api/docs/items/{id}`, `GET /api/docs/by-entity/{entityId}`, `GET /api/docs/list`, `GET /api/docs/{slug}`.

Example: create a demo alert
```
curl -X POST /api/alerts -H 'Content-Type: application/json' \
  -d '{"entity":"Entity-1","severity":"medium"}'
```

## Development
- Start: `pnpm dev`
- Build: `pnpm build` then `pnpm start`
- Lint: `pnpm lint`

## Notes
- Auth is client-side via `localStorage` token; `/login` redirects to `/dashboard` on success.
- Color tokens live in `app/globals.css`. Sidebar/components use Tailwind + shadcn primitives.
- Transactions are validated against a strict Zod schema (`TransactionFullSchema`) at ingest. UI maps to a lighter `Transaction` type for display and filtering.
- Suggestions are stored in-memory for demo only; refresh clears state. Creating a proposal for the same update reuses any existing pending suggestion (no duplicates).
 - RBAC roles (footer switcher): `relationship_manager` (uploads, alert actions), `compliance_manager` (alert actions, doc review), `legal` (doc final review).

## Contributor Guide
See AGENTS.md for structure, style, and contribution standards:
- ../AGENTS.md

## More Docs
- API Cheatsheet: ./API.md
- Architecture: ./ARCHITECTURE.md
- Transactions & Data Model: ./DATA.md
- User Guide: ../guides/suggestions-demo/README.md
