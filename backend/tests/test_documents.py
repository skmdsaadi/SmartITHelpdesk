import io
import subprocess
from unittest.mock import patch

import pytest

from app.documents import DocumentError, extract_document, split_chunks
from app.knowledge_limits import CHUNK_SIZE, MAX_UPLOAD_BYTES


def sample_pdf(texts=None, *, encrypted=False, blank_pages=0):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for text in texts or []:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        literal = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream.set_data(f'BT /F1 12 Tf 50 700 Td ({literal}) Tj ET'.encode())
        page[NameObject('/Contents')] = stream
    for _ in range(blank_pages):
        writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt('test-only-password')
    output = io.BytesIO(); writer.write(output)
    return output.getvalue()


def test_utf8_bom_windows_lines_and_filename_sanitization():
    raw = '\ufeffWi-Fi guide\r\nReconnect to the approved wireless network.\r\n\r\nবাংলা নির্দেশনা এখানে সংরক্ষিত থাকবে।'.encode()
    document = extract_document(raw, r'C:\uploads\guide.TXT')
    assert document['filename'] == 'guide.TXT'
    assert document['chunks'][0]['page_number'] is None
    assert '\r' not in document['chunks'][0]['text']
    assert 'বাংলা' in document['chunks'][1]['text']
    assert document['byte_size'] == len(raw)


def test_chunking_preserves_long_tail_and_page_provenance():
    text = ' '.join(f'word{i}' for i in range(800))
    chunks = split_chunks([{'page_number': 7, 'text': text}])
    assert len(chunks) > 2
    assert all(len(c['text']) <= CHUNK_SIZE and c['page_number'] == 7 for c in chunks)
    assert chunks[-1]['text'].endswith('word799')
    assert {f'word{i}' for i in range(800)} <= set(' '.join(c['text'] for c in chunks).split())


@pytest.mark.parametrize('raw,name', [(b'', 'empty.txt'), (b'x' * (MAX_UPLOAD_BYTES + 1), 'large.txt'),
    (b'\xff\xfe\x00', 'bad.txt'), (b'unsafe\x00text', 'bad.txt'),
    (b'plain text pretending to be PDF', 'wrong.pdf'), (b'data', 'wrong.exe')])
def test_invalid_uploads_are_rejected(raw, name):
    with pytest.raises(DocumentError):
        extract_document(raw, name)


def test_real_pdf_extraction_page_numbers_and_blank_page_warning():
    doc = extract_document(sample_pdf(['Password reset uses the approved account recovery portal.',
        'Printer offline troubleshooting begins with printer power and paper.'], blank_pages=1), 'guide.pdf')
    assert doc['page_count'] == 3
    assert [c['page_number'] for c in doc['chunks']] == [1, 2]
    assert 'Password reset' in doc['chunks'][0]['text'] and doc['warnings']


def test_encrypted_scanned_and_excessive_page_pdfs_are_rejected():
    for raw in [sample_pdf(['Password reset using the account recovery portal.'], encrypted=True),
                sample_pdf(blank_pages=1), sample_pdf(blank_pages=51), b'%PDF-1.7\ninvalid']:
        with pytest.raises(DocumentError):
            extract_document(raw, 'guide.pdf')


def test_pdf_timeout_returns_actionable_error():
    with patch('app.documents.subprocess.run', side_effect=subprocess.TimeoutExpired('worker', 15)):
        with pytest.raises(DocumentError, match='too long'):
            extract_document(b'%PDF-1.7\n', 'guide.pdf')
