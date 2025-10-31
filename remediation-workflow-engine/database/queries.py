from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .models import WorkflowInstance, WorkflowAction, AuditEntry, Document, EmailTemplate

class WorkflowQueries:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_workflow_instance(self, alert_data: Dict[str, Any]) -> WorkflowInstance:
        """Create a new workflow instance"""
        workflow = WorkflowInstance(
            alert_id=alert_data["alert_id"],
            workflow_template=alert_data.get("workflow_template", "standard"),
            risk_score=alert_data["risk_score"],
            severity=alert_data["severity"],
            customer_id=alert_data["customer_id"],
            jurisdiction=alert_data["jurisdiction"],
            state_data=alert_data,
            assigned_to=alert_data.get("assigned_to", "system")
        )
        
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        
        # Create initial audit entry
        await self.create_audit_entry(
            workflow_instance_id=workflow.id,
            action="workflow_created",
            details=f"Workflow created for alert {alert_data['alert_id']}",
            user="system"
        )
        
        return workflow
    
    async def get_workflow_instance(self, workflow_instance_id: str) -> Optional[WorkflowInstance]:
        """Get workflow instance by ID"""
        result = await self.db.execute(
            select(WorkflowInstance).where(WorkflowInstance.id == workflow_instance_id)
        )
        return result.scalar_one_or_none()
    
    async def update_workflow_state(self, workflow_instance_id: str, updates: Dict[str, Any]) -> WorkflowInstance:
        """Update workflow instance state"""
        # Add updated timestamp
        updates["updated_at"] = datetime.utcnow()
        
        await self.db.execute(
            update(WorkflowInstance)
            .where(WorkflowInstance.id == workflow_instance_id)
            .values(**updates)
        )
        await self.db.commit()
        
        # Return updated workflow
        return await self.get_workflow_instance(workflow_instance_id)
    
    async def create_workflow_action(self, workflow_instance_id: str, action_data: Dict[str, Any]) -> WorkflowAction:
        """Create a workflow action"""
        action = WorkflowAction(
            workflow_instance_id=workflow_instance_id,
            action_type=action_data["action_type"],
            action_name=action_data["action_name"],
            parameters=action_data.get("parameters", {}),
            status=action_data.get("status", "pending")
        )
        
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action
    
    async def update_action_status(self, action_id: str, status: str, result_data: Dict[str, Any] = None) -> WorkflowAction:
        """Update action status"""
        updates = {"status": status, "updated_at": datetime.utcnow()}
        
        if status == "in_progress" and not result_data:
            updates["started_at"] = datetime.utcnow()
        elif status in ["completed", "failed"]:
            updates["completed_at"] = datetime.utcnow()
            if result_data:
                updates["result_data"] = result_data
        
        await self.db.execute(
            update(WorkflowAction)
            .where(WorkflowAction.id == action_id)
            .values(**updates)
        )
        await self.db.commit()
        
        result = await self.db.execute(
            select(WorkflowAction).where(WorkflowAction.id == action_id)
        )
        return result.scalar_one_or_none()
    
    async def create_audit_entry(self, workflow_instance_id: str, action: str, details: str, user: str = "system", metadata: Dict = None) -> AuditEntry:
        """Create audit entry"""
        audit_entry = AuditEntry(
            workflow_instance_id=workflow_instance_id,
            action=action,
            details=details,
            user=user,
            metadata=metadata or {}
        )
        
        self.db.add(audit_entry)
        await self.db.commit()
        await self.db.refresh(audit_entry)
        return audit_entry
    
    async def get_workflow_audit_trail(self, workflow_instance_id: str) -> List[AuditEntry]:
        """Get audit trail for workflow instance"""
        result = await self.db.execute(
            select(AuditEntry)
            .where(AuditEntry.workflow_instance_id == workflow_instance_id)
            .order_by(AuditEntry.timestamp)
        )
        return result.scalars().all()
    
    async def get_pending_workflows(self) -> List[WorkflowInstance]:
        """Get workflows that need attention"""
        result = await self.db.execute(
            select(WorkflowInstance)
            .where(WorkflowInstance.status == "active")
            .order_by(WorkflowInstance.updated_at.desc())
        )
        return result.scalars().all()
    
    async def get_sla_breach_workflows(self) -> List[WorkflowInstance]:
        """Get workflows that have breached SLA"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)  # 24h SLA
        result = await self.db.execute(
            select(WorkflowInstance)
            .where(
                (WorkflowInstance.status == "active") &
                (WorkflowInstance.updated_at < cutoff_time)
            )
        )
        return result.scalars().all()

class EmailTemplateQueries:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_email_template(self, template_name: str) -> Optional[EmailTemplate]:
        """Get email template by name"""
        result = await self.db.execute(
            select(EmailTemplate).where(EmailTemplate.template_name == template_name)
        )
        return result.scalar_one_or_none()
    
    async def create_email_template(self, template_data: Dict[str, Any]) -> EmailTemplate:
        """Create new email template"""
        template = EmailTemplate(**template_data)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template