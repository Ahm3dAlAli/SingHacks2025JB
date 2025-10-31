# Transaction Analysis Engine (TAE) - Architecture Documentation

## Overview

The Transaction Analysis Engine (TAE) is a microservice within the Real-Time AML Monitoring & Alerts system. It uses LangGraph multi-agent architecture powered by Groq API to analyze financial transactions against regulatory rules and detect suspicious patterns.

**Processing Volume**: 1,000 transactions/hour (batch processing)
**Technology Stack**: Python, FastAPI, LangGraph, PostgreSQL, Docker, Groq API

---

## System Context - 4 Microservices

```
┌─────────────────────────────────────────────────────────────────┐
│                  COMPLETE SYSTEM ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────┘

Service 1: Regulatory Ingestion Engine (Port 8001)
  ├─ Crawls MAS, FINMA, HKMA regulatory sources
  ├─ Parses unstructured regulatory circulars
  ├─ Extracts actionable rules
  └─ Writes to: regulatory_rules table
      │
      │
Service 2: Transaction Analysis Engine - TAE (Port 8002) ← YOU BUILD THIS
  ├─ Reads: regulatory_rules table
  ├─ Processes: 1000 tx/hour batches
  ├─ LangGraph multi-agent analysis
  ├─ Writes: transactions, risk_assessments, agent_execution_logs
  └─ Output: Risk scores + alert triggers
      │
      │
Service 3: Alert System (Port 8003)
  ├─ Reads: risk_assessments table
  ├─ Routes alerts by role (Front Office, Compliance, Legal)
  ├─ Tailors messaging per team
  ├─ Tracks acknowledgments and SLAs
  └─ Writes: alerts table
      │
      │
Service 4: Remediation Workflows (Port 8004)
  ├─ Reads: alerts table
  ├─ Suggests automated actions
  ├─ Provides workflow templates
  └─ Writes: remediation_actions table


Shared Database: PostgreSQL (Port 5432)
  └─ All services read/write to shared schema
```

---

## TAE Layer Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    LAYER 1: API INTERFACE                        │
│  FastAPI endpoints for batch upload, status checks, results      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                  LAYER 2: BATCH PROCESSOR                        │
│  CSV ingestion, validation, deduplication, batch ID stamping     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│               LAYER 3: LANGGRAPH ORCHESTRATOR                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Agent 1: Regulatory Rule Parser                         │  │
│  │  ├─ Input: Transaction + Regulatory rules from DB        │  │
│  │  ├─ Process: Interpret natural language rules (Groq)     │  │
│  │  └─ Output: Structured rule criteria                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│          ┌──────────────────┴──────────────────┐                │
│          │                                     │                │
│  ┌───────▼──────────┐              ┌──────────▼──────────┐     │
│  │  Agent 2:        │              │  Agent 3:           │     │
│  │  Static Rules    │              │  Behavioral Pattern │     │
│  │  Engine          │              │  Analyzer           │     │
│  │                  │              │                     │     │
│  │  • Cash limits   │              │  • Velocity checks  │     │
│  │  • KYC expiry    │              │  • Smurfing         │     │
│  │  • PEP checks    │              │  • Clustering       │     │
│  │  • Sanctions     │              │  • Anomalies        │     │
│  │  • Travel rule   │              │                     │     │
│  └───────┬──────────┘              └──────────┬──────────┘     │
│          │                                     │                │
│          └──────────────────┬──────────────────┘                │
│                             │                                    │
│                   ┌─────────▼──────────┐                        │
│                   │  Agent 4:          │                        │
│                   │  Contextual Risk   │                        │
│                   │  Scorer            │                        │
│                   │                    │                        │
│                   │  • Combine signals │                        │
│                   │  • Weight factors  │                        │
│                   │  • Final score     │                        │
│                   │  • Alert level     │                        │
│                   └─────────┬──────────┘                        │
│                             │                                    │
│                   ┌─────────▼──────────┐                        │
│                   │  Agent 5:          │                        │
│                   │  Explainability    │                        │
│                   │  Agent             │                        │
│                   │                    │                        │
│                   │  • Natural lang.   │                        │
│                   │    explanation     │                        │
│                   │  • Regulatory cite │                        │
│                   │  • Evidence list   │                        │
│                   │  • Audit trail     │                        │
│                   └─────────┬──────────┘                        │
│                             │                                    │
└─────────────────────────────┼────────────────────────────────────┘
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                  LAYER 4: DATA PERSISTENCE                       │
│  Write to PostgreSQL: risk_assessments, agent_logs, audit_trail │
└──────────────────────────────────────────────────────────────────┘
```

---

## Multi-Agent Workflow (LangGraph)

### State Flow

```
Input: Transaction + Regulatory Rules
   │
   ▼
┌────────────────────────────┐
│  Agent 1: Rule Parser      │  ← Uses Groq LLM
│  Interprets NL rules       │
└────────────┬───────────────┘
             │
             ├─────────────────────────────┐
             │                             │
             ▼                             ▼
┌────────────────────────┐    ┌────────────────────────┐
│ Agent 2: Static Rules  │    │ Agent 3: Behavioral    │
│ Threshold checks       │    │ Pattern detection      │
│ (No LLM needed)        │    │ (No LLM needed)        │
└────────────┬───────────┘    └────────────┬───────────┘
             │                             │
             └─────────────┬───────────────┘
                           │
                           ▼
             ┌─────────────────────────┐
             │ Agent 4: Risk Scorer    │
             │ Combines all signals    │
             └─────────────┬───────────┘
                           │
                           ▼
             ┌─────────────────────────┐
             │ Agent 5: Explainer      │  ← Uses Groq LLM
             │ Natural language output │
             └─────────────┬───────────┘
                           │
                           ▼
                Output: Risk Score + Explanation
```

### Execution Strategy

**Sequential Steps**:
1. Rule Parser (must go first)
2. Static + Behavioral (run in parallel)
3. Risk Scorer (waits for 2 & 3)
4. Explainer (final step)

**Why this order?**
- Rule Parser provides context for other agents
- Static & Behavioral are independent (can parallelize)
- Risk Scorer needs both results
- Explainer needs final score to contextualize

---

## Agent Responsibilities

### Agent 1: Regulatory Rule Parser
**Purpose**: Convert natural language regulations into structured criteria
**Input**: Regulatory rule text from database
**Processing**: Groq LLM interprets rule conditions, thresholds, severity
**Output**: Structured JSON with rule parameters
**Groq Usage**: YES - Complex NL interpretation

---

### Agent 2: Static Rules Engine
**Purpose**: Apply threshold-based compliance checks
**Rules Coverage**:
- **HKMA/SFC (Hong Kong)**: Cash limits, PEP checks, KYC expiry
- **MAS (Singapore)**: Travel rule, sanctions screening, FX spreads
- **FINMA (Switzerland)**: Cash structuring, EDD requirements, SOW documentation
- **Global**: STR filings, virtual asset exposure

**Processing**: Rule-based logic (if/then conditions)
**Output**: List of triggered rules with severity scores
**Groq Usage**: NO - Pure logic

---

### Agent 3: Behavioral Pattern Analyzer
**Purpose**: Detect suspicious transaction patterns
**Detection Methods**:
- **Velocity Analysis**: Unusual frequency/volume
- **Smurfing Detection**: Multiple transactions below thresholds
- **Clustering**: Similar amounts, structured timing
- **Geographic Anomalies**: High-risk country pairs
- **Profile Mismatches**: Complex products for low-risk customers

**Processing**: Statistical analysis, pattern matching
**Output**: Behavioral risk flags with scores
**Groq Usage**: NO - Statistical methods

---

### Agent 4: Contextual Risk Scorer
**Purpose**: Combine all risk signals into final score
**Scoring Logic**:
- Merge static rule scores (0-100)
- Merge behavioral scores (0-100)
- Apply jurisdiction-specific weights
- Consider customer risk rating, PEP status
- Output final score (0-100) and alert level (CRITICAL/HIGH/MEDIUM/LOW)

**Alert Classification**:
- **CRITICAL** (76-100): Immediate action, possible STR
- **HIGH** (51-75): 4-hour SLA
- **MEDIUM** (26-50): 24-hour SLA
- **LOW** (0-25): Monitoring only

**Groq Usage**: NO - Mathematical aggregation

---

### Agent 5: Explainability Agent
**Purpose**: Generate audit-ready natural language explanation
**Output Includes**:
- Why alert was triggered
- Which rules were violated
- Evidence from transaction
- Regulatory citations
- Recommended next steps

**Groq Usage**: YES - Natural language generation

---

## API Endpoints

### Base URL: `http://localhost:8002/api/v1/tae`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/analyze-batch` | Upload CSV, start batch processing |
| GET | `/batch/{batch_id}/status` | Check processing progress |
| GET | `/batch/{batch_id}/results` | Get final analysis summary |
| POST | `/analyze-transaction` | Real-time single transaction analysis |
| GET | `/transaction/{tx_id}/risk-detail` | Detailed risk breakdown |
| GET | `/explain/{tx_id}` | Natural language explanation |
| GET | `/health` | Service health check |

---

## Database Schema

### Tables TAE Writes To

**transactions**
- Stores all transaction data from CSV
- Includes calculated fields (HKD/SGD/CHF equivalents)
- Raw data stored as JSONB for flexibility

**risk_assessments**
- Final risk scores per transaction
- Rules triggered (JSONB array)
- Behavioral patterns detected (JSONB array)
- Natural language explanation
- Alert level classification

**agent_execution_logs**
- Audit trail of each agent's execution
- Input/output data for debugging
- Execution time tracking
- Error logging

**audit_trail**
- System-wide audit log
- All services write here
- Tracks every action for regulatory compliance

### Tables TAE Reads From

**regulatory_rules**
- Written by Service 1 (Regulatory Ingestion)
- Contains parsed rules from HKMA/MAS/FINMA
- Versioned (effective dates, active status)

---

## Project Structure

```
transaction-analysis-engine/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
├── README.md
│
├── app/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Environment config
│   │
│   ├── api/
│   │   ├── routes.py              # API endpoints
│   │   └── models.py              # Request/response schemas
│   │
│   ├── langgraph/
│   │   ├── graph.py               # Workflow definition
│   │   ├── state.py               # Shared state
│   │   └── agents/
│   │       ├── rule_parser.py
│   │       ├── static_rules.py
│   │       ├── behavioral.py
│   │       ├── risk_scorer.py
│   │       └── explainer.py
│   │
│   ├── database/
│   │   ├── connection.py          # PostgreSQL pool
│   │   ├── models.py              # SQLAlchemy models
│   │   └── queries.py             # DB operations
│   │
│   ├── services/
│   │   ├── groq_client.py         # Groq API wrapper
│   │   └── batch_processor.py     # CSV ingestion
│   │
│   └── utils/
│       ├── logger.py
│       └── validators.py
│
├── database/
│   ├── init.sql                   # Schema creation
│   └── seed_rules.sql             # Mock regulatory rules
│
├── tests/
│   ├── test_agents.py
│   ├── test_api.py
│   └── test_data/
│
└── data/
    └── transactions_mock_1000_for_participants.csv
```

---

## Docker Architecture

```
┌─────────────────────────────────────────────────┐
│         Docker Compose Stack (TAE Dev)          │
└─────────────────────────────────────────────────┘

Container: postgres
  ├─ Image: postgres:15
  ├─ Port: 5432
  ├─ Volumes:
  │   ├─ postgres_data (persistent)
  │   └─ init.sql (schema initialization)
  └─ Health check: pg_isready

Container: tae
  ├─ Build: Dockerfile
  ├─ Port: 8002
  ├─ Depends on: postgres (healthy)
  ├─ Environment:
  │   ├─ POSTGRES_* (connection)
  │   ├─ GROQ_API_KEY
  │   └─ GROQ_MODEL
  └─ Volumes:
      ├─ ./data (transaction CSVs)
      └─ ./logs (application logs)
```

---

## Development Workflow

### Phase 1: Setup Infrastructure
1. Create PostgreSQL schema (init.sql)
2. Seed mock regulatory rules (seed_rules.sql)
3. Configure Docker Compose
4. Set up environment variables
5. Test database connectivity

### Phase 2: Build Core Components
1. Implement FastAPI skeleton
2. Create Pydantic models
3. Set up PostgreSQL connection pool
4. Build CSV batch processor
5. Create Groq API client wrapper

### Phase 3: Implement Agents
1. **Agent 2 (Static Rules)** - Start here (no LLM, quick win)
2. **Agent 3 (Behavioral)** - No LLM, pure logic
3. **Agent 4 (Risk Scorer)** - Aggregation logic
4. **Agent 1 (Rule Parser)** - First Groq integration
5. **Agent 5 (Explainer)** - Second Groq integration

### Phase 4: LangGraph Integration
1. Define TAEState class
2. Create workflow graph
3. Connect agents to graph nodes
4. Test graph execution with sample data
5. Add error handling and retries

### Phase 5: API Development
1. Implement batch upload endpoint
2. Add status checking endpoint
3. Create results retrieval endpoint
4. Build single transaction analysis
5. Add health check endpoint

### Phase 6: Testing
1. Unit tests per agent
2. Integration tests (API + DB)
3. End-to-end test with 10 transactions
4. Performance test with 1000 transactions
5. Load test for concurrent batches

### Phase 7: Demo Preparation
1. Create compelling demo scenarios
2. Prepare sample datasets
3. Build presentation flow
4. Test live demo execution
5. Prepare fallback (pre-recorded results)

---

## Key Technical Decisions

### Why LangGraph?
- Built for agent orchestration
- State management between agents
- Conditional routing support
- Easy visualization of workflow
- Production-ready error handling

### Why PostgreSQL?
- Shared database across 4 microservices
- JSONB support for flexible data storage
- Strong ACID guarantees for audit trail
- Proven reliability at scale
- Easy to query for analytics

### Why FastAPI?
- Async support (important for parallel processing)
- Auto-generated API docs (OpenAPI/Swagger)
- Type safety with Pydantic
- High performance
- Easy to test

### Why Groq?
- Extremely fast inference (important for 1000 tx/hour)
- Cost-effective for hackathon
- Simple API (OpenAI-compatible)
- Good models (Llama 3.1 70B)
- Reliable uptime

---

## Performance Targets

**Throughput**: 1,000 transactions/hour = ~17 tx/minute

**Per-Transaction Timing Budget**:
- Agent 1 (Rule Parser): ~500ms (Groq API)
- Agent 2 (Static Rules): ~50ms (pure logic)
- Agent 3 (Behavioral): ~100ms (DB query + logic)
- Agent 4 (Risk Scorer): ~20ms (math)
- Agent 5 (Explainer): ~600ms (Groq API)
- Database writes: ~50ms
- **Total**: ~1.3 seconds per transaction

**With 4 parallel workers**: 60-80 transactions/minute (exceeds target)

**Optimization Strategies**:
- Cache parsed rules (Agent 1 doesn't re-parse same rule)
- Parallel execution of Agent 2 & 3
- Batch database writes
- Connection pooling
- Async I/O throughout

---

## Demo Scenarios

### Scenario 1: Sanctions Hit (CRITICAL)
**Transaction**: Customer with potential sanctions match
**Alert Level**: CRITICAL
**Why**: MAS-SANC-001 triggered
**Action**: Immediate hold, escalate to Legal

### Scenario 2: Smurfing Pattern (HIGH)
**Transactions**: 5 cash deposits, same customer, same day, each ~HKD 7,500
**Alert Level**: HIGH
**Why**: Behavioral pattern detected (structuring)
**Action**: Enhanced Due Diligence, investigate source of funds

### Scenario 3: Expired KYC (HIGH)
**Transaction**: Large wire transfer, customer KYC expired
**Alert Level**: HIGH
**Why**: HKMA-KYC-001 triggered
**Action**: Hold transaction, update KYC immediately

### Scenario 4: Multi-Jurisdiction (MEDIUM)
**Transaction**: HK → SG → CH routing
**Alert Level**: MEDIUM
**Why**: Multiple jurisdictions, complex routing
**Action**: Review transaction purpose, verify legitimate business need

---

## Monitoring & Observability

**Metrics to Track**:
- Transactions processed per minute
- Average risk score distribution
- Alert level breakdown
- Agent execution times
- Groq API latency
- Database query performance
- Error rates per agent

**Logging Strategy**:
- Structured JSON logs
- Log level: INFO for production
- DEBUG for development
- All agent decisions logged to database
- Full audit trail for compliance

---

## Risk Mitigation

**Technical Risks**:
- **Groq API rate limits**: Implement backoff, caching
- **Database connection limits**: Use connection pooling
- **Agent failures**: Add retry logic, circuit breakers
- **Data quality issues**: Robust validation layer

**Business Risks**:
- **False positives**: Tune thresholds, feedback loop
- **False negatives**: Multi-layered detection (static + behavioral)
- **Regulatory changes**: Version-controlled rules
- **Audit requirements**: Comprehensive logging

---

## Success Metrics

**Hackathon Goals**:
- [ ] Process 1,000 transactions successfully
- [ ] Generate risk scores for all transactions
- [ ] Detect at least 50 alerts (MEDIUM+)
- [ ] Provide natural language explanations
- [ ] Complete end-to-end demo in <5 minutes
- [ ] Show multi-agent workflow visually
- [ ] Demonstrate API responses
- [ ] Prove scalability (time to process 1000 tx)

---

## Timeline Estimation

**Day 1**: Infrastructure + Database (4 hours)
**Day 2**: Agents 2, 3, 4 (6 hours)
**Day 3**: Agents 1, 5 + LangGraph (6 hours)
**Day 4**: API endpoints + Testing (6 hours)
**Day 5**: Demo prep + Polish (4 hours)

**Total**: ~26 hours of development

---

## Next Steps

1. Confirm environment setup (Docker, Groq API key)
2. Review and approve architecture
3. Create PostgreSQL schema
4. Generate mock regulatory rules
5. Start Agent 2 implementation (first deliverable)

---

**Last Updated**: 2024-10-31
**Version**: 1.0.0
**Status**: Architecture Design Phase
