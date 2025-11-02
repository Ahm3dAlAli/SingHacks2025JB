# Agents & Frameworks Deep Dive

## Stack Overview (What We Use)
- FastAPI: HTTP APIs per service with Pydantic models and `/health` endpoints.
- LangGraph: Multi-agent orchestration (graphs of nodes with typed state and conditional edges).
- Groq SDK: LLM/Vision calls for explanation, validation, and image analysis.
- IBM Docling: Document structure extraction (DCE).
- Celery + Redis: Background jobs and scheduling (DCE workers, batching).
- SQLAlchemy + Alembic: ORM + migrations (Postgres services); SQLite for DCE demo.
- Pytest: Unit/integration tests per service.
- Docker Compose: One stack per service for local reproducibility.

## Agent Model (LangGraph Basics)
- State: Typed dict or Pydantic model shared across nodes; holds inputs, intermediate results, and errors.
- Nodes: Pure Python callables; each does one task (parse, validate, score, explain).
- Edges: Conditional routing based on state (e.g., images → ImageAnalyzer; low risk → fast exit).
- Determinism: Prefer deterministic checks first; use LLM only for explanation/format analysis.
- Observability: Log timing per node; persist agent step logs to DB where applicable (e.g., `agent_execution_logs`).

## Service Patterns
- DCE (Document Corroboration Engine)
  - Pipeline: DocumentProcessor → FormatValidator → [ImageAnalyzer?] → RiskScorer
  - Background: Celery tasks run the pipeline; Redis as broker/result backend.
  - Inputs: file bytes + metadata. Outputs: structured text/structure, risk, audit entries.
- TAE (Transaction Analysis Engine)
  - Pipeline: RuleParser → StaticRules → BehavioralPatterns → RiskScorer → Explainer
  - Deterministic-first: thresholds, sanctions, KYC expiry in code; LLM for human explanations only.
- RWE (Remediation Workflow Engine)
  - Pipeline: Orchestrator → DecisionEngine → ContextEnricher → ActionExecutor → ComplianceChecker
  - Template-driven: choose workflow by severity/PEP/rules; append audit entries per step.
- REE (Regulatory Ingestion Engine)
  - Deterministic ingestion + NLP parsing; exposes searchable rules for TAE.

## LangGraph Skeleton (Example)
```python
# state.py
from typing import TypedDict, Optional
class DocState(TypedDict, total=False):
    file_path: str
    text: str
    structure: dict
    image_findings: dict
    risk_score: float
    errors: list[str]
```
```python
# nodes.py
from groq import Groq
client = Groq(api_key=os.environ["GROQ_API_KEY"])  # set in .env

def document_processor(state: DocState) -> DocState:
    text, structure = extract_with_docling(state["file_path"])  # deterministic
    state.update(text=text, structure=structure)
    return state

def format_validator(state: DocState) -> DocState:
    prompt = build_format_prompt(state["structure"])
    ai = client.chat.completions.create(model="llama3-70b", messages=[{"role":"user","content":prompt}])
    state.setdefault("findings", {})["format"] = parse(ai)
    return state
```
```python
# graph.py
from langgraph.graph import StateGraph
from .state import DocState
from .nodes import document_processor, format_validator, image_analyzer, risk_scorer

g = StateGraph(DocState)

g.add_node("document_processor", document_processor)
g.add_node("format_validator", format_validator)
g.add_node("image_analyzer", image_analyzer)
g.add_node("risk_scorer", risk_scorer)

# edges
g.add_edge("document_processor", "format_validator")

def needs_image_analysis(state: DocState) -> str:
    return "image_analyzer" if is_image(state["file_path"]) else "risk_scorer"

g.add_conditional_edges("format_validator", needs_image_analysis, {
    "image_analyzer": "image_analyzer",
    "risk_scorer": "risk_scorer",
})

g.add_edge("image_analyzer", "risk_scorer")
workflow = g.compile()
```

## LLM Prompting & Guardrails
- Ground inputs: pass numeric thresholds, parsed tables, and normalized fields to LLMs to reduce hallucination.
- Bounded outputs: request JSON schemas; parse and validate with Pydantic; default on parse failure.
- Retries: exponential backoff for transient LLM errors; cap by latency budgets.
- Cost control: keep context windows small; only call LLM where deterministic logic is insufficient.

## Concurrency, Reliability, and Idempotency
- DCE: Celery concurrency N workers; idempotent tasks by `document_id`; use result backend to avoid duplicate work.
- TAE: async FastAPI handlers; DB indexes on `tx_id`, `ts`; batch jobs run sequential nodes for observability.
- RWE: step retries with backoff; compensating actions on failure; workflow instance state machine persisted in DB.
- All: health checks, structured logs with correlation ids; `docker-compose up -d --build` to re-create clean stack.

## Adding a New Agent (Checklist)
1. Define state fields and validation (Pydantic/TypedDict).
2. Implement a pure node function; keep I/O at the edges (services/clients).
3. Register node + edges in `graph.py`; add conditional routing if needed.
4. Log latency and outcome; persist to agent execution logs where available.
5. Add tests: unit for node logic, integration for graph path.
6. Wire into API route and/or Celery task; document in README.

## Env & Configuration (Common)
- GROQ_API_KEY, DATABASE_URL/POSTGRES_*, REDIS_URL, LOG_LEVEL.
- Each service: copy `.env.example` → `.env`; never commit secrets.

## References (Repo)
- DCE graph/nodes: `services/document-corroboration-engine/app/agents/*`
- TAE graphs/rules: `services/transaction-analysis-engine/app/langgraph/*`
- RWE graph: `services/remediation-workflow-engine/langgraph/*`
- REE ingestion: `services/regulatory-ingestion-engine/app/*`
