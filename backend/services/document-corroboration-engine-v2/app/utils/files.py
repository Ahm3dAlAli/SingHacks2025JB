from pathlib import Path
from typing import List

from pypdf import PdfReader
from docx import Document


def extract_text_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".txt":
        return path.read_text(errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix}")


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks: List[str] = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        chunks.append(text)
    return "\n".join(chunks)


def _read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)

