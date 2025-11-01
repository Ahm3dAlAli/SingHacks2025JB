"""
HKMA (Hong Kong Monetary Authority) API connector.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin

import aiohttp
from pydantic import HttpUrl

from .base import BaseConnector, DocumentMetadata, DocumentContent, DocumentType, DocumentSource
from .local_connector import LocalConnector

logger = logging.getLogger(__name__)

class HKMAConnector(BaseConnector):
    """Connector for HKMA's API with local fallback."""
    
    BASE_URL = "https://api.hkma.gov.hk/public/"
    SOURCE = DocumentSource.HKMA
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the HKMA connector.
        
        Args:
            config: Configuration dictionary with:
                - api_key: API key for HKMA (optional for public endpoints)
                - base_url: Base URL for the API (defaults to public HKMA API)
                - local_fallback_path: Path to local document storage
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum number of retry attempts (default: 3)
        """
        super().__init__(config)
        self.api_key = self.config.get("api_key")
        self.base_url = self.config.get("base_url", self.BASE_URL)
        self.timeout = aiohttp.ClientTimeout(total=self.config.get("timeout", 30))
        self.max_retries = self.config.get("max_retries", 3)
        self.local_connector = LocalConnector({
            "base_path": self.local_fallback_path,
            "source": self.SOURCE.value
        })
    
    @property
    def source(self) -> DocumentSource:
        return self.SOURCE
    
    async def list_documents(self, **filters) -> List[DocumentMetadata]:
        """List available documents from HKMA API with local fallback."""
        try:
            # Try to get documents from the API
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # This is a simplified example - adjust endpoints as per actual HKMA API
                url = urljoin(self.base_url, "regulatory-documents")
                
                for attempt in range(self.max_retries):
                    try:
                        async with session.get(url, params={"api_key": self.api_key}) as response:
                            if response.status == 200:
                                data = await response.json()
                                return self._parse_document_list(data)
                            elif response.status == 404:
                                logger.warning("HKMA API endpoint not found, falling back to local storage")
                                break
                            else:
                                logger.warning(f"HKMA API returned {response.status}, attempt {attempt + 1}/{self.max_retries}")
                                if attempt == self.max_retries - 1:
                                    logger.error("Max retries reached, falling back to local storage")
                                    break
                                await asyncio.sleep(1)  # Simple backoff
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        logger.warning(f"Error connecting to HKMA API: {str(e)}")
                        if attempt == self.max_retries - 1:
                            logger.error("Max retries reached, falling back to local storage")
                            break
                        await asyncio.sleep(1)  # Simple backoff
        except Exception as e:
            logger.error(f"Unexpected error in list_documents: {str(e)}")
        
        # Fall back to local storage
        return await self.local_connector.list_documents(**filters)
    
    async def get_document(self, document_id: str) -> DocumentContent:
        """Get a document by ID from HKMA API with local fallback."""
        try:
            # Try to get the document from the API
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # This is a simplified example - adjust endpoint as per actual HKMA API
                url = urljoin(self.base_url, f"regulatory-documents/{document_id}")
                
                for attempt in range(self.max_retries):
                    try:
                        async with session.get(url, params={"api_key": self.api_key}) as response:
                            if response.status == 200:
                                content_type = response.headers.get('Content-Type', '')
                                
                                if 'application/json' in content_type:
                                    data = await response.json()
                                    return self._parse_document(document_id, data)
                                else:
                                    content = await response.read()
                                    return self._parse_binary_document(document_id, content, content_type)
                            elif response.status == 404:
                                logger.warning(f"Document {document_id} not found in HKMA API")
                                break
                            else:
                                logger.warning(f"HKMA API returned {response.status} for document {document_id}, attempt {attempt + 1}/{self.max_retries}")
                                if attempt == self.max_retries - 1:
                                    logger.error("Max retries reached, falling back to local storage")
                                    break
                                await asyncio.sleep(1)  # Simple backoff
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        logger.warning(f"Error fetching document {document_id} from HKMA API: {str(e)}")
                        if attempt == self.max_retries - 1:
                            logger.error("Max retries reached, falling back to local storage")
                            break
                        await asyncio.sleep(1)  # Simple backoff
        except Exception as e:
            logger.error(f"Unexpected error in get_document: {str(e)}")
        
        # Fall back to local storage
        return await self.local_connector.get_document(document_id)
    
    def _parse_document_list(self, data: Dict[str, Any]) -> List[DocumentMetadata]:
        """Parse document list from HKMA API response."""
        documents = []
        
        # This is a simplified example - adjust parsing based on actual API response
        for item in data.get("result", []):
            try:
                doc_id = item.get("id") or item.get("document_id")
                if not doc_id:
                    continue
                    
                doc_type = self._map_document_type(item.get("type"))
                doc_date = self._parse_date(item.get("date"))
                
                metadata = DocumentMetadata(
                    source=self.SOURCE,
                    document_id=doc_id,
                    title=item.get("title", f"HKMA Document {doc_id}"),
                    document_type=doc_type,
                    jurisdiction="HK",
                    regulator="HKMA",
                    document_date=doc_date,
                    effective_date=self._parse_date(item.get("effective_date")),
                    expiry_date=self._parse_date(item.get("expiry_date")),
                    url=HttpUrl(item["url"]) if item.get("url") else None,
                    file_name=item.get("file_name"),
                    file_type=item.get("file_type"),
                    file_size=item.get("file_size"),
                    metadata={
                        "source": "HKMA API",
                        "api_data": {k: v for k, v in item.items() if k not in ["id", "title", "type", "date"]}
                    }
                )
                documents.append(metadata)
            except Exception as e:
                logger.error(f"Error parsing document from HKMA API: {str(e)}")
                continue
                
        return documents
    
    def _parse_document(self, document_id: str, data: Dict[str, Any]) -> DocumentContent:
        """Parse a single document from HKMA API response."""
        doc_type = self._map_document_type(data.get("type"))
        doc_date = self._parse_date(data.get("date"))
        
        metadata = DocumentMetadata(
            source=self.SOURCE,
            document_id=document_id,
            title=data.get("title", f"HKMA Document {document_id}"),
            document_type=doc_type,
            jurisdiction="HK",
            regulator="HKMA",
            document_date=doc_date,
            effective_date=self._parse_date(data.get("effective_date")),
            expiry_date=self._parse_date(data.get("expiry_date")),
            url=HttpUrl(data["url"]) if data.get("url") else None,
            file_name=data.get("file_name"),
            file_type=data.get("file_type"),
            file_size=data.get("file_size"),
            metadata={
                "source": "HKMA API",
                "api_data": {k: v for k, v in data.items() if k not in ["id", "title", "type", "date", "content"]}
            }
        )
        
        # Extract content - this depends on the API response structure
        content = data.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False, indent=2)
        
        return DocumentContent(
            metadata=metadata,
            content=content,
            is_binary=False
        )
    
    def _parse_binary_document(self, document_id: str, content: bytes, content_type: str) -> DocumentContent:
        """Handle binary document content from HKMA API."""
        # Create metadata for binary document
        metadata = DocumentMetadata(
            source=self.SOURCE,
            document_id=document_id,
            title=f"HKMA Document {document_id}",
            document_type=DocumentType.OTHER,
            jurisdiction="HK",
            regulator="HKMA",
            document_date=datetime.utcnow().date(),
            file_name=f"{document_id}.{content_type.split('/')[-1]}",
            file_type=content_type.split('/')[-1],
            file_size=len(content),
            metadata={
                "source": "HKMA API",
                "content_type": content_type
            }
        )
        
        return DocumentContent(
            metadata=metadata,
            content=content,
            is_binary=True
        )
    
    def _map_document_type(self, doc_type: Optional[str]) -> DocumentType:
        """Map HKMA document type to our DocumentType enum."""
        if not doc_type:
            return DocumentType.OTHER
            
        doc_type = doc_type.upper()
        
        type_mapping = {
            "REGULATION": DocumentType.REGULATION,
            "GUIDELINE": DocumentType.GUIDELINE,
            "CIRCULAR": DocumentType.CIRCULAR,
            "NOTICE": DocumentType.NOTICE,
            "RULE": DocumentType.RULE,
            "GUIDANCE": DocumentType.GUIDELINE,
            "ANNEX": DocumentType.OTHER,
            "FORM": DocumentType.OTHER,
        }
        
        return type_mapping.get(doc_type, DocumentType.OTHER)
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string from HKMA API response."""
        if not date_str:
            return None
            
        try:
            # Try ISO 8601 format first
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            # Try other common formats
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except (ValueError, TypeError):
                    continue
        
        return None
