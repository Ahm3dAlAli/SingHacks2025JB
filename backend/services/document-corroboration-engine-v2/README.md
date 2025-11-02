# Document Corroboration Engine v2 (Lite)

Lightweight FastAPI microservice for simple text corroboration. No Celery, Redis, or external AI services. Accepts raw text or basic files (PDF/DOCX/TXT) and returns a similarity score with top overlapping keywords.

## Features

- Single endpoint to corroborate a primary text against references
- Optional file upload variant (PDF/DOCX/TXT)
- Simple, explainable scoring (Jaccard similarity over normalized tokens)
- Minimal dependencies; quick to run locally or via Docker

## Quick Start (Docker)

```bash
cd services/document-corroboration-engine-v2
docker-compose up -d --build
curl http://localhost:8010/health
```

Corroborate with JSON:
```bash
curl -s -X POST http://localhost:8010/api/v1/corroborate \
  -H 'Content-Type: application/json' \
  -d '{
    "primary_text": "Acme Corp revenue was $10M in 2024.",
    "reference_texts": [
      "2024 financial report shows Acme Corp revenue at $10 million.",
      "Acme posted revenue growth in FY2024 to $10M."
    ]
  }'
```

Upload files (primary + multiple references):
```bash
curl -s -X POST http://localhost:8010/api/v1/corroborate/upload \
  -F primary_file=@samples/primary.pdf \
  -F reference_files=@samples/ref1.txt \
  -F reference_files=@samples/ref2.docx
```

## Local Dev

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

## API

- GET `/health` — service status
- POST `/api/v1/corroborate` — JSON: `{ primary_text: str, reference_texts: [str] }`
- POST `/api/v1/corroborate/upload` — multipart form: `primary_file`, `reference_files[]`

## Notes

- Supported file types: .pdf, .docx, .txt
- This is a simple baseline for hackathon flows and testing. Upgrade paths: TF-IDF, embeddings, entity-level checks.

