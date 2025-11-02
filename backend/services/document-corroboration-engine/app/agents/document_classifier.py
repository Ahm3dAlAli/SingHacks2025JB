from typing import Dict, Any, Tuple
import re
from enum import Enum
from app.utils.logger import setup_logger

class DocumentType(str, Enum):
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    IDENTIFICATION = "identification"
    CONTRACT = "contract"
    OTHER = "other"

class DocumentClassifier:
    def __init__(self):
        self.logger = setup_logger(__name__)
        # Keywords for document type classification
        self.type_keywords = {
            DocumentType.LEGAL: [
                'agreement', 'contract', 'terms and conditions', 'terms of service',
                'privacy policy', 'nda', 'non-disclosure', 'legal notice', 'law', 'act',
                'statute', 'regulation', 'clause', 'warranty', 'indemnity', 'liability'
            ],
            DocumentType.COMPLIANCE: [
                'compliance', 'gdpr', 'ccpa', 'hipaa', 'pci dss', 'soc 2', 'iso 27001',
                'regulatory', 'policy', 'procedure', 'standard', 'guideline', 'framework',
                'audit', 'certification', 'accreditation'
            ],
            DocumentType.FINANCIAL: [
                'invoice', 'receipt', 'statement', 'balance sheet', 'income statement',
                'cash flow', 'financial report', 'tax return', 'w-2', '1099', 'bank statement',
                'transaction history', 'ledger', 'profit and loss', 'p&l'
            ],
            DocumentType.IDENTIFICATION: [
                'passport', 'driving license', 'id card', 'national id', 'ssn',
                'social security', 'birth certificate', 'address proof', 'utility bill',
                'government issued', 'photo id'
            ],
            DocumentType.CONTRACT: [
                'contract', 'agreement', 'mou', 'memorandum of understanding',
                'service agreement', 'employment contract', 'lease agreement',
                'purchase agreement', 'sales contract', 'nda', 'non-disclosure agreement'
            ]
        }
        
        # Keywords for proof verification
        self.proof_keywords = [
            'signature', 'stamp', 'seal', 'notarized', 'witnessed', 'certified',
            'official', 'government', 'issued', 'approved', 'verified', 'attested',
            'notary', 'commissioner', 'authorized', 'stamped', 'sealed', 'signed',
            'endorsed', 'countersigned', 'notarization', 'authentication'
        ]
        
        # Keywords for relevance checking
        self.relevance_keywords = [
            'legal', 'law', 'act', 'statute', 'regulation', 'compliance', 'policy',
            'agreement', 'contract', 'terms', 'condition', 'clause', 'warranty',
            'liability', 'indemnity', 'confidential', 'proprietary', 'disclosure',
            'governance', 'risk', 'compliance', 'audit', 'certification', 'standard'
        ]
    
    def classify_document(self, text: str) -> Dict[str, Any]:
        """
        Classify the document type based on content analysis
        Returns a dictionary with classification results
        """
        text_lower = text.lower()
        scores = {doc_type: 0 for doc_type in DocumentType}
        
        # Score each document type based on keyword matches
        for doc_type, keywords in self.type_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    scores[doc_type] += 1
        
        # Get the highest scoring document type
        if not any(scores.values()):
            document_type = DocumentType.OTHER
        else:
            document_type = max(scores.items(), key=lambda x: x[1])[0]
        
        # Check for proof indicators
        has_proof = any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) 
                        for keyword in self.proof_keywords)
        
        # Check relevance
        is_relevant = any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) 
                         for keyword in self.relevance_keywords)
        
        # Extract proof details if any
        proof_details = self._extract_proof_details(text_lower) if has_proof else {}
        
        return {
            'document_type': document_type.value,
            'is_relevant': is_relevant,
            'has_proof': has_proof,
            'proof_details': proof_details,
            'confidence_scores': {k.value: v for k, v in scores.items()}
        }
    
    def _extract_proof_details(self, text: str) -> Dict[str, Any]:
        """Extract details about the proof found in the document"""
        proof_details = {
            'proof_types': [],
            'signatures': [],
            'dates': [],
            'authorities': []
        }
        
        # Look for proof types
        proof_matches = []
        for keyword in self.proof_keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                proof_matches.append(keyword)
        
        proof_details['proof_types'] = list(set(proof_matches))
        
        # Simple regex for signatures and dates (can be enhanced)
        signature_matches = re.findall(r'(?i)(?:signed|signature)[:\s]*(?:by)?[\s]*(.*?)(?:\.|\n|$)', text)
        date_matches = re.findall(r'\b(?:date|on|as of)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})\b', text)
        
        if signature_matches:
            proof_details['signatures'] = [s.strip() for s in signature_matches if len(s.strip()) > 3]
        
        if date_matches:
            proof_details['dates'] = date_matches
        
        # Look for authorities (e.g., notary, government)
        authority_keywords = ['notary', 'government', 'official', 'certified by', 'authorized by']
        authority_matches = []
        
        for keyword in authority_keywords:
            matches = re.findall(rf'(?i){keyword}[\s:]+([^\n\.]+)', text)
            authority_matches.extend(matches)
        
        if authority_matches:
            proof_details['authorities'] = [a.strip() for a in authority_matches if len(a.strip()) > 3]
        
        return proof_details
