"""add_media_table

Revision ID: 7b1cbbe52f0b
Revises: ef858959d5ae
Create Date: 2025-07-31 11:58:10.248201

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b1cbbe52f0b"
down_revision: Union[str, Sequence[str], None] = "ef858959d5ae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create media table
    op.create_table(
        "media",
        sa.Column("file_reference", sa.String(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(50), nullable=False),
        sa.Column("text_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("file_reference"),
    )

    # Create indexes for faster queries
    op.create_index("ix_media_type", "media", ["media_type"], unique=False)
    op.create_index("ix_media_chat_id", "media", ["chat_id"], unique=False)
    op.create_index("ix_media_message_id", "media", ["message_id"], unique=False)
    op.create_index("ix_media_chat_message", "media", ["chat_id", "message_id"], unique=False)

    # Add foreign key constraints
    op.create_foreign_key("fk_media_chat_id", "media", "chats", ["chat_id"], ["id"], ondelete="CASCADE")

    # Add composite foreign key for message (chat_id, message_id)
    op.create_foreign_key("fk_media_message", "media", "messages", ["chat_id", "message_id"], ["chat_id", "message_id"], ondelete="CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop media table
    op.drop_foreign_key("fk_media_message", "media", type_="foreignkey")
    op.drop_foreign_key("fk_media_chat_id", "media", type_="foreignkey")
    op.drop_index("ix_media_chat_message", table_name="media")
    op.drop_index("ix_media_message_id", table_name="media")
    op.drop_index("ix_media_chat_id", table_name="media")
    op.drop_index("ix_media_type", table_name="media")
    op.drop_table("media")
