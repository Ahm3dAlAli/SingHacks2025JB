from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import logging

from .models import (
    AlertRequest,
    WorkflowStartResponse,
    WorkflowStatusResponse,
    WorkflowActionRequest,
    WorkflowActionResponse,
    AuditEntryResponse,
    WorkflowListResponse,
    ErrorResponse,
    DocumentUploadRequest,
    DocumentResponse,
    WorkflowStepUpdate,
    WorkflowSearchFilters,
    SystemMetricsResponse,
    WorkflowStatus,
    ActionStatus
)
from database.connection import get_db
from database.queries import WorkflowQueries, EmailTemplateQueries
from services.groq_client import GroqClient
from services.email_service import EmailService
from services.document_service import DocumentService
from services.audit_service import AuditService
from langgraph.graph import RemediationWorkflowGraph

router = APIRouter()

# Initialize services
groq_client = GroqClient()
email_service = EmailService()
document_service = DocumentService()
audit_service = AuditService()

# Initialize workflow graph
workflow_graph = RemediationWorkflowGraph(
    groq_client=groq_client,
    email_service=email_service,
    document_service=document_service,
    audit_service=audit_service
)

logger = logging.getLogger(__name__)

@router.post(
    "/workflows/start",
    response_model=WorkflowStartResponse,
    summary="Start Remediation Workflow",
    description="Start a new AML remediation workflow for an alert",
    responses={
        200: {"description": "Workflow started successfully"},
        400: {"description": "Invalid alert data"},
        500: {"description": "Internal server error"}
    }
)
async def start_remediation_workflow(
    alert: AlertRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start a new remediation workflow for an alert"""
    try:
        logger.info(f"Starting workflow for alert: {alert.alert_id}")
        
        # Validate alert data
        if alert.risk_score < 0 or alert.risk_score > 100:
            raise HTTPException(
                status_code=400,
                detail="Risk score must be between 0 and 100"
            )
        
        # Create workflow instance in database
        workflow_queries = WorkflowQueries(db)
        workflow_instance = await workflow_queries.create_workflow_instance(alert.dict())
        
        # Process through LangGraph workflow
        workflow_result = await workflow_graph.process_alert(alert.dict())
        
        # Update workflow with results
        updates = {
            "selected_workflow": workflow_result.get("selected_workflow"),
            "decision_rationale": workflow_result.get("decision_rationale"),
            "assigned_to": workflow_result.get("assigned_to", "system"),
            "state_data": workflow_result
        }
        
        updated_workflow = await workflow_queries.update_workflow_state(
            workflow_instance.id,
            updates
        )
        
        # Log workflow start
        await audit_service.log_workflow_start(
            workflow_instance.id,
            alert.dict()
        )
        
        response = WorkflowStartResponse(
            workflow_instance_id=workflow_instance.id,
            alert_id=alert.alert_id,
            status=WorkflowStatus.ACTIVE,
            selected_workflow=workflow_result.get("selected_workflow", "unknown"),
            assigned_to=workflow_result.get("assigned_to", "system"),
            decision_rationale=workflow_result.get("decision_rationale", ""),
            estimated_completion_hours=workflow_result.get("estimated_completion_hours", 48),
            created_at=workflow_instance.created_at
        )
        
        logger.info(f"Workflow started successfully: {workflow_instance.id}")
        return response
        
    except ValueError as e:
        logger.error(f"Validation error for alert {alert.alert_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start workflow for alert {alert.alert_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start workflow: {str(e)}"
        )

@router.get(
    "/workflows/{workflow_instance_id}",
    response_model=WorkflowStatusResponse,
    summary="Get Workflow Status",
    description="Get current status and details of a workflow instance",
    responses={
        200: {"description": "Workflow status retrieved successfully"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_workflow_status(
    workflow_instance_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get current status of a workflow instance"""
    try:
        workflow_queries = WorkflowQueries(db)
        workflow = await workflow_queries.get_workflow_instance(workflow_instance_id)
        
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_instance_id} not found"
            )
        
        # Calculate progress based on completed actions
        total_actions = len(workflow.actions)
        completed_actions = len([a for a in workflow.actions if a.status == ActionStatus.COMPLETED])
        progress = (completed_actions / total_actions * 100) if total_actions > 0 else 0
        
        # Calculate next deadline (simplified - in real system, use step deadlines)
        next_deadline = workflow.updated_at + timedelta(hours=24)
        
        response = WorkflowStatusResponse(
            workflow_instance_id=workflow.id,
            alert_id=workflow.alert_id,
            status=WorkflowStatus(workflow.status),
            current_step=workflow.current_step,
            progress=round(progress, 2),
            selected_workflow=workflow.selected_workflow or workflow.workflow_template,
            risk_score=workflow.risk_score,
            severity=workflow.severity,
            escalation_level=workflow.escalation_level,
            assigned_to=workflow.assigned_to,
            sla_breach=workflow.sla_breach,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            next_deadline=next_deadline
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status {workflow_instance_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workflow status: {str(e)}"
        )

@router.post(
    "/workflows/{workflow_instance_id}/actions",
    response_model=WorkflowActionResponse,
    summary="Execute Workflow Action",
    description="Execute a specific action within a workflow",
    responses={
        200: {"description": "Action executed successfully"},
        404: {"description": "Workflow not found"},
        400: {"description": "Invalid action"},
        500: {"description": "Internal server error"}
    }
)
async def execute_workflow_action(
    workflow_instance_id: str,
    action_request: WorkflowActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Execute a specific action within a workflow"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Verify workflow exists
        workflow = await workflow_queries.get_workflow_instance(workflow_instance_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_instance_id} not found"
            )
        
        # Create action record
        action_data = {
            "action_type": "manual",
            "action_name": action_request.action,
            "parameters": action_request.parameters,
            "status": ActionStatus.IN_PROGRESS
        }
        
        action = await workflow_queries.create_workflow_action(
            workflow_instance_id,
            action_data
        )
        
        # Execute action through workflow graph
        try:
            # This would integrate with the LangGraph action executor
            # For now, simulate action execution
            result_data = {
                "executed_by": action_request.user,
                "action": action_request.action,
                "parameters": action_request.parameters,
                "notes": action_request.notes,
                "execution_time": datetime.now().isoformat(),
                "status": "completed"
            }
            
            # Update action status
            updated_action = await workflow_queries.update_action_status(
                action.id,
                ActionStatus.COMPLETED,
                result_data
            )
            
            # Create audit entry
            await workflow_queries.create_audit_entry(
                workflow_instance_id,
                f"action_executed_{action_request.action}",
                f"Action {action_request.action} executed by {action_request.user}",
                action_request.user,
                {"action_id": action.id, "parameters": action_request.parameters}
            )
            
            response = WorkflowActionResponse(
                action_id=action.id,
                workflow_instance_id=workflow_instance_id,
                action=action_request.action,
                status=ActionStatus.COMPLETED,
                result_data=result_data,
                executed_by=action_request.user,
                executed_at=action.created_at,
                completion_time=updated_action.completed_at
            )
            
            return response
            
        except Exception as action_error:
            # Update action as failed
            await workflow_queries.update_action_status(
                action.id,
                ActionStatus.FAILED,
                {"error": str(action_error)}
            )
            
            raise HTTPException(
                status_code=400,
                detail=f"Action execution failed: {str(action_error)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute action for workflow {workflow_instance_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute action: {str(e)}"
        )

@router.get(
    "/workflows/{workflow_instance_id}/audit-trail",
    response_model=List[AuditEntryResponse],
    summary="Get Workflow Audit Trail",
    description="Get complete audit trail for a workflow instance",
    responses={
        200: {"description": "Audit trail retrieved successfully"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_workflow_audit_trail(
    workflow_instance_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get complete audit trail for a workflow instance"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Verify workflow exists
        workflow = await workflow_queries.get_workflow_instance(workflow_instance_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_instance_id} not found"
            )
        
        # Get audit entries
        audit_entries = await workflow_queries.get_workflow_audit_trail(workflow_instance_id)
        
        response = [
            AuditEntryResponse(
                id=entry.id,
                workflow_instance_id=entry.workflow_instance_id,
                timestamp=entry.timestamp,
                action=entry.action,
                user=entry.user,
                details=entry.details,
                metadata=entry.metadata
            )
            for entry in audit_entries
        ]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit trail for workflow {workflow_instance_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit trail: {str(e)}"
        )

@router.get(
    "/workflows",
    response_model=WorkflowListResponse,
    summary="List Workflows",
    description="Get paginated list of workflows with optional filtering",
    responses={
        200: {"description": "Workflows retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def list_workflows(
    status: Optional[WorkflowStatus] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of workflows with filtering"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Get all workflows (in real system, apply filters)
        all_workflows = await workflow_queries.get_pending_workflows()
        
        # Apply filters (simplified - in real system, use database queries)
        filtered_workflows = all_workflows
        
        if status:
            filtered_workflows = [w for w in filtered_workflows if w.status == status]
        if severity:
            filtered_workflows = [w for w in filtered_workflows if w.severity == severity]
        if customer_id:
            filtered_workflows = [w for w in filtered_workflows if w.customer_id == customer_id]
        if assigned_to:
            filtered_workflows = [w for w in filtered_workflows if w.assigned_to == assigned_to]
        
        # Paginate
        total_count = len(filtered_workflows)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_workflows = filtered_workflows[start_idx:end_idx]
        
        # Convert to response models
        workflow_responses = []
        for workflow in paginated_workflows:
            # Calculate progress
            total_actions = len(workflow.actions)
            completed_actions = len([a for a in workflow.actions if a.status == ActionStatus.COMPLETED])
            progress = (completed_actions / total_actions * 100) if total_actions > 0 else 0
            
            workflow_responses.append(
                WorkflowStatusResponse(
                    workflow_instance_id=workflow.id,
                    alert_id=workflow.alert_id,
                    status=WorkflowStatus(workflow.status),
                    current_step=workflow.current_step,
                    progress=round(progress, 2),
                    selected_workflow=workflow.selected_workflow or workflow.workflow_template,
                    risk_score=workflow.risk_score,
                    severity=workflow.severity,
                    escalation_level=workflow.escalation_level,
                    assigned_to=workflow.assigned_to,
                    sla_breach=workflow.sla_breach,
                    created_at=workflow.created_at,
                    updated_at=workflow.updated_at,
                    next_deadline=workflow.updated_at + timedelta(hours=24)
                )
            )
        
        response = WorkflowListResponse(
            workflows=workflow_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list workflows: {str(e)}"
        )

@router.post(
    "/workflows/{workflow_instance_id}/documents",
    response_model=DocumentResponse,
    summary="Upload Document",
    description="Upload a document for a workflow instance",
    responses={
        200: {"description": "Document uploaded successfully"},
        404: {"description": "Workflow not found"},
        400: {"description": "Invalid document"},
        500: {"description": "Internal server error"}
    }
)
async def upload_document(
    workflow_instance_id: str,
    document_type: str = Form(..., description="Type of document"),
    file_name: str = Form(..., description="Original file name"),
    description: Optional[str] = Form(None, description="Document description"),
    file: UploadFile = File(..., description="Document file"),
    db: AsyncSession = Depends(get_db)
):
    """Upload a document for a workflow instance"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Verify workflow exists
        workflow = await workflow_queries.get_workflow_instance(workflow_instance_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_instance_id} not found"
            )
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )
        
        # Store document
        storage_result = await document_service.store_document(
            workflow_instance_id,
            file_content,
            document_type,
            file_name
        )
        
        if not storage_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to store document: {storage_result.get('error', 'Unknown error')}"
            )
        
        # Validate document format
        validation_result = await document_service.validate_document_format(
            storage_result["file_path"],
            document_type
        )
        
        # Create document record in database (simplified)
        # In real system, you would have a proper document model and queries
        
        response = DocumentResponse(
            document_id=str(uuid.uuid4()),  # In real system, use actual document ID
            workflow_instance_id=workflow_instance_id,
            document_type=document_type,
            file_name=storage_result["file_name"],
            original_name=file_name,
            status="validated" if validation_result["valid"] else "validation_failed",
            validation_result=validation_result,
            uploaded_at=datetime.now(),
            validated_at=datetime.now() if validation_result["valid"] else None
        )
        
        # Create audit entry
        await workflow_queries.create_audit_entry(
            workflow_instance_id,
            "document_uploaded",
            f"Document {file_name} uploaded for {document_type}",
            "system",
            {
                "document_type": document_type,
                "file_name": file_name,
                "validation_result": validation_result
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document for workflow {workflow_instance_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )

@router.put(
    "/workflows/{workflow_instance_id}/steps",
    summary="Update Workflow Step",
    description="Update the status of a workflow step",
    responses={
        200: {"description": "Step updated successfully"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"}
    }
)
async def update_workflow_step(
    workflow_instance_id: str,
    step_update: WorkflowStepUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update the status of a workflow step"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Verify workflow exists
        workflow = await workflow_queries.get_workflow_instance(workflow_instance_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_instance_id} not found"
            )
        
        # Update workflow state
        updates = {
            "current_step": step_update.step_name,
            "updated_at": datetime.now()
        }
        
        await workflow_queries.update_workflow_state(workflow_instance_id, updates)
        
        # Create audit entry
        await workflow_queries.create_audit_entry(
            workflow_instance_id,
            "step_updated",
            f"Step {step_update.step_name} updated to {step_update.status}",
            "system",
            {
                "step_name": step_update.step_name,
                "status": step_update.status,
                "notes": step_update.notes,
                "result_data": step_update.result_data
            }
        )
        
        return {"message": "Step updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update step for workflow {workflow_instance_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update step: {str(e)}"
        )

@router.get(
    "/metrics/system",
    response_model=SystemMetricsResponse,
    summary="Get System Metrics",
    description="Get system-wide metrics and statistics",
    responses={
        200: {"description": "Metrics retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def get_system_metrics(db: AsyncSession = Depends(get_db)):
    """Get system-wide metrics and statistics"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Get all workflows for metrics calculation
        all_workflows = await workflow_queries.get_pending_workflows()
        
        # Calculate metrics (simplified - in real system, use database aggregates)
        total_workflows = len(all_workflows)
        active_workflows = len([w for w in all_workflows if w.status == WorkflowStatus.ACTIVE])
        
        # Calculate completed today
        today = datetime.now().date()
        completed_today = len([
            w for w in all_workflows 
            if w.status == WorkflowStatus.COMPLETED and w.updated_at.date() == today
        ])
        
        # Calculate average completion time (simplified)
        completed_workflows = [w for w in all_workflows if w.status == WorkflowStatus.COMPLETED]
        if completed_workflows:
            total_completion_time = sum([
                (w.updated_at - w.created_at).total_seconds() 
                for w in completed_workflows
            ])
            average_completion_time_hours = total_completion_time / len(completed_workflows) / 3600
        else:
            average_completion_time_hours = 0
        
        # Count SLA breaches
        sla_breach_count = len([w for w in all_workflows if w.sla_breach])
        
        # Calculate distributions
        workflow_distribution = {}
        risk_distribution = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }
        
        for workflow in all_workflows:
            # Workflow type distribution
            workflow_type = workflow.selected_workflow or workflow.workflow_template
            workflow_distribution[workflow_type] = workflow_distribution.get(workflow_type, 0) + 1
            
            # Risk distribution
            risk_distribution[workflow.severity] = risk_distribution.get(workflow.severity, 0) + 1
        
        response = SystemMetricsResponse(
            total_workflows=total_workflows,
            active_workflows=active_workflows,
            completed_today=completed_today,
            average_completion_time_hours=round(average_completion_time_hours, 2),
            sla_breach_count=sla_breach_count,
            workflow_distribution=workflow_distribution,
            risk_distribution=risk_distribution,
            timestamp=datetime.now()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system metrics: {str(e)}"
        )

@router.post(
    "/workflows/{workflow_instance_id}/escalate",
    summary="Escalate Workflow",
    description="Manually escalate a workflow to a higher level",
    responses={
        200: {"description": "Workflow escalated successfully"},
        404: {"description": "Workflow not found"},
        500: {"description": "Internal server error"}
    }
)
async def escalate_workflow(
    workflow_instance_id: str,
    reason: str = Form(..., description="Escalation reason"),
    target_level: int = Form(..., ge=1, le=5, description="Target escalation level"),
    user: str = Form(..., description="User initiating escalation"),
    db: AsyncSession = Depends(get_db)
):
    """Manually escalate a workflow to a higher level"""
    try:
        workflow_queries = WorkflowQueries(db)
        
        # Verify workflow exists
        workflow = await workflow_queries.get_workflow_instance(workflow_instance_id)
        if not workflow:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow {workflow_instance_id} not found"
            )
        
        # Update escalation level
        escalation_paths = {
            1: "compliance_analyst",
            2: "compliance_team_lead", 
            3: "senior_compliance_officer",
            4: "head_of_compliance",
            5: "chief_risk_officer"
        }
        
        updates = {
            "escalation_level": target_level,
            "assigned_to": escalation_paths.get(target_level, "senior_compliance_officer"),
            "updated_at": datetime.now()
        }
        
        await workflow_queries.update_workflow_state(workflow_instance_id, updates)
        
        # Create audit entry
        await workflow_queries.create_audit_entry(
            workflow_instance_id,
            "workflow_escalated_manual",
            f"Workflow manually escalated to level {target_level}: {reason}",
            user,
            {
                "target_level": target_level,
                "reason": reason,
                "previous_level": workflow.escalation_level
            }
        )
        
        return {"message": f"Workflow escalated to level {target_level} successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to escalate workflow {workflow_instance_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to escalate workflow: {str(e)}"
        )

# Error handler
@router.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    error_response = ErrorResponse(
        error=exc.detail,
        code=str(exc.status_code),
        timestamp=datetime.now()
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )