"""Preserve the AI assessment alongside each ticket's selected category."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tickets", sa.Column("ai_assessment", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("tickets", "ai_assessment")
