"""extend_memories_with_user_and_position

Revision ID: 6f42f0d9a1b7
Revises: 3c8f2f6d4e1a
Create Date: 2026-02-16 12:00:00.000000

"""

# pylint: disable=no-member

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f42f0d9a1b7"
down_revision: Union[str, Sequence[str], None] = "3c8f2f6d4e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "chat_memories",
        "chat_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.add_column(
        "chat_memories",
        sa.Column("user_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "chat_memories",
        sa.Column("source_message_position", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_memories_user_id_users",
        "chat_memories",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_chat_memories_user_id",
        "chat_memories",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_memories_user_active",
        "chat_memories",
        ["user_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_chat_memories_user_importance",
        "chat_memories",
        ["user_id", "importance"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_chat_memories_user_importance",
        table_name="chat_memories",
    )
    op.drop_index("ix_chat_memories_user_active", table_name="chat_memories")
    op.drop_index("ix_chat_memories_user_id", table_name="chat_memories")
    op.drop_constraint(
        "fk_chat_memories_user_id_users",
        "chat_memories",
        type_="foreignkey",
    )
    op.drop_column("chat_memories", "source_message_position")
    op.drop_column("chat_memories", "user_id")
    op.alter_column(
        "chat_memories",
        "chat_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
