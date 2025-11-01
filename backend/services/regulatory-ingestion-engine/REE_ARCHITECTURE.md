╔══════════════════════════════════════════════════════════════════════════════════╗
║                         REGULATORY INGESTION ENGINE                              ║
╚══════════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           LAYER 1: SOURCE INGESTION                             │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
    │   HKMA API   │      │  MAS EMAIL   │      │  FINMA RSS   │      │   OTHER      │
    │              │      │              │      │              │      │ REGULATORS   │
    │  JSON REST   │      │  SMTP/IMAP   │      │  XML FEED    │      │ (Web/API)    │
    └──────┬───────┘      └──────┬───────┘      └──────┬───────┘      └──────┬───────┘
           │                     │                     │                     │
           │  HTTP GET           │  Email Poll         │  RSS Parse          │  HTTP/Scrape
           │                     │                     │                     │
           └─────────────────────┴─────────────────────┴─────────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  INGESTION SCHEDULER │
                              │  - Polling intervals │
                              │  - Rate limiting     │
                              │  - Error handling    │
                              │  - Deduplication     │
                              └──────────┬───────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      LAYER 2: DOCUMENT EXTRACTION & PARSING                     │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────────┐
                              │  RAW DOCUMENT STORE  │
                              │  - PDF, HTML, DOCX   │
                              │  - Metadata capture  │
                              │  - Source tracking   │
                              └──────────┬───────────┘
                                         │
                         ┌───────────────┼───────────────┐
                         │               │               │
                         ▼               ▼               ▼
              ┌─────────────────┐ ┌─────────────┐ ┌────────────────┐
              │  TEXT EXTRACTOR │ │   METADATA  │ │   ATTACHMENT   │
              │  - PDF parsing  │ │  EXTRACTOR  │ │    HANDLER     │
              │  - OCR (if req) │ │  - Date     │ │  - Tables      │
              │  - HTML parsing │ │  - Type     │ │  - Annexes     │
              │  - DOCX parsing │ │  - Category │ │  - References  │
              └────────┬────────┘ └──────┬──────┘ └────────┬───────┘
                       │                 │                 │
                       └─────────────────┴─────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  STRUCTURED DOCUMENT │
                              │  - Full text         │
                              │  - Metadata          │
                              │  - Sections          │
                              │  - Tables/Annexes    │
                              └──────────┬───────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    LAYER 3: RULE PARSING & TRANSFORMATION                       │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────────┐
                              │   NLP/LLM PROCESSOR  │
                              │  - Entity extraction │
                              │  - Clause parsing    │
                              │  - Requirement ID    │
                              │  - Obligation detect │
                              └──────────┬───────────┘
                                         │
                         ┌───────────────┼───────────────┐
                         │               │               │
                         ▼               ▼               ▼
              ┌─────────────────┐ ┌─────────────┐ ┌────────────────┐
              │   RULE ENGINE   │ │  CRITERIA   │ │   COMPLIANCE   │
              │   - Obligations │ │  GENERATOR  │ │    MAPPING     │
              │   - Prohibitions│ │  - KPIs     │ │  - FINMA rules │
              │   - Thresholds  │ │  - Alerts   │ │  - MAS rules   │
              │   - Timelines   │ │  - Metrics  │ │  - HKMA rules  │
              └────────┬────────┘ └──────┬──────┘ └────────┬───────┘
                       │                 │                 │
                       └─────────────────┴─────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  ACTIONABLE CRITERIA │
                              │  {                   │
                              │    rule_id,          │
                              │    requirement,      │
                              │    threshold,        │
                              │    monitoring_logic, │
                              │    alert_conditions  │
                              │  }                   │
                              └──────────┬───────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    LAYER 4: VERSION CONTROL & AUDIT TRAIL                       │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────────┐
                              │   CHANGE DETECTOR    │
                              │  - Document diff     │
                              │  - Rule comparison   │
                              │  - Impact analysis   │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │   VERSION CONTROL    │
                              │                      │
                              │  ┌─────────────────┐ │
                              │  │ Version 1.0     │ │
                              │  │ 2024-01-15      │ │
                              │  │ - Rule A: ...   │ │
                              │  └─────────────────┘ │
                              │         │            │
                              │         ▼            │
                              │  ┌─────────────────┐ │
                              │  │ Version 2.0     │ │
                              │  │ 2024-06-20      │ │
                              │  │ - Rule A: ΔΔΔΔ  │ │
                              │  │ - Rule B: NEW   │ │
                              │  └─────────────────┘ │
                              │         │            │
                              │         ▼            │
                              │  ┌─────────────────┐ │
                              │  │ Version 3.0     │ │
                              │  │ 2024-10-31      │ │
                              │  │ - Rule A: ΔΔΔΔ  │ │
                              │  │ - Rule C: NEW   │ │
                              │  └─────────────────┘ │
                              └──────────┬───────────┘
                                         │
                         ┌───────────────┼───────────────┐
                         │               │               │
                         ▼               ▼               ▼
              ┌─────────────────┐ ┌─────────────┐ ┌────────────────┐
              │  AUDIT LOG DB   │ │  CHANGELOG  │ │  NOTIFICATION  │
              │  - Who/What/When│ │  GENERATOR  │ │    SYSTEM      │
              │  - Full history │ │  - Summary  │ │  - Compliance  │
              │  - Rollback     │ │  - Impact   │ │  - Legal team  │
              └─────────────────┘ └─────────────┘ └────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           LAYER 5: OUTPUT & STORAGE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────────┐
                              │   KNOWLEDGE BASE     │
                              │                      │
                              │  ┌────────────────┐  │
                              │  │ Regulatory DB  │  │
                              │  │ - Searchable   │  │
                              │  │ - Versioned    │  │
                              │  │ - Queryable    │  │
                              │  └────────────────┘  │
                              └──────────┬───────────┘
                                         │
                         ┌───────────────┼───────────────┐
                         │               │               │
                         ▼               ▼               ▼
              ┌─────────────────┐ ┌─────────────┐ ┌────────────────┐
              │  DOWNSTREAM     │ │  COMPLIANCE │ │   API LAYER    │
              │  APPLICATIONS   │ │   MONITOR   │ │  - GraphQL/REST│
              │  - Integration  │ │  - Alerts   │ │  - Query rules │
              │  - Consumption  │ │  - Reports  │ │  - Subscribe   │
              └─────────────────┘ └─────────────┘ └────────────────┘


═══════════════════════════════════════════════════════════════════════════════════

KEY COMPONENTS:

[SOURCE]     → Original regulatory authority documents
[INGESTION]  → Automated collection and deduplication
[EXTRACTION] → Convert docs to structured text + metadata
[PARSING]    → NLP/LLM to identify obligations and rules
[TRANSFORM]  → Convert to actionable monitoring criteria
[VERSION]    → Track changes, diffs, audit trail
[STORAGE]    → Knowledge base for querying and integration

═══════════════════════════════════════════════════════════════════════════════════