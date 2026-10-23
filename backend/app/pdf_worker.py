"""Bounded PDF text extraction child process; stdin and stdout are explicit UTF-8/bytes."""
import io
import json
import logging
import sys

from .knowledge_limits import MAX_CHARACTERS, MAX_PAGES, MAX_UPLOAD_BYTES


def extract(raw: bytes) -> dict:
    from pypdf import PdfReader, filters
    from .documents import clean_text

    # pypdf checks decoded Flate output; the process limit covers other allocations.
    filters.ZLIB_MAX_OUTPUT_LENGTH = 4 * 1024 * 1024
    reader = PdfReader(io.BytesIO(raw), strict=False)
    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported. Upload an unlocked copy.")
    if not 1 <= len(reader.pages) <= MAX_PAGES:
        raise ValueError("PDFs must contain between 1 and 50 pages.")
    pages = []
    total = 0
    empty_pages = 0
    for number, page in enumerate(reader.pages, 1):
        stream = page.get_contents()
        if stream is not None and len(stream.get_data()) > 4 * 1024 * 1024:
            raise ValueError("A PDF page is too complex. Export it as plain text.")
        value = clean_text(page.extract_text() or "")
        # PostgreSQL text cannot contain NUL. Strip extraction-only control codes.
        value = "".join(c for c in value if ord(c) >= 32 or c in "\n\t")
        total += len(value)
        if total > MAX_CHARACTERS:
            raise ValueError("The extracted text exceeds 200,000 characters. Split the document.")
        if value:
            pages.append({"page_number": number, "text": value})
        else:
            empty_pages += 1
    warnings = []
    if empty_pages:
        warnings.append(f"{empty_pages} page(s) had no extractable text. Scanned pages need OCR.")
    return {"pages": pages, "page_count": len(reader.pages), "warnings": warnings}


def main():
    # Windows has the same timeout/size/page limits, but no POSIX address-space cap.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
    except ImportError:
        pass
    logging.disable(logging.CRITICAL)
    code = 0
    try:
        raw = sys.stdin.buffer.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise ValueError("PDF exceeds the 2 MiB upload limit.")
        result = extract(raw)
    except ValueError as exc:
        # Only explicitly authored validation messages are returned; parser errors are generic.
        allowed = ("Password-protected", "PDFs must", "A PDF page", "The extracted text", "PDF exceeds")
        message = str(exc)
        result = {"error": message if message.startswith(allowed) else "The PDF is damaged or unsupported. Try a TXT export."}
        code = 1
    except Exception:
        result = {"error": "The PDF is damaged, too complex or unsupported. Try a TXT export."}
        code = 1
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
