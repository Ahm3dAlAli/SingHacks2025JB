-- ============================================
-- Alert Service Database Schema
-- ============================================
-- Database: alert_service_db
-- Created: 2025-11-01

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Main alerts table
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    transaction_id UUID NOT NULL,
    customer_id VARCHAR(50) NOT NULL,

    -- Risk Assessment
    risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
    alert_level VARCHAR(20) NOT NULL CHECK (alert_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),

    -- Content
    explanation TEXT,
    summary VARCHAR(500),
    rules_violated JSONB DEFAULT '[]'::jsonb,
    behavioral_flags JSONB DEFAULT '[]'::jsonb,
    recommended_action VARCHAR(100),

    -- Transaction Context
    transaction_data JSONB,

    -- Routing & Assignment
    assigned_to VARCHAR(100),
    priority INTEGER DEFAULT 50,

    -- Status Management
    status VARCHAR(20) DEFAULT 'NEW' CHECK (status IN ('NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE')),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR(100),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),

    -- Audit
    created_by VARCHAR(100) DEFAULT 'TAE_SERVICE',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Alert notifications tracking
-- ============================================
CREATE TABLE IF NOT EXISTS alert_notifications (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    recipient VARCHAR(255),
    status VARCHAR(20) DEFAULT 'PENDING',
    sent_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- ============================================
-- Alert notes (user comments)
-- ============================================
CREATE TABLE IF NOT EXISTS alert_notes (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL,
    note_text TEXT NOT NULL,
    created_by VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- ============================================
-- Alert status history (audit trail)
-- ============================================
CREATE TABLE IF NOT EXISTS alert_status_history (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

-- ============================================
-- Indexes for performance
-- ============================================

-- Main table indexes
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_alert_level ON alerts(alert_level);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_customer_id ON alerts(customer_id);
CREATE INDEX IF NOT EXISTS idx_alerts_assigned_to ON alerts(assigned_to);
CREATE INDEX IF NOT EXISTS idx_alerts_transaction_id ON alerts(transaction_id);

-- Foreign key indexes for child tables (performance improvement)
CREATE INDEX IF NOT EXISTS idx_alert_notifications_alert_id ON alert_notifications(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_notes_alert_id ON alert_notes(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_status_history_alert_id ON alert_status_history(alert_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_alerts_status_created ON alerts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_customer_created ON alerts(customer_id, created_at DESC);

-- ============================================
-- Trigger for updated_at column
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_alerts_updated_at
    BEFORE UPDATE ON alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Comments for documentation
-- ============================================
COMMENT ON TABLE alerts IS 'Main alerts table storing all risk alerts from TAE';
COMMENT ON TABLE alert_notifications IS 'Tracks alert notifications sent to various channels';
COMMENT ON TABLE alert_notes IS 'User comments and notes on alerts';
COMMENT ON TABLE alert_status_history IS 'Audit trail of alert status changes';

COMMENT ON COLUMN alerts.transaction_id IS 'References transactions.transaction_id in aml_monitoring database (cross-database FK enforced at application level)';
COMMENT ON COLUMN alerts.rules_violated IS 'JSONB array of regulatory rules that were violated';
COMMENT ON COLUMN alerts.behavioral_flags IS 'JSONB array of behavioral analysis flags';
COMMENT ON COLUMN alerts.transaction_data IS 'JSONB snapshot of transaction data for context';
