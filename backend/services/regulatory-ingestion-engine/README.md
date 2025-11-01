# Regulatory Ingestion Engine

> Automated Regulatory Document Processing & Rule Extraction Service

## Overview

The Regulatory Ingestion Engine is a microservice designed to process, analyze, and extract structured information from regulatory documents. It supports multiple regulatory bodies and provides a unified API for document management and rule extraction.

**Key Features**:
- Document ingestion from multiple sources (local files, APIs)
- Automated text extraction from PDF, DOCX, and HTML formats
- Rule extraction using NLP and pattern matching
- Version control for regulatory documents
- RESTful API for integration with other services

**Technology Stack**: Python, FastAPI, PostgreSQL, SQLAlchemy, spaCy, Docker

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Python 3.8+
- Ports 8003 and 5433 available

### Setup Instructions

1. **Clone and navigate to the service directory**
   ```bash
   cd backend/services/regulatory-ingestion-engine
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit .env file**
   ```bash
   nano .env  # or use your preferred editor
   ```

   Configure the following variables:
   ```
   # Database
   DB_HOST=postgres
   DB_PORT=5433
   DB_USER=reg_user
   DB_PASSWORD=reg_password
   DB_NAME=regulatory_db
   
   # Server
   HOST=0.0.0.0
   PORT=8003
   LOG_LEVEL=info
   
   # File Storage
   DOCUMENT_STORAGE_PATH=./data/documents
   UPLOAD_DIR=./data/uploads
   ```

4. **Start the services**
   ```bash
   docker-compose up -d --build
   ```

5. **Verify services are running**
   ```bash
   docker-compose ps
   ```

   Both `postgres` and `regulatory-service` should be running.

6. **Initialize the database**
   ```bash
   docker-compose exec regulatory-service alembic upgrade head
   ```

## API Documentation

Once the service is running, you can access:

- **API Documentation**: http://localhost:8003/api/docs
- **Redoc Documentation**: http://localhost:8003/api/redoc
- **Health Check**: http://localhost:8003/health

## Project Structure

```
regulatory-ingestion-engine/
├── app/
│   ├── api/                  # API endpoints and routes
│   ├── connectors/           # Document source connectors
│   ├── core/                 # Core configuration and utilities
│   ├── db/                   # Database session and connection management
│   ├── models/               # SQLAlchemy models
│   ├── processing/           # Document processing logic
│   └── rule_parsing/         # Rule extraction and processing
├── database/                 # Database initialization scripts
├── data/                    # Storage for uploaded and processed documents
├── migrations/              # Database migrations (Alembic)
├── tests/                   # Test files
├── .env.example            # Example environment variables
├── alembic.ini             # Alembic configuration
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Service Dockerfile
├── requirements.txt        # Python dependencies
└── start.sh               # Service startup script
```

## Development

### Local Development Setup

1. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Start the development server**
   ```bash
   ./start.sh
   ```

### Running Tests

```bash
pytest
```

## API Endpoints

### Documents

- `GET /api/v1/documents` - List all documents
- `GET /api/v1/documents/{document_id}` - Get document details
- `POST /api/v1/documents/upload` - Upload a new document
- `GET /api/v1/documents/sources` - List available document sources

### Processing

- `POST /api/v1/process/upload` - Upload and process a document
- `POST /api/v1/process/url` - Process a document from a URL
- `GET /api/v1/process/status/{task_id}` - Get processing status

### Rules

- `GET /api/v1/rules` - List all extracted rules
- `GET /api/v1/rules/{rule_id}` - Get rule details
- `GET /api/v1/rules/search` - Search rules by criteria

## Deployment

### Docker

Build and start the service:

```bash
docker-compose up -d --build
```

### Kubernetes

Kubernetes deployment files are provided in the `k8s/` directory.

## Monitoring

The service exposes the following monitoring endpoints:

- `/health` - Service health check
- `/metrics` - Prometheus metrics (if enabled)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FastAPI for the awesome web framework
- spaCy for NLP capabilities
- SQLAlchemy for ORM
- Alembic for database migrations

## Support

For support, please open an issue in the GitHub repository.
