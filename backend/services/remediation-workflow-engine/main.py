from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import logging
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory storage for development
workflow_instances = {}
audit_trail = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting AML Remediation Workflow Engine...")
    yield
    # Shutdown
    logger.info("🛑 AML Remediation Workflow Engine Stopped")

app = FastAPI(
    title="AML Remediation Workflow Engine",
    description="AI-Powered Remediation Workflows for AML Compliance",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class AlertRequest(BaseModel):
    alert_id: str
    risk_score: float
    severity: str
    customer_id: str
    transaction_ids: List[str]
    triggered_rules: List[str]
    customer_profile: Dict
    jurisdiction: str
    alert_type: str

class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str
    status: str
    current_step: str
    progress: float
    created_at: datetime
    updated_at: datetime

@app.get("/")
async def root():
    return {
        "status": "active", 
        "service": "AML Remediation Workflows",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "workflows_active": len(workflow_instances),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v1/workflows/start")
async def start_remediation_workflow(alert: AlertRequest):
    """Start a new remediation workflow for an alert"""
    try:
        workflow_instance_id = f"WF_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        
        # Simple workflow selection logic
        if alert.risk_score >= 85:
            selected_workflow = "CRITICAL_BLOCK_WORKFLOW"
            assigned_to = "senior_compliance_officer"
        elif alert.customer_profile.get("is_pep", False):
            selected_workflow = "EDD_PEP_WORKFLOW"
            assigned_to = "compliance_team_lead"
        elif alert.risk_score >= 60:
            selected_workflow = "EDD_STANDARD_WORKFLOW"
            assigned_to = "compliance_analyst"
        else:
            selected_workflow = "ENHANCED_MONITORING_WORKFLOW"
            assigned_to = "junior_analyst"
        
        # Create workflow instance
        workflow_data = {
            "workflow_instance_id": workflow_instance_id,
            "alert_id": alert.alert_id,
            "risk_score": alert.risk_score,
            "severity": alert.severity,
            "customer_id": alert.customer_id,
            "selected_workflow": selected_workflow,
            "status": "active",
            "current_step": "initialize",
            "progress": 0.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "assigned_to": assigned_to,
            "jurisdiction": alert.jurisdiction,
            "triggered_rules": alert.triggered_rules
        }
        
        workflow_instances[workflow_instance_id] = workflow_data
        
        # Create audit entry
        audit_trail[workflow_instance_id] = [{
            "timestamp": datetime.now().isoformat(),
            "action": "workflow_created",
            "details": f"Workflow created for alert {alert.alert_id}",
            "user": "system",
            "workflow_template": selected_workflow
        }]
        
        logger.info(f"✅ Started workflow {workflow_instance_id} for alert {alert.alert_id}")
        
        return {
            "workflow_instance_id": workflow_instance_id,
            "status": "started",
            "alert_id": alert.alert_id,
            "selected_workflow": selected_workflow,
            "assigned_to": assigned_to,
            "current_step": "initialize",
            "message": "Remediation workflow started successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")

@app.get("/api/v1/workflows/{workflow_instance_id}")
async def get_workflow_status(workflow_instance_id: str):
    """Get current status of a workflow instance"""
    if workflow_instance_id not in workflow_instances:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    
    workflow = workflow_instances[workflow_instance_id]
    
    # Calculate progress based on current step
    progress_map = {
        "initialize": 10,
        "request_documents": 25,
        "validate_documents": 50,
        "compliance_review": 75,
        "complete": 100
    }
    
    progress = progress_map.get(workflow["current_step"], 10)
    
    return {
        "workflow_instance_id": workflow_instance_id,
        "status": workflow["status"],
        "current_step": workflow["current_step"],
        "progress": progress,
        "selected_workflow": workflow["selected_workflow"],
        "risk_score": workflow["risk_score"],
        "severity": workflow["severity"],
        "assigned_to": workflow["assigned_to"],
        "created_at": workflow["created_at"],
        "updated_at": workflow["updated_at"]
    }

@app.get("/api/v1/workflows/{workflow_instance_id}/audit-trail")
async def get_workflow_audit_trail(workflow_instance_id: str):
    """Get audit trail for workflow instance"""
    if workflow_instance_id not in audit_trail:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    
    return {
        "workflow_instance_id": workflow_instance_id,
        "audit_entries": audit_trail[workflow_instance_id]
    }

@app.post("/api/v1/workflows/{workflow_instance_id}/execute-step")
async def execute_workflow_step(workflow_instance_id: str, step_name: str):
    """Execute a specific step in the workflow"""
    if workflow_instance_id not in workflow_instances:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    
    workflow = workflow_instances[workflow_instance_id]
    
    # Update workflow state
    workflow["current_step"] = step_name
    workflow["updated_at"] = datetime.now().isoformat()
    
    # Add audit entry
    if workflow_instance_id not in audit_trail:
        audit_trail[workflow_instance_id] = []
    
    audit_trail[workflow_instance_id].append({
        "timestamp": datetime.now().isoformat(),
        "action": f"step_executed",
        "details": f"Executed workflow step: {step_name}",
        "user": "system",
        "step_name": step_name
    })
    
    logger.info(f"✅ Executed step {step_name} for workflow {workflow_instance_id}")
    
    return {
        "workflow_instance_id": workflow_instance_id,
        "step_executed": step_name,
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "next_steps": get_next_steps(workflow["selected_workflow"], step_name)
    }

@app.post("/api/v1/workflows/{workflow_instance_id}/complete")
async def complete_workflow(workflow_instance_id: str):
    """Mark workflow as completed"""
    if workflow_instance_id not in workflow_instances:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    
    workflow = workflow_instances[workflow_instance_id]
    workflow["status"] = "completed"
    workflow["current_step"] = "complete"
    workflow["updated_at"] = datetime.now().isoformat()
    
    # Add completion audit entry
    audit_trail[workflow_instance_id].append({
        "timestamp": datetime.now().isoformat(),
        "action": "workflow_completed",
        "details": f"Workflow completed successfully",
        "user": "system"
    })
    
    logger.info(f"🎉 Completed workflow {workflow_instance_id}")
    
    return {
        "workflow_instance_id": workflow_instance_id,
        "status": "completed",
        "message": "Workflow completed successfully"
    }

@app.get("/api/v1/workflows")
async def list_workflows(status: Optional[str] = None):
    """List all workflows with optional filtering"""
    workflows = list(workflow_instances.values())
    
    if status:
        workflows = [wf for wf in workflows if wf["status"] == status]
    
    return {
        "workflows": workflows,
        "total_count": len(workflows),
        "active_count": len([wf for wf in workflows if wf["status"] == "active"]),
        "filters": {"status": status}
    }

@app.delete("/api/v1/workflows/{workflow_instance_id}")
async def delete_workflow(workflow_instance_id: str):
    """Delete a workflow instance (for testing)"""
    if workflow_instance_id in workflow_instances:
        del workflow_instances[workflow_instance_id]
        if workflow_instance_id in audit_trail:
            del audit_trail[workflow_instance_id]
        
        logger.info(f"🗑️ Deleted workflow {workflow_instance_id}")
        
        return {
            "message": f"Workflow {workflow_instance_id} deleted successfully"
        }
    else:
        raise HTTPException(status_code=404, detail="Workflow instance not found")

def get_next_steps(workflow_template: str, current_step: str) -> List[str]:
    """Get possible next steps for a workflow"""
    workflow_steps = {
        "CRITICAL_BLOCK_WORKFLOW": ["initialize", "block_transactions", "notify_stakeholders", "investigation", "complete"],
        "EDD_STANDARD_WORKFLOW": ["initialize", "request_documents", "validate_documents", "compliance_review", "complete"],
        "EDD_PEP_WORKFLOW": ["initialize", "pep_verification", "senior_approval", "source_validation", "complete"],
        "ENHANCED_MONITORING_WORKFLOW": ["initialize", "setup_monitoring", "periodic_review", "complete"]
    }
    
    steps = workflow_steps.get(workflow_template, [])
    current_index = steps.index(current_step) if current_step in steps else 0
    
    if current_index + 1 < len(steps):
        return steps[current_index + 1:]
    return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=8004,
        reload=True
    )