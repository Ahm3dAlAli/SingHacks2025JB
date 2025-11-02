-- ============================================
-- AML Platform - Database Initialization
-- ============================================
-- This script creates all databases for the AML platform services

-- Create database for Transaction Analysis Engine (TAE)
CREATE DATABASE aml_monitoring;

-- Create database for Regulatory Ingestion Engine
CREATE DATABASE regulatory_db;

-- Create database for Remediation Workflow Engine
CREATE DATABASE aml_workflows;

-- Create database for Alert Service
CREATE DATABASE alert_service_db;

-- Create database for Document Corroboration Engine
CREATE DATABASE document_db;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE aml_monitoring TO postgres;
GRANT ALL PRIVILEGES ON DATABASE regulatory_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE aml_workflows TO postgres;
GRANT ALL PRIVILEGES ON DATABASE alert_service_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE document_db TO postgres;
