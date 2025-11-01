from typing import Dict, Any, List
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self):
        self.audit_log = []
    
    async def log_action(self, workflow_instance_id: str, action: str, 
                        user: str, details: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Log action to audit trail"""
        
        audit_entry = {
            "id": f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            "workflow_instance_id": workflow_instance_id,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user": user,
            "details": details,
            "metadata": metadata or {}
        }
        
        self.audit_log.append(audit_entry)
        logger.info(f"Audit log: {action} for workflow {workflow_instance_id}")
        
        return audit_entry
    
    async def get_audit_trail(self, workflow_instance_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for workflow instance"""
        
        return [entry for entry in self.audit_log 
                if entry["workflow_instance_id"] == workflow_instance_id]
    
    async def log_workflow_start(self, workflow_instance_id: str, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log workflow start"""
        
        return await self.log_action(
            workflow_instance_id=workflow_instance_id,
            action="workflow_started",
            user="system",
            details=f"Workflow started for alert {alert_data.get('alert_id')}",
            metadata={"alert_data": alert_data}
        )
    
    async def log_workflow_completion(self, workflow_instance_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Log workflow completion"""
        
        return await self.log_action(
            workflow_instance_id=workflow_instance_id,
            action="workflow_completed", 
            user="system",
            details=f"Workflow completed with status {result.get('status')}",
            metadata={"completion_result": result}
        )
    
    async def log_escalation(self, workflow_instance_id: str, escalation_reason: str, level: int) -> Dict[str, Any]:
        """Log workflow escalation"""
        
        return await self.log_action(
            workflow_instance_id=workflow_instance_id,
            action="workflow_escalated",
            user="system", 
            details=f"Workflow escalated to level {level}: {escalation_reason}",
            metadata={"escalation_level": level, "reason": escalation_reason}
        )