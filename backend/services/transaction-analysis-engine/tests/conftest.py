"""
Pytest configuration and shared fixtures for TAE tests.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock

from app.database.models import Transaction, RegulatoryRule
from app.api.models import RuleViolation, BehavioralFlag, SeverityLevel
from app.agent_config_module.agent_config import (
    AgentConfig,
    SeverityConfig,
    JurisdictionConfig,
    reset_agent_config,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset agent configuration before each test"""
    reset_agent_config()
    yield
    reset_agent_config()


@pytest.fixture
def mock_db_session():
    """Mock async database session"""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_transaction():
    """Create a sample clean transaction"""
    return Transaction(
        id=1,
        transaction_id=uuid4(),
        booking_jurisdiction="HK",
        regulator="HKMA/SFC",
        booking_datetime=datetime.utcnow(),
        value_date=date.today(),
        amount=Decimal("5000.00"),
        currency="HKD",
        channel="ONLINE",
        product_type="FX",
        # Customer info
        customer_id="CUST-001",
        customer_type="INDIVIDUAL",
        customer_risk_rating="MEDIUM",
        customer_is_pep=False,
        kyc_last_completed=date.today() - timedelta(days=100),
        kyc_due_date=date.today() + timedelta(days=100),
        edd_required=False,
        edd_performed=False,
        # SWIFT fields
        swift_f50_present=True,
        swift_f59_present=True,
        travel_rule_complete=True,
        # FX info
        fx_indicator=True,
        fx_base_ccy="HKD",
        fx_quote_ccy="USD",
        fx_applied_rate=Decimal("7.85"),
        fx_market_rate=Decimal("7.83"),
        fx_spread_bps=250,
        # Screening
        sanctions_screening="CLEAR",
        # Cash fields
        cash_id_verified=True,
        daily_cash_total_customer=Decimal("5000.00"),
        daily_cash_txn_count=1,
        # Originator/Beneficiary
        originator_country="HK",
        beneficiary_country="US",
        # Complex products
        product_complex=False,
        suitability_assessed=True,
        # Timestamps
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def high_value_transaction(sample_transaction):
    """Transaction with high value (cash limit violation)"""
    sample_transaction.amount = Decimal("150000.00")
    sample_transaction.currency = "HKD"
    return sample_transaction


@pytest.fixture
def pep_transaction(sample_transaction):
    """Transaction from PEP customer"""
    sample_transaction.customer_is_pep = True
    sample_transaction.edd_required = True
    sample_transaction.edd_performed = False
    return sample_transaction


@pytest.fixture
def expired_kyc_transaction(sample_transaction):
    """Transaction with expired KYC"""
    sample_transaction.kyc_due_date = date.today() - timedelta(days=30)
    return sample_transaction


@pytest.fixture
def sanctions_hit_transaction(sample_transaction):
    """Transaction with sanctions hit"""
    sample_transaction.sanctions_screening = "HIT"
    sample_transaction.originator_country = "IR"
    return sample_transaction


@pytest.fixture
def travel_rule_violation_transaction(sample_transaction):
    """Transaction violating travel rule"""
    sample_transaction.amount = Decimal("2000.00")
    sample_transaction.currency = "SGD"
    sample_transaction.swift_f50_present = False
    sample_transaction.swift_f59_present = False
    sample_transaction.travel_rule_complete = False
    return sample_transaction


@pytest.fixture
def fx_spread_violation_transaction(sample_transaction):
    """Transaction with FX spread violation"""
    sample_transaction.fx_spread_bps = 350  # > 300 bps
    return sample_transaction


@pytest.fixture
def sample_regulatory_rules():
    """Create sample regulatory rules"""
    return [
        # HKMA Cash Rule
        RegulatoryRule(
            id=1,
            rule_id="HKMA-CASH-001",
            jurisdiction="HK",
            regulator="HKMA/SFC",
            rule_type="cash_limit",
            rule_text="Cash transactions exceeding HKD 8,000 require enhanced monitoring",
            rule_parameters={"threshold": 8000, "currency": "HKD"},
            severity="HIGH",
            priority=100,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
        # HKMA KYC Rule
        RegulatoryRule(
            id=2,
            rule_id="HKMA-KYC-001",
            jurisdiction="HK",
            regulator="HKMA/SFC",
            rule_type="kyc_expiry",
            rule_text="KYC must be updated every 24 months",
            rule_parameters={"expiry_months": 24},
            severity="HIGH",
            priority=90,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
        # HKMA PEP Rule
        RegulatoryRule(
            id=3,
            rule_id="HKMA-PEP-001",
            jurisdiction="HK",
            regulator="HKMA/SFC",
            rule_type="pep_screening",
            rule_text="PEPs require enhanced due diligence",
            rule_parameters={"requires_edd": True},
            severity="CRITICAL",
            priority=95,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
        # MAS Sanctions Rule
        RegulatoryRule(
            id=4,
            rule_id="MAS-SANC-001",
            jurisdiction="SG",
            regulator="MAS",
            rule_type="sanctions_screening",
            rule_text="Mandatory sanctions screening",
            rule_parameters={"screening_required": True},
            severity="CRITICAL",
            priority=100,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
        # MAS Travel Rule
        RegulatoryRule(
            id=5,
            rule_id="MAS-TRAVEL-001",
            jurisdiction="SG",
            regulator="MAS",
            rule_type="travel_rule",
            rule_text="Travel rule compliance for transfers > SGD 1,500",
            rule_parameters={"threshold": 1500, "currency": "SGD"},
            severity="HIGH",
            priority=90,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
        # MAS FX Spread Rule
        RegulatoryRule(
            id=6,
            rule_id="MAS-FX-001",
            jurisdiction="SG",
            regulator="MAS",
            rule_type="fx_spread",
            rule_text="FX spread must not exceed 300 bps",
            rule_parameters={"max_spread_bps": 300},
            severity="MEDIUM",
            priority=70,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
        # HK EDD Rule
        RegulatoryRule(
            id=7,
            rule_id="HKMA-EDD-001",
            jurisdiction="HK",
            regulator="HKMA/SFC",
            rule_type="edd_required",
            rule_text="EDD must be performed when required",
            rule_parameters={"requires_edd": True},
            severity="HIGH",
            priority=85,
            effective_date=date(2024, 1, 1),
            is_active=True,
            version=1,
        ),
    ]


@pytest.fixture
def sample_rule_violations():
    """Create sample rule violations"""
    return [
        RuleViolation(
            rule_id="HKMA-CASH-001",
            rule_type="cash_limit",
            severity=SeverityLevel.HIGH,
            score=65,
            description="Cash transaction HKD 150,000 exceeds HKD 8,000 threshold",
            jurisdiction="HK",
            parameters={"threshold": 8000, "currency": "HKD"},
        ),
        RuleViolation(
            rule_id="HKMA-PEP-001",
            rule_type="pep_screening",
            severity=SeverityLevel.CRITICAL,
            score=100,
            description="Customer is PEP - enhanced due diligence required",
            jurisdiction="HK",
            parameters={"requires_edd": True},
        ),
        RuleViolation(
            rule_id="HKMA-KYC-001",
            rule_type="kyc_expiry",
            severity=SeverityLevel.HIGH,
            score=65,
            description="KYC expired 30 days ago",
            jurisdiction="HK",
            parameters={"expiry_months": 24},
        ),
    ]


@pytest.fixture
def sample_behavioral_flags():
    """Create sample behavioral flags"""
    return [
        BehavioralFlag(
            flag_type="VELOCITY_ANOMALY",
            severity=SeverityLevel.MEDIUM,
            score=45,
            description="Transaction frequency 4x normal (12 transactions in 24h)",
            detection_details={"transactions_24h": 12, "normal_rate": 3, "multiplier": 4.0},
            historical_context={"avg_daily_transactions": 3, "days_analyzed": 30},
        ),
        BehavioralFlag(
            flag_type="SMURFING_PATTERN",
            severity=SeverityLevel.HIGH,
            score=60,
            description="5 similar transactions on same day, each below threshold",
            detection_details={
                "transaction_count": 5,
                "currency": "HKD",
                "total_amount": 37500.0,
                "avg_amount": 7500.0,
                "threshold": 8000,
            },
            historical_context={"date": "2025-10-31"},
        ),
    ]


@pytest.fixture
def historical_transactions(sample_transaction):
    """Create historical transactions for behavioral analysis"""
    transactions = []
    base_time = datetime.utcnow() - timedelta(days=10)

    # Create 20 historical transactions over 10 days
    for i in range(20):
        txn = Transaction(
            id=i + 100,
            transaction_id=uuid4(),
            booking_jurisdiction="HK",
            regulator="HKMA/SFC",
            booking_datetime=base_time + timedelta(days=i // 2, hours=i % 24),
            value_date=date.today() - timedelta(days=10 - i // 2),
            amount=Decimal("3000.00") + Decimal(str(i * 500)),  # High variation: 3K to 12.5K
            currency="HKD",
            customer_id="CUST-001",
            customer_type="INDIVIDUAL",
            customer_risk_rating="MEDIUM",
            customer_is_pep=False,
            kyc_due_date=date.today() + timedelta(days=100),
            sanctions_screening="CLEAR",
            created_at=base_time + timedelta(days=i // 2),
            updated_at=base_time + timedelta(days=i // 2),
        )
        transactions.append(txn)

    return transactions


@pytest.fixture
def high_velocity_transactions(sample_transaction):
    """Create transactions showing high velocity pattern (12 in last 24h)"""
    transactions = []
    now = datetime.utcnow()

    # Create 12 transactions in last 24 hours
    for i in range(12):
        txn = Transaction(
            id=i + 200,
            transaction_id=uuid4(),
            booking_jurisdiction="HK",
            regulator="HKMA/SFC",
            booking_datetime=now - timedelta(hours=23 - i * 2),
            value_date=date.today(),
            amount=Decimal("3000.00"),
            currency="HKD",
            customer_id="CUST-001",
            customer_type="INDIVIDUAL",
            customer_risk_rating="MEDIUM",
            customer_is_pep=False,
            kyc_due_date=date.today() + timedelta(days=100),
            sanctions_screening="CLEAR",
            created_at=now - timedelta(hours=23 - i * 2),
            updated_at=now - timedelta(hours=23 - i * 2),
        )
        transactions.append(txn)

    # Add some older transactions for baseline
    for i in range(8):
        txn = Transaction(
            id=i + 300,
            transaction_id=uuid4(),
            booking_jurisdiction="HK",
            regulator="HKMA/SFC",
            booking_datetime=now - timedelta(days=15 - i),
            value_date=date.today() - timedelta(days=15 - i),
            amount=Decimal("3000.00"),
            currency="HKD",
            customer_id="CUST-001",
            customer_type="INDIVIDUAL",
            customer_risk_rating="MEDIUM",
            customer_is_pep=False,
            kyc_due_date=date.today() + timedelta(days=100),
            sanctions_screening="CLEAR",
            created_at=now - timedelta(days=15 - i),
            updated_at=now - timedelta(days=15 - i),
        )
        transactions.append(txn)

    return transactions


@pytest.fixture
def smurfing_transactions(sample_transaction):
    """Create transactions showing smurfing pattern (5 × HKD 7,000 same day)"""
    transactions = []
    today = datetime.utcnow()

    for i in range(5):
        txn = Transaction(
            id=i + 400,
            transaction_id=uuid4(),
            booking_jurisdiction="HK",
            regulator="HKMA/SFC",
            booking_datetime=today.replace(hour=9 + i * 2, minute=30),
            value_date=date.today(),
            amount=Decimal("7000.00"),  # Below 90% of HKD 8,000 threshold (7,200)
            currency="HKD",
            customer_id="CUST-001",
            customer_type="INDIVIDUAL",
            customer_risk_rating="MEDIUM",
            customer_is_pep=False,
            kyc_due_date=date.today() + timedelta(days=100),
            sanctions_screening="CLEAR",
            created_at=today.replace(hour=9 + i * 2, minute=30),
            updated_at=today.replace(hour=9 + i * 2, minute=30),
        )
        transactions.append(txn)

    return transactions


@pytest.fixture
def custom_test_config():
    """Create custom test configuration"""
    return AgentConfig(
        severity=SeverityConfig(critical=90, high=60, medium=35, low=15),
        jurisdiction=JurisdictionConfig(hk_weight=1.5, sg_weight=1.0, ch_weight=1.2),
    )


# Groq API mocking fixtures (TASK-005)


@pytest.fixture
def mock_groq_response_rule_parser():
    """Mock Groq API response for rule parser"""
    return {
        "rule_id": "TEST-RULE-001",
        "conditions": ["cash transaction", "exceeds threshold"],
        "thresholds": {"amount": 8000, "currency": "HKD"},
        "severity_score": 85,
        "applies_to": ["CASH", "FX"],
        "required_actions": ["CTR", "Enhanced monitoring"],
    }


@pytest.fixture
def mock_groq_response_explainer():
    """Mock Groq API response for explainer"""
    return {
        "explanation": "This transaction triggered a CRITICAL alert due to multiple high-severity violations. The customer attempted a HKD 150,000 cash transaction, exceeding Hong Kong's HKD 8,000 threshold by 1,775%. Additionally, KYC documentation expired 45 days ago, and behavioral analysis detected 12 transactions in 24 hours—4x normal activity.",
        "regulatory_basis": [
            "HKMA-CASH-001: Cash Transaction Limit",
            "HKMA-KYC-002: KYC Renewal Requirements",
        ],
        "evidence": [
            "Cash amount exceeds threshold by 1,775%",
            "KYC expired 45 days ago",
            "Transaction velocity 4x normal",
        ],
        "recommended_action": "ENHANCED_DUE_DILIGENCE",
        "confidence": "HIGH",
    }


@pytest.fixture
def mock_groq_client(mock_groq_response_rule_parser, mock_groq_response_explainer):
    """Mock GroqClient for testing"""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.complete = AsyncMock()
    # Default to rule parser response
    client.complete.return_value = mock_groq_response_rule_parser
    return client
