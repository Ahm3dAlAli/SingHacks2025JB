# Transaction Analysis Engine (TAE)

> Real-Time AML Monitoring & Alerts System using LangGraph Multi-Agent Architecture

## Overview

The Transaction Analysis Engine (TAE) is a microservice that analyzes financial transactions against regulatory rules to detect suspicious patterns and money laundering activities. It uses LangGraph for multi-agent orchestration powered by Groq API.

**Processing Volume**: 1,000 transactions/hour
**Technology Stack**: Python, FastAPI, LangGraph, PostgreSQL, Docker, Groq API

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Groq API key ([Get one here](https://console.groq.com/keys))
- Ports 5432 and 8002 available

### Setup Instructions

1. **Clone and navigate to the service directory**
   ```bash
   cd backend/services/transaction-analysis-engine
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit .env file and add your Groq API key**
   ```bash
   nano .env  # or use your preferred editor
   ```

   Replace `<GET_FROM_GROQ_DASHBOARD>` with your actual Groq API key.

4. **Start the services**
   ```bash
   docker-compose up -d
   ```

5. **Verify services are running**
   ```bash
   docker-compose ps
   ```

   Both `tae_postgres` and `tae_service` should show as "healthy".

6. **Test database connectivity**
   ```bash
   python scripts/test_db_connection.py
   ```

### Verify Installation

Check that all database tables were created:
```bash
docker-compose exec postgres psql -U tae_user -d aml_monitoring -c "\dt"
```

You should see 5 tables:
- transactions
- risk_assessments
- agent_execution_logs
- audit_trail
- regulatory_rules

Verify seed data loaded (should show 15 rules):
```bash
docker-compose exec postgres psql -U tae_user -d aml_monitoring -c "SELECT COUNT(*) FROM regulatory_rules;"
```

## Architecture

### Database Schema

**5 Core Tables:**
1. **transactions** - All transaction data from CSV (53 columns)
2. **risk_assessments** - Risk scores and analysis results
3. **agent_execution_logs** - Audit trail per agent
4. **audit_trail** - System-wide compliance log
5. **regulatory_rules** - 15 mock rules (HKMA, MAS, FINMA)

### Multi-Agent Workflow

```
Transaction Input
      ↓
Agent 1: Rule Parser (Groq LLM)
      ↓
┌─────┴─────┐
Agent 2      Agent 3
Static       Behavioral
Rules        Pattern
(No LLM)     (No LLM)
└─────┬─────┘
      ↓
Agent 4: Risk Scorer
      ↓
Agent 5: Explainer (Groq LLM)
      ↓
Risk Score + Explanation
```

## API Endpoints

Base URL: `http://localhost:8002/api/v1/tae`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/analyze-batch` | Upload CSV, start batch processing |
| GET | `/batch/{batch_id}/status` | Check processing progress |
| GET | `/batch/{batch_id}/results` | Get final analysis summary |
| POST | `/analyze-transaction` | Real-time single transaction analysis |
| GET | `/transaction/{tx_id}/risk-detail` | Detailed risk breakdown |
| GET | `/explain/{tx_id}` | Natural language explanation |
| GET | `/health` | Service health check |

## Common Commands

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f tae
docker-compose logs -f postgres
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Access database directly
```bash
docker-compose exec postgres psql -U tae_user -d aml_monitoring
```

### Reset database (WARNING: Deletes all data)
```bash
docker-compose down -v
docker-compose up -d
```

## Development

### Project Structure
```
transaction-analysis-engine/
├── app/                    # Application code
│   ├── api/               # FastAPI routes
│   ├── langgraph/         # Agent implementations
│   ├── database/          # DB models and queries
│   ├── services/          # Groq client, batch processor
│   └── utils/             # Helpers and validators
├── database/              # SQL scripts
│   ├── init.sql          # Schema definition
│   └── seed_rules.sql    # Mock regulatory rules
├── data/                  # Transaction CSVs
├── logs/                  # Application logs
├── tests/                 # Unit and integration tests
├── docker-compose.yml     # Container orchestration
├── Dockerfile            # TAE service image
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Running Tests
```bash
# Inside the container
docker-compose exec tae pytest tests/

# Or locally with venv
python -m pytest tests/
```

## Performance Targets

- **Throughput**: 1,000 transactions/hour (~17 tx/min)
- **Per-Transaction**: ~1.3 seconds total
  - Agent 1 (Rule Parser): 500ms
  - Agent 2 (Static Rules): 50ms
  - Agent 3 (Behavioral): 100ms
  - Agent 4 (Risk Scorer): 20ms
  - Agent 5 (Explainer): 600ms
  - Database writes: 50ms

## Regulatory Coverage

### Hong Kong (HKMA/SFC)
- Cash limits, PEP checks, KYC expiry
- STR filing requirements

### Singapore (MAS)
- Travel rule, sanctions screening
- FX spreads, cash structuring

### Switzerland (FINMA)
- EDD requirements, source of wealth
- Complex product suitability

## Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Check port conflicts
lsof -i :5432
lsof -i :8002
```

### Database connection errors
```bash
# Verify postgres is healthy
docker-compose ps postgres

# Check credentials in .env
cat .env | grep POSTGRES
```

### Missing Groq API key
Edit `.env` file and add your Groq API key from https://console.groq.com/keys

## Security Notes

- Never commit `.env` file to git
- Rotate API keys regularly
- Use strong database passwords in production
- The old exposed Groq API key (`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`) must be revoked!

## Related Documentation

- [TAE_ARCHITECTURE.md](./TAE_ARCHITECTURE.md) - Complete architecture specification
- [Main README.md](../../../README.md) - Hackathon requirements

## Support

For issues or questions, refer to the architecture documentation or contact the development team.

---

**Version**: 1.0.0
**Last Updated**: 2025-10-31
**Status**: Phase 1 - Infrastructure Complete
