import os
import uuid
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    async def store_document(self, workflow_instance_id: str, document_data: bytes, 
                           document_type: str, file_name: str) -> Dict[str, Any]:
        """Store document locally"""
        
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file_name)[1]
            unique_filename = f"{workflow_instance_id}_{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Write file
            with open(file_path, "wb") as f:
                f.write(document_data)
            
            logger.info(f"Document stored: {file_path}")
            
            return {
                "success": True,
                "file_path": file_path,
                "file_name": unique_filename,
                "original_name": file_name,
                "document_type": document_type,
                "stored_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to store document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_document_format(self, file_path: str, document_type: str) -> Dict[str, Any]:
        """Basic document format validation"""
        
        try:
            # Check file exists
            if not os.path.exists(file_path):
                return {"valid": False, "error": "File not found"}
            
            # Check file size (max 10MB)
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB
                return {"valid": False, "error": "File too large (max 10MB)"}
            
            # Basic format validation based on document type
            allowed_extensions = {
                "passport": [".pdf", ".jpg", ".jpeg", ".png"],
                "proof_of_address": [".pdf", ".jpg", ".jpeg", ".png"],
                "source_of_wealth": [".pdf", ".doc", ".docx"]
            }
            
            file_extension = os.path.splitext(file_path)[1].lower()
            allowed = allowed_extensions.get(document_type, [".pdf", ".jpg", ".jpeg", ".png"])
            
            if file_extension not in allowed:
                return {"valid": False, "error": f"Invalid file type for {document_type}. Allowed: {allowed}"}
            
            return {
                "valid": True,
                "file_size": file_size,
                "file_extension": file_extension
            }
            
        except Exception as e:
            logger.error(f"Document validation failed: {e}")
            return {"valid": False, "error": str(e)}
    
    async def extract_document_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract basic document metadata"""
        
        try:
            stats = os.stat(file_path)
            
            return {
                "file_size": stats.st_size,
                "created_time": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "file_extension": os.path.splitext(file_path)[1].lower()
            }
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            return {"error": str(e)}