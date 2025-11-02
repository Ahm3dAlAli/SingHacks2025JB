from pathlib import Path
from typing import List
import subprocess
import tempfile
import os

from pypdf import PdfReader
from docx import Document
from app.services.groq_ocr import GroqOCR


def extract_text_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".txt":
        return path.read_text(errors="ignore")
    if suffix in (".png", ".jpg", ".jpeg"):
        data = path.read_bytes()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        ocr = GroqOCR()
        return ocr.ocr_image_bytes(data, mime)
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
    text_all = "\n".join(chunks)
    # Fallback to OCR if text is likely empty (scanned PDF)
    if len(text_all.strip()) < 40:
        try:
            ocr_text = _ocr_pdf_with_groq(path)
            if ocr_text:
                return ocr_text
        except Exception:
            pass
    return text_all


def _ocr_pdf_with_groq(path: Path) -> str:
    # Render PDF pages to PNG using Ghostscript, then OCR via Groq
    from app.services.groq_ocr import GroqOCR
    ocr = GroqOCR()
    with tempfile.TemporaryDirectory() as td:
        out_pat = os.path.join(td, "page-%03d.png")
        # Render at 144 DPI for speed/quality balance
        cmd = [
            "gs", "-dSAFER", "-dBATCH", "-dNOPAUSE",
            "-sDEVICE=png16m",
            "-r144",
            "-o", out_pat,
            str(path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Collect generated images
        files = sorted([p for p in Path(td).glob("page-*.png")])
        texts: List[str] = []
        for img in files:
            try:
                data = img.read_bytes()
                t = ocr.ocr_image_bytes(data, "image/png")
                texts.append(t or "")
            except Exception:
                continue
        return "\n".join(texts).strip()


def _read_docx(path: Path) -> str:
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)
