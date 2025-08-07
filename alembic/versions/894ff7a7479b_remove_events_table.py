"""remove_events_table

Revision ID: 894ff7a7479b
Revises: 7b1cbbe52f0b
Create Date: 2025-07-31 12:13:38.002318

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "894ff7a7479b"
down_revision: Union[str, Sequence[str], None] = "7b1cbbe52f0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop events table and its foreign key constraints

    # Drop indexes first
    op.drop_index("ix_events_message_id", table_name="events")
    op.drop_index("ix_events_chat_id", table_name="events")

    # Drop the events table (foreign key will be dropped automatically)
    op.drop_table("events")


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate events table
    op.create_table(
        "events",
        sa.Column("event_id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )

    # Recreate indexes
    op.create_index("ix_events_chat_id", "events", ["chat_id"], unique=False)
    op.create_index("ix_events_message_id", "events", ["message_id"], unique=False)

    # Recreate foreign key constraint
    op.create_foreign_key("fk_events_chat_id", "events", "chats", ["chat_id"], ["id"], ondelete="CASCADE")
