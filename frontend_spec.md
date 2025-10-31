# Frontend Consumption Spec (v1)

> Plain markdown overview of what the UI shows, which backend routes it calls, and what states it handles. Keep alongside your backend API list.

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
