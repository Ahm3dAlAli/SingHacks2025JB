BASE: /api/v1
Auth via OIDC bearer; all write routes accept Idempotency-Key; page with ?page=&limit=.

──────────────────────────
scraper-v1 (Regulatory Ingestion)
──────────────────────────
GET   /ingestion/sources                      → List sources (MAS, FINMA, HKMA, etc.)
POST  /ingestion/sources/scan                 → Trigger on-demand crawl/poll
POST  /ingestion/webhooks/{source}            → Inbound push (email/RSS/webhook)
GET   /ingestion/items                        → Raw docs (PDF/HTML/DOCX) + status
GET   /ingestion/items/{itemId}               → Raw doc metadata & fetch URL
POST  /ingestion/items/{itemId}/parse         → Extract text/meta/sections (async)
GET   /ingestion/parses/{parseId}             → Parsed result (structured doc)

──────────────────────────
rules-v1 (Rules Registry & Compile)
──────────────────────────
GET   /rules                                  → List active/inactive rule versions
POST  /rules                                  → Create rule (DSL/JSON)
POST  /rules/validate                         → Lint & dry-run rule on sample
POST  /rules/compile                          → Compile rule set → artifact hash
POST  /rules/promote                          → Activate compiled version (with approvals)
GET   /rules/{ruleId}                         → Rule detail & history
GET   /rules/versions/{versionId}/diff        → Version diff summary
POST  /rules/replay                           → Re-evaluate last N hours for regressions

──────────────────────────
tx-v1 (Transactions & Scoring)
──────────────────────────
POST  /tx/ingest                              → Batch/stream ingest (CSV/mock)
GET   /tx/{txnId}                             → Transaction detail + features
GET   /entities/{entityId}/tx                 → List entity transactions
POST  /tx/evaluate                            → Run rules on payload (sync for demo)
GET   /scores/entities/{entityId}             → Current risk score & trend

──────────────────────────
alerts-v1 (Alert Lifecycle & Routing)
──────────────────────────
GET   /alerts                                 → Filter by severity/status/entity
POST  /alerts                                 → Create alert (manual or from tx eval)
GET   /alerts/{alertId}                       → Alert detail (rule hits, links)
POST  /alerts/{alertId}/ack                   → Acknowledge
POST  /alerts/{alertId}/status                → Transition (OPEN→IN_PROGRESS→CLOSED)
POST  /alerts/{alertId}/assign                → Set assignee & SLA
POST  /alerts/{alertId}/comment               → Add note (appears in audit)
GET   /alerts/{alertId}/timeline              → Event timeline (audit view)

──────────────────────────
docs-v1 (Documents, OCR, Findings)
──────────────────────────
POST  /docs                                   → Create doc; returns signed upload URL
GET   /docs/{docId}                           → Doc meta (hash, pages, status)
POST  /docs/{docId}/process                   → Run OCR + validators + image checks
GET   /docs/{docId}/findings                  → Findings list + severities
GET   /docs/{docId}/evidence                  → Evidence bundle (hashes, EXIF, snippets)
GET   /docs/{docId}/score                     → Risk score & rationale

──────────────────────────
integrations-v1 (Cross-linking & Cases)
──────────────────────────
POST  /alerts/{alertId}/link-doc/{docId}      → Link doc to alert
GET   /cases                                  → List unified cases (alert+docs)
GET   /cases/{caseId}                         → Case bundle (summary, assets)
POST  /cases/{caseId}/escalate                → Escalate (P1/P2) with reason

──────────────────────────
remediation-v1 (Actions & Templates)
──────────────────────────
GET   /remediation/templates                  → List actions (EDD, Re-KYC, block)
POST  /alerts/{alertId}/remediation           → Create remediation task from template
PATCH /remediation/{actionId}                 → Update status, due date, owner

──────────────────────────
reports-v1 (Exports)
──────────────────────────
POST  /reports/alert/{alertId}                → Generate PDF summary (async)
POST  /reports/case/{caseId}                  → Generate combined report (async)
GET   /reports/{reportId}                     → Download URL + status

──────────────────────────
audit-v1 (Audit & Observability)
──────────────────────────
GET   /audit                                  → Query audit by ref_type/ref_id
GET   /metrics                                → Demo metrics (latency, FPR, pass rate)
GET   /health                                 → Liveness/readiness

──────────────────────────
agent-v1 (Agentic Orchestration — optional)
──────────────────────────
POST  /agent/summarize/alert/{alertId}        → LLM summary + recommended action
POST  /agent/auto-triage                      → Batch triage; returns approve/hold/escalate
POST  /agent/learn                            → Submit human feedback for tuning

──────────────────────────
auth-v1 (Sessions & Profiles)
──────────────────────────
GET   /me                                     → Current user & roles
GET   /me/prefs                               → UI preferences
PATCH /me/prefs                                → Update prefs
WS    /ws                                     → SSE/WS: alert:created, alert:updated, doc:scored

──────────────────────────
kb-v1 (Knowledge Base / Search)
──────────────────────────
GET   /kb/search?q=&type=rule|doc|alert       → Unified search across rules, regulatory docs, alerts
GET   /kb/rules/{ruleId}                      → Parsed rule (normalized text, clauses, citations)
GET   /kb/docs/{docId}                        → Regulatory source doc (structured sections, metadata)
GET   /kb/references?alertId=...              → All citations/references linked to an alert/case

──────────────────────────
users-v1 (Users, Roles & Teams)
──────────────────────────
GET   /users                                  → List users (name, email, roles)
POST  /users                                  → Create user (admin only)
GET   /users/{userId}                         → User detail
PATCH /users/{userId}/roles                   → Update roles (Front/Compliance/Legal/Admin)
GET   /teams                                  → List teams / groups
PATCH /users/{userId}/status                  → Activate / suspend user

──────────────────────────
notify-v1 (Notifications Center)
──────────────────────────
GET   /notifications                          → List in-app notifications (paged)
PATCH /notifications/{id}/read                → Mark one notification as read
PATCH /notifications/read-all                 → Mark all as read
GET   /subscriptions                          → Current WS/SSE topics bound to user

──────────────────────────
dashboard-v1 (Aggregates & KPIs)
──────────────────────────
GET   /dashboard/summary                      → High-level KPIs (open alerts by severity, SLA breaches)
GET   /dashboard/trends?window=7d             → Time-series for alerts/doc pass-rate/latency
GET   /dashboard/my-work                      → “My” queue (assigned alerts/cases, due soon)

──────────────────────────
scheduler-v1 (Jobs, Crawls & Replays)
──────────────────────────
GET   /scheduler/jobs                         → List scheduled jobs (crawl, replay, report)
POST  /scheduler/jobs/run                     → Trigger a job now (by type/id)
GET   /scheduler/runs?jobId=...               → Recent runs with status & timings

──────────────────────────
lineage-v1 (Data Lineage & Traceability)
──────────────────────────
GET   /lineage/{objectId}                     → Upstream/downstream graph for alert/doc/rule
GET   /lineage/trace?alertId=...              → End-to-end trace (txn → rule → alert → report)

──────────────────────────
integrations-v1 (External Systems)
──────────────────────────
GET   /integrations                           → List configured integrations (Jira, Slack, ServiceNow)
POST  /integrations/{type}/sync               → Push object to external system (e.g., create Jira)
GET   /integrations/{type}/status/{extId}     → Sync status / deep link to external ticket

──────────────────────────
agent-v1 (Agentic Orchestration — extensions)
──────────────────────────
POST  /agent/explain/{alertId}                → Human-readable rationale (rules, evidence, doc issues)
POST  /agent/feedback                         → Record human decision (approve/reject/override + reason)
POST  /agent/tune                             → Propose threshold/rule-weight adjustments from feedback
