# Postman Guide - Transaction Analysis Engine (TAE)

**Service**: Transaction Analysis Engine (TAE)
**Base URL**: `http://localhost:8002`
**Version**: 1.0.0
**Tech Stack**: FastAPI, LangGraph, Groq AI, PostgreSQL

---

## Quick Setup

### 1. Start the Service

```bash
cd backend/services/transaction-analysis-engine
docker-compose up -d
```

**Wait 10-15 seconds** for services to fully start.

### 2. Verify Service is Running

```bash
docker-compose ps
```

You should see:
- `tae_postgres` - **healthy**
- `tae_service` - **healthy** (or running)

---

## Available Endpoints

### 1. Health Check ✅

**Endpoint**: `GET /health`
**Purpose**: Check if service and database are running
**Authentication**: None

**Postman Setup**:
1. Create new request
2. Method: `GET`
3. URL: `http://localhost:8002/health`
4. Click **Send**

**Expected Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "TAE",
  "version": "1.0.0",
  "timestamp": "2025-11-01T12:30:00.000000Z",
  "database": "connected",
  "environment": "development"
}
```

**Unhealthy Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "service": "TAE",
  "version": "1.0.0",
  "timestamp": "2025-11-01T12:30:00.000000Z",
  "database": "disconnected",
  "environment": "development"
}
```

---

### 2. Service Info ✅

**Endpoint**: `GET /`
**Purpose**: Get basic service information
**Authentication**: None

**Postman Setup**:
1. Create new request
2. Method: `GET`
3. URL: `http://localhost:8002/`
4. Click **Send**

**Expected Response** (200 OK):
```json
{
  "service": "Transaction Analysis Engine (TAE)",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 3. API Documentation 📖

**Endpoint**: `GET /docs`
**Purpose**: Interactive Swagger UI documentation
**Authentication**: None

**Access**:
1. Open browser: `http://localhost:8002/docs`
2. View all available endpoints
3. Test endpoints directly from browser

**Alternative Documentation**:
- **ReDoc**: `http://localhost:8002/redoc`

---

## Postman Collection Setup

### Create a New Collection

1. **Open Postman**
2. Click **New** → **Collection**
3. Name: `Transaction Analysis Engine (TAE)`
4. Description: `AML Monitoring & Alerts System`

### Add Collection Variables

1. Click on collection → **Variables** tab
2. Add variables:

| Variable | Initial Value | Current Value |
|----------|--------------|---------------|
| `base_url` | `http://localhost:8002` | `http://localhost:8002` |
| `api_version` | `v1` | `v1` |

3. Save collection

### Use Variables in Requests

Instead of: `http://localhost:8002/health`
Use: `{{base_url}}/health`

---

## Testing Workflow (Current Implementation)

### Note on API Endpoints

⚠️ **Current Status**: The TAE currently has the workflow engine implemented but **does not have REST API endpoints** for transaction analysis yet.

**What Exists**:
- ✅ 5-agent workflow engine (Agent 1-5)
- ✅ LangGraph orchestration
- ✅ Database models
- ✅ Groq AI integration
- ✅ Health check endpoints

**What's Missing**:
- ❌ POST endpoint to analyze transactions
- ❌ GET endpoint to retrieve analysis results
- ❌ Batch processing endpoint

### How to Test the Workflow Engine

**Option 1: Direct Python Testing**
```bash
# Enter the Docker container
docker-compose exec tae_service bash

# Run Python interactively
python

# Test the workflow
from app.workflows.workflow import execute_workflow
from app.database.models import Transaction

# Create a test transaction
transaction = {
    "transaction_id": "TXN_TEST_001",
    "customer_id": "CUST_123456",
    "amount": 150000.00,
    "currency": "HKD",
    "jurisdiction": "HK"
}

# Execute workflow (returns analysis results)
result = await execute_workflow(transaction)
print(result)
```

**Option 2: Run Tests**
```bash
# Run all tests
docker-compose exec tae_service pytest

# Run specific test
docker-compose exec tae_service pytest tests/test_integration/test_graph.py -v
```

---

## Sample API Endpoints (To Be Implemented)

### Analyze Single Transaction

**Endpoint**: `POST /api/v1/transactions/analyze` (NOT YET IMPLEMENTED)
**Purpose**: Analyze a single transaction through the 5-agent workflow

**Request Body**:
```json
{
  "transaction_id": "TXN_20241101_001",
  "customer_id": "CUST_123456",
  "customer_name": "John Smith",
  "customer_risk_rating": "medium",
  "customer_type": "individual",
  "kyc_last_update": "2024-06-15",
  "is_pep": false,
  "is_sanctioned": false,

  "amount": 150000.00,
  "currency": "HKD",
  "booking_datetime": "2024-11-01T14:30:00Z",
  "value_date": "2024-11-01",

  "transaction_type": "cash_deposit",
  "channel": "branch",
  "product_complex": false,

  "originator_account": "HK-ACC-001",
  "originator_name": "John Smith",
  "originator_country": "HK",
  "originator_city": "Hong Kong",

  "beneficiary_account": "HK-ACC-002",
  "beneficiary_name": "John Smith",
  "beneficiary_country": "HK",
  "beneficiary_city": "Hong Kong",

  "jurisdiction": "HK",
  "branch_code": "HKG001",
  "relationship_manager": "RM-001"
}
```

**Expected Response**:
```json
{
  "transaction_id": "TXN_20241101_001",
  "analysis_timestamp": "2024-11-01T14:30:15Z",
  "processing_time_ms": 1250,

  "risk_assessment": {
    "final_score": 75.5,
    "alert_level": "HIGH",
    "confidence": 0.92
  },

  "agent_results": {
    "rule_parser": {
      "parsed_rules": {...},
      "execution_time_ms": 500
    },
    "static_rules": {
      "violations": [
        {
          "rule_id": "HKMA_CASH_001",
          "severity": "HIGH",
          "score": 70,
          "description": "Cash transaction exceeds threshold"
        }
      ],
      "execution_time_ms": 50
    },
    "behavioral": {
      "flags": [
        {
          "pattern": "velocity_increase",
          "severity": "MEDIUM",
          "score": 40,
          "description": "Transaction frequency increased 200% in last 7 days"
        }
      ],
      "execution_time_ms": 100
    },
    "risk_scorer": {
      "static_score": 70,
      "behavioral_score": 40,
      "combined_score": 75.5,
      "alert_level": "HIGH",
      "execution_time_ms": 20
    },
    "explainer": {
      "explanation": "Transaction flagged due to cash amount exceeding HKD 120,000 threshold...",
      "regulatory_citations": ["HKMA-CASH-001", "HKMA-KYC-002"],
      "recommended_action": "ENHANCED_DUE_DILIGENCE",
      "execution_time_ms": 600
    }
  },

  "recommended_actions": [
    "ENHANCED_DUE_DILIGENCE",
    "DOCUMENT_SOURCE_OF_FUNDS",
    "NOTIFY_COMPLIANCE_TEAM"
  ],

  "audit_trail": [
    {
      "timestamp": "2024-11-01T14:30:10.100Z",
      "agent": "rule_parser",
      "action": "parse_rules",
      "status": "completed"
    },
    {
      "timestamp": "2024-11-01T14:30:10.650Z",
      "agent": "static_rules",
      "action": "check_compliance",
      "status": "completed"
    }
  ]
}
```

### Get Analysis Results

**Endpoint**: `GET /api/v1/transactions/{transaction_id}/analysis` (NOT YET IMPLEMENTED)
**Purpose**: Retrieve previous analysis results

**URL Parameters**:
- `transaction_id`: Transaction identifier

**Example**: `GET /api/v1/transactions/TXN_20241101_001/analysis`

**Expected Response**: Same as analyze response above

### Batch Analysis

**Endpoint**: `POST /api/v1/transactions/batch-analyze` (NOT YET IMPLEMENTED)
**Purpose**: Analyze multiple transactions

**Request Body**:
```json
{
  "transactions": [
    { /* transaction 1 */ },
    { /* transaction 2 */ },
    { /* transaction 3 */ }
  ],
  "batch_id": "BATCH_20241101_001",
  "parallel_processing": true
}
```

**Expected Response**:
```json
{
  "batch_id": "BATCH_20241101_001",
  "total_transactions": 3,
  "processed": 3,
  "failed": 0,
  "processing_time_ms": 3500,
  "results": [
    { /* analysis result 1 */ },
    { /* analysis result 2 */ },
    { /* analysis result 3 */ }
  ],
  "summary": {
    "critical_alerts": 1,
    "high_alerts": 1,
    "medium_alerts": 1,
    "low_alerts": 0
  }
}
```

---

## Troubleshooting

### Service Not Responding

**Check if running**:
```bash
docker-compose ps
```

**Check logs**:
```bash
docker-compose logs -f tae_service
```

**Restart service**:
```bash
docker-compose restart tae_service
```

### Database Connection Errors

**Check database**:
```bash
docker-compose ps db
```

**Verify database connection**:
```bash
docker-compose exec tae_service python -c "
from app.database.connection import test_connection
import asyncio
result = asyncio.run(test_connection())
print('Connected!' if result else 'Failed!')
"
```

### Port Already in Use (8002)

**Check what's using port 8002**:
```bash
lsof -i :8002
```

**Kill process**:
```bash
kill -9 <PID>
```

**Or change port in `.env`**:
```bash
TAE_PORT=8003
```

---

## Environment Variables

Edit `.env` file to configure:

```bash
# Database
POSTGRES_HOST=localhost  # Use 'postgres' in Docker
POSTGRES_PORT=5432
POSTGRES_DB=aml_monitoring
POSTGRES_USER=tae_user
POSTGRES_PASSWORD=your_password_here

# Groq API (for LLM agents)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Application
TAE_PORT=8002
LOG_LEVEL=INFO
ENVIRONMENT=development
WORKERS=4
```

---

## Common HTTP Status Codes

| Code | Meaning | When You See It |
|------|---------|----------------|
| 200 | OK | Request successful |
| 422 | Unprocessable Entity | Invalid request data |
| 500 | Internal Server Error | Service error, check logs |
| 503 | Service Unavailable | Database not connected |

---

## Postman Environment Setup

### Create Environment

1. Click **Environments** (top right)
2. Click **+** to create new
3. Name: `TAE - Development`

### Add Variables

| Variable | Initial Value | Current Value |
|----------|--------------|---------------|
| `base_url` | `http://localhost:8002` | `http://localhost:8002` |
| `groq_api_key` | `your_key_here` | `your_key_here` |
| `transaction_id` | `TXN_TEST_001` | `TXN_TEST_001` |

### Use in Requests

```
URL: {{base_url}}/health
Header: Authorization: Bearer {{groq_api_key}}
Body: "transaction_id": "{{transaction_id}}"
```

---

## Next Steps: Implementing REST APIs

To make the TAE fully testable via Postman, these API endpoints need to be implemented:

### Priority 1: Core Endpoints
- [ ] `POST /api/v1/transactions/analyze` - Single transaction analysis
- [ ] `GET /api/v1/transactions/{id}/analysis` - Get analysis results
- [ ] `GET /api/v1/transactions/{id}/audit-trail` - Get audit trail

### Priority 2: Batch Processing
- [ ] `POST /api/v1/transactions/batch-analyze` - Batch analysis
- [ ] `GET /api/v1/batches/{batch_id}` - Get batch status

### Priority 3: Monitoring
- [ ] `GET /api/v1/metrics` - System metrics
- [ ] `GET /api/v1/agents/status` - Agent health status

### Priority 4: Configuration
- [ ] `GET /api/v1/rules` - List regulatory rules
- [ ] `POST /api/v1/rules` - Add new rule
- [ ] `PUT /api/v1/rules/{rule_id}` - Update rule

---

## Testing the 5-Agent Workflow

Once REST APIs are implemented, you can test the complete workflow:

### Agent Flow Visualization

```
Transaction Input
      ↓
Agent 1: Rule Parser (Groq LLM) ← ~500ms
      ↓
┌─────┴─────┐
│ PARALLEL  │
Agent 2     Agent 3
Static      Behavioral ← ~150ms combined
Rules       Pattern
~50ms       ~100ms
└─────┬─────┘
      ↓
Agent 4: Risk Scorer ← ~20ms
      ↓
Agent 5: Explainer (Groq LLM) ← ~600ms
      ↓
Analysis Complete (~1.3 seconds total)
```

### Test Each Agent Individually

**Note**: These endpoints don't exist yet but should be implemented for testing:

1. **Agent 1 - Rule Parser**: `POST /api/v1/agents/rule-parser/test`
2. **Agent 2 - Static Rules**: `POST /api/v1/agents/static-rules/test`
3. **Agent 3 - Behavioral**: `POST /api/v1/agents/behavioral/test`
4. **Agent 4 - Risk Scorer**: `POST /api/v1/agents/risk-scorer/test`
5. **Agent 5 - Explainer**: `POST /api/v1/agents/explainer/test`

---

## Sample Postman Collection JSON

```json
{
  "info": {
    "name": "Transaction Analysis Engine (TAE)",
    "description": "AML Monitoring & Alerts System",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8002"
    }
  ],
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Service Info",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/",
          "host": ["{{base_url}}"],
          "path": [""]
        }
      }
    }
  ]
}
```

**To Import**:
1. Copy JSON above
2. Postman → **Import** → **Raw text**
3. Paste and click **Continue**

---

## Status Summary

### ✅ What Works Now
- Health check endpoint
- Service info endpoint
- Interactive API documentation (/docs)
- Complete 5-agent workflow engine (via Python)
- 117 passing tests
- Docker deployment

### ⚠️ What Needs Implementation
- REST API endpoints for transaction analysis
- Batch processing endpoints
- Result retrieval endpoints
- Audit trail API
- Metrics API

### 📊 Performance Targets
- Single transaction: < 2 seconds
- Batch (100 transactions): < 3 minutes
- Agent 1: ~500ms
- Agent 2: ~50ms
- Agent 3: ~100ms
- Agent 4: ~20ms
- Agent 5: ~600ms

---

**Last Updated**: 2025-11-01
**Status**: ⚠️ Workflow engine complete, REST APIs pending
**Recommendation**: Implement REST API layer to enable full Postman testing
