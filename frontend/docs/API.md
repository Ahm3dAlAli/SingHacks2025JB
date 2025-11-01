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
