# Project Documentation

This frontend implements a marketing site and an authenticated app shell with a mock Alerts workflow and agentic endpoints for demos.

## Overview
- Landing: Marketing copy with blue brand palette and CTAs (`/`).
- Auth: Mock login saves a token; redirects authenticated users to `/dashboard`.
- Layouts: Route groups — `(marketing)` for site pages, `(app)` for authenticated UI with shadcn sidebar.
- Alerts Manager (`/alerts`): Card layout with severity/status, rule-hit badges, AI summary, and always-on rationale (rules + evidence). Users can Approve, Hold, or Escalate with comments; actions also post feedback.
- Alert Detail (`/alerts/[alertId]`): Summary cards, rule hits, transactions, documents, timeline, and AI summary section.

## Routing
- Marketing: `/` (home), `/login` (mock login).
- App: `/dashboard`, `/alerts`, `/alerts/[alertId]`.

## Mock APIs
- Alerts: `GET /api/alerts`, `POST /api/alerts`, `GET /api/alerts/{id}`, `POST /api/alerts/{id}/ack`, `POST /api/alerts/{id}/status`, `POST /api/alerts/{id}/assign`, `POST /api/alerts/{id}/comment`, `GET /api/alerts/{id}/timeline`.
- Agent orchestration: `POST /api/agent/summarize/alert/{id}`, `POST /api/agent/auto-triage`, `POST /api/agent/learn`, `POST /api/agent/explain/{id}`, `POST /api/agent/feedback`, `POST /api/agent/tune`.

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

## Contributor Guide
See AGENTS.md for structure, style, and contribution standards:
- ../AGENTS.md

## More Docs
- API Cheatsheet: ./API.md
- Architecture: ./ARCHITECTURE.md
