"""Validate uploads and produce bounded, page-aware text chunks. No original files are kept."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading

from .knowledge_limits import (
    CHUNK_OVERLAP, CHUNK_SIZE, MAX_CHARACTERS, MAX_DOCUMENT_CHUNKS,
    MAX_UPLOAD_BYTES, PDF_TIMEOUT_SECONDS,
)


class DocumentError(ValueError):
    pass


_parser_slot = threading.BoundedSemaphore(1)


def clean_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n")
    value = re.sub(r"[^\S\n]+", " ", value)
    return re.sub(r"\n[ \t]+", "\n", value).strip()


def split_chunks(pages: list[dict]) -> list[dict]:
    chunks = []
    for page in pages:
        # Separate paragraphs keep unrelated FAQ answers apart. Long paragraphs overlap.
        for paragraph in re.split(r"\n\s*\n", page["text"]):
            paragraph = paragraph.strip()
            start = 0
            while start < len(paragraph):
                end = min(start + CHUNK_SIZE, len(paragraph))
                if end < len(paragraph):
                    boundary = paragraph.rfind(" ", start + CHUNK_SIZE // 2, end)
                    if boundary > start:
                        end = boundary
                snippet = paragraph[start:end].strip()
                if snippet:
                    chunks.append({"chunk_index": len(chunks) + 1,
                                   "page_number": page["page_number"], "text": snippet})
                    if len(chunks) > MAX_DOCUMENT_CHUNKS:
                        raise DocumentError("Too many passages. Split this document into smaller files.")
                if end == len(paragraph):
                    break
                start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def extract_document(raw: bytes, filename: str) -> dict:
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise DocumentError("Choose a non-empty file of at most 2 MiB.")
    filename = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not filename or len(filename) > 160 or any(ord(c) < 32 for c in filename):
        raise DocumentError("Use a filename of 1 to 160 characters without control characters.")
    kind = Path(filename).suffix.lower()
    warnings = []
    if kind == ".txt":
        try:
            value = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise DocumentError("TXT files must use UTF-8 encoding. Save as UTF-8 and try again.") from None
        if value.lstrip().startswith("%PDF-") or any(ord(c) < 32 and c not in "\n\r\t\f" for c in value):
            raise DocumentError("The file does not contain supported plain text.")
        pages = [{"page_number": None, "text": clean_text(value)}]
        page_count = 0
    elif kind == ".pdf":
        if b"%PDF-" not in raw[:1024]:
            raise DocumentError("The file does not have a valid PDF header.")
        if not _parser_slot.acquire(blocking=False):
            raise DocumentError("Another PDF is being processed. Wait a moment and retry.")
        try:
            # Separate interpreter: timeout kills the child, and POSIX adds resource limits.
            result = subprocess.run(
                [sys.executable, "-m", "app.pdf_worker"], input=raw,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                timeout=PDF_TIMEOUT_SECONDS, cwd=Path(__file__).resolve().parents[1],
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise DocumentError("PDF processing took too long. Use a smaller PDF or a UTF-8 TXT file.") from None
        finally:
            _parser_slot.release()
        try:
            parsed = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeError, ValueError):
            raise DocumentError("PDF processing exceeded its limits or the file is damaged. Try a TXT export.") from None
        if result.returncode != 0 or "error" in parsed:
            raise DocumentError(parsed.get("error", "Could not extract this PDF."))
        pages, warnings, page_count = parsed["pages"], parsed["warnings"], parsed["page_count"]
    else:
        raise DocumentError("Only PDF and UTF-8 TXT files are supported.")
    characters = sum(len(p["text"]) for p in pages)
    if characters > MAX_CHARACTERS:
        raise DocumentError("The extracted text exceeds 200,000 characters. Split the document.")
    if sum(c.isalpha() for p in pages for c in p["text"]) < 20:
        raise DocumentError("No usable text found. Scanned PDFs need OCR before upload.")
    chunks = split_chunks(pages)
    return {"filename": filename, "media_type": "application/pdf" if kind == ".pdf" else "text/plain",
            "byte_size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "page_count": page_count, "character_count": characters,
            "warnings": warnings, "chunks": chunks}
