from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .schemas import InputModel


class DocumentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    filename: str
    media_type: str
    byte_size: int
    is_active: bool
    version: int
    page_count: int
    chunk_count: int
    character_count: int
    warnings: list[str]
    created_at: datetime


class ChunkOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    chunk_index: int
    page_number: int | None
    text: str


class DocumentDetail(DocumentOutput):
    chunks: list[ChunkOutput]


class DocumentPage(BaseModel):
    items: list[DocumentOutput]
    total: int
    page: int
    page_size: int


class DocumentUpdate(InputModel):
    is_active: bool
    version: int = Field(ge=1)


class AskInput(InputModel):
    question: str = Field(min_length=5, max_length=2000)
    thread_id: int | None = Field(default=None, ge=1)
    request_id: UUID

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value):
        if isinstance(value, str):
            if "\x00" in value:
                raise ValueError("Question cannot contain NUL characters.")
            return value.strip()
        return value


class ThreadOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ThreadPage(BaseModel):
    items: list[ThreadOutput]
    total: int
    page: int
    page_size: int


class CitationOutput(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    filename: str
    page_number: int | None
    chunk_index: int
    text: str
    score: float


class TurnOutput(BaseModel):
    id: int
    thread_id: int
    request_id: str
    question: str
    answer: str
    reason: Literal["matched", "no_match", "no_documents", "sources_unavailable"]
    method: str
    corpus_revision: int
    sources: list[CitationOutput]
    unavailable_sources: int
    created_at: datetime


class ThreadDetail(ThreadOutput):
    turns: list[TurnOutput]
