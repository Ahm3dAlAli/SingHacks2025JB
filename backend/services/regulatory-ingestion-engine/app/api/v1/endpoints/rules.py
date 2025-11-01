"""
API endpoints for querying extracted regulatory rules.

This module provides REST API endpoints for querying rules extracted from
regulatory documents. Rules are joined with document metadata to provide
enriched responses including jurisdiction and regulator information.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import date
from uuid import UUID

from app.db.session import get_db
from app.models.rule import Rule, RuleType, RuleStatus
from app.models.document import Document

# Create API router
router = APIRouter()


class RuleResponse(BaseModel):
    """
    Response model for a single regulatory rule.

    Enriched with document metadata (jurisdiction, regulator, title)
    from JOIN with documents table.
    """
    # Core rule fields
    id: UUID
    document_id: UUID
    rule_number: Optional[str] = None
    rule_type: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    summary: str
    full_text: str
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    status: str

    # Enriched fields from document join
    jurisdiction: Optional[str] = None
    regulator: Optional[str] = None
    document_title: Optional[str] = None

    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class RulesListResponse(BaseModel):
    """
    Response model for list of rules with pagination metadata.
    """
    rules: List[RuleResponse]
    total: int
    limit: int
    offset: int


@router.get("/", response_model=RulesListResponse)
def get_rules(
    jurisdiction: Optional[str] = Query(
        None,
        description="Filter by jurisdiction (HK, SG, CH, etc.)",
        example="HK"
    ),
    status: Optional[str] = Query(
        "ACTIVE",
        description="Filter by rule status (ACTIVE, DRAFT, INACTIVE, SUPERSEDED)",
        example="ACTIVE"
    ),
    effective_date_after: Optional[date] = Query(
        None,
        description="Filter rules effective after this date",
        example="2024-01-01"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of rules to return (1-1000)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of rules to skip for pagination"
    ),
    db: Session = Depends(get_db)
):
    """
    Query extracted regulatory rules with filtering and pagination.

    Returns rules from the regulatory database with optional filters.
    Joins with documents table to include jurisdiction and regulator information.

    **Query Parameters**:
    - **jurisdiction**: Filter by jurisdiction code (HK, SG, CH, etc.)
    - **status**: Filter by rule status (default: ACTIVE)
    - **effective_date_after**: Only rules effective after this date
    - **limit**: Page size (1-1000, default: 100)
    - **offset**: Pagination offset (default: 0)

    **Response**:
    - Returns 200 with empty list if no rules match filters
    - Includes total count of matching rules (before pagination)
    - Rules are ordered by effective_date descending (newest first)

    **Example**:
    ```
    GET /api/v1/regulatory/rules?jurisdiction=HK&status=ACTIVE&limit=10
    ```
    """
    try:
        # Build query with JOIN to enrich rules with document metadata
        query = select(Rule, Document).join(
            Document,
            Rule.document_id == Document.id
        )

        # Apply filters
        filters = []

        # Status filter (default: ACTIVE)
        if status:
            try:
                # Validate status is a valid RuleStatus enum value
                status_enum = RuleStatus[status.upper()]
                filters.append(Rule.status == status_enum)
            except KeyError:
                # Invalid status provided, return empty result
                return RulesListResponse(
                    rules=[],
                    total=0,
                    limit=limit,
                    offset=offset
                )

        # Effective date filter
        if effective_date_after:
            filters.append(Rule.effective_date >= effective_date_after)

        # Jurisdiction filter (from document table)
        if jurisdiction:
            filters.append(Document.jurisdiction == jurisdiction.upper())

        # Apply all filters
        if filters:
            query = query.where(and_(*filters))

        # Get total count (before pagination)
        count_query = select(func.count()).select_from(
            select(Rule.id).join(Document, Rule.document_id == Document.id).where(
                and_(*filters) if filters else True
            ).subquery()
        )
        total = db.execute(count_query).scalar() or 0

        # Apply ordering and pagination
        query = query.order_by(Rule.effective_date.desc()).limit(limit).offset(offset)

        # Execute query
        result = db.execute(query)
        rows = result.all()

        # Transform to response models
        rules = []
        for rule, document in rows:
            rule_dict = {
                "id": rule.id,
                "document_id": rule.document_id,
                "rule_number": rule.rule_number,
                "rule_type": rule.rule_type.value if isinstance(rule.rule_type, RuleType) else str(rule.rule_type),
                "category": rule.category,
                "subcategory": rule.subcategory,
                "summary": rule.summary,
                "full_text": rule.full_text,
                "effective_date": rule.effective_date,
                "expiry_date": rule.expiry_date,
                "status": rule.status.value if isinstance(rule.status, RuleStatus) else str(rule.status),
                # Enriched fields from document
                "jurisdiction": document.jurisdiction.value if hasattr(document.jurisdiction, 'value') else str(document.jurisdiction),
                "regulator": document.regulator,
                "document_title": document.title
            }
            rules.append(RuleResponse(**rule_dict))

        return RulesListResponse(
            rules=rules,
            total=total,
            limit=limit,
            offset=offset
        )

    except Exception as e:
        # Log error and return 500
        import logging
        logging.error(f"Error querying rules: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Database query error: {str(e)}"
        )
