-- This file is for reference - the actual database is created by SQLAlchemy
-- Additional indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_uploader ON documents(uploader_id);
CREATE INDEX IF NOT EXISTS idx_documents_risk_score ON documents(risk_score);
CREATE INDEX IF NOT EXISTS idx_audit_trail_document_id ON audit_trails(document_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp ON audit_trails(timestamp);