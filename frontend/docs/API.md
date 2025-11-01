# API Cheatsheet (Mock)

All endpoints are mocked via Next.js route handlers and return deterministic data for demos.

Base URL when running locally: `http://localhost:3000`

## Alerts Lifecycle
- List alerts
```
curl \
  'http://localhost:3000/api/alerts?severity=high&status=new'
```
- Create alert (manual)
```
curl -X POST 'http://localhost:3000/api/alerts' \
  -H 'Content-Type: application/json' \
  -d '{"entity":"Entity-1","severity":"medium"}'
```
- Get alert detail
```
curl 'http://localhost:3000/api/alerts/demo-1'
```
- Acknowledge
```
curl -X POST 'http://localhost:3000/api/alerts/demo-1/ack'
```
- Change status (OPEN→IN_PROGRESS→CLOSED)
```
curl -X POST 'http://localhost:3000/api/alerts/demo-1/status' \
  -H 'Content-Type: application/json' \
  -d '{"status":"in_progress"}'
```
- Assign SLA / Assignee
```
curl -X POST 'http://localhost:3000/api/alerts/demo-1/assign' \
  -H 'Content-Type: application/json' \
  -d '{"assignee":"analyst.1","sla":{"hours":8}}'
```
- Add comment (appears in audit)
```
curl -X POST 'http://localhost:3000/api/alerts/demo-1/comment' \
  -H 'Content-Type: application/json' \
  -d '{"text":"Investigating counterparties"}'
```
- Timeline
```
curl 'http://localhost:3000/api/alerts/demo-1/timeline'
```

## Agentic Orchestration
- Summarize alert + recommendation
```
curl -X POST 'http://localhost:3000/api/agent/summarize/alert/demo-1'
```
- Auto-triage a batch
```
curl -X POST 'http://localhost:3000/api/agent/auto-triage' \
  -H 'Content-Type: application/json' \
  -d '{"alertIds":["demo-1","demo-2"]}'
```
- Explain rationale (rules, evidence, doc issues)
```
curl -X POST 'http://localhost:3000/api/agent/explain/demo-1'
```
- Record human feedback (approve/hold/escalate)
```
curl -X POST 'http://localhost:3000/api/agent/feedback' \
  -H 'Content-Type: application/json' \
  -d '{"id":"demo-1","decision":"escalate","reason":"PEP match"}'
```
- Submit learning payload (free-form)
```
curl -X POST 'http://localhost:3000/api/agent/learn' \
  -H 'Content-Type: application/json' \
  -d '{"labels":[{"id":"demo-1","decision":"approve"}]}'
```
- Propose tuning from signals
```
curl -X POST 'http://localhost:3000/api/agent/tune' \
  -H 'Content-Type: application/json' \
  -d '{"signals":[{"name":"Velocity anomaly","outcome":"escalate"}]}'
```

## Notes
- v1 aliases for detail + timeline also exist at `/api/v1/alerts/{id}` and `/api/v1/alerts/{id}/timeline`.
- All data is ephemeral and per-request only (no DB).

## Entities & Background Reports
- List clients
```
curl 'http://localhost:3000/api/entities'
```
- Get client profile
```
curl 'http://localhost:3000/api/entities/p-1'
```
- Generate background summary + KYC profile (derived)
```
curl -X POST 'http://localhost:3000/api/agent/background/p-1'
```
- List documents linked to a client
```
curl 'http://localhost:3000/api/docs/by-entity/p-1'
```

## Transactions
- Validate server-side and return full rows
```
curl 'http://localhost:3000/api/v1/transactions'
```

## Regulatory Updates
- List updates (optional filters `authority`, `q`)
```
curl 'http://localhost:3000/api/regulatory/updates?authority=MAS&q=aml'
```

## Rule Suggestions (from Regulatory Updates)
- Generate suggestion from update
```
curl -X POST 'http://localhost:3000/api/rules/suggestions/from-update/reg-1'
```
- Note: If a pending suggestion already exists for the same update, this returns the existing one (no duplicate).
- List suggestions (pending review)
```
curl 'http://localhost:3000/api/rules/suggestions?status=needs_review'
```
- Filter suggestions by updateId
```
curl 'http://localhost:3000/api/rules/suggestions?status=promoted&updateId=reg-1'
```
- Suggestion detail
```
curl 'http://localhost:3000/api/rules/suggestions/sug-abc123'
```
- Validate suggestion
```
curl -X POST 'http://localhost:3000/api/rules/suggestions/sug-abc123/validate'
```
- Replay impact
```
curl -X POST 'http://localhost:3000/api/rules/suggestions/sug-abc123/replay'
```
- Approve / Reject / Promote
```
curl -X POST 'http://localhost:3000/api/rules/suggestions/sug-abc123/approve'
curl -X POST 'http://localhost:3000/api/rules/suggestions/sug-abc123/reject'
curl -X POST 'http://localhost:3000/api/rules/suggestions/sug-abc123/promote'
```
Response fields
- `status`: one of `needs_review | approved | rejected | promoted`
- `unifiedDiff`: string (rendered with red/green highlights in UI)
- `structuredDiff[]`: semantic change hints (e.g., threshold from/to)
- `createdVersionId`: set on approve for diff linkage
- `compileArtifact` + `promotedAt`: set on promote

## Scraper / Ingestion
- List sources
```
curl 'http://localhost:3000/api/ingestion/sources'
```
- Trigger scan
```
curl -X POST 'http://localhost:3000/api/ingestion/sources/scan'
```
- Inbound webhook (mock)
```
curl -X POST 'http://localhost:3000/api/ingestion/webhooks/mas' -H 'Content-Type: application/json' -d '{"id":"abc"}'
```
- List items
```
curl 'http://localhost:3000/api/ingestion/items'
```
- Item detail
```
curl 'http://localhost:3000/api/ingestion/items/mas-item-1'
```
- Parse item (async mock → returns parseId)
```
curl -X POST 'http://localhost:3000/api/ingestion/items/mas-item-1/parse'
```
- Get parsed result
```
curl 'http://localhost:3000/api/ingestion/parses/parse-1234'
```

## Rules Registry
- List rules
```
curl 'http://localhost:3000/api/rules'
```
- Create rule (mock)
```
curl -X POST 'http://localhost:3000/api/rules' -H 'Content-Type: application/json' -d '{"name":"High Amount","dsl":"rule when amount > 10000 then score 10"}'
```
- Validate rule
```
curl -X POST 'http://localhost:3000/api/rules/validate' -H 'Content-Type: application/json' -d '{"dsl":"rule ..."}'
```
- Compile rule set
```
curl -X POST 'http://localhost:3000/api/rules/compile' -H 'Content-Type: application/json' -d '{"rules":["rule-1","rule-2"]}'
```
- Promote compiled artifact
```
curl -X POST 'http://localhost:3000/api/rules/promote' -H 'Content-Type: application/json' -d '{"artifact":"art-xyz"}'
```
- Rule detail & history
```
curl 'http://localhost:3000/api/rules/rule-1'
```
- Version diff
```
curl 'http://localhost:3000/api/rules/versions/v-rule-1-1/diff'
```
- Replay last N hours
```
curl -X POST 'http://localhost:3000/api/rules/replay' -H 'Content-Type: application/json' -d '{"hours":6}'
```

## Regulatory Ingestion (scraper-v1)
- List sources
```
curl 'http://localhost:3000/api/ingestion/sources'
```
- Trigger on-demand crawl/poll
```
curl -X POST 'http://localhost:3000/api/ingestion/sources/scan'
```
- Inbound push (email/RSS/webhook)
```
curl -X POST 'http://localhost:3000/api/ingestion/webhooks/mas' -H 'Content-Type: application/json' -d '{"event":"new"}'
```
- List raw items
```
curl 'http://localhost:3000/api/ingestion/items'
```
- Get item
```
curl 'http://localhost:3000/api/ingestion/items/mas-item-1'
```
- Parse item → returns parseId
```
curl -X POST 'http://localhost:3000/api/ingestion/items/mas-item-1/parse'
```
- Get parsed result
```
curl 'http://localhost:3000/api/ingestion/parses/parse-123'
```

## Rules Registry (rules-v1)
- List rules
```
curl 'http://localhost:3000/api/rules'
```
- Create rule
```
curl -X POST 'http://localhost:3000/api/rules' -H 'Content-Type: application/json' -d '{"name":"My Rule","dsl":"rule ..."}'
```
- Validate rule
```
curl -X POST 'http://localhost:3000/api/rules/validate' -H 'Content-Type: application/json' -d '{"dsl":"rule ..."}'
```
- Compile ruleset
```
curl -X POST 'http://localhost:3000/api/rules/compile' -H 'Content-Type: application/json' -d '{"rules":["rule-1","rule-2"]}'
```
- Promote compiled artifact
```
curl -X POST 'http://localhost:3000/api/rules/promote' -H 'Content-Type: application/json' -d '{"artifact":"art-abc"}'
```
- Rule detail & history
```
curl 'http://localhost:3000/api/rules/rule-1'
```
- Version diff
```
curl 'http://localhost:3000/api/rules/versions/v-rule-1-0/diff'
```
- Replay (re-evaluate window)
```
curl -X POST 'http://localhost:3000/api/rules/replay' -H 'Content-Type: application/json' -d '{"hours":6}'
```
## Documentation Review
- Upload (RM)
```
curl -X POST 'http://localhost:3000/api/docs/upload' \
  -H 'Content-Type: multipart/form-data' \
  -F 'title=Purchase Agreement' \
  -F 'entityId=p-1' \
  -F 'role=relationship_manager' \
  -F 'file=@/path/to/file.pdf;type=application/pdf'
```
- Review queue
```
curl 'http://localhost:3000/api/docs/review?role=compliance_manager'
```
- Item detail
```
curl 'http://localhost:3000/api/docs/items/abc123'
```
- Take action (approve/reject/escalate)
```
curl -X POST 'http://localhost:3000/api/docs/items/abc123' \
  -H 'Content-Type: application/json' \
  -d '{"role":"compliance_manager","action":"escalate","note":"Reverse image hit","fraud":true}'
```
- List docs (markdown) and fetch content (for browsing `/docs`)
```
curl 'http://localhost:3000/api/docs/list'
curl 'http://localhost:3000/api/docs/README'
```
