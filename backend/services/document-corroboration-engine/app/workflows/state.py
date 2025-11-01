from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum

class WorkflowState(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentState(BaseModel):
    document_id: str
    current_step: str
    workflow_state: WorkflowState
    progress: float = 0.0
    results: Dict[str, Any] = {}
    errors: List[str] = []
    metadata: Dict[str, Any] = {}

class WorkflowManager:
    def __init__(self):
        self.active_workflows: Dict[str, DocumentState] = {}
    
    def create_workflow(self, document_id: str) -> DocumentState:
        """Create new workflow state"""
        state = DocumentState(
            document_id=document_id,
            current_step="initialized",
            workflow_state=WorkflowState.PENDING
        )
        self.active_workflows[document_id] = state
        return state
    
    def update_progress(self, document_id: str, step: str, progress: float, results: Dict[str, Any] = None):
        """Update workflow progress"""
        if document_id in self.active_workflows:
            state = self.active_workflows[document_id]
            state.current_step = step
            state.progress = progress
            state.workflow_state = WorkflowState.PROCESSING
            
            if results:
                state.results.update(results)
    
    def complete_workflow(self, document_id: str, final_results: Dict[str, Any]):
        """Mark workflow as completed"""
        if document_id in self.active_workflows:
            state = self.active_workflows[document_id]
            state.current_step = "completed"
            state.progress = 100.0
            state.workflow_state = WorkflowState.COMPLETED
            state.results.update(final_results)
    
    def fail_workflow(self, document_id: str, error: str):
        """Mark workflow as failed"""
        if document_id in self.active_workflows:
            state = self.active_workflows[document_id]
            state.current_step = "failed"
            state.workflow_state = WorkflowState.FAILED
            state.errors.append(error)
    
    def get_workflow_state(self, document_id: str) -> Optional[DocumentState]:
        """Get current workflow state"""
        return self.active_workflows.get(document_id)

# Global workflow manager instance
workflow_manager = WorkflowManager()