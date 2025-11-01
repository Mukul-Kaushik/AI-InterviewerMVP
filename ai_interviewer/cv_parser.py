"""Utilities to ingest CV/resume documents."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import docx
from PyPDF2 import PdfReader


def _read_pdf(path: Path) -> Iterable[str]:
    reader = PdfReader(str(path))
    for page in reader.pages:
        text = page.extract_text() or ""
        yield text.strip()


def _read_docx(path: Path) -> Iterable[str]:
    document = docx.Document(str(path))
    for para in document.paragraphs:
        if para.text:
            yield para.text.strip()


def _read_text(path: Path) -> Iterable[str]:
    yield from path.read_text(encoding="utf-8", errors="ignore").splitlines()


def extract_text(path: Path) -> str:
    """Extract clean text from a supported CV format."""

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        lines = _read_pdf(path)
    elif suffix in {".doc", ".docx"}:
        lines = _read_docx(path)
    else:
        lines = _read_text(path)
    content = "\n".join(line for line in lines if line)
    return content.strip()
