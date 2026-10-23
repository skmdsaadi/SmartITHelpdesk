"""Knowledge documents, source citations and private conversations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("knowledge_state", sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("revision", sa.Integer(), nullable=False),
                    sa.CheckConstraint("id = 1", name="ck_knowledge_singleton"))
    op.execute("INSERT INTO knowledge_state (id, revision) VALUES (1, 1)")
    op.create_table("knowledge_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("filename", sa.String(160), nullable=False),
        sa.Column("media_type", sa.String(30), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"))
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_table("chat_threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_chat_threads_owner_updated", "chat_threads", ["user_id", "updated_at"])
    op.create_table("chat_turns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("method", sa.String(60), nullable=False),
        sa.Column("corpus_revision", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", name="uq_chat_request"))
    op.create_index("ix_chat_turns_thread_id", "chat_turns", ["thread_id"])
    op.create_table("chat_citations",
        sa.Column("turn_id", sa.Integer(), sa.ForeignKey("chat_turns.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False))


def downgrade():
    for table in ["chat_citations", "chat_turns", "chat_threads", "knowledge_chunks", "knowledge_documents", "knowledge_state"]:
        op.drop_table(table)
