# Backend Architecture — Presentation Deck

## 1) Title & Context
- Project: SingHacks 2025 — AML Intelligence Backend
- Pattern: Python microservices + LangGraph multi‑agent workflows
- Services: DCE (docs), TAE (transactions), REE (reg ingestion), RWE (remediation)

## 2) Problem & Goals
- Detect risky transactions and documents; automate remediation and audit.
- Provide auditable, API‑first services that can scale independently.
- Encode regulatory rules (HKMA, MAS, FINMA) and keep them current.

## 3) Architecture at a Glance
- Directory: `backend/services/*` (one service per folder) + `database/` shared SQL.
- Each service ships its own `Dockerfile`, `docker-compose.yml`, `requirements.txt`.
- Datastores: Postgres (TAE, REE), SQLite (DCE), Postgres (RWE).
- Orchestration: LangGraph agents + Groq LLM/Vision where applicable.

## 4) Service Overview
- DCE — Document Corroboration Engine (port 8000)
  - Validates documents (PDF/DOCX/IMG), OCR/Docling, risk scoring, audit.
- TAE — Transaction Analysis Engine (port 8002)
  - Parses rules, analyzes batches/transactions, scores risk, explains results.
- REE — Regulatory Ingestion Engine (port 8003)
  - Ingests regulatory texts, extracts rules, exposes APIs for rules/search.
- RWE — Remediation Workflow Engine (port 8004)
  - Orchestrates AML remediation workflows, audit trail, stakeholder actions.

## 5) Data Flow (High Level)
1. REE ingests/updates regulatory rules → available to TAE.
2. TAE scores transactions → emits alerts with reasons.
3. RWE receives alerts → runs multi‑agent remediation workflows and audits.
4. DCE validates user/EDD documents → risk signals feed into RWE decisions.

## 6) Key APIs (Examples)
- DCE: `POST /api/v1/documents/upload`, `GET /documents/{id}`, `GET /health` (8000)
- TAE: `POST /api/v1/tae/analyze-batch`, `GET /transaction/{tx_id}/risk-detail`, `/health` (8002)
- REE: `GET /api/docs` (Swagger), `GET /health`, rule/query endpoints (8003)
- RWE: `POST /api/v1/workflows/start`, `GET /workflows/{id}`, `/health` (8004)

## 7) Tech Stack
- Python, FastAPI, SQLAlchemy, LangGraph; Celery + Redis (DCE workers).
- Databases: Postgres (TAE, REE, RWE), SQLite (DCE demo).
- LLM/Vision: Groq LLM + Groq Vision; IBM Docling for structure extraction.

## 8) Local Run (Per Service)
```bash
cd services/<service>
cp .env.example .env  # add GROQ_API_KEY etc.
docker-compose up -d --build
docker-compose ps && curl http://localhost:<port>/health
```
- Logs: `docker-compose logs -f <service_name>`; Reset DB: `docker-compose down -v`.

## 9) Security & Compliance
- Never commit `.env`; rotate Groq keys; revoke any exposed sample keys.
- Use HTTPS, auth (JWT/API keys), rate limits in prod; size/type‑check file uploads.
- Maintain immutable audit trails (TAE/RWE/DCE) for regulator review.

## 10) Metrics & Scaling
- Throughput targets: DCE 1k docs/hr, TAE 1k tx/hr, RWE 500 workflows/day.
- Scale horizontally per service; isolate DB per service; monitor `/health` and queue depth.

## 11) Demo Script (5–7 min)
1. Start TAE and upload a CSV → show risk summary and explanation endpoint.
2. Start DCE, upload a PDF → show structure, risks, and audit trail.
3. Kick off RWE workflow with a high‑risk alert → check status + audit.
4. Open REE docs UI → show how rules flow into TAE logic.

## 12) Repo Map (Quick)
- `services/document-corroboration-engine` — DCE (FastAPI + Celery/Redis)
- `services/transaction-analysis-engine` — TAE (FastAPI + Postgres)
- `services/regulatory-ingestion-engine` — REE (FastAPI + Postgres + Alembic)
- `services/remediation-workflow-engine` — RWE (FastAPI + Postgres)
- `database/init-all-dbs.sql` — helper SQL/init

