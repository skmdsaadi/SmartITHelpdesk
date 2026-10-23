from pathlib import Path
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from test_documents import sample_pdf
from test_workflow import admin_client, register, ticket
from app.knowledge_limits import MAX_UPLOAD_BYTES

GUIDE = (Path(__file__).resolve().parents[2] / 'docs/examples/IT_Helpdesk_Demo_Guide.txt').read_bytes()


@pytest.fixture(autouse=True)
def clean_knowledge(app_context):
    from app.database import get_engine
    from app.models import ChatThread, KnowledgeDocument, KnowledgeState
    # app_context guarantees an isolated randomly named test schema.
    with Session(get_engine()) as db:
        db.execute(delete(ChatThread)); db.execute(delete(KnowledgeDocument))
        db.get(KnowledgeState, 1).revision += 1
        db.commit()


def upload(client, raw=GUIDE, filename='guide.txt', title='Demo IT Support Guide'):
    return client.post('/api/v1/knowledge/documents', params={'title': title, 'filename': filename},
                       content=raw, headers={'Content-Type': 'application/octet-stream'})


def ask(client, question='How do I troubleshoot a Wi-Fi connection?', thread_id=None, request_id=None):
    return client.post('/api/v1/chat/ask', json={'question': question, 'thread_id': thread_id,
                       'request_id': request_id or str(uuid.uuid4())})


def test_document_authentication_roles_csrf_and_input_limits(clients):
    assert upload(clients()).status_code == 401
    employee = clients(); register(employee)
    assert upload(employee).status_code == 403
    assert employee.patch('/api/v1/knowledge/documents/1', json={'is_active': False, 'version': 1}).status_code == 403
    assert employee.delete('/api/v1/knowledge/documents/1?version=1').status_code == 403
    admin = admin_client(clients)
    assert upload(admin, title='  ').status_code == 422
    assert upload(admin, filename='guide.exe').status_code == 422
    assert admin.post('/api/v1/knowledge/documents?title=Guide&filename=guide.txt', content=GUIDE,
                      headers={'X-Helpdesk-Request': ''}).status_code == 403
    assert admin.post('/api/v1/knowledge/documents?title=Guide&filename=guide.txt', content=GUIDE,
                      headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert admin.get('/api/v1/knowledge/documents?page=0').status_code == 422


def test_upload_source_pages_duplicate_guard_and_actual_stream_limit(clients):
    admin = admin_client(clients)
    doc = upload(admin); assert doc.status_code == 201, doc.text
    assert upload(admin).status_code == 409
    pdf = upload(admin, sample_pdf(['Printer offline troubleshooting: check printer power and paper.']), 'printer.pdf', 'Printer PDF')
    assert pdf.status_code == 201, pdf.text
    assert pdf.json()['page_count'] == 1
    detail = admin.get('/api/v1/knowledge/documents/' + str(pdf.json()['id'])).json()
    assert detail['chunks'][0]['page_number'] == 1 and 'printer power' in detail['chunks'][0]['text']
    assert admin.get('/api/v1/knowledge/documents?search=Printer').json()['total'] == 1
    assert admin.get('/api/v1/knowledge/documents?search=%25').json()['total'] == 0
    # No Content-Length: middleware must count actual streamed bytes.
    oversized = admin.post('/api/v1/knowledge/documents?title=Large&filename=large.txt',
        content=iter([b'a' * MAX_UPLOAD_BYTES, b'b']), headers={'Content-Type': 'application/octet-stream'})
    assert oversized.status_code == 413


def test_private_chat_idempotency_and_exact_source_citations(clients):
    admin = admin_client(clients); doc = upload(admin).json()
    employee, other = clients(), clients(); register(employee); register(other)
    request_id = str(uuid.uuid4())
    response = ask(employee, request_id=request_id); assert response.status_code == 200, response.text
    turn = response.json(); assert turn['reason'] == 'matched' and turn['sources']
    source = turn['sources'][0]
    chunks = employee.get('/api/v1/knowledge/documents/' + str(doc['id'])).json()['chunks']
    assert source['text'] == next(c['text'] for c in chunks if c['id'] == source['chunk_id'])
    assert ask(employee, request_id=request_id).json()['id'] == turn['id']
    assert ask(employee, 'Different question about printers', request_id=request_id).status_code == 409
    thread_url = '/api/v1/chat/threads/' + str(turn['thread_id'])
    assert len(employee.get(thread_url).json()['turns']) == 1
    assert other.get(thread_url).status_code == admin.get(thread_url).status_code == 404
    assert ask(other, thread_id=turn['thread_id']).status_code == 404
    assert other.delete(thread_url).status_code == 404
    assert other.get('/api/v1/chat/threads').json()['total'] == 0
    assert employee.post('/api/v1/chat/ask', json={'question': 'How do I reset a password?',
        'request_id': str(uuid.uuid4()), 'user_id': 1}).status_code == 422
    assert clients().get('/api/v1/chat/threads').status_code == 401


def test_deactivation_and_removal_revoke_search_sources_and_history(clients):
    from app.database import get_engine
    from app.models import ChatCitation, KnowledgeChunk
    admin = admin_client(clients); document = upload(admin).json()
    employee = clients(); register(employee)
    turn = ask(employee).json()
    url = '/api/v1/knowledge/documents/' + str(document['id'])
    thread_url = '/api/v1/chat/threads/' + str(turn['thread_id'])
    inactive = admin.patch(url, json={'is_active': False, 'version': document['version']})
    assert inactive.status_code == 200
    assert employee.get(url).status_code == 404
    assert employee.get('/api/v1/knowledge/documents?include_inactive=true').json()['total'] == 0
    old = employee.get(thread_url).json()['turns'][0]
    assert old['reason'] == 'sources_unavailable' and old['sources'] == []
    assert ask(employee, thread_id=turn['thread_id']).json()['reason'] == 'no_documents'
    assert admin.patch(url, json={'is_active': True, 'version': document['version']}).status_code == 409
    active = admin.patch(url, json={'is_active': True, 'version': inactive.json()['version']}).json()
    assert employee.get(thread_url).json()['turns'][0]['sources']
    assert admin.delete(url + '?version=' + str(active['version'])).status_code == 204
    assert employee.get(thread_url).json()['turns'][0]['sources'] == []
    with Session(get_engine()) as db:
        assert db.scalar(select(func.count()).select_from(KnowledgeChunk)) == 0
        assert db.scalar(select(func.count()).select_from(ChatCitation)) == 0
    # Re-uploaded documents have distinct IDs and cannot resurrect deleted citation links.
    assert upload(admin).status_code == 201
    assert employee.get(thread_url).json()['turns'][0]['reason'] == 'sources_unavailable'


def test_fallback_search_failure_rolls_back_and_tickets_still_work(clients):
    employee = clients(); register(employee)
    assert ask(employee).json()['reason'] == 'no_documents'
    admin = admin_client(clients); assert upload(admin).status_code == 201
    unknown = ask(employee, 'How do I bake a chocolate birthday cake?').json()
    assert unknown['reason'] == 'no_match' and unknown['sources'] == []
    before = employee.get('/api/v1/chat/threads').json()['total']
    with patch('app.retrieval.retrieve', side_effect=RuntimeError('test unavailable')):
        assert ask(employee).status_code == 503
    assert employee.get('/api/v1/chat/threads').json()['total'] == before
    assert ticket(employee)['id']


def test_document_capacity_checks_are_atomic(clients):
    admin = admin_client(clients)
    with patch('app.knowledge_api.MAX_CORPUS_CHUNKS', 0):
        assert upload(admin).status_code == 409
    assert admin.get('/api/v1/knowledge/documents').json()['total'] == 0
    assert upload(admin).status_code == 201
    with patch('app.knowledge_api.MAX_DOCUMENTS', 1):
        assert upload(admin, GUIDE + b'\nExtra guidance.', 'other.txt').status_code == 409
    assert admin.get('/api/v1/knowledge/documents').json()['total'] == 1


def test_conversation_limits_and_owner_deletion(clients):
    employee = clients(); register(employee)
    first = ask(employee).json()
    with patch('app.knowledge_api.MAX_THREADS_PER_USER', 1), patch('app.knowledge_api.MAX_TURNS_PER_THREAD', 2):
        assert ask(employee).status_code == 409
        assert ask(employee, thread_id=first['thread_id']).status_code == 200
        assert ask(employee, thread_id=first['thread_id']).status_code == 409
    url = '/api/v1/chat/threads/' + str(first['thread_id'])
    assert employee.delete(url).status_code == 204
    assert employee.get(url).status_code == 404
    assert employee.get('/api/v1/chat/threads').json()['total'] == 0
