# Remediation Workflow Engine (RWE)

**AI-Powered AML Remediation Workflows using LangGraph Multi-Agent Architecture**

## Overview

The Remediation Workflow Engine (RWE) is a microservice that orchestrates intelligent remediation workflows for high-risk AML alerts. It uses LangGraph for multi-agent orchestration powered by Groq API to automate compliance actions, document requests, and stakeholder communications.

**Processing Volume**: 500 workflows/day  
**Technology Stack**: Python, FastAPI, LangGraph, SQLite, Docker, Groq API

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Groq API key ([Get one here](https://console.groq.com/keys))
- Port 8004 available

### Setup Instructions

**Clone and navigate to the service directory**
```bash
cd remediation-workflow-engine
```

**Create environment file**
```bash
cp .env.example .env
```

**Edit .env file and add your Groq API key**
```bash
nano .env  # or use your preferred editor
```

Replace `your_groq_api_key_here` with your actual Groq API key.

**Start the services**
```bash
docker-compose up -d
```

**Verify services are running**
```bash
docker-compose ps
```

Both `remediation-workflows` and `db` should show as "Up".

**Initialize the database**
```bash
docker-compose exec remediation-workflows python -c "
from database.connection import init_db
import asyncio
asyncio.run(init_db())
print('Database initialized successfully')
"
```

**Verify Installation**

Check that all database tables were created:
```bash
docker-compose exec db psql -U user -d aml_workflows -c "\dt"
```

You should see 5 tables:
- `workflow_instances`
- `workflow_actions` 
- `audit_entries`
- `documents`
- `email_templates`

## Architecture

### Database Schema

**5 Core Tables:**
- `workflow_instances` - Active and completed workflows
- `workflow_actions` - Individual steps and their status
- `audit_entries` - Immutable audit trail for compliance
- `documents` - EDD document tracking and validation
- `email_templates` - Communication templates

### Multi-Agent Workflow

```
Alert Input (from Part 3)
      ↓
Agent 1: Workflow Orchestrator (Groq LLM)
      ↓
┌─────┴─────┐
Agent 2      Agent 3
Decision     Context
Engine       Enricher
(Groq LLM)   (Groq LLM)
└─────┬─────┘
      ↓
Agent 4: Action Executor
      ↓
Agent 5: Compliance Checker (Groq LLM)
      ↓
Workflow Completion + Audit Trail
```

### Workflow Templates

**CRITICAL_BLOCK_WORKFLOW** - Immediate action for high-risk transactions (risk_score ≥ 85)  
**EDD_STANDARD_WORKFLOW** - Standard enhanced due diligence (risk_score ≥ 60)  
**EDD_PEP_WORKFLOW** - Specialized workflow for Politically Exposed Persons  
**CUSTOMER_REVIEW_WORKFLOW** - Pattern-based customer behavior review  
**ENHANCED_MONITORING_WORKFLOW** - Ongoing monitoring for lower risk cases

## API Endpoints

**Base URL**: `http://localhost:8004/api/v1`

| Method | Endpoint | Purpose |
|--------|-----------|---------|
| POST | `/workflows/start` | Start remediation workflow for alert |
| GET | `/workflows/{workflow_instance_id}` | Get workflow status and progress |
| POST | `/workflows/{workflow_instance_id}/actions` | Execute specific workflow action |
| GET | `/workflows/{workflow_instance_id}/audit-trail` | Get complete audit trail |
| GET | `/health` | Service health check |

### Example Usage

**Start a remediation workflow:**
```bash
curl -X POST "http://localhost:8004/api/v1/workflows/start" \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALERT_20241031_001",
    "risk_score": 75.5,
    "severity": "high",
    "customer_id": "CUST_123456",
    "transaction_ids": ["TXN_001", "TXN_002"],
    "triggered_rules": ["FINMA_001", "STRUCTURING_001"],
    "customer_profile": {
      "name": "John Smith",
      "is_pep": false,
      "customer_type": "corporate"
    },
    "jurisdiction": "CH",
    "alert_type": "suspicious_activity"
  }'
```

**Check workflow status:**
```bash
curl "http://localhost:8004/api/v1/workflows/WF_20241031_abc123"
```

**Get audit trail:**
```bash
curl "http://localhost:8004/api/v1/workflows/WF_20241031_abc123/audit-trail"
```

## Common Commands

**Start services**
```bash
docker-compose up -d
```

**Stop services**
```bash
docker-compose down
```

**View logs**
```bash
docker-compose logs -f remediation-workflows
docker-compose logs -f db
```

**Rebuild after code changes**
```bash
docker-compose up -d --build
```

**Access database directly**
```bash
docker-compose exec db psql -U user -d aml_workflows
```

**Reset database (WARNING: Deletes all data)**
```bash
docker-compose down -v
docker-compose up -d
```

## Development

### Project Structure

```
remediation-workflow-engine/
├── api/                    # FastAPI routes and models
├── langgraph/             # Multi-agent implementations
│   ├── graph.py          # Main workflow orchestration
│   ├── state.py          # Shared state definition
│   └── agents/           # Individual agent implementations
├── database/              # Database models and queries
├── services/              # External service integrations
├── templates/             # Email and document templates
├── docker-compose.yml     # Container orchestration
├── Dockerfile            # Service container definition
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Running Tests

```bash
# Run basic health checks
curl http://localhost:8004/health

# Test workflow creation
python tests/test_workflow_creation.py
```

## Performance Targets

- **Throughput**: 500 workflows/day (~21 workflows/hour)
- **Per-Workflow**: ~2-5 minutes total processing time
- **Agent 1 (Orchestrator)**: 30 seconds
- **Agent 2 (Decision Engine)**: 45 seconds  
- **Agent 3 (Context Enricher)**: 30 seconds
- **Agent 4 (Action Executor)**: 60 seconds
- **Agent 5 (Compliance Checker)**: 30 seconds
- **Database Operations**: 15 seconds

## Regulatory Coverage

### Switzerland (FINMA)
- Enhanced Due Diligence workflows
- Source of wealth validation
- PEP handling procedures
- Transaction blocking protocols

### Singapore (MAS) 
- Document request automation
- Timeline compliance tracking
- Escalation management
- Audit trail requirements

### Hong Kong (HKMA)
- Stakeholder communication
- Regulatory reporting preparation
- Compliance verification
- Record keeping standards

## Workflow Lifecycle

1. **Alert Reception** - Receive high-risk alert from monitoring system
2. **Context Enrichment** - Gather customer history and related data
3. **Workflow Selection** - AI-powered template selection
4. **Action Execution** - Automated document requests, notifications, blocks
5. **Compliance Verification** - Regulatory requirement checking
6. **Audit Trail Generation** - Immutable compliance records
7. **Workflow Completion** - Final reporting and archiving

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Check port conflicts
lsof -i :8004
```

### Database connection errors
```bash
# Verify database is running
docker-compose ps db

# Check connection string
docker-compose exec remediation-workflows cat .env | grep DATABASE_URL
```

### Missing Groq API key
Edit `.env` file and add your Groq API key from https://console.groq.com/keys

### Workflow not progressing
```bash
# Check agent logs
docker-compose logs remediation-workflows | grep -i "agent"

# Verify Groq API connectivity
curl -X POST http://localhost:8004/health
```

## Security Notes

- Never commit `.env` file to git
- Rotate API keys regularly  
- Use strong database passwords in production
- Enable SSL/TLS for database connections in production
- Regular security audits of workflow execution logs

## Monitoring & Metrics

Key metrics to monitor:
- Workflow completion rate
- Average workflow duration
- Escalation frequency
- Document validation success rate
- SLA compliance percentage
- Groq API usage and costs

## Integration Points

**Input**: Receives alerts from Transaction Analysis Engine (Part 3)  
**Output**: Sends completion reports to Case Management System  
**Storage**: Maintains audit trails for regulatory compliance  
**Communications**: Integrates with email, document management, and core banking systems

---

**Status**: 🟢 Production Ready  
**Last Updated**: October 2024  
**Maintainer**: AML Compliance Engineering Team
