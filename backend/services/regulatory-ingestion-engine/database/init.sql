-- Create the database schema for Regulatory Ingestion Engine

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Document Sources
CREATE TABLE IF NOT EXISTS document_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL, -- 'API', 'EMAIL', 'RSS', 'UPLOAD', etc.
    config JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- Regulatory Documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES document_sources(id) ON DELETE SET NULL,
    external_id VARCHAR(255),
    title TEXT NOT NULL,
    document_type VARCHAR(100) NOT NULL, -- 'REGULATION', 'GUIDELINE', 'CIRCULAR', etc.
    jurisdiction VARCHAR(100) NOT NULL,  -- 'HK', 'SG', 'CH', etc.
    regulator VARCHAR(100) NOT NULL,     -- 'HKMA', 'MAS', 'FINMA', etc.
    document_date DATE,
    effective_date DATE,
    expiry_date DATE,
    status VARCHAR(50) DEFAULT 'DRAFT',  -- 'DRAFT', 'ACTIVE', 'WITHDRAWN', 'SUPERSEDED'
    raw_content TEXT,
    file_path TEXT,
    file_type VARCHAR(50),
    file_size BIGINT,
    checksum VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, external_id)
);

-- Document Versions
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    version_date TIMESTAMP WITH TIME ZONE NOT NULL,
    change_summary TEXT,
    raw_content TEXT NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, version_number)
);

-- Extracted Rules
CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    rule_number VARCHAR(50),
    rule_type VARCHAR(50) NOT NULL, -- 'OBLIGATION', 'PROHIBITION', 'REQUIREMENT', 'EXEMPTION'
    category VARCHAR(100),
    subcategory VARCHAR(100),
    summary TEXT NOT NULL,
    full_text TEXT NOT NULL,
    effective_date DATE,
    expiry_date DATE,
    status VARCHAR(50) DEFAULT 'DRAFT', -- 'DRAFT', 'ACTIVE', 'INACTIVE'
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, rule_number)
);

-- Rule Attributes
CREATE TABLE IF NOT EXISTS rule_attributes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value TEXT,
    data_type VARCHAR(50), -- 'STRING', 'NUMBER', 'DATE', 'BOOLEAN', 'JSON'
    confidence_score FLOAT,
    extraction_method VARCHAR(50), -- 'MANUAL', 'NLP', 'TEMPLATE', 'LLM'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(rule_id, attribute_name)
);

-- Rule Relationships
CREATE TABLE IF NOT EXISTS rule_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    target_rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL, -- 'REFERENCES', 'AMENDS', 'SUPERSEDES', 'RELATED_TO'
    description TEXT,
    confidence_score FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_rule_id, target_rule_id, relationship_type),
    CHECK (source_rule_id != target_rule_id)
);

-- Processing Logs
CREATE TABLE IF NOT EXISTS processing_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    process_name VARCHAR(100) NOT NULL, -- 'INGESTION', 'EXTRACTION', 'PARSING', 'VALIDATION'
    status VARCHAR(50) NOT NULL, -- 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit Trail
CREATE TABLE IF NOT EXISTS audit_trail (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL, -- 'DOCUMENT', 'RULE', 'SOURCE', etc.
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100) DEFAULT 'system',
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_documents_jurisdiction ON documents(jurisdiction, regulator);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_document_date ON documents(document_date);
CREATE INDEX IF NOT EXISTS idx_rules_document_id ON rules(document_id);
CREATE INDEX IF NOT EXISTS idx_rules_rule_type ON rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_rules_status ON rules(status);
CREATE INDEX IF NOT EXISTS idx_rule_attributes_rule_id ON rule_attributes(rule_id);
CREATE INDEX IF NOT EXISTS idx_processing_logs_document_id ON processing_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_audit_trail_entity ON audit_trail(entity_type, entity_id);

-- Create a function to update the updated_at column
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to update updated_at columns
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.columns 
        WHERE column_name = 'updated_at' 
        AND table_schema = 'public'
        AND table_name IN ('documents', 'rules', 'rule_attributes')
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS update_%s_updated_at ON %I', 
                      t.table_name, t.table_name);
        EXECUTE format('CREATE TRIGGER update_%s_updated_at
                      BEFORE UPDATE ON %I
                      FOR EACH ROW EXECUTE FUNCTION update_modified_column()',
                      t.table_name, t.table_name);
    END LOOP;
END;
$$;

-- Create audit trail trigger function
CREATE OR REPLACE FUNCTION log_audit_trail()
RETURNS TRIGGER AS $$
DECLARE
    old_data JSONB;
    new_data JSONB;
    audit_action VARCHAR(50);
BEGIN
    IF TG_OP = 'INSERT' THEN
        audit_action := 'CREATE';
        old_data := NULL;
        new_data := to_jsonb(NEW);
    ELSIF TG_OP = 'UPDATE' THEN
        audit_action := 'UPDATE';
        old_data := to_jsonb(OLD);
        new_data := to_jsonb(NEW);
    ELSIF TG_OP = 'DELETE' THEN
        audit_action := 'DELETE';
        old_data := to_jsonb(OLD);
        new_data := NULL;
    END IF;

    INSERT INTO audit_trail (
        action,
        entity_type,
        entity_id,
        old_values,
        new_values,
        changed_by
    ) VALUES (
        audit_action,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        old_data,
        new_data,
        current_user
    );

    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create audit triggers for key tables
DO $$
DECLARE
    t record;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name IN ('documents', 'document_versions', 'rules', 'rule_attributes', 'document_sources')
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS audit_trigger_%s ON %I', 
                      t.table_name, t.table_name);
        EXECUTE format('CREATE TRIGGER audit_trigger_%s
                      AFTER INSERT OR UPDATE OR DELETE ON %I
                      FOR EACH ROW EXECUTE FUNCTION log_audit_trail()',
                      t.table_name, t.table_name);
    END LOOP;
END;
$$;

-- Create a function to get the current version of a document
CREATE OR REPLACE FUNCTION get_document_current_version(document_uuid UUID)
RETURNS TABLE (
    document_id UUID,
    version_number INTEGER,
    version_date TIMESTAMP WITH TIME ZONE,
    change_summary TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dv.document_id,
        dv.version_number,
        dv.version_date,
        dv.change_summary
    FROM document_versions dv
    WHERE dv.document_id = document_uuid
    ORDER BY dv.version_number DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql STABLE;
