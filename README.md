# Julius Baer — Agentic AI for Real-Time AML Monitoring and Alerts

> **AML Agentic AI Solutions** — Build two agentic AI-driven solutions for Anti-Money Laundering (AML) Monitoring and Document & Image Corroboration

---

## Challenge Summary

**Goal**: Ship two working agentic AI solutions that can **monitor AML risks in real-time** → **process compliance documents** → **generate actionable alerts** → **maintain audit trails**.

**Build path**: Implement **Part 1** (Real-Time AML Monitoring) and **Part 2** (Document & Image Corroboration) as a Integrated solution 

> **📖 IMPORTANT**: Before diving into the code, please read this **README.md** document first. It contains essential context, detailed requirements, and additional guidance that will help you build a winning solution.

---

## 📋 The Problem We're Solving

### Current State
- **Part 1**: External regulatory circulars are released continuously, imposing new AML surveillance rules that are difficult to track and implement consistently
- **Part 2**: Compliance teams perform manual, time-consuming checks on client corroboration documents with high error rates
- **Cross-functional friction**: Front, Compliance, and Legal teams struggle to detect risks in real-time due to information silos
- **High operational risk**: Manual processes lead to inconsistencies and potential regulatory violations

### What You're Building
- **Part 1: Real-Time AML Monitoring**
  - Continuously ingest external regulatory circulars and internal rule changes
  - Analyze client transactions and behaviors in real-time against regulatory requirements
  - Surface tailored alerts for Front and Compliance teams
  - Provide remediation workflows with audit trail maintenance

- **Part 2: Document & Image Corroboration**
  - Upload and process multiple file types: PDFs, text documents, and images
  - Detect formatting errors, spelling/grammar issues, and missing sections
  - Perform image integrity analysis (reverse search, AI-generated detection, tampering checks)
  - Provide real-time feedback and risk scoring for compliance officers

### Who Benefits
- **End users**: Operations and regulatory compliance employees
- **Front teams**: Relationship Managers with real-time risk alerts
- **Compliance teams**: Automated document verification and risk assessment
- **Legal teams**: Enhanced audit trails and regulatory compliance

---

## Provided Resources

### 1) `transactions_mock_1000_for_participants.csv` — **Part 1: Real-Time AML Monitoring**
A synthetic set of 1,000 transactions (jurisdiction, regulator, amounts, screening flags, SWIFT fields, etc.).  
Use it to prototype your rules engine, compute risk scores, and generate role-based alerts (Front/Compliance/Legal).

### 2) `Swiss_Home_Purchase_Agreement_Scanned_Noise_forparticipants.pdf` — **Part 2: Document & Image Corroboration**
A scanned client corroboration document for OCR and validation.  
Use it to extract fields, check formatting/consistency (amounts, dates, annexes, IDs), and produce a document risk score + findings list.

## 🎯 What You're Building

Two agentic AI-driven AML solutions that work together:

```
┌─────────────────────────────────────────────────────────────────┐
│  Part 1: Real-Time AML Monitoring & Alerts                     │
│  ↓ Ingest regulations → Analyze transactions → Surface alerts    │
├─────────────────────────────────────────────────────────────────┤
│  Part 2: Document & Image Corroboration                        │
│  ↓ Upload documents → Detect issues → Generate risk reports    │
├─────────────────────────────────────────────────────────────────┤
│  Integration Layer: Unified AML Platform                       │
│  ↓ Cross-reference alerts with document analysis               │
├─────────────────────────────────────────────────────────────────┤
```

---


## 🏗️ Solution Components — Step-by-Step Build Guide

### Part 1: Real-Time AML Monitoring & Alerts

**What it does**: Continuously monitors regulatory changes and client transactions to detect AML risks in real-time.

**Key Components**:

#### 1. Regulatory Ingestion Engine
- **Crawl external sources**: MAS,FINMA, HKMA, and other regulatory bodies
- **Parse unstructured rules**: Convert regulatory circulars into actionable monitoring criteria
- **Version control**: Maintain audit trail of rule changes over time

#### 2. Transaction Analysis Engine
- **Real-time monitoring**: Analyze client transactions against current rules
- **Behavioral analysis**: Detect unusual patterns and suspicious activities
- **Risk scoring**: Assign risk scores based on multiple factors
- **Pattern recognition**: Identify complex money laundering schemes

#### 3. Alert System
- **Role-specific alerts**: Tailored notifications for Front, Compliance, and Legal teams
- **Priority routing**: High-risk alerts escalated immediately
- **Context provision**: Include relevant transaction history and regulatory context
- **Acknowledgment tracking**: Ensure alerts are reviewed and acted upon

#### 4. Remediation Workflows
- **Automated suggestions**: Recommend specific actions (enhanced due diligence, transaction blocking, escalation)
- **Workflow templates**: Pre-defined processes for common scenarios
- **Audit trail maintenance**: Record all actions taken for compliance defensibility
- **Integration capabilities**: Connect with existing compliance systems

**Deliverables**:
- [ ] Working regulatory ingestion system
- [ ] Real-time transaction monitoring with configurable rules
- [ ] Alert system with role-based routing
- [ ] Remediation workflow engine
- [ ] Comprehensive audit trail functionality

---

### Part 2: Document & Image Corroboration

**What it does**: Automates the verification of client corroboration documents to detect inconsistencies and potential fraud.

**Key Components**:

#### 1. Document Processing Engine
- **Multi-format support**: Handle PDFs, text documents, and images
- **Content extraction**: Extract text, metadata, and structural information
- **Format validation**: Check document structure and formatting consistency
- **Quality assessment**: Evaluate document completeness and accuracy

#### 2. Format Validation System
- **Formatting checks**: Detect double spacing, irregular fonts, inconsistent indentation
- **Content validation**: Identify spelling mistakes, incorrect headers, missing sections
- **Structure analysis**: Verify document organization and completeness
- **Template matching**: Compare against standard document templates

#### 3. Image Analysis Engine
- **Authenticity verification**: Detect stolen images using reverse image search
- **AI-generated detection**: Identify AI-generated or synthetic images
- **Tampering detection**: Analyze metadata and pixel-level anomalies
- **Forensic analysis**: Deep inspection for manipulation indicators

#### 4. Risk Scoring & Reporting
- **Risk assessment**: Calculate risk scores based on multiple factors
- **Real-time feedback**: Provide immediate feedback to compliance officers
- **Report generation**: Create detailed reports highlighting issues
- **Audit trail**: Maintain comprehensive logs of all analysis performed

**Deliverables**:
- [ ] Multi-format document processing system
- [ ] Advanced format validation with detailed error reporting
- [ ] Sophisticated image analysis capabilities
- [ ] Risk scoring and feedback system
- [ ] Comprehensive reporting functionality



## 🏆 Judging Criteria

Your submission will be evaluated on:

### Main Hackathon Criteria

| Criteria | Weight | Description |
|----------|--------|-------------|
| **Objective Achievement** | 20% | Did this meet the stated objectives |
| **Creativity** | 20% | Innovative application of agentic workflows and interface ideas |
| **Visual Design** | 20% | Clarity, User Experience, polished user interactions |
| **Presentation Skills** | 20% | Clarity, timeliness, and flow |
| **Technical Depth** | 20% | Architecture, use of frameworks, etc. |

---

## ✅ Features Checklist

### Part 1: Real-Time AML Monitoring
- [ ] Regulatory ingestion system working with external sources
- [ ] Real-time transaction monitoring with configurable rules
- [ ] Alert system with role-based routing and priority handling
- [ ] Remediation workflow engine with automated suggestions
- [ ] Comprehensive audit trail for all activities
- [ ] Integration with existing compliance systems (if applicable)

### Part 2: Document Corroboration
- [ ] Multi-format document processing (PDF, text, images)
- [ ] Advanced format validation with detailed error reporting
- [ ] Image authenticity and tampering detection
- [ ] Risk scoring system with real-time feedback
- [ ] Comprehensive reporting with evidence and citations
- [ ] Audit trail for all document analysis performed

### Integration & Output
- [ ] Unified dashboard (if building integrated solution)
- [ ] Cross-reference capabilities between transaction and document analysis
- [ ] PDF report generation with red flags and problematic areas
- [ ] Professional presentation and user interface
- [ ] Scalable architecture for production deployment


## 🤝 Support & Contact

**Mentor:
- **Wee Kiat** — Open Innovation Lead, AI, Data & Innovation

**Getting Help**:
- Technical questions: Ask during mentor sessions
- Regulatory guidance: Reference FINMA and HKMA Website

