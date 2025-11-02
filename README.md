# SingHacks2025 - Julius Baer Track - RegClock — Agentic AI for Real-Time AML Monitoring and Alerts

> **Team RegClock's AML Agentic AI Solutions** — A comprehensive, production-ready platform for Anti-Money Laundering (AML) Monitoring, Document Corroboration, and Automated Remediation Workflows

---

## 🚀 What We Built

**RegClock** is a complete end-to-end AML intelligence platform powered by multi-agent AI systems. We've created a **four-engine architecture** that seamlessly integrates regulatory ingestion, transaction analysis, document corroboration, and automated remediation workflows.

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  RegClock Platform Architecture                                     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌────────────────────┐    ┌─────────────────────┐                │
│  │ REE: Regulatory    │───▶│ TAE: Transaction    │                │
│  │ Ingestion Engine   │    │ Analysis Engine     │                │
│  │ (Port 8003)        │    │ (Port 8002)         │                │
│  └────────────────────┘    └─────────────────────┘                │
│           │                          │                              │
│           │                          ▼                              │
│           │                ┌─────────────────────┐                │
│           │                │ RWE: Remediation    │                │
│           └───────────────▶│ Workflow Engine     │                │
│                            │ (Port 8004)         │                │
│                            └─────────────────────┘                │
│                                     │                              │
│                                     ▼                              │
│                          ┌─────────────────────┐                  │
│                          │ DCE: Document       │                  │
│                          │ Corroboration Engine│                  │
│                          │ (Port 8000)         │                  │
│                          └─────────────────────┘                  │
│                                                                      │
│  Intelligence Layer: LangGraph Multi-Agent Orchestration           │
│  AI Models: Groq (Llama 3.3 70B) + IBM Docling + Vision API      │
│  Data: PostgreSQL + Redis + SQLite                                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Challenge Objectives — What We Delivered

### Part 1: Real-Time AML Monitoring ✅

**Delivered**: A complete 5-agent LangGraph workflow that processes 1,000+ transactions/hour with regulatory rule parsing, behavioral analysis, and risk scoring.

**Key Features**:
- ✅ **Regulatory Ingestion Engine (REE)**: Ingests regulations from HKMA, MAS, FINMA, BaFin; converts unstructured PDFs into structured rules with NLP
- ✅ **Transaction Analysis Engine (TAE)**: 5-agent workflow analyzing transactions against 100+ rules in real-time
  - Agent 1: Rule Parser (Groq LLM)
  - Agent 2: Static Rules Engine (Cash limits, KYC, PEP, Sanctions)
  - Agent 3: Behavioral Pattern Analyzer (Velocity, Smurfing, Clustering)
  - Agent 4: Risk Scorer (Weighted aggregation with jurisdiction multipliers)
  - Agent 5: Explainer (Audit-ready explanations with regulatory citations)
- ✅ **Alert System**: Role-based routing (RM/Compliance/Legal) with priority handling
- ✅ **Batch Processing**: CSV upload supporting 1,000+ transactions with async processing
- ✅ **Full Audit Trail**: Every agent execution logged with timing and decision rationale

### Part 2: Document & Image Corroboration ✅

**Delivered**: A multi-agent document analysis system with advanced vision AI for tamper detection and comprehensive risk scoring.

**Key Features**:
- ✅ **Document Processing Engine (DCE)**: Multi-format support (PDF, DOCX, TXT, JPG, PNG) with IBM Docling + Groq Vision
- ✅ **4-Agent Workflow**:
  - Agent 1: Document Processor (OCR + Structure Extraction)
  - Agent 2: Format Validator (AI-enhanced style checks)
  - Agent 3: Image Analyzer (Authenticity + Tampering Detection)
  - Agent 4: Risk Scorer (5-category risk breakdown)
- ✅ **Image Analysis**: Groq Vision API for authenticity, quality, content consistency, and tamper detection
- ✅ **Risk Scoring**: 5-dimensional risk assessment (Format, Content, Authenticity, Compliance, Structural)
- ✅ **Real-time Feedback**: Immediate risk reports with actionable recommendations
- ✅ **Comprehensive Audit**: Immutable audit trail for every document processed

### Integration Layer: Automated Remediation ✅

**Delivered**: A 6-agent workflow orchestrator that automatically routes high-risk alerts through compliance workflows with human-in-the-loop approvals.

**Key Features**:
- ✅ **Remediation Workflow Engine (RWE)**: Multi-agent workflow selection and execution with 4 pre-built templates
- ✅ **Workflow Templates**:
  - CRITICAL_BLOCK_WORKFLOW (immediate transaction blocking)
  - EDD_STANDARD_WORKFLOW (enhanced due diligence)
  - EDD_PEP_WORKFLOW (PEP-specific procedures)
  - LEGAL_ESCALATION_WORKFLOW (mandatory legal review)
- ✅ **Human-in-the-Loop**: Approval gates for Relationship Managers, Compliance Officers, and Legal teams
- ✅ **Context Enrichment**: AI-powered historical pattern analysis and risk scenario generation
- ✅ **Action Execution**: Automated emails, document requests, escalations, and compliance checks
- ✅ **Full Auditability**: Complete audit trail of workflow execution, approvals, and actions

---

## 🏗️ Technical Architecture

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Python 3.11, FastAPI | RESTful APIs for all services |
| **AI Orchestration** | LangGraph | Multi-agent workflow coordination |
| **LLM** | Groq (Llama 3.3 70B Versatile) | Rule parsing, risk explanation, workflow decisions |
| **Vision AI** | Groq Vision (LLaVA 1.5 7B) | Image authenticity and tamper detection |
| **Document Processing** | IBM Docling | PDF/DOCX structure extraction |
| **Databases** | PostgreSQL (TAE, REE, RWE), SQLite (DCE) | Persistent storage |
| **Async Processing** | Celery + Redis | Background batch jobs (DCE) |
| **ORM** | SQLAlchemy 2.0 + Alembic | Database models and migrations |
| **Testing** | Pytest | Unit and integration tests |
| **Containerization** | Docker + Docker Compose | Service isolation and deployment |

### Service Breakdown

| Service | Port | Agents | Database | Description |
|---------|------|--------|----------|-------------|
| **DCE** | 8000 | 4 | SQLite | Document upload, OCR, format validation, image analysis, risk scoring |
| **TAE** | 8002 | 5 | PostgreSQL | Transaction analysis, rule parsing, behavioral detection, risk scoring, explanation |
| **REE** | 8003 | N/A | PostgreSQL | Regulatory document ingestion, rule extraction, API exposure |
| **RWE** | 8004 | 6 | PostgreSQL | Workflow orchestration, decision engine, action execution, compliance verification |

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Groq API Key ([get one free](https://console.groq.com))

### Quick Start (Docker)

```bash
# 1. Clone the repository
git clone <repository-url>
cd backend

# 2. Set up environment variables for each service
cd services/transaction-analysis-engine
cp .env.example .env
# Add your GROQ_API_KEY to .env

cd ../document-corroboration-engine
cp .env.example .env
# Add your GROQ_API_KEY to .env

cd ../remediation-workflow-engine
cp .env.example .env
# Add your GROQ_API_KEY to .env

# 3. Start all services
cd services/transaction-analysis-engine
docker-compose up -d --build

cd ../document-corroboration-engine
docker-compose up -d --build

cd ../regulatory-ingestion-engine
docker-compose up -d --build

cd ../remediation-workflow-engine
docker-compose up -d --build

# 4. Verify services are running
curl http://localhost:8002/health  # TAE
curl http://localhost:8000/health  # DCE
curl http://localhost:8003/health  # REE
curl http://localhost:8004/health  # RWE
```

### Quick Demo (5 minutes)

#### 1. Upload Regulatory Document (REE)
```bash
curl -X POST "http://localhost:8003/api/v1/process/upload" \
  -F "file=@regulatory-docs/hkma/sample.pdf" \
  -F "extract_rules=true"
```

#### 2. Analyze Transaction Batch (TAE)
```bash
curl -X POST "http://localhost:8002/api/v1/tae/analyze-batch" \
  -F "file=@data/transactions_mock_1000_for_participants.csv" \
  -F "user_id=demo-user"
```

#### 3. Upload Document for Corroboration (DCE)
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@data/Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf" \
  -F "uploader_id=demo-user"
```

#### 4. Start Remediation Workflow (RWE)
```bash
curl -X POST "http://localhost:8004/api/v1/workflows/start" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALERT-001",
    "risk_score": 85,
    "customer_id": "CUST-001",
    "triggered_rules": ["CASH_LIMIT", "PEP_STATUS"],
    "jurisdiction": "HK"
  }'
```



---

## 🎨 Features Implemented

### Part 1: Real-Time AML Monitoring
- [x] Regulatory ingestion from HKMA, MAS, FINMA, BaFin (REE)
- [x] Real-time transaction monitoring with 100+ configurable rules (TAE)
- [x] 5-agent LangGraph workflow with parallel execution
- [x] Behavioral analysis (velocity, smurfing, clustering, geographic risk)
- [x] Risk scoring with jurisdiction-specific weights
- [x] Audit-ready explanations with regulatory citations (Groq LLM)
- [x] Batch CSV upload supporting 1,000+ transactions
- [x] Comprehensive audit trail with agent execution logs
- [x] Role-based alert routing (RM/Compliance/Legal)

### Part 2: Document Corroboration
- [x] Multi-format support (PDF, DOCX, TXT, JPG, PNG)
- [x] IBM Docling structure extraction (tables, sections, metadata)
- [x] Groq Vision OCR for images
- [x] AI-enhanced format validation (style, consistency, completeness)
- [x] Advanced image analysis (authenticity, quality, tampering)
- [x] 5-dimensional risk scoring (Format, Content, Authenticity, Compliance, Structural)
- [x] Real-time feedback with actionable recommendations
- [x] Comprehensive audit trail for all document operations
- [x] Batch processing with Celery + Redis

### Integration & Remediation
- [x] Automated workflow orchestration (RWE)
- [x] 4 pre-built workflow templates (CRITICAL_BLOCK, EDD_STANDARD, EDD_PEP, LEGAL_ESCALATION)
- [x] Human-in-the-loop approvals (RM, Compliance, Legal)
- [x] AI-powered context enrichment and risk scenario generation
- [x] Action execution (emails, document requests, escalations)
- [x] Compliance verification and audit trail maintenance
- [x] Cross-service integration (TAE alerts → RWE workflows → DCE document checks)

---

## 📚 Documentation

### Key Documents
- **[AGENTS.md](backend/AGENTS.md)**: Repository guidelines, coding standards, testing procedures
- **[AGENTS_AND_FRAMEWORKS.md](backend/AGENTS_AND_FRAMEWORKS.md)**: Deep dive into LangGraph, agents, and frameworks
- **[BACKEND_OVERVIEW_SLIDES.md](backend/BACKEND_OVERVIEW_SLIDES.md)**: Architecture presentation deck
- **[HACKATHON_DECK.md](backend/HACKATHON_DECK.md)**: Full hackathon submission deck
- **[HACKATHON_TECH_DECK.md](backend/HACKATHON_TECH_DECK.md)**: Technical deep dive deck

### Service READMEs
- **[TAE README](backend/services/transaction-analysis-engine/README.md)**: Transaction Analysis Engine
- **[DCE README](backend/services/document-corroboration-engine/README.md)**: Document Corroboration Engine
- **[REE README](backend/services/regulatory-ingestion-engine/README.md)**: Regulatory Ingestion Engine
- **[RWE README](backend/services/remediation-workflow-engine/README.md)**: Remediation Workflow Engine

---

## 🏆 Why RegClock Wins

### 1. Complete End-to-End Solution
- We didn't just build Part 1 OR Part 2 — we built **both** PLUS an automated remediation layer
- Every component is production-ready with proper error handling, logging, and audit trails
- Seamless integration between all four engines

### 2. Advanced AI Orchestration
- **Multi-agent workflows** using LangGraph (not just simple API calls)
- **Parallel execution** where possible (Agent 2 & 3 run simultaneously)
- **Intelligent routing** with conditional edges based on state
- **Human-in-the-loop** approvals at critical decision points

### 3. Real-World Regulatory Compliance
- Actual rules from HKMA, MAS, FINMA, BaFin encoded as agents
- Jurisdiction-specific weights and thresholds
- Full auditability with regulatory citations
- PEP screening, sanctions checks, travel rule compliance

### 4. Production-Ready Architecture
- **Microservices**: Each engine is independently deployable
- **Async processing**: Celery + Redis for batch jobs
- **Database per service**: PostgreSQL (TAE, REE, RWE), SQLite (DCE)
- **Comprehensive logging**: Structured logs with correlation IDs
- **Health checks**: `/health` endpoints on all services
- **Docker Compose**: One-command deployment

### 5. Advanced Document Intelligence
- **Vision AI**: Groq Vision for image authenticity and tamper detection
- **Structure extraction**: IBM Docling for professional document parsing
- **Multi-dimensional risk scoring**: 5 categories with weighted aggregation
- **Actionable feedback**: Specific recommendations for compliance officers

### 6. Innovation Beyond Requirements
- **Remediation workflows**: Fully automated compliance workflows with approval gates
- **Context enrichment**: AI-generated historical pattern analysis
- **Cross-service integration**: TAE alerts automatically trigger RWE workflows
- **Batch processing**: Handle 1,000+ transactions/documents efficiently


## 👥 Team RegClock

**Built with passion for real-world impact by Team RegClock**

- **Mentor**: Wee Kiat — Open Innovation Lead, AI, Data & Innovation, Julius Baer

---

## 📄 License

This project is proprietary and confidential. All rights reserved by Team RegClock and Julius Baer.

---

## 🙏 Acknowledgments

- **Julius Baer** for hosting SingHacks 2025 and providing this incredible challenge
- **Groq** for blazing-fast LLM inference (<5s latency)
- **IBM Docling** for professional document structure extraction
- **LangGraph** for elegant multi-agent orchestration
- **Our Mentor** for guidance and regulatory domain expertise

---

**🚀 RegClock — Agentic AI for Real-Time AML Intelligence**

*Building the future of regulatory compliance, one agent at a time.*
