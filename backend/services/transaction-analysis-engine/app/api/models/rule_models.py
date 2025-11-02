"""
Pydantic models for Regulatory Rules API responses.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RuleBase(BaseModel):
    """Base model for rule responses."""
    rule_id: str = Field(..., description="Unique identifier for the rule")
    jurisdiction: str = Field(..., description="Jurisdiction code (e.g., 'HK', 'SG', 'CH')")
    regulator: str = Field(..., description="Regulatory body (e.g., 'HKMA/SFC', 'MAS', 'FINMA')")
    rule_type: str = Field(..., description="Type/category of the rule")
    rule_text: str = Field(..., description="Human-readable description of the rule")
    severity: str = Field(..., description="Severity level (e.g., 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW')")
    is_active: bool = Field(..., description="Whether the rule is currently active")


class RuleResponse(RuleBase):
    """Response model for listing rules with essential fields."""
    pass


class RuleDetailResponse(RuleResponse):
    """Detailed response model for a single rule with all fields."""
    rule_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Rule parameters in JSON format"
    )
    effective_date: datetime = Field(
        ...,
        description="Date when the rule became/will become effective"
    )
    expiry_date: Optional[datetime] = Field(
        None,
        description="Date when the rule expires (if applicable)"
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing the rule"
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the rule was created"
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the rule was last updated"
    )


class RuleListResponse(BaseModel):
    """Response model for paginated list of rules."""
    data: List[RuleResponse] = Field(
        ...,
        description="List of regulatory rules"
    )
    total: int = Field(
        ...,
        description="Total number of rules matching the filter criteria"
    )
    skip: int = Field(
        ...,
        description="Number of records skipped for pagination"
    )
    limit: int = Field(
        ...,
        description="Maximum number of records returned per page"
    )

    class Config:
        schema_extra = {
            "example": {
                "data": [
                    {
                        "rule_id": "HKMA-CASH-001",
                        "jurisdiction": "HK",
                        "regulator": "HKMA/SFC",
                        "rule_type": "cash_limit",
                        "rule_text": "Cash transactions exceeding HKD 8,000 require enhanced monitoring...",
                        "severity": "HIGH",
                        "is_active": True
                    }
                ],
                "total": 15,
                "skip": 0,
                "limit": 10
            }
        }


class RuleSyncRequest(BaseModel):
    """Request model for rule synchronization.
    
    This model is used to request synchronization of regulatory rules from the regulatory service.
    """
    jurisdiction: Optional[str] = Field(
        None,
        description="Filter rules by jurisdiction (e.g., 'HK', 'SG', 'CH'). If not provided, all jurisdictions are included."
    )
    force: bool = Field(
        False,
        description="Force synchronization even if no changes are detected"
    )
    dry_run: bool = Field(
        False,
        description="If true, performs a dry run without making any changes"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "HK",
                "force": False,
                "dry_run": False
            }
        }
    }


class RuleSyncResponse(BaseModel):
    """Response model for rule synchronization.
    
    This model provides a summary of the rule synchronization operation.
    """
    status: str = Field(..., description="Synchronization status (e.g., 'COMPLETED', 'FAILED')")
    timestamp: datetime = Field(..., description="Synchronization timestamp")
    duration_seconds: float = Field(..., description="Duration of the synchronization in seconds")
    
    # Statistics
    total_rules: int = Field(..., description="Total number of rules processed")
    rules_added: int = Field(..., description="Number of new rules added")
    rules_updated: int = Field(..., description="Number of existing rules updated")
    rules_deactivated: int = Field(..., description="Number of rules deactivated (no longer in source)")
    rules_skipped: int = Field(..., description="Number of rules skipped (no changes)")
    
    # Metadata
    jurisdiction: Optional[str] = Field(
        None,
        description="Jurisdiction filter used for synchronization, if any"
    )
    dry_run: bool = Field(..., description="Whether this was a dry run")
    
    # Error information (if any)
    error: Optional[str] = Field(
        None,
        description="Error message if synchronization failed"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "COMPLETED",
                "timestamp": "2025-01-15T14:30:00Z",
                "duration_seconds": 2.45,
                "total_rules": 15,
                "rules_added": 3,
                "rules_updated": 5,
                "rules_deactivated": 2,
                "rules_skipped": 5,
                "jurisdiction": "HK",
                "dry_run": False,
                "error": None
            }
        }
    }
