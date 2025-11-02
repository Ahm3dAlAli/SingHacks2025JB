# Repository Guidelines

## Project Structure & Module Organization
- Root modules: `database/` (shared SQL like `init-all-dbs.sql`), `services/` (each microservice self-contained).
- Service layout: each service has its own `Dockerfile`, `docker-compose.yml`, `requirements.txt`, and README. Common code paths include `app/` or `api/`, `database/`/`db/`, `langgraph/` (agents), and `tests/` where applicable.
- Examples: `services/transaction-analysis-engine`, `services/regulatory-ingestion-engine`, `services/remediation-workflow-engine`.

## Build, Test, and Development Commands
- Run a service (Docker):
  - `cd services/<service>`
  - `docker-compose up -d --build` — build and start containers
  - `docker-compose logs -f <service_name>` — tail service logs
- Local dev (Python):
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - Start per service README (e.g., `python main.py` or `./start.sh`).
- Tests (when present):
  - In container: `docker-compose exec <service_name> pytest -q`
  - Locally: `pytest -q tests/`

## Coding Style & Naming Conventions
- Language: Python. Follow PEP 8 with 4-space indentation and 88–100 col soft wrap.
- Names: `snake_case` for files/functions, `PascalCase` for classes, constants in `UPPER_SNAKE`.
- Modules live within each service (e.g., `app/`, `api/`, `langgraph/agents/`). Keep service boundaries strict; avoid cross-service imports.
- Env files: use `.env` per service (`cp .env.example .env`). Never commit secrets.

## Testing Guidelines
- Framework: `pytest` (service-scoped). Place tests under `tests/` using `test_*.py` naming.
- Add unit tests for new modules and integration tests for new endpoints/flows.
- Example: `cd services/transaction-analysis-engine && docker-compose exec tae pytest -q`.

## Commit & Pull Request Guidelines
- Style: Prefer Conventional Commits with service scope and task id when available.
  - Examples: `feat(tae): add risk scorer [TASK-010]`, `fix(regulatory-ingestion): handle empty PDF`.
- PRs must include:
  - Clear description and motivation, affected service(s), and screenshots/log snippets or curl examples for APIs.
  - Linked issues/task IDs and checklist of tested paths.
  - Verification that `docker-compose up -d --build` succeeds for the changed service.

## Security & Configuration Tips
- Secrets: never commit `.env`; rotate API keys (e.g., Groq) and verify via service health endpoints (`/health`).
- Databases: destructive resets use `docker-compose down -v` (confirm before running).
- Ports: check conflicts with `lsof -i :<port>` if services fail to start.

