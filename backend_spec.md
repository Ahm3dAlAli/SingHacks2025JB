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
