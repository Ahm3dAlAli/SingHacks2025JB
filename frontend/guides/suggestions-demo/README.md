# User Guide (Click-Through Walkthrough)

This short guide walks you through the demo workflow end‑to‑end. Screenshots are referenced as placeholders; you can capture and drop them into `public/docs/` later.

## Prerequisites
- Install deps and start the app:
  - `pnpm install`
  - `pnpm dev`
- Open `http://localhost:3000` in your browser.

## 1) Login
- Go to `/login` and submit the mock credentials (any non-empty values work).
- You will be redirected to `/dashboard`.

![Login](../public/guides/suggestions-demo/01-login.svg)

## 2) Regulatory Updates → Propose
- Navigate to `/regulatory-updates`.
- Use filters (Authority, Search) to find an update.
- Click “Propose Rule Change” on any card.
- You’ll be redirected to the suggestion review page.

![Regulatory Updates](../public/guides/suggestions-demo/02-reg-updates.svg)

## 3) What’s New / Recently Applied
- At the top of `/regulatory-updates`, see:
  - What’s New: pending proposals with +/- counts and quick Review links.
  - Recently Applied: promoted proposals with applied time and View links.
- The “Regulatory Updates” sidebar shows a small badge with the pending count.

![What’s New and Recently Applied](../public/guides/suggestions-demo/03-new-applied.svg)

## 4) Suggestion Review (Single Page)
- On `/action-required/[id]`, review everything on one page:
  - Full Rule (Current): fetches the full rule from the Rules API.
  - Proposed Change: side-by-side current vs suggested, plus a red/green unified diff with +/- counts and structured changes.
  - Impact: replay summary (mock).
  - Validation: compile/lint output (mock).
  - Rationale: mapping context and provenance.
- Actions:
  - Validate: runs compile/lint.
  - Replay: runs mock impact.
  - Approve: marks as approved and attaches a new version id.
  - Promote: compiles and promotes a mock artifact; the suggestion moves to “Recently Applied”.

![Suggestion Review](../public/guides/suggestions-demo/04-suggestion-review.svg)

## 5) Update Cards Reflect State
- Back on `/regulatory-updates`, cards show:
  - No proposal: “Propose Rule Change”.
  - Proposed: “Proposed” pill and a “Review Proposal” button.
  - Applied: “Applied” pill and a “View Applied” button.
- Proposing on the same update while a proposal is pending reuses the existing suggestion (no duplicates).

![Card States](../public/guides/suggestions-demo/05-card-states.svg)

## 6) Other Areas (Optional)
- Alerts: `/alerts` — Alert Manager with AI summary/explain, actions, and detail pages.
- Entities: `/entities` — Background report per entity.
- Transactions: `/transactions` — Evaluate + filter transactions, links to entities.
- Rules: `/rules` — List, detail, versions diff API endpoints.

## 7) API Cheatsheet
- See `docs/API.md` for cURL examples (alerts, entities, tx, ingestion, rules, and suggestions).

## Troubleshooting
- In-memory data: Suggestions and some lists reset on page reload/server restart.
- Not found: If you deep-link to an old suggestion ID, you may see “Suggestion not found”. Create a new proposal from `/regulatory-updates`.
- Auth: Most app routes redirect to `/login` if not logged in.

---

Tip: Replace mock endpoints with your backend step-by-step while keeping the same API shapes to minimize UI changes.
