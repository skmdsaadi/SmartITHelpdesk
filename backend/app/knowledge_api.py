"""Authenticated document management and owner-private, source-backed conversations."""
import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from . import retrieval
from .documents import DocumentError, extract_document
from .knowledge_limits import MAX_CORPUS_CHUNKS, MAX_DOCUMENTS, MAX_THREADS_PER_USER, MAX_TURNS_PER_THREAD, MAX_UPLOAD_BYTES
from .knowledge_schemas import (
    AskInput, ChunkOutput, DocumentDetail, DocumentOutput, DocumentPage, DocumentUpdate,
    ThreadDetail, ThreadOutput, ThreadPage, TurnOutput,
)
from .models import ChatCitation, ChatThread, ChatTurn, KnowledgeChunk, KnowledgeDocument, KnowledgeState, User, utcnow
from .security import AdminUser, CurrentUser, DB, limit_user

router = APIRouter(prefix="/api/v1", tags=["Knowledge and chat"])
logger = logging.getLogger(__name__)


def state_lock(db, *, shared=False):
    state = db.scalar(select(KnowledgeState).where(KnowledgeState.id == 1).with_for_update(read=shared))
    if state is None:
        raise HTTPException(503, "Knowledge setup is incomplete. Run database migrations.")
    return state


def find_document(db, user, document_id):
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
    if user.role != "admin":
        stmt = stmt.where(KnowledgeDocument.is_active.is_(True))
    document = db.scalar(stmt)
    if document is None:
        raise HTTPException(404, "Document not found or no longer available.")
    return document


@router.get("/knowledge/documents", response_model=DocumentPage)
def list_documents(user: CurrentUser, db: DB, include_inactive: bool = False,
                   search: Annotated[str, Query(max_length=160)] = "",
                   page: Annotated[int, Query(ge=1, le=100000)] = 1):
    stmt = select(KnowledgeDocument)
    if not (include_inactive and user.role == "admin"):
        stmt = stmt.where(KnowledgeDocument.is_active.is_(True))
    if search.strip():
        stmt = stmt.where(KnowledgeDocument.title.icontains(search.strip(), autoescape=True))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(KnowledgeDocument.created_at.desc(), KnowledgeDocument.id.desc())
                      .offset((page - 1) * 10).limit(10)).all()
    return {"items": items, "total": total, "page": page, "page_size": 10}


def save_upload(db, user, raw, filename, title):
    try:
        extracted = extract_document(raw, filename)
    except DocumentError as exc:
        raise HTTPException(422, str(exc)) from None
    state = state_lock(db)
    if db.scalar(select(KnowledgeDocument.id).where(KnowledgeDocument.sha256 == extracted["sha256"])):
        raise HTTPException(409, "This file is already uploaded. Open the existing document or reactivate it.")
    if db.scalar(select(func.count()).select_from(KnowledgeDocument)) >= MAX_DOCUMENTS:
        raise HTTPException(409, "The knowledge base allows 30 documents. Remove an unused document first.")
    chunks = extracted.pop("chunks")
    count = db.scalar(select(func.count()).select_from(KnowledgeChunk))
    if count + len(chunks) > MAX_CORPUS_CHUNKS:
        raise HTTPException(409, "The knowledge base allows 500 passages in total. Remove unused documents first.")
    document = KnowledgeDocument(title=title, uploaded_by=user.id, chunk_count=len(chunks), **extracted)
    db.add(document)
    db.flush()
    db.add_all(KnowledgeChunk(document_id=document.id, **chunk) for chunk in chunks)
    state.revision += 1
    db.commit()
    return document


@router.post("/knowledge/documents", response_model=DocumentOutput, status_code=201,
             openapi_extra={"requestBody": {"required": True, "content": {
                 "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}})
async def upload_document(request: Request, user: AdminUser, db: DB,
                          title: Annotated[str, Query(min_length=3, max_length=160)],
                          filename: Annotated[str, Query(min_length=1, max_length=300)]):
    title = title.strip()
    if len(title) < 3 or any(ord(c) < 32 for c in title):
        raise HTTPException(422, "Use a document title of at least three characters without control characters.")
    limit_user(user.id, "upload", 6)
    data = bytearray()
    async for part in request.stream():
        if len(data) + len(part) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File exceeds the 2 MiB upload limit.")
        data.extend(part)
    return await run_in_threadpool(save_upload, db, user, bytes(data), filename, title)


@router.get("/knowledge/documents/{document_id}", response_model=DocumentDetail)
def document_detail(document_id: int, user: CurrentUser, db: DB):
    document = find_document(db, user, document_id)
    result = DocumentOutput.model_validate(document).model_dump()
    result["chunks"] = [ChunkOutput.model_validate(c) for c in db.scalars(
        select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id).order_by(KnowledgeChunk.chunk_index))]
    return result


@router.patch("/knowledge/documents/{document_id}", response_model=DocumentOutput)
def update_document(document_id: int, data: DocumentUpdate, user: AdminUser, db: DB):
    state = state_lock(db)
    document = find_document(db, user, document_id)
    if document.version != data.version:
        raise HTTPException(409, "This document changed. Refresh before updating it.")
    if document.is_active != data.is_active:
        document.is_active = data.is_active
        document.version += 1
        state.revision += 1
        db.commit()
    return document


@router.delete("/knowledge/documents/{document_id}", status_code=204)
def remove_document(document_id: int, user: AdminUser, db: DB,
                    version: Annotated[int, Query(ge=1)]):
    state = state_lock(db)
    document = find_document(db, user, document_id)
    if document.version != version:
        raise HTTPException(409, "This document changed. Refresh before removing it.")
    # Database cascades remove passages and citation links; chat questions remain private.
    db.delete(document)
    state.revision += 1
    db.commit()


def find_thread(db, user, thread_id):
    # Administrators have no override for another person's private conversations.
    thread = db.scalar(select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user.id))
    if thread is None:
        raise HTTPException(404, "Conversation not found.")
    return thread


def source_map(db, turn_ids):
    if not turn_ids:
        return {}
    rows = db.execute(select(ChatCitation, KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeChunk, ChatCitation.chunk_id == KnowledgeChunk.id)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(ChatCitation.turn_id.in_(turn_ids), KnowledgeDocument.is_active.is_(True))
        .order_by(ChatCitation.turn_id, ChatCitation.rank)).all()
    result = {}
    for citation, chunk, document in rows:
        result.setdefault(citation.turn_id, []).append({
            "chunk_id": chunk.id, "document_id": document.id, "document_title": document.title,
            "filename": document.filename, "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index, "text": chunk.text, "score": citation.score})
    return result


def turn_output(turn, sources):
    unavailable = turn.source_count - len(sources)
    reason = turn.reason
    if reason == "matched" and not sources:
        reason = "sources_unavailable"
    answers = {
        "matched": "These passages match your question. Check the source and whether its guidance applies to your situation.",
        "no_match": "I could not find a sufficiently close passage in the active documents. Use the document's wording or create a support ticket.",
        "no_documents": "There are no active knowledge documents yet. An administrator can upload a PDF or TXT guide. You can also create a support ticket.",
        "sources_unavailable": "The sources for this earlier response are no longer available. Ask again to search the current knowledge base.",
    }
    answer = answers[reason]
    if sources and unavailable:
        answer += " Some earlier sources are no longer available; only active sources are shown."
    return {"id": turn.id, "thread_id": turn.thread_id, "request_id": turn.request_id,
            "question": turn.question, "answer": answer, "reason": reason, "method": turn.method,
            "corpus_revision": turn.corpus_revision, "sources": sources,
            "unavailable_sources": unavailable, "created_at": turn.created_at}


@router.get("/chat/threads", response_model=ThreadPage)
def list_threads(user: CurrentUser, db: DB, page: Annotated[int, Query(ge=1, le=100000)] = 1):
    stmt = select(ChatThread).where(ChatThread.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    threads = db.scalars(stmt.order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
                        .offset((page - 1) * 20).limit(20)).all()
    return {"items": threads, "total": total, "page": page, "page_size": 20}


@router.get("/chat/threads/{thread_id}", response_model=ThreadDetail)
def thread_detail(thread_id: int, user: CurrentUser, db: DB):
    thread = find_thread(db, user, thread_id)
    turns = db.scalars(select(ChatTurn).where(ChatTurn.thread_id == thread.id)
                      .order_by(ChatTurn.created_at, ChatTurn.id)).all()
    sources = source_map(db, [t.id for t in turns])
    return {**ThreadOutput.model_validate(thread).model_dump(),
            "turns": [turn_output(t, sources.get(t.id, [])) for t in turns]}


@router.delete("/chat/threads/{thread_id}", status_code=204)
def remove_thread(thread_id: int, user: CurrentUser, db: DB):
    # Use the same per-user lock as submit, so delete and append cannot interleave.
    db.scalar(select(User).where(User.id == user.id).with_for_update(key_share=True))
    db.delete(find_thread(db, user, thread_id))
    db.commit()


@router.post("/chat/ask", response_model=TurnOutput)
def ask(data: AskInput, user: CurrentUser, db: DB):
    # NO KEY UPDATE serializes requests for one user while allowing FK key-share locks.
    db.scalar(select(User).where(User.id == user.id).with_for_update(key_share=True))
    previous = db.scalar(select(ChatTurn).where(ChatTurn.user_id == user.id,
                                               ChatTurn.request_id == str(data.request_id)))
    if previous:
        if previous.question != data.question or data.thread_id not in (None, previous.thread_id):
            raise HTTPException(409, "This request ID belongs to a different question or conversation.")
        return turn_output(previous, source_map(db, [previous.id]).get(previous.id, []))
    limit_user(user.id, "ask", 20)
    if data.thread_id is None:
        count = db.scalar(select(func.count()).select_from(ChatThread).where(ChatThread.user_id == user.id))
        if count >= MAX_THREADS_PER_USER:
            raise HTTPException(409, "You have 100 conversations. Delete an unused conversation before starting another.")
        thread = ChatThread(user_id=user.id, title=data.question[:100])
        db.add(thread)
        db.flush()
    else:
        thread = find_thread(db, user, data.thread_id)
    count = db.scalar(select(func.count()).select_from(ChatTurn).where(ChatTurn.thread_id == thread.id))
    if count >= MAX_TURNS_PER_THREAD:
        raise HTTPException(409, "This conversation has 50 questions. Start another conversation to continue.")
    state = state_lock(db, shared=True)
    rows = db.execute(select(KnowledgeChunk.id, KnowledgeChunk.text)
                      .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                      .where(KnowledgeDocument.is_active.is_(True)).order_by(KnowledgeChunk.id)).all()
    chunks = [{"id": row.id, "text": row.text} for row in rows]
    try:
        matches = retrieval.retrieve(chunks, data.question)
    except Exception as exc:
        logger.error("Knowledge search failed (%s).", type(exc).__name__)
        raise HTTPException(503, "Knowledge search is unavailable. Try again later or create a support ticket.") from None
    reason = "matched" if matches else ("no_match" if chunks else "no_documents")
    turn = ChatTurn(thread_id=thread.id, user_id=user.id, request_id=str(data.request_id),
                    question=data.question, reason=reason, method=retrieval.METHOD,
                    corpus_revision=state.revision, source_count=len(matches))
    db.add(turn)
    db.flush()
    db.add_all(ChatCitation(turn_id=turn.id, chunk_id=m["chunk_id"], rank=i, score=m["score"])
               for i, m in enumerate(matches, 1))
    thread.updated_at = utcnow()
    db.commit()
    return turn_output(turn, source_map(db, [turn.id]).get(turn.id, []))
