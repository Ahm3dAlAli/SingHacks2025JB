from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .. import models, schemas

class CRUDRegulatoryRule:
    def get(self, db: Session, id: Any) -> Optional[models.RegulatoryRule]:
        return db.query(models.RegulatoryRule).filter(models.RegulatoryRule.rule_id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100, **kwargs
    ) -> List[models.RegulatoryRule]:
        query = db.query(models.RegulatoryRule)
        
        # Apply filters from kwargs
        for key, value in kwargs.items():
            if hasattr(models.RegulatoryRule, key):
                query = query.filter(getattr(models.RegulatoryRule, key) == value)
                
        return query.offset(skip).limit(limit).all()

    def get_by_jurisdiction(
        self, db: Session, *, jurisdiction: str, skip: int = 0, limit: int = 100
    ) -> List[models.RegulatoryRule]:
        return (
            db.query(models.RegulatoryRule)
            .filter(models.RegulatoryRule.jurisdiction == jurisdiction)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_regulator(
        self, db: Session, *, regulator: str, skip: int = 0, limit: int = 100
    ) -> List[models.RegulatoryRule]:
        return (
            db.query(models.RegulatoryRule)
            .filter(models.RegulatoryRule.regulator == regulator)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_rules(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[models.RegulatoryRule]:
        return (
            db.query(models.RegulatoryRule)
            .filter(models.RegulatoryRule.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

regulatory_rule = CRUDRegulatoryRule()
