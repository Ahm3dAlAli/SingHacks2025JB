# Architecture Overview

This is a Next.js App Router project with two route groups, client-side mock auth, and mock API routes to simulate an alerts platform with agentic helpers.

## High-Level
```
Browser
  ├─ (marketing) layout ── /  /login (Header)
  └─ (app) layout (Sidebar) ── /dashboard /alerts /alerts/[id]
                               │
                               └── calls mock API routes (Next Route Handlers)
```

## UI Layers
- Marketing: `app/(marketing)` shows the landing page and login.
- App: `app/(app)` includes a shadcn-style sidebar and all authenticated pages.
- Auth: client-side token in `localStorage`; `useSyncExternalStore` hook (`lib/use-auth.ts`) keeps SSR/CSR in sync.

## Alerts Flow
- List: `/alerts` renders cards with
  - Severity/status badges, entity/created time
  - Rule-hit badges (from detail)
  - AI summary (from `/api/agent/summarize/alert/{id}`)
  - Rationale panel (rules + evidence from `/api/agent/explain/{id}`)
  - Actions: Approve/Hold/Escalate + optional comment
- Detail: `/alerts/[id]` shows header info, rule hits, transactions, documents, timeline, and on-demand AI summary.

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

## Styling & Components
- Tailwind v4 tokens in `app/globals.css` with blue-based `--primary` theme.
- shadcn/ui primitives for sidebar, inputs, sheet, tooltip.

## Notes
- Replace localStorage token with secure cookies and server auth for production.
- Replace mock routes with your backend; keep endpoints stable to minimize UI rewrites.
