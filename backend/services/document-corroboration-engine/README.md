# Document Corroboration Engine (DCE)

**AI-Powered Document Validation & Risk Assessment System using Multi-Agent Architecture**

## Overview

The Document Corroboration Engine (DCE) is a microservice that analyzes documents (PDF, DOCX, TXT, images) for authenticity, compliance, and risk using Groq Vision AI and IBM Docling. It employs a multi-agent architecture for comprehensive document validation and fraud detection.

**Processing Capacity:** 1,000 documents/hour  
**Technology Stack:** Python, FastAPI, IBM Docling, Groq Vision API, LangGraph, SQLite, Docker, Redis

---

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Groq API key ([Get one here](https://console.groq.com/keys))
- Ports 8000, 6379 available
- Minimum 4GB RAM, 10GB disk space

### Setup Instructions

**1. Clone and navigate to the service directory**

```bash
cd backend/services/document-corroboration-engine
```

**2. Create environment file**

```bash
cp .env.example .env
```

**3. Edit .env file and add your Groq API key**

```bash
nano .env  # or use your preferred editor
```

Replace `<GET_FROM_GROQ_DASHBOARD>` with your actual Groq API key.

⚠️ **IMPORTANT:** The exposed API key in `.env.example` must be revoked immediately!

**4. Start the services**

```bash
docker-compose up -d
```

**5. Verify services are running**

```bash
docker-compose ps
```

All services should show as "healthy":
- `document-api` (FastAPI server)
- `redis` (Task queue)
- `celery-worker` (Background processing)
- `celery-beat` (Scheduled tasks)

**6. Test the API**

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "services": {
    "ocr": "available",
    "docling": "available",
    "vision": "available"
  }
}
```

---

## Architecture

### Database Schema

**3 Core Tables:**

- **documents** - Document metadata, processing results, risk scores (14 columns)
- **audit_trails** - Complete compliance and action history (8 columns)
- **processing_templates** - Document validation rules and templates (7 columns)

### Multi-Agent Workflow

```
Document Upload (PDF/DOCX/TXT/JPG/PNG)
           ↓
┌──────────────────────────────────┐
│  Agent 1: Document Processor     │
│  • Docling (structured docs)     │
│  • Groq Vision OCR (images)      │
│  • Text extraction & structure   │
└──────────┬───────────────────────┘
           ↓
┌──────────┴───────────────────────┐
│  Agent 2: Format Validator       │
│  • Basic format checks           │
│  • AI format analysis (Groq)     │
│  • Content validation (Groq)     │
└──────────┬───────────────────────┘
           ↓
┌──────────┴───────────────────────┐
│  Agent 3: Image Analyzer         │  (Images only)
│  • Authenticity check (Groq)     │
│  • Tampering detection (Groq)    │
│  • Quality assessment (Groq)     │
│  • Content consistency (Groq)    │
└──────────┬───────────────────────┘
           ↓
┌──────────┴───────────────────────┐
│  Agent 4: Risk Scorer            │
│  • Multi-dimensional risk calc   │
│  • Weighted scoring               │
│  • Recommendations                │
└──────────┬───────────────────────┘
           ↓
  Risk Score + Detailed Analysis
```

---

## API Endpoints

**Base URL:** `http://localhost:8000/api/v1`

### Document Operations

| Method | Endpoint | Purpose | Response Time |
|--------|----------|---------|---------------|
| POST | `/documents/upload` | Upload single document | ~1-30s |
| POST | `/documents/upload/batch` | Upload multiple documents | Varies |
| GET | `/documents/{id}` | Get complete analysis | <100ms |
| GET | `/documents` | List documents with filters | <200ms |
| GET | `/documents/{id}/text` | Get extracted text only | <100ms |
| GET | `/documents/{id}/structure` | Get structure analysis | <100ms |
| GET | `/documents/{id}/risks` | Get risk assessment | <100ms |
| POST | `/documents/{id}/reprocess` | Reprocess document | ~1-30s |
| DELETE | `/documents/{id}` | Delete document | <100ms |
| POST | `/documents/compare` | Compare two documents | <200ms |

### Audit & Analytics

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/documents/{id}/audit` | Get audit trail |
| GET | `/statistics` | System-wide statistics |

### System

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Service health check |
| GET | `/status` | System status and version |

---

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
# API logs
docker-compose logs -f document-api

# Worker logs
docker-compose logs -f celery-worker

# All logs
docker-compose logs -f
```

### Rebuild after code changes

```bash
docker-compose up -d --build
```

### Access database directly

```bash
docker-compose exec document-api sqlite3 data/documents.db
```

### Reset database (⚠️ WARNING: Deletes all data)

```bash
docker-compose down -v
docker-compose up -d
```

### Check service status

```bash
docker-compose ps
```

---

## Development

### Project Structure

```
document-corroboration-engine/
├── app/                          # Application code
│   ├── api/                      # FastAPI routes & models
│   │   ├── models.py            # 18 Pydantic models
│   │   └── routes.py            # 16 API endpoints
│   ├── agents/                   # Multi-agent system
│   │   ├── document_processor.py    # Agent 1: Doc processing
│   │   ├── format_validator.py      # Agent 2: Format validation
│   │   ├── image_analyzer.py        # Agent 3: Image analysis
│   │   └── risk_scorer.py           # Agent 4: Risk scoring
│   ├── services/                 # External service wrappers
│   │   ├── docling_service.py       # IBM Docling integration
│   │   ├── groq_client.py           # Groq LLM client
│   │   ├── ocr_service.py           # Groq Vision OCR
│   │   └── vision_service.py        # Advanced vision analysis
│   ├── database/                 # DB models and queries
│   │   ├── models.py                # SQLAlchemy models
│   │   └── connection.py            # DB connection
│   ├── workflows/                # Celery workflows
│   │   ├── workflow.py              # Main processing workflow
│   │   └── state.py                 # Workflow state management
│   ├── utils/                    # Utility functions
│   │   └── logger.py                # Logging setup
│   ├── config.py                 # Configuration management
│   └── main.py                   # FastAPI application
├── database/                     # SQL scripts
│   ├── init.sql                 # Schema definition
│   └── seed_templates.sql       # Template data
├── data/                         # Data directory
│   ├── uploads/                 # Uploaded documents
│   └── processed/               # Processed documents
├── tests/                        # Unit and integration tests
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # DCE service image
├── requirements.txt              # Python dependencies
├── .env.example                 # Environment template
└── README.md                    # This file
```

### Running Tests

```bash
# Inside the container
docker-compose exec document-api pytest tests/

# Or locally with venv
python -m pytest tests/ -v
```


---

## Document Analysis Components

### 1. Structure Analysis
```json
{
  "total_pages": 5,
  "total_paragraphs": 23,
  "total_words": 1234,
  "total_characters": 6789,
  "headings_count": 8,
  "sections": [...],
  "tables": [...],
  "images": [...]
}
```

### 2. Format Validation
```json
{
  "overall_format_score": 0.85,
  "format_rating": "good",
  "basic_checks": {
    "issues": ["mixed_numbering_styles"],
    "warnings": [],
    "paragraph_count": 23
  },
  "ai_analysis": {
    "professionalism_score": 0.9,
    "formatting_issues": [...]
  }
}
```

### 3. Image Analysis (Images Only)
```json
{
  "overall_trust_score": 0.75,
  "trust_rating": "moderate_trust",
  "authenticity_analysis": {
    "confidence": 0.8,
    "assessment": "genuine"
  },
  "tampering_analysis": {
    "tampering_confidence": 0.1,
    "manipulation_likelihood": "low"
  },
  "quality_analysis": {
    "quality_score": 0.7,
    "processing_suitability": "good"
  },
  "recommendations": [...]
}
```

### 4. Risk Assessment
```json
{
  "overall_risk_score": 0.35,
  "risk_level": "low",
  "risk_breakdown": {
    "format_risk": 0.15,
    "content_risk": 0.25,
    "authenticity_risk": 0.10,
    "compliance_risk": 0.20,
    "structural_risk": 0.05
  },
  "primary_concerns": [...],
  "recommendations": [
    "Low risk - standard processing applicable"
  ]
}
```

---

## Usage Examples

### 1. Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@contract.pdf" \
  -F "uploader_id=user123"
```

**Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Document uploaded and processing started",
  "estimated_processing_time": 30
}
```

### 2. Get Analysis Results

```bash
curl "http://localhost:8000/api/v1/documents/550e8400-e29b-41d4-a716-446655440000"
```

### 3. List High-Risk Documents

```bash
curl "http://localhost:8000/api/v1/documents?risk_level=high&limit=50"
```

### 4. Compare Two Documents

```bash
curl -X POST "http://localhost:8000/api/v1/documents/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id_1": "abc-123",
    "document_id_2": "def-456"
  }'
```

### 5. Get System Statistics

```bash
curl "http://localhost:8000/api/v1/statistics"
```

**Response:**
```json
{
  "total_documents": 1547,
  "documents_by_status": {
    "completed": 1423,
    "processing": 12,
    "failed": 8,
    "pending": 104
  },
  "documents_by_risk_level": {
    "minimal": 234,
    "low": 789,
    "medium": 412,
    "high": 98,
    "critical": 14
  },
  "average_processing_time": 2.3,
  "average_risk_score": 0.42,
  "total_high_risk": 112,
  "recent_uploads": 67
}
```

### 6. Batch Upload

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload/batch" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.jpg" \
  -F "files=@doc3.docx" \
  -F "uploader_id=user123"
```

---

## Supported Use Cases

### 1. **KYC/AML Compliance**
- Identity document verification
- Proof of address validation
- Corporate document authentication
- Risk-based customer screening

### 2. **Contract Analysis**
- Format and structure validation
- Completeness verification
- Compliance checking
- Risk assessment

### 3. **Invoice/Receipt Verification**
- Authenticity checking
- Tampering detection
- Data extraction validation
- Fraud prevention

### 4. **Document Fraud Detection**
- Image manipulation detection
- Copy-paste artifact identification
- Metadata inconsistency analysis
- Quality assessment

### 5. **Batch Document Processing**
- Bulk upload and processing
- Automated risk scoring
- Compliance screening
- Quality assurance

---

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose logs

# Check port conflicts
lsof -i :8000
lsof -i :6379

# Restart services
docker-compose down
docker-compose up -d
```

### Database Connection Errors

```bash
# Verify database file
ls -lh data/documents.db

# Check permissions
chmod -R 755 data/

# Reinitialize database
rm data/documents.db
docker-compose restart document-api
```

### Missing Groq API Key

Edit `.env` file and add your Groq API key:
```bash
GROQ_API_KEY=your_actual_groq_api_key_here
```

Then restart services:
```bash
docker-compose restart
```

### Processing Stuck

```bash
# Check worker status
docker-compose logs -f celery-worker

# Restart workers
docker-compose restart celery-worker

# Check Redis connection
docker-compose exec redis redis-cli ping
```

### High Memory Usage

```bash
# Check resource usage
docker stats

# Reduce concurrent workers (edit docker-compose.yml)
# Change: celery worker --concurrency=4

# Restart with new settings
docker-compose up -d --build
```

---

## Security Notes

🔒 **CRITICAL SECURITY REQUIREMENTS:**

1. **Never commit `.env` file to git**
   - Added to `.gitignore`
   - Contains sensitive API keys

2. **Rotate API keys regularly**
   - Change Groq API key monthly
   - Update in `.env` file

3. **Use strong authentication in production**
   - Implement JWT or API key authentication
   - Add rate limiting
   - Enable HTTPS

4. **Exposed API Key Warning**
   - The Groq API key in `.env.example` (`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`) **MUST BE REVOKED**
   - This is a security vulnerability
   - Never use example keys in production

5. **File Upload Security**
   - Max file size: 100MB (configurable)
   - Allowed extensions validated
   - File type verification recommended
   - Virus scanning recommended for production

6. **Database Security**
   - Use encrypted connections in production
   - Implement proper access controls
   - Regular backups required
   - Sensitive data encryption recommended

---

## Environment Variables

### Required

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### Optional

```bash
# Database
DATABASE_URL=sqlite:///./data/documents.db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Application
DEBUG=false
LOG_LEVEL=INFO

# File Processing
MAX_FILE_SIZE=104857600  # 100MB in bytes
UPLOAD_DIR=data/uploads
PROCESSED_DIR=data/processed
ALLOWED_EXTENSIONS=.pdf,.docx,.txt,.jpg,.jpeg,.png
```

---

## Technology Stack

### Core Technologies
- **Python 3.11+** - Programming language
- **FastAPI** - Web framework
- **SQLAlchemy** - ORM
- **SQLite** - Database (PostgreSQL for production)
- **Redis** - Task queue and caching
- **Celery** - Background task processing

### AI/ML Services
- **Groq API** - LLM inference (Llama 3 70B)
- **Groq Vision API** - Vision model inference (LLaVA v1.5 7B)
- **IBM Docling** - Document understanding
- **LangGraph** - Multi-agent orchestration (optional)

### Document Processing
- **python-docx** - DOCX processing
- **pypdf** - PDF processing
- **Pillow (PIL)** - Image processing

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Uvicorn** - ASGI server

---

## API Models & Types

### Risk Levels
- `minimal` - Very low risk (0.0-0.2)
- `low` - Low risk (0.2-0.4)
- `medium` - Medium risk (0.4-0.6)
- `high` - High risk (0.6-0.8)
- `critical` - Critical risk (0.8-1.0)

### Processing Status
- `pending` - Queued for processing
- `processing` - Currently being processed
- `completed` - Successfully completed
- `failed` - Processing failed

### Document Types
- `pdf` - PDF documents
- `docx` - Word documents
- `txt` - Text files
- `jpg`, `jpeg`, `png` - Image files

---



---

## Related Documentation

- **API Documentation:** http://localhost:8000/docs (when running)
- **Architecture Details:** See code comments and docstrings
- **Groq API Docs:** https://console.groq.com/docs
- **IBM Docling:** https://github.com/DS4SD/docling


---

## Changelog

### v1.0.0 (2025-11-01)
- ✅ Initial release
- ✅ Multi-agent architecture implemented
- ✅ Groq Vision integration
- ✅ IBM Docling integration
- ✅ Complete API (16 endpoints)
- ✅ Risk scoring system
- ✅ Batch processing
- ✅ Audit trail
- ✅ Docker support

---

