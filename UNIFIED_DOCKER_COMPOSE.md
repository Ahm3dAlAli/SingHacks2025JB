# Unified Docker Compose Architecture

## Summary
All three AML platform services now use a single unified `docker-compose.yml` at the root level with one shared PostgreSQL database container.

## Changes Made

### 1. Moved Remediation Workflow Engine
- Moved `remediation-workflow-engine/` → `backend/services/remediation-workflow-engine/`
- Now consistent with other services structure

### 2. Created Unified Docker Compose
- **Location**: `/docker-compose.yml` (root level)
- **Single PostgreSQL Container**: `postgres` (port 5432)
- **Three Databases**:
  - `aml_monitoring` - Transaction Analysis Engine
  - `regulatory_db` - Regulatory Ingestion Engine  
  - `aml_workflows` - Remediation Workflow Engine

### 3. Service Configuration

#### PostgreSQL (Shared Database)
- Container: `aml_postgres`
- Port: `5432`
- Initializes all three databases via scripts
- Single data volume: `postgres_data`

#### Transaction Analysis Engine (TAE)
- Container: `tae_service`
- Port: `8002`
- Database: `aml_monitoring`
- Context: `./backend/services/transaction-analysis-engine`

#### Regulatory Ingestion Engine
- Container: `regulatory_service`
- Port: `8003`
- Database: `regulatory_db`
- Context: `./backend/services/regulatory-ingestion-engine`

#### Remediation Workflow Engine
- Container: `remediation_service`
- Port: `8004`
- Database: `aml_workflows`
- Context: `./backend/services/remediation-workflow-engine`

#### PgAdmin
- Container: `aml_pgadmin`
- Port: `5050`
- Access to all databases

### 4. Database Initialization
- **Location**: `backend/database/init-all-dbs.sql`
- Creates all three databases on first startup
- Service-specific schemas loaded from their respective init scripts

### 5. Network
- Single network: `aml_network`
- All services can communicate with each other

## Usage

### Start all services
```bash
docker-compose up -d
```

### Start specific service
```bash
docker-compose up -d tae-service
docker-compose up -d regulatory-service
docker-compose up -d remediation-service
```

### View logs
```bash
docker-compose logs -f [service-name]
```

### Stop all services
```bash
docker-compose down
```

### Stop and remove volumes
```bash
docker-compose down -v
```

## Environment Variables
Create a `.env` file at the root with:
```env
# Global
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
GROQ_API_KEY=your_key_here
ENVIRONMENT=development

# Database names
TAE_POSTGRES_DB=aml_monitoring
REGULATORY_DB_NAME=regulatory_db
REMEDIATION_DB_NAME=aml_workflows

# SMTP for Remediation Service
SMTP_SERVER=smtp.company.com
SMTP_PORT=587

# PgAdmin
PGADMIN_EMAIL=admin@aml.com
PGADMIN_PASSWORD=admin123
```

## Benefits
1. Single PostgreSQL instance reduces resource usage
2. Simplified management and maintenance
3. All services on one network for easy communication
4. Centralized configuration at root level
5. Consistent service structure in `backend/services/`
