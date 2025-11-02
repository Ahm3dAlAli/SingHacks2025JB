from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import date

# Shared properties
class RegulatoryRuleBase(BaseModel):
    rule_id: str = Field(..., description="Unique identifier for the rule")
    jurisdiction: str = Field(..., description="Jurisdiction code (e.g., 'HK', 'SG', 'CH')")
    regulator: str = Field(..., description="Regulatory body (e.g., 'HKMA/SFC', 'MAS', 'FINMA')")
    rule_type: str = Field(..., description="Type/category of the rule")
    rule_text: str = Field(..., description="Human-readable description of the rule")
    rule_parameters: Dict[str, Any] = Field(..., description="Rule parameters in JSON format")
    severity: str = Field(..., description="Severity level (e.g., 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')")
    effective_date: date = Field(..., description="Date when the rule became/will become effective")
    is_active: bool = Field(True, description="Whether the rule is currently active")

# Properties to receive on rule creation
class RegulatoryRuleCreate(RegulatoryRuleBase):
    pass

# Properties to receive on rule update
class RegulatoryRuleUpdate(RegulatoryRuleBase):
    rule_text: Optional[str] = None
    rule_parameters: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None

# Properties shared by models stored in DB
class RegulatoryRuleInDBBase(RegulatoryRuleBase):
    class Config:
        orm_mode = True

# Properties to return to client
class RegulatoryRule(RegulatoryRuleInDBBase):
    pass

# Properties stored in DB
class RegulatoryRuleInDB(RegulatoryRuleInDBBase):
    pass
