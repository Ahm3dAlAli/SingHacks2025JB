# Architecture Overview

This is a Next.js App Router project with two route groups, client-side mock auth, and mock API routes to simulate an alerts platform with agentic helpers.

## High-Level
```
Browser
  ├─ (marketing) layout ── /  /login (Header)
  └─ (app) layout (Sidebar) ── /dashboard /alerts /alerts/[id] /entities /entities/[id] /transactions /regulatory-updates /rules
                               │
                               └── calls mock API routes (Next Route Handlers)
```

## UI Layers
- Marketing: `app/(marketing)` shows the landing page and login.
- App: `app/(app)` includes a shadcn-style sidebar and all authenticated pages.
- Auth: client-side token in `localStorage`; `useSyncExternalStore` hook (`lib/use-auth.ts`) keeps SSR/CSR in sync.

## Alerts Flow
- List: `/alerts` renders cards with
  - Severity/status badges, person name (from Entities), created time
  - Rule-hit badges (from detail)
  - AI summary (from `/api/agent/summarize/alert/{id}`)
  - Rationale panel (rules + evidence from `/api/agent/explain/{id}`)
  - Actions: Approve/Hold/Escalate + optional comment
  - Background button → `/entities/{entityId}`
- Detail: `/alerts/[id]` shows header info, person name, rule hits, transactions, documents, timeline, and AI summary; includes Background Check link.

## API Surface (Mock)
- Alerts (CRUD-ish + timeline): `/api/alerts/*` and limited `/api/v1/alerts/*`.
- Agent orchestration: `/api/agent/*` summarize/triage/explain/feedback/tune.
- Data: generated deterministically in `lib/mock/alerts.ts` (no persistence).

## Data Flow (example)
```
/alerts (client)
  ├─ GET /api/alerts?filters → list
  ├─ GET /api/alerts/{id} → ruleHits + risk for badges
  ├─ POST /api/agent/summarize/alert/{id} → summary + recommendation
  ├─ POST /api/agent/explain/{id} → rules + evidence
  └─ POST /api/agent/feedback + POST /api/alerts/{id}/status → action with comment
```

Background report
```
/entities (client)
  ├─ GET /api/entities → people list
  ├─ GET /api/entities/{id} → person profile
  └─ POST /api/agent/background/{id} → unconventional background report
```

Transactions
```
/transactions (client)
  ├─ GET /api/entities → entity dropdown
  ├─ GET /api/entities/{id}/tx → recent transactions for entity
  └─ POST /api/tx/evaluate → per-transaction evaluation (score/decision)
```

Regulatory updates → rules suggestions
```
/regulatory-updates (client)
  ├─ GET /api/regulatory/updates → cards
  ├─ GET /api/rules/suggestions?status=needs_review → "What’s New"
  ├─ GET /api/rules/suggestions?status=promoted → "Recently Applied"
  └─ POST /api/rules/suggestions/from-update/{updateId} → create (or reuse) suggestion and deep link to review

/action-required/[id] (client, deep link)
  ├─ GET /api/rules/suggestions/{id} → suggestion detail
  ├─ GET /api/rules/{ruleId} → full rule + history
  ├─ POST /api/rules/suggestions/{id}/validate → compile/lint
  ├─ POST /api/rules/suggestions/{id}/replay → mock impact
  ├─ POST /api/rules/suggestions/{id}/approve → creates version link
  └─ POST /api/rules/suggestions/{id}/promote → compiles + promotes artifact
```

UI behavior
- Regulatory Updates shows two summary sections at the top:
  - What’s New: pending proposals with +/- counts; Review button.
  - Recently Applied: promoted proposals with applied timestamps; View link.
- Each update card reflects its state:
  - No proposal: “Propose Rule Change” button
  - Proposed: “Review Proposal” button + “Proposed” pill
  - Applied: “View Applied” button + “Applied” pill
- The review page shows: full current rule, suggested rule, unified red/green diff with +/- header counts, structured changes, validation output, replay impact, rationale, and actions.

Data model (mock)
- `lib/mock/suggestions.ts` stores suggestions in-memory with fields: `status`, `unifiedDiff`, `structuredDiff[]`, `createdVersionId`, `compileArtifact`, `promotedAt`.
- The API deduplicates proposals per update: creating a suggestion for an update with an existing pending suggestion returns the existing one instead of creating a duplicate.

## Styling & Components
- Tailwind v4 tokens in `app/globals.css` with blue-based `--primary` theme.
- shadcn/ui primitives for sidebar, inputs, sheet, tooltip.
- `components/DiffView.tsx` renders unified diffs with red/green line highlighting and +/- counts.

## Notes
- Replace localStorage token with secure cookies and server auth for production.
- Replace mock routes with your backend; keep endpoints stable to minimize UI rewrites.
- The suggestions store is ephemeral and per-session; refreshing clears state.
