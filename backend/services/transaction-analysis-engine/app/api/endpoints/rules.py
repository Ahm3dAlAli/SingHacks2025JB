"""
Regulatory Rules API Endpoints

Provides read-only access to regulatory rules stored in the database.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_session
from app.database.models import RegulatoryRule
from app.api.models.rule_models import RuleResponse, RuleListResponse, RuleDetailResponse

router = APIRouter(prefix="/api/v1/rules", tags=["Regulatory Rules"])

@router.get(
    "/",
    response_model=RuleListResponse,
    summary="List all regulatory rules",
    description="Retrieve a paginated list of regulatory rules with optional filtering"
)
async def list_rules(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction code (e.g., 'HK', 'SG', 'CH')"),
    regulator: Optional[str] = Query(None, description="Filter by regulator name (e.g., 'HKMA/SFC', 'MAS', 'FINMA')"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    session: AsyncSession = Depends(get_async_session)
) -> RuleListResponse:
    """
    Retrieve a paginated list of regulatory rules with optional filtering.
    """
    try:
        # Build query
        query = select(RegulatoryRule)
        
        # Apply filters
        if jurisdiction:
            query = query.where(RegulatoryRule.jurisdiction == jurisdiction.upper())
        if regulator:
            query = query.where(RegulatoryRule.regulator == regulator)
        if rule_type:
            query = query.where(RegulatoryRule.rule_type == rule_type)
        if is_active is not None:
            query = query.where(RegulatoryRule.is_active == is_active)
            
        # Get total count for pagination
        total_query = select(func.count()).select_from(query.subquery())
        total = (await session.execute(total_query)).scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await session.execute(query)
        rules = result.scalars().all()
        
        # Convert to response models
        rule_responses = [
            RuleResponse(
                rule_id=rule.rule_id,
                jurisdiction=rule.jurisdiction,
                regulator=rule.regulator,
                rule_type=rule.rule_type,
                rule_text=rule.rule_text,
                severity=rule.severity,
                is_active=rule.is_active
            )
            for rule in rules
        ]
        
        return RuleListResponse(
            data=rule_responses,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving rules: {str(e)}"
        )

@router.get(
    "/{rule_id}",
    response_model=RuleDetailResponse,
    summary="Get rule by ID",
    responses={
        200: {"description": "Rule found"},
        404: {"description": "Rule not found"}
    }
)
async def get_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_async_session)
) -> RuleDetailResponse:
    """
    Retrieve detailed information about a specific regulatory rule.
    """
    try:
        query = select(RegulatoryRule).where(RegulatoryRule.rule_id == rule_id)
        result = await session.execute(query)
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise HTTPException(
                status_code=404,
                detail=f"Rule with ID '{rule_id}' not found"
            )
            
        return RuleDetailResponse(
            rule_id=rule.rule_id,
            jurisdiction=rule.jurisdiction,
            regulator=rule.regulator,
            rule_type=rule.rule_type,
            rule_text=rule.rule_text,
            rule_parameters=rule.rule_parameters or {},
            severity=rule.severity,
            effective_date=rule.effective_date,
            is_active=rule.is_active,
            tags=rule.tags or [],
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving rule: {str(e)}"
        )
