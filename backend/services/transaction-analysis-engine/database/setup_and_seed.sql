-- Drop the table if it exists to start fresh
DROP TABLE IF EXISTS regulatory_rules CASCADE;

-- Create the table with the correct schema
CREATE TABLE regulatory_rules (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL UNIQUE,
    jurisdiction VARCHAR(10) NOT NULL,
    regulator VARCHAR(50) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    rule_text TEXT NOT NULL,
    rule_parameters JSONB NOT NULL,
    severity VARCHAR(20) NOT NULL,
    priority INTEGER NOT NULL,
    effective_date DATE NOT NULL,
    expiry_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    version VARCHAR(20),
    source_url TEXT,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_regulatory_rules_jurisdiction ON regulatory_rules(jurisdiction);
CREATE INDEX idx_regulatory_rules_rule_type ON regulatory_rules(rule_type);
CREATE INDEX idx_regulatory_rules_severity ON regulatory_rules(severity);
CREATE INDEX idx_regulatory_rules_is_active ON regulatory_rules(is_active);

-- Insert seed data
INSERT INTO regulatory_rules (rule_id, jurisdiction, regulator, rule_type, rule_text, rule_parameters, severity, priority, effective_date, is_active) VALUES
('HKMA-CASH-001', 'HK', 'HKMA/SFC', 'cash_limit',
 'Cash transactions exceeding HKD 8,000 require enhanced monitoring and potential reporting under anti-money laundering guidelines.',
 '{"threshold": 8000, "currency": "HKD", "action": "enhanced_monitoring"}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('HKMA-KYC-001', 'HK', 'HKMA/SFC', 'kyc_expiry',
 'All customer KYC documentation must be updated at least every 24 months. Transactions from customers with expired KYC must be flagged for review.',
 '{"expiry_months": 24, "action": "flag_for_review"}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('HKMA-PEP-001', 'HK', 'HKMA/SFC', 'pep_screening',
 'All transactions involving Politically Exposed Persons (PEPs) require enhanced due diligence and senior management approval.',
 '{"requires_edd": true, "requires_approval": "senior_management"}'::jsonb,
 'CRITICAL', 200, '2024-01-01', true),

('SFC-VA-001', 'HK', 'HKMA/SFC', 'virtual_asset',
 'Products with virtual asset exposure must have proper risk disclosure provided to clients. Suitability assessment is mandatory.',
 '{"requires_disclosure": true, "requires_suitability": true}'::jsonb,
 'MEDIUM', 50, '2024-06-01', true),

('HKMA-STR-001', 'HK', 'HKMA/SFC', 'suspicious_transaction',
 'Suspicious transaction reports (STR) must be filed with JFIU within 14 days of suspicion determination.',
 '{"filing_deadline_days": 14, "authority": "JFIU"}'::jsonb,
 'CRITICAL', 200, '2024-01-01', true),

('MAS-TRAVEL-001', 'SG', 'MAS', 'travel_rule',
 'Virtual asset transfers exceeding SGD 1,500 must include originator and beneficiary information (Travel Rule compliance).',
 '{"threshold": 1500, "currency": "SGD", "requires_originator_info": true}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('MAS-SANC-001', 'SG', 'MAS', 'sanctions_screening',
 'Mandatory sanctions screening against MAS consolidated list for all transactions. Potential matches require immediate escalation.',
 '{"screening_required": true, "escalation_level": "immediate"}'::jsonb,
 'CRITICAL', 200, '2024-01-01', true),

('MAS-FX-001', 'SG', 'MAS', 'fx_spread',
 'Foreign exchange spreads exceeding 50 basis points from market rate require justification and disclosure to clients.',
 '{"max_spread_bps": 50, "requires_justification": true}'::jsonb,
 'MEDIUM', 50, '2024-01-01', true),

('MAS-CASH-001', 'SG', 'MAS', 'cash_structuring',
 'Multiple cash transactions below SGD 5,000 within 24 hours from same customer may indicate structuring. Enhanced monitoring required.',
 '{"threshold": 5000, "currency": "SGD", "time_window_hours": 24}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('MAS-EDD-001', 'SG', 'MAS', 'enhanced_dd',
 'Enhanced due diligence required for high-risk customers including PEPs, customers from high-risk jurisdictions, and complex ownership structures.',
 '{"triggers": ["pep", "high_risk_country", "complex_structure"], "requires_edd": true}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('FINMA-CASH-001', 'CH', 'FINMA', 'cash_limit',
 'Cash transactions exceeding CHF 15,000 require identification verification and source of funds documentation.',
 '{"threshold": 15000, "currency": "CHF", "requires_id": true, "requires_sof": true}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('FINMA-EDD-001', 'CH', 'FINMA', 'enhanced_dd',
 'Enhanced due diligence mandatory for clients from high-risk countries, complex ownership structures, and transactions exceeding CHF 100,000.',
 '{"high_risk_threshold": 100000, "currency": "CHF", "requires_ownership_verification": true}'::jsonb,
 'HIGH', 100, '2024-01-01', true),

('FINMA-SOW-001', 'CH', 'FINMA', 'source_of_wealth',
 'Source of wealth documentation required for all new client relationships and when cumulative transactions exceed CHF 500,000.',
 '{"new_client": true, "cumulative_threshold": 500000, "currency": "CHF"}'::jsonb,
 'MEDIUM', 50, '2024-01-01', true),

('FINMA-PEP-001', 'CH', 'FINMA', 'pep_identification',
 'Politically exposed persons must be identified at onboarding. Senior management approval required for establishing PEP relationships.',
 '{"onboarding_check": true, "requires_approval": "senior_management"}'::jsonb,
 'CRITICAL', 200, '2024-01-01', true),

('FINMA-COMPLEX-001', 'CH', 'FINMA', 'complex_products',
 'Complex financial products require suitability assessment and risk profile matching. Clients must acknowledge understanding of risks.',
 '{"requires_suitability": true, "requires_acknowledgment": true, "risk_profile_match": true}'::jsonb,
 'MEDIUM', 50, '2024-01-01', true);

-- Verify the data was loaded
SELECT COUNT(*) as total_rules,
       COUNT(CASE WHEN jurisdiction = 'HK' THEN 1 END) as hk_rules,
       COUNT(CASE WHEN jurisdiction = 'SG' THEN 1 END) as sg_rules,
       COUNT(CASE WHEN jurisdiction = 'CH' THEN 1 END) as ch_rules
FROM regulatory_rules;
