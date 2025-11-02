import re
from collections import Counter
from typing import Iterable, List, Tuple


_BASIC_STOPWORDS = {
    "the","a","an","and","or","but","if","then","else","for","to","of","in","on","at","by","with","as","is","are","was","were","be","been","being","this","that","these","those","it","its","from","into","over","under","we","you","they","he","she","them","his","her","their","our","us"
}


def _normalize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9$%\- ]+", " ", text)
    tokens = [t for t in text.split() if t and t not in _BASIC_STOPWORDS]
    return tokens


def jaccard_similarity(a_tokens: Iterable[str], b_tokens: Iterable[str]) -> float:
    a_set, b_set = set(a_tokens), set(b_tokens)
    if not a_set or not b_set:
        return 0.0
    inter = len(a_set & b_set)
    union = len(a_set | b_set)
    return inter / union if union else 0.0


def top_overlap_keywords(a_tokens: List[str], b_tokens: List[str], k: int = 8) -> List[Tuple[str, int]]:
    a_counts = Counter(a_tokens)
    b_counts = Counter(b_tokens)
    common = (a_counts & b_counts)
    return common.most_common(k)


def corroborate(primary_text: str, reference_texts: List[str]) -> dict:
    primary_tokens = _normalize(primary_text)
    ref_tokens_list = [_normalize(t) for t in reference_texts if t and t.strip()]
    if not primary_tokens or not ref_tokens_list:
        return {
            "score": 0.0,
            "matched_keywords": [],
            "details": [],
            "summary": "Insufficient content for corroboration"
        }

    per_ref = []
    best_keywords = []
    best_score = 0.0
    for idx, rt in enumerate(ref_tokens_list):
        s = jaccard_similarity(primary_tokens, rt)
        kws = top_overlap_keywords(primary_tokens, rt)
        per_ref.append({
            "reference_index": idx,
            "similarity": round(s, 4),
            "top_keywords": kws,
        })
        if s > best_score:
            best_score = s
            best_keywords = kws

    avg_score = sum(d["similarity"] for d in per_ref) / len(per_ref)
    summary = (
        "High corroboration" if avg_score >= 0.66 else
        "Moderate corroboration" if avg_score >= 0.33 else
        "Low corroboration"
    )

    return {
        "score": round(avg_score, 4),
        "matched_keywords": best_keywords,
        "details": per_ref,
        "summary": summary
    }

