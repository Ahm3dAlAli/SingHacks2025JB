-- Transaction Analysis Engine (TAE) - Database Schema
-- PostgreSQL 15+
-- Created: 2025-10-31

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE 1: transactions
-- Stores all transaction data from CSV with calculated fields
-- ============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    -- Primary Key
    id SERIAL PRIMARY KEY,
    transaction_id UUID UNIQUE NOT NULL,

    -- Basic Transaction Info
    booking_jurisdiction VARCHAR(10) NOT NULL,
    regulator VARCHAR(50) NOT NULL,
    booking_datetime TIMESTAMP NOT NULL,
    value_date DATE,
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    channel VARCHAR(50),
    product_type VARCHAR(50),

    -- Originator Info
    originator_name VARCHAR(255),
    originator_account VARCHAR(100),
    originator_country VARCHAR(2),

    -- Beneficiary Info
    beneficiary_name VARCHAR(255),
    beneficiary_account VARCHAR(100),
    beneficiary_country VARCHAR(2),

    -- SWIFT Fields
    swift_mt VARCHAR(20),
    ordering_institution_bic VARCHAR(11),
    beneficiary_institution_bic VARCHAR(11),
    swift_f50_present BOOLEAN DEFAULT FALSE,
    swift_f59_present BOOLEAN DEFAULT FALSE,
    swift_f70_purpose TEXT,
    swift_f71_charges VARCHAR(10),
    travel_rule_complete BOOLEAN DEFAULT FALSE,

    -- FX Info
    fx_indicator BOOLEAN DEFAULT FALSE,
    fx_base_ccy VARCHAR(3),
    fx_quote_ccy VARCHAR(3),
    fx_applied_rate DECIMAL(10, 6),
    fx_market_rate DECIMAL(10, 6),
    fx_spread_bps INTEGER,
    fx_counterparty VARCHAR(255),

    -- Customer Info
    customer_id VARCHAR(50) NOT NULL,
    customer_type VARCHAR(50),
    customer_risk_rating VARCHAR(20),
    customer_is_pep BOOLEAN DEFAULT FALSE,
    kyc_last_completed DATE,
    kyc_due_date DATE,
    edd_required BOOLEAN DEFAULT FALSE,
    edd_performed BOOLEAN DEFAULT FALSE,
    sow_documented BOOLEAN DEFAULT FALSE,

    -- Transaction Details
    purpose_code VARCHAR(10),
    narrative TEXT,
    is_advised BOOLEAN DEFAULT FALSE,
    product_complex BOOLEAN DEFAULT FALSE,
    client_risk_profile VARCHAR(20),
    suitability_assessed BOOLEAN DEFAULT FALSE,
    suitability_result VARCHAR(50),
    product_has_va_exposure BOOLEAN DEFAULT FALSE,
    va_disclosure_provided BOOLEAN DEFAULT FALSE,

    -- Cash Transaction Fields
    cash_id_verified BOOLEAN DEFAULT FALSE,
    daily_cash_total_customer DECIMAL(15, 2) DEFAULT 0,
    daily_cash_txn_count INTEGER DEFAULT 0,

    -- Screening & Compliance
    sanctions_screening VARCHAR(20),
    suspicion_determined_datetime TIMESTAMP,
    str_filed_datetime TIMESTAMP,

    -- Flexible Storage
    raw_data JSONB,

    -- Batch Processing
    batch_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_transactions_transaction_id ON transactions(transaction_id);
CREATE INDEX idx_transactions_customer_id ON transactions(customer_id);
CREATE INDEX idx_transactions_booking_datetime ON transactions(booking_datetime);
CREATE INDEX idx_transactions_batch_id ON transactions(batch_id);
CREATE INDEX idx_transactions_jurisdiction ON transactions(booking_jurisdiction);
CREATE INDEX idx_transactions_sanctions ON transactions(sanctions_screening);

-- ============================================================================
-- TABLE 2: risk_assessments
-- Final risk scores and analysis results per transaction
-- ============================================================================
CREATE TABLE IF NOT EXISTS risk_assessments (
    id SERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id) ON DELETE CASCADE,

    -- Risk Scoring
    risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    alert_level VARCHAR(20) NOT NULL CHECK (alert_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),

    -- Analysis Results
    rules_triggered JSONB DEFAULT '[]'::jsonb,
    patterns_detected JSONB DEFAULT '[]'::jsonb,
    explanation TEXT,

    -- Agent Contributions
    static_rules_score INTEGER,
    behavioral_score INTEGER,

    -- Timestamps
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(transaction_id)
);

-- Indexes for risk_assessments
CREATE INDEX idx_risk_assessments_transaction_id ON risk_assessments(transaction_id);
CREATE INDEX idx_risk_assessments_alert_level ON risk_assessments(alert_level);
CREATE INDEX idx_risk_assessments_risk_score ON risk_assessments(risk_score);

-- ============================================================================
-- TABLE 3: agent_execution_logs
-- Audit trail of each agent's execution for debugging and compliance
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_execution_logs (
    id SERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL,
    agent_name VARCHAR(100) NOT NULL,

    -- Execution Data
    input_data JSONB,
    output_data JSONB,
    execution_time_ms INTEGER,

    -- Status Tracking
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'skipped')),
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agent_execution_logs
CREATE INDEX idx_agent_logs_transaction_id ON agent_execution_logs(transaction_id);
CREATE INDEX idx_agent_logs_agent_name ON agent_execution_logs(agent_name);
CREATE INDEX idx_agent_logs_status ON agent_execution_logs(status);
CREATE INDEX idx_agent_logs_created_at ON agent_execution_logs(created_at);

-- ============================================================================
-- TABLE 4: audit_trail
-- System-wide audit log for regulatory compliance
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_trail (
    id SERIAL PRIMARY KEY,

    -- Service & Action
    service_name VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,

    -- User Info (for future multi-user support)
    user_id VARCHAR(100),

    -- Resource Info
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),

    -- Details
    details JSONB,

    -- Network Info
    ip_address INET,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit_trail
CREATE INDEX idx_audit_trail_service_name ON audit_trail(service_name);
CREATE INDEX idx_audit_trail_action ON audit_trail(action);
CREATE INDEX idx_audit_trail_resource_type ON audit_trail(resource_type);
CREATE INDEX idx_audit_trail_created_at ON audit_trail(created_at);

-- ============================================================================
-- TABLE 5: regulatory_rules
-- Read-only table containing regulatory rules (written by Service 1)
-- ============================================================================
CREATE TABLE IF NOT EXISTS regulatory_rules (
    id SERIAL PRIMARY KEY,

    -- Rule Identification
    rule_id VARCHAR(50) UNIQUE NOT NULL,
    jurisdiction VARCHAR(10) NOT NULL,
    regulator VARCHAR(50) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,

    -- Rule Content
    rule_text TEXT NOT NULL,
    rule_parameters JSONB,

    -- Severity & Priority
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    priority INTEGER DEFAULT 100,

    -- Versioning
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,

    -- Metadata
    source_url TEXT,
    tags VARCHAR(255)[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for regulatory_rules
CREATE INDEX idx_regulatory_rules_rule_id ON regulatory_rules(rule_id);
CREATE INDEX idx_regulatory_rules_jurisdiction ON regulatory_rules(jurisdiction);
CREATE INDEX idx_regulatory_rules_regulator ON regulatory_rules(regulator);
CREATE INDEX idx_regulatory_rules_is_active ON regulatory_rules(is_active);
CREATE INDEX idx_regulatory_rules_effective_date ON regulatory_rules(effective_date);

-- ============================================================================
-- TABLE 6: batch_metadata
-- Tracks batch processing status for CSV uploads
-- ============================================================================
CREATE TABLE IF NOT EXISTS batch_metadata (
    -- Primary Key
    batch_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Batch Info
    filename VARCHAR(255) NOT NULL,
    total_transactions INTEGER NOT NULL,
    processed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,

    -- Status Tracking
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),

    -- Timestamps
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,

    -- Error Handling
    error_message TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for batch_metadata
CREATE INDEX idx_batch_metadata_batch_id ON batch_metadata(batch_id);
CREATE INDEX idx_batch_metadata_status ON batch_metadata(status);
CREATE INDEX idx_batch_metadata_created_at ON batch_metadata(created_at);

-- ============================================================================
-- TRIGGERS for updated_at timestamps
-- ============================================================================

-- Function to update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_risk_assessments_updated_at BEFORE UPDATE ON risk_assessments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_regulatory_rules_updated_at BEFORE UPDATE ON regulatory_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_batch_metadata_updated_at BEFORE UPDATE ON batch_metadata
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- GRANTS (for tae_user)
-- ============================================================================

-- These will be applied after user creation in docker-compose
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tae_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tae_user;
