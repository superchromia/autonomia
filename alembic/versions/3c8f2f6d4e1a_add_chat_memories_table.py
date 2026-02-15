"""add_chat_memories_table

Revision ID: 3c8f2f6d4e1a
Revises: 241025db83a7
Create Date: 2026-02-15 20:30:00.000000

"""

# pylint: disable=no-member

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c8f2f6d4e1a"
down_revision: Union[str, Sequence[str], None] = "241025db83a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "chat_memories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("memory_text", sa.Text(), nullable=False),
        sa.Column(
            "memory_type",
            sa.String(length=30),
            nullable=False,
            server_default="fact",
        ),
        sa.Column(
            "importance",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["chats.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_memories_chat_active",
        "chat_memories",
        ["chat_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_chat_memories_importance",
        "chat_memories",
        ["chat_id", "importance"],
        unique=False,
    )
    op.create_index(
        "ix_chat_memories_chat_id",
        "chat_memories",
        ["chat_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_chat_memories_chat_id", table_name="chat_memories")
    op.drop_index("ix_chat_memories_importance", table_name="chat_memories")
    op.drop_index("ix_chat_memories_chat_active", table_name="chat_memories")
    op.drop_table("chat_memories")
