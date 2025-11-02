from __future__ import annotations

import time
from threading import Lock
from typing import Dict


_lock = Lock()
_total_success = 0
_total_errors = 0
_sum_score = 0.0
_sum_duration = 0.0
_timestamps: list[float] = []
_risk_levels: Dict[str, int] = {"low": 0, "medium": 0, "high": 0}


def _risk_from_score(score: float) -> str:
    # Inverse mapping: low corroboration => high risk
    if score < 0.33:
        return "high"
    if score < 0.66:
        return "medium"
    return "low"


def record_request(success: bool, score: float | None, duration_sec: float | None) -> None:
    global _total_success, _total_errors, _sum_score, _sum_duration
    with _lock:
        if success:
            _total_success += 1
            if score is not None:
                _sum_score += float(score)
                lvl = _risk_from_score(float(score))
                _risk_levels[lvl] = _risk_levels.get(lvl, 0) + 1
            if duration_sec is not None:
                _sum_duration += float(duration_sec)
            _timestamps.append(time.time())
        else:
            _total_errors += 1


def get_statistics() -> Dict[str, object]:
    with _lock:
        total = int(_total_success)
        avg_score = (_sum_score / total) if total > 0 else 0.0
        avg_duration = (_sum_duration / total) if total > 0 else 0.0
        # recent uploads in last 24h
        cutoff = time.time() - 24 * 3600
        recent = sum(1 for t in _timestamps if t >= cutoff)

        documents_by_status = {
            "processed": total,
            "failed": int(_total_errors),
        }

        documents_by_risk_level = dict(_risk_levels)

        return {
            "total_documents": total,
            "documents_by_status": documents_by_status,
            "documents_by_risk_level": documents_by_risk_level,
            "average_processing_time": round(avg_duration, 4),
            # Report average "risk" as inverse of corroboration score
            "average_risk_score": round(max(0.0, 1.0 - avg_score), 4),
            "total_high_risk": int(_risk_levels.get("high", 0)),
            "recent_uploads": int(recent),
        }

