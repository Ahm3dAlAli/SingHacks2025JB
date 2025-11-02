from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import tempfile

from app.core.corroborator import corroborate
from app.core.stats import record_request, get_statistics
from app.storage.db import save_record, list_records, get_record, ensure_db
from app.utils.files import extract_text_from_path


app = FastAPI(
    title="Document Corroboration Engine v2 (Lite)",
    version="2.0.0",
    description="Lightweight service for simple text corroboration"
)

ensure_db()


class CorroborationRequest(BaseModel):
    primary_text: str = Field(..., description="Main text to corroborate")
    reference_texts: List[str] = Field(default_factory=list, description="List of reference texts")


@app.get("/health")
def health():
    return {"status": "healthy", "version": "2.0.0"}


@app.post("/api/v1/corroborate")
def corroborate_texts(payload: CorroborationRequest):
    import time as _t
    import uuid, datetime
    started = _t.perf_counter()
    try:
        if not payload.primary_text.strip():
            raise HTTPException(status_code=400, detail="primary_text is empty")
        if not payload.reference_texts:
            raise HTTPException(status_code=400, detail="reference_texts is required and cannot be empty")
        result = corroborate(payload.primary_text, payload.reference_texts)
        duration = _t.perf_counter() - started
        record_request(True, float(result.get("score", 0.0)), duration)
        # persist minimal record
        rec = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "primary_name": "text",
            "ref_count": len(payload.reference_texts),
            "score": float(result.get("score", 0.0)),
            "summary": result.get("summary"),
            "details_full": result,
        }
        save_record(rec)
        return result
    except HTTPException:
        record_request(False, None, None)
        raise
    except Exception as e:
        record_request(False, None, None)
        raise


@app.post("/api/v1/corroborate/upload")
async def corroborate_files(
    primary_file: UploadFile = File(...),
    reference_files: Optional[List[UploadFile]] = File(None)
):
    import time as _t
    import uuid, datetime
    started = _t.perf_counter()
    try:
        if not reference_files:
            raise HTTPException(status_code=400, detail="At least one reference_files is required")

        with tempfile.TemporaryDirectory() as td:
            p_path = Path(td) / primary_file.filename
            p_bytes = await primary_file.read()
            p_path.write_bytes(p_bytes)
            try:
                primary_text = extract_text_from_path(p_path)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"primary_file error: {e}")

            refs: List[str] = []
            for f in reference_files:
                r_path = Path(td) / f.filename
                r_bytes = await f.read()
                r_path.write_bytes(r_bytes)
                try:
                    refs.append(extract_text_from_path(r_path))
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"reference_file {f.filename} error: {e}")

        result = corroborate(primary_text, refs)
        duration = _t.perf_counter() - started
        record_request(True, float(result.get("score", 0.0)), duration)
        rec = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "primary_name": primary_file.filename,
            "ref_count": len(reference_files),
            "score": float(result.get("score", 0.0)),
            "summary": result.get("summary"),
            "details_full": result,
        }
        save_record(rec)
        return result
    except HTTPException:
        record_request(False, None, None)
        raise
    except Exception:
        record_request(False, None, None)
        raise


@app.get("/api/v1/statistics")
def statistics():
    return get_statistics()


@app.get("/api/v1/history")
def history(limit: int = 50):
    """List recent corroboration results (persisted)."""
    try:
        return {"items": list_records(limit=max(1, min(500, int(limit))))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history/{rec_id}")
def history_item(rec_id: str):
    """Fetch a specific corroboration result by id."""
    try:
        rec = get_record(rec_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Not found")
        return rec
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
