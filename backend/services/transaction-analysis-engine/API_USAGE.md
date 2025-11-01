# Transaction Analysis Engine - API Usage Guide

Complete guide for using the TAE REST API endpoints.

## Base URL

```
http://localhost:8002/api/v1/tae
```

## Authentication

Currently no authentication required (development mode).
**Production**: Will require JWT tokens.

---

## Endpoints Overview

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/analyze-batch` | POST | Upload CSV batch | <1s |
| `/batch/{id}/status` | GET | Check batch progress | <50ms |
| `/batch/{id}/results` | GET | Get batch results | <200ms |
| `/analyze-transaction` | POST | Analyze single transaction | <3s |
| `/transaction/{id}/risk-detail` | GET | Get detailed breakdown | <100ms |
| `/explain/{id}` | GET | Get NL explanation | <100ms |
| `/health` | GET | Health check | <100ms |

---

## 1. Batch Processing

### 1.1 Upload CSV Batch

**Endpoint**: `POST /api/v1/tae/analyze-batch`

Upload a CSV file for batch processing. Returns immediately with a batch ID.

**Request**:
```bash
curl -X POST http://localhost:8002/api/v1/tae/analyze-batch \
  -F "file=@data/transactions_mock_1000_for_participants.csv"
```

**Response** (202 Accepted):
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "total_transactions": 1000,
  "status_url": "/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/status",
  "estimated_completion": "2025-11-01T15:45:00Z"
}
```

**CSV Requirements**:
- Format: CSV with 54 columns
- Max file size: 10MB
- Required columns: `transaction_id`, `booking_jurisdiction`, `booking_datetime`, `amount`, `currency`, `customer_id`

**Error Responses**:
- `413 Payload Too Large`: File exceeds 10MB
- `415 Unsupported Media Type`: File is not CSV
- `422 Unprocessable Entity`: Invalid CSV format or missing columns

---

### 1.2 Check Batch Status

**Endpoint**: `GET /api/v1/tae/batch/{batch_id}/status`

Poll this endpoint to check batch processing progress.

**Request**:
```bash
curl http://localhost:8002/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/status
```

**Response** (200 OK):
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "total_transactions": 1000,
  "processed_count": 450,
  "failed_count": 2,
  "progress_percent": 45.0,
  "started_at": "2025-11-01T15:30:00Z",
  "estimated_completion": "2025-11-01T15:45:00Z",
  "completed_at": null,
  "error_message": null
}
```

**Status Values**:
- `PENDING`: Batch queued, not started yet
- `PROCESSING`: Currently being processed
- `COMPLETED`: All transactions processed successfully
- `FAILED`: Batch processing failed

**Error Responses**:
- `404 Not Found`: Batch ID does not exist

---

### 1.3 Get Batch Results

**Endpoint**: `GET /api/v1/tae/batch/{batch_id}/results`

Retrieve results from a completed batch. Supports pagination and filtering.

**Request** (basic):
```bash
curl http://localhost:8002/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/results
```

**Request** (with pagination):
```bash
curl "http://localhost:8002/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/results?limit=100&offset=0"
```

**Request** (with filters):
```bash
curl "http://localhost:8002/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/results?alert_level=HIGH&min_risk_score=70"
```

**Query Parameters**:
- `limit` (optional): Results per page (1-1000, default: 100)
- `offset` (optional): Starting position (default: 0)
- `alert_level` (optional): Filter by CRITICAL, HIGH, MEDIUM, or LOW
- `min_risk_score` (optional): Minimum risk score (0-100)
- `max_risk_score` (optional): Maximum risk score (0-100)

**Response** (200 OK):
```json
{
  "batch_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "summary": {
    "total": 1000,
    "critical": 15,
    "high": 87,
    "medium": 234,
    "low": 664
  },
  "processing_duration_seconds": 238,
  "results": [
    {
      "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
      "risk_score": 85,
      "alert_level": "CRITICAL",
      "explanation_summary": "PEP status + cash limit violation",
      "recommended_action": "FILE_STR"
    }
  ],
  "pagination": {
    "total": 1000,
    "limit": 100,
    "offset": 0,
    "next": "/api/v1/tae/batch/550e8400.../results?offset=100&limit=100"
  }
}
```

---

## 2. Single Transaction Analysis

### 2.1 Analyze Transaction

**Endpoint**: `POST /api/v1/tae/analyze-transaction`

Submit a single transaction for real-time analysis.

**Request**:
```bash
curl -X POST http://localhost:8002/api/v1/tae/analyze-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST12345",
    "amount": 150000.00,
    "currency": "HKD",
    "booking_jurisdiction": "HK",
    "booking_datetime": "2025-11-01T10:30:00Z",
    "customer_is_pep": true,
    "customer_risk_rating": "HIGH",
    "originator_country": "HK",
    "beneficiary_country": "SG",
    "product_type": "FX"
  }'
```

**Required Fields**:
- `customer_id`: Customer identifier
- `amount`: Transaction amount (must be > 0)
- `currency`: 3-letter currency code (e.g., HKD, SGD, CHF)
- `booking_jurisdiction`: HK, SG, or CH
- `booking_datetime`: ISO 8601 timestamp

**Optional Fields**:
- `transaction_id`: Custom UUID (auto-generated if not provided)
- `customer_is_pep`: Boolean (default: false)
- `customer_risk_rating`: String (e.g., HIGH, MEDIUM, LOW)
- `originator_country`: 2-letter country code
- `beneficiary_country`: 2-letter country code
- `product_type`: String (e.g., FX, CASH, WIRE)

**Response** (200 OK):
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "risk_score": 75,
  "alert_level": "HIGH",
  "explanation": "Transaction flagged due to PEP status and amount exceeding daily cash limit",
  "rules_violated": [
    {
      "rule_id": "HKMA-CASH-001",
      "rule_type": "cash_limit",
      "severity": "HIGH",
      "score": 70,
      "description": "Cash transaction exceeds HKD 8,000 threshold",
      "jurisdiction": "HK"
    }
  ],
  "behavioral_flags": [
    {
      "flag_type": "VELOCITY_HIGH",
      "severity": "MEDIUM",
      "score": 40,
      "description": "Transaction frequency 4x normal"
    }
  ],
  "recommended_action": "ENHANCED_DUE_DILIGENCE",
  "processing_time_ms": 1850
}
```

**Error Responses**:
- `422 Unprocessable Entity`: Invalid input (e.g., negative amount, invalid jurisdiction)

---

### 2.2 Get Risk Detail

**Endpoint**: `GET /api/v1/tae/transaction/{transaction_id}/risk-detail`

Get detailed risk breakdown including all agent outputs.

**Request**:
```bash
curl http://localhost:8002/api/v1/tae/transaction/123e4567-e89b-12d3-a456-426614174000/risk-detail
```

**Response** (200 OK):
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "risk_score": 85,
  "alert_level": "HIGH",
  "explanation": "High risk due to multiple violations",
  "static_violations": [...],
  "behavioral_flags": [...],
  "static_rules_score": 65,
  "behavioral_score": 40,
  "agent_execution_timeline": [
    {
      "agent": "rule_parser",
      "execution_time_ms": 200,
      "status": "success",
      "timestamp": "2025-11-01T10:30:00.123Z"
    },
    {
      "agent": "static_rules",
      "execution_time_ms": 150,
      "status": "success",
      "timestamp": "2025-11-01T10:30:00.323Z"
    }
  ],
  "analyzed_at": "2025-11-01T10:30:00Z"
}
```

---

### 2.3 Get Explanation

**Endpoint**: `GET /api/v1/tae/explain/{transaction_id}`

Get human-readable explanation with regulatory citations.

**Request**:
```bash
curl http://localhost:8002/api/v1/tae/explain/123e4567-e89b-12d3-a456-426614174000
```

**Response** (200 OK):
```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "explanation": "This transaction requires enhanced due diligence due to the customer's PEP status combined with a cash transaction amount of HKD 150,000 which significantly exceeds the HKD 8,000 threshold set by HKMA guidelines...",
  "regulatory_citations": [
    "HKMA AML/CFT Guideline 3.1.2",
    "FATF Recommendation 10"
  ],
  "evidence": [
    "Customer is classified as PEP",
    "Cash transaction exceeds HKD 8,000 threshold",
    "Transaction frequency 4x above customer's normal pattern"
  ],
  "recommended_action": "ENHANCED_DUE_DILIGENCE",
  "confidence": "HIGH"
}
```

---

## 3. Health Check

**Endpoint**: `GET /health`

Check service health and database connectivity.

**Request**:
```bash
curl http://localhost:8002/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "service": "TAE",
  "version": "1.0.0",
  "timestamp": "2025-11-01T10:30:00.000Z",
  "database": "connected",
  "environment": "development"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "unhealthy",
  "service": "TAE",
  "version": "1.0.0",
  "timestamp": "2025-11-01T10:30:00.000Z",
  "database": "disconnected",
  "environment": "development"
}
```

---

## 4. Complete Workflow Examples

### Example 1: Batch Processing (1,000 transactions)

```bash
# Step 1: Upload CSV
BATCH_RESPONSE=$(curl -s -X POST http://localhost:8002/api/v1/tae/analyze-batch \
  -F "file=@data/transactions_mock_1000_for_participants.csv")

BATCH_ID=$(echo $BATCH_RESPONSE | jq -r '.batch_id')
echo "Batch ID: $BATCH_ID"

# Step 2: Poll status every 5 seconds
while true; do
  STATUS=$(curl -s http://localhost:8002/api/v1/tae/batch/$BATCH_ID/status)
  BATCH_STATUS=$(echo $STATUS | jq -r '.status')
  PROGRESS=$(echo $STATUS | jq -r '.progress_percent')

  echo "Status: $BATCH_STATUS ($PROGRESS%)"

  if [ "$BATCH_STATUS" = "COMPLETED" ]; then
    break
  elif [ "$BATCH_STATUS" = "FAILED" ]; then
    echo "Batch failed!"
    exit 1
  fi

  sleep 5
done

# Step 3: Get results
curl -s "http://localhost:8002/api/v1/tae/batch/$BATCH_ID/results?limit=10" | jq

# Step 4: Get high-risk transactions only
curl -s "http://localhost:8002/api/v1/tae/batch/$BATCH_ID/results?alert_level=HIGH&min_risk_score=70" | jq
```

### Example 2: Single Transaction Analysis

```bash
# Step 1: Analyze transaction
TX_RESPONSE=$(curl -s -X POST http://localhost:8002/api/v1/tae/analyze-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST_URGENT_001",
    "amount": 500000.00,
    "currency": "HKD",
    "booking_jurisdiction": "HK",
    "booking_datetime": "2025-11-01T10:30:00Z",
    "customer_is_pep": true,
    "customer_risk_rating": "HIGH"
  }')

TX_ID=$(echo $TX_RESPONSE | jq -r '.transaction_id')
RISK_SCORE=$(echo $TX_RESPONSE | jq -r '.risk_score')
ALERT=$(echo $TX_RESPONSE | jq -r '.alert_level')

echo "Transaction: $TX_ID"
echo "Risk Score: $RISK_SCORE"
echo "Alert Level: $ALERT"

# Step 2: Get detailed breakdown
curl -s http://localhost:8002/api/v1/tae/transaction/$TX_ID/risk-detail | jq

# Step 3: Get audit-ready explanation
curl -s http://localhost:8002/api/v1/tae/explain/$TX_ID | jq
```

---

## 5. OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

These provide:
- Interactive API testing
- Complete schema documentation
- Example requests and responses
- Authentication requirements (when enabled)

---

## 6. Error Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 202 | Accepted | Batch queued for processing |
| 404 | Not Found | Batch/transaction ID doesn't exist |
| 413 | Payload Too Large | CSV file > 10MB |
| 415 | Unsupported Media Type | File is not CSV |
| 422 | Unprocessable Entity | Invalid input data |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Database connection failed |

---

## 7. Rate Limiting (Future)

**Not implemented yet** - Will be added in production:
- 100 requests/minute per IP address
- 10 concurrent batch uploads per account
- Batch uploads queue with max 1000 pending batches

---

## 8. Performance Expectations

| Operation | Target | Typical |
|-----------|--------|---------|
| Batch upload acceptance | <1s | ~200ms |
| Single transaction analysis | <3s | ~1.8s |
| Batch status check | <50ms | ~20ms |
| Batch results (100 items) | <200ms | ~100ms |
| Health check | <100ms | ~50ms |
| 1,000 transaction batch | <4 min | ~3.5 min |

---

## 9. Troubleshooting

### Issue: "Batch not found"
- Check batch_id is valid UUID
- Batch may have expired (retention policy TBD)

### Issue: "CSV has wrong number of columns"
- Ensure CSV has exactly 54 columns
- Use the sample CSV as template: `data/transactions_mock_1000_for_participants.csv`

### Issue: "File too large"
- Maximum file size is 10MB
- Split large files into multiple batches

### Issue: "Service unavailable"
- Check database connectivity: `curl http://localhost:8002/health`
- Verify PostgreSQL is running: `docker-compose ps`

---

## 10. Contact & Support

- **GitHub Issues**: https://github.com/your-repo/issues
- **Documentation**: See README.md
- **Swagger UI**: http://localhost:8002/docs
