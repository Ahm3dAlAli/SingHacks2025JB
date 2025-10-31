# Frontend Consumption Spec (v1)

> Plain markdown overview of what the UI shows, which backend routes it calls, and what states it handles. Keep alongside your backend API list.

---

## Platform & Conventions

* **BASE:** `/api/v1`
* **Auth:** OIDC Bearer token.
* **Idempotency:** All write routes accept `Idempotency-Key` header.
* **Pagination:** `?page=&limit=` on list routes.
* **Realtime Transport:** `WS/SSE /api/v1/ws` emitting `alert:created`, `alert:updated`, `doc:scored`. UI shows degraded banner and auto-polls on disconnect.

---

## Screens

### 1) **Login / Session**

* Shows: “Sign in”, loading spinner.
* Uses: `GET /api/v1/me`
* States: `unauthenticated` → `authenticated`
* Actions: Redirect to Dashboard on success.

### 2) **Dashboard**

* Shows: Alert list (severity, status, client, created_at), filters, quick stats.
* Uses: `GET /api/v1/alerts`
* Realtime: `WS alert:created`, `WS alert:updated`
* States: `loading`, `ready (results)`, `empty`, `error`

### 3) **Alert Detail**

* Shows: header (risk, severity, status), rule hits, txn list, linked documents, timeline.
* Uses: `GET /api/v1/alerts/{alertId}`, `GET /api/v1/alerts/{alertId}/timeline`
* Actions: `POST /api/v1/alerts/{alertId}/ack`, `POST /api/v1/alerts/{alertId}/status`, `POST /api/v1/alerts/{alertId}/comment`
* Realtime: `WS alert:updated`
* States: `loading`, `ready`, `updating`, `error`

### 4) **Documents**

* Shows: document list or single document view, findings, evidence, score.
* Uses:

  * List/meta: `GET /api/v1/docs/{docId}`
  * Findings: `GET /api/v1/docs/{docId}/findings`
  * Evidence: `GET /api/v1/docs/{docId}/evidence`
  * Score: `GET /api/v1/docs/{docId}/score`
* Actions:

  * Create/upload: `POST /api/v1/docs` → upload → `POST /api/v1/docs/{docId}/process`
* Realtime: `WS doc:scored`
* States: `uploading`, `processing`, `review`, `passed/failed`, `error`

### 5) **Linking (Doc ↔ Alert)**

* Shows: picker to attach documents to an alert, confirmation.
* Uses: `POST /api/v1/alerts/{alertId}/link-doc/{docId}`
* States: `ready`, `linking`, `linked`, `error`

### 6) **Cases & Remediation**

* Shows: case board (owner, SLA, status), remediation actions.
* Uses: `GET /api/v1/cases`, `GET /api/v1/cases/{caseId}`, `GET /api/v1/remediation/templates`
* Actions: `POST /api/v1/alerts/{alertId}/remediation`, `PATCH /api/v1/remediation/{actionId}`
* States: `loading`, `ready`, `updating`, `error`

### 7) **Reports**

* Shows: generate/download report for alert or case.
* Uses: `POST /api/v1/reports/alert/{alertId}`, `POST /api/v1/reports/case/{caseId}`, `GET /api/v1/reports/{reportId}`
* States: `queued`, `generating`, `ready (download)`, `error`

### 8) **Rules (Read-only for most users)**

* Shows: active rules, versions, diffs.
* Uses: `GET /api/v1/rules`, `GET /api/v1/rules/{ruleId}`, `GET /api/v1/rules/versions/{versionId}/diff`
* States: `loading`, `ready`, `empty`, `error`

### 9) **Admin (optional)**

* Shows: import/validate/promote rule, replays.
* Uses: `POST /api/v1/rules/validate`, `POST /api/v1/rules/compile`, `POST /api/v1/rules/promote`, `POST /api/v1/rules/replay`
* States: `ready`, `validating`, `promoting`, `error`

---

## Realtime Events (UI reacts)

* `alert:created` → Prepend to Dashboard list; show toast.
* `alert:updated` → Patch Alert Detail; refresh Dashboard row.
* `doc:scored` → Update Document view (score, findings); surface banner on linked alert.

---

## Filters & Sorting (Dashboard)

* Filters: severity, status, assignee, client, date range.
* Query params: passed to `GET /api/v1/alerts`.
* Sort: created_at desc (default), risk desc (toggle).

---

## User Actions (one-liners)

* **Acknowledge alert** → `POST /alerts/{id}/ack`
* **Change alert status** → `POST /alerts/{id}/status`
* **Comment on alert** → `POST /alerts/{id}/comment`
* **Upload document** → `POST /docs` → upload → `POST /docs/{id}/process`
* **Link document to alert** → `POST /alerts/{alertId}/link-doc/{docId}`
* **Create remediation** → `POST /alerts/{id}/remediation`
* **Generate report** → `POST /reports/alert/{id}` or `/reports/case/{id}`

---

## UI States & Empty/Error Messages

* **Loading:** skeleton rows/panels.
* **Empty:**

  * Dashboard: “No alerts match your filters.”
  * Documents: “No findings yet — processing or not started.”
* **Error:** compact inline banner with retry.
* **Degraded:** banner when realtime disconnected; auto-poll fallback.

---

## Roles & Visibility (RBAC)

* **Front/RM:** Dashboard, Alert Detail, link docs, acknowledge.
* **Compliance:** All above + Documents, Cases, Remediation, Reports.
* **Legal:** Read-only across alerts/cases; rule references; approve exceptions.
* **Admin:** Rules management, replays, promotions.

---

## Quick Navigation Model

* Global nav: **Dashboard · Documents · Cases · Reports · Rules**
* Right-side drawer for **Alert Detail** and **Document Review** to keep context.
* Consistent top bar for severity filter + search.

---

## Notifications

* In-app toasts for: new P1 alert, doc scored, remediation assigned.
* (Optional) Email/ticketing for escalations triggered server-side.

---

## Reporting (what appears in the PDF)

* Header: entity, alert id, timestamps, actors.
* Sections: rule hits, transaction excerpts, linked documents + findings.
* Summary: recommended action, final decision, signatures.

---

## Audit Surfacing (read-only)

* Timeline component shows user/system events from `GET /audit?ref=...`
* Always visible in **Alert Detail** and **Case** views.

---

## Minimal Acceptance (Frontend)

* See alerts stream into Dashboard without refresh.
* Open alert → view rule hits, link a doc, see doc score auto-appear.
* Acknowledge alert and generate a report from the same session.

---

## Backend Modules → UI Hooks (added)

**scraper-v1 (Regulatory Ingestion)**

* UI: Admin > Jobs (manual scan), KB Docs preview drawers.
* Routes: `GET /ingestion/sources`, `POST /ingestion/sources/scan`, `POST /ingestion/webhooks/{source}`, `GET /ingestion/items`, `GET /ingestion/items/{itemId}`, `POST /ingestion/items/{itemId}/parse`, `GET /ingestion/parses/{parseId}`.

**rules-v1 (Rules Registry & Compile)**

* UI: Rules page (list, versions, diffs); Admin promote/validate; Replay from Admin > Jobs.
* Routes: `GET/POST /rules`, `POST /rules/validate`, `POST /rules/compile`, `POST /rules/promote`, `GET /rules/{ruleId}`, `GET /rules/versions/{versionId}/diff`, `POST /rules/replay`.

**tx-v1 (Transactions & Scoring)**

* UI: Alert Detail → transaction list; Entity drawer.
* Routes: `POST /tx/ingest`, `GET /tx/{txnId}`, `GET /entities/{entityId}/tx`, `POST /tx/evaluate`, `GET /scores/entities/{entityId}`.

**alerts-v1 (Alert Lifecycle & Routing)**

* UI: Dashboard, Alert Detail, assign/SLA, comments, timeline.
* Routes: `GET/POST /alerts`, `GET /alerts/{alertId}`, `POST /alerts/{alertId}/ack`, `POST /alerts/{alertId}/status`, `POST /alerts/{alertId}/assign`, `POST /alerts/{alertId}/comment`, `GET /alerts/{alertId}/timeline`.

**docs-v1 (Documents, OCR, Findings)**

* UI: Documents list & review drawer; Evidence tab on doc detail & alert linkouts.
* Routes: `POST /docs`, `GET /docs/{docId}`, `POST /docs/{docId}/process`, `GET /docs/{docId}/findings`, `GET /docs/{docId}/evidence`, `GET /docs/{docId}/score`.

**integrations-v1 (Cross-linking & Cases)**

* UI: Link Doc to Alert action; Cases board; Case detail.
* Routes: `POST /alerts/{alertId}/link-doc/{docId}`, `GET /cases`, `GET /cases/{caseId}`, `POST /cases/{caseId}/escalate`.

**remediation-v1 (Actions & Templates)**

* UI: Remediation panel in Alert Detail & Case; templates picker.
* Routes: `GET /remediation/templates`, `POST /alerts/{alertId}/remediation`, `PATCH /remediation/{actionId}`.

**reports-v1 (Exports)**

* UI: Reports page and inline Generate in Alert/Case.
* Routes: `POST /reports/alert/{alertId}`, `POST /reports/case/{caseId}`, `GET /reports/{reportId}`.

**audit-v1 (Audit & Observability)**

* UI: Timeline components; Admin > Observability.
* Routes: `GET /audit`, `GET /metrics`, `GET /health`.

**agent-v1 (Agentic Orchestration — core & extensions)**

* UI: "AI Reasoning" pane with Explain, Summary, and Approve/Reject; Auto-triage demo.
* Routes: `POST /agent/summarize/alert/{alertId}`, `POST /agent/auto-triage`, `POST /agent/learn`, `POST /agent/explain/{alertId}`, `POST /agent/feedback`, `POST /agent/tune`.

**auth-v1 (Sessions & Profiles)**

* UI: Login; Profile/Prefs page.
* Routes: `GET /me`, `GET /me/prefs`, `PATCH /me/prefs`, `WS/SSE /ws`.

**kb-v1 (Knowledge Base / Search)**

* UI: Global search bar; rule/doc preview drawers; alert references tab.
* Routes: `GET /kb/search`, `GET /kb/rules/{ruleId}`, `GET /kb/docs/{docId}`, `GET /kb/references`.

**users-v1 (Users, Roles & Teams)**

* UI: Admin > Users; role matrix; suspend/reactivate.
* Routes: `GET/POST /users`, `GET /users/{userId}`, `PATCH /users/{userId}/roles`, `GET /teams`, `PATCH /users/{userId}/status`.

**notify-v1 (Notifications Center)**

* UI: Bell menu + Notifications page.
* Routes: `GET /notifications`, `PATCH /notifications/{id}/read`, `PATCH /notifications/read-all`, `GET /subscriptions`.

**dashboard-v1 (Aggregates & KPIs)**

* UI: Dashboard summary tiles and trend charts; My Work.
* Routes: `GET /dashboard/summary`, `GET /dashboard/trends?window=7d`, `GET /dashboard/my-work`.

**scheduler-v1 (Jobs, Crawls & Replays)**

* UI: Admin > Jobs; "Run now" buttons; Recent runs drawer.
* Routes: `GET /scheduler/jobs`, `POST /scheduler/jobs/run`, `GET /scheduler/runs`.

**lineage-v1 (Data Lineage & Traceability)**

* UI: "View lineage" button on Alert/Doc; Trace view.
* Routes: `GET /lineage/{objectId}`, `GET /lineage/trace`.

**integrations-v1 (External Systems)**

* UI: "Create external ticket" action + backlink chip.
* Routes: `GET /integrations`, `POST /integrations/{type}/sync`, `GET /integrations/{type}/status/{extId}`.

---

## Tiny Frontend Hooks (where these show up)

* **Knowledge Search** → global search bar; rule/doc preview drawers.
* **Users & Roles** → Admin > Users page; who-can-see-what matrix.
* **Notifications** → bell menu + “All notifications” page.
* **Dashboard KPIs** → top summary tiles + trend charts on Dashboard.
* **Scheduler** → Admin > Jobs; manual “Run now” for demo.
* **Lineage** → “View lineage” button on Alert/Document detail.
* **Integrations** → “Create external ticket” action; show back-links.
* **Agent Explain/Feedback** → “AI Reasoning” pane + Approve/Reject buttons.
