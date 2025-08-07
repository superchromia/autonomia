"""add_foreign_keys_to_chat_id

Revision ID: ef858959d5ae
Revises: 9b4e71c8bc90
Create Date: 2025-07-31 11:08:44.261414

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ef858959d5ae"
down_revision: Union[str, Sequence[str], None] = "9b4e71c8bc90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Clean up orphaned records before adding foreign key constraints

    # Delete events with non-existent chat_id
    op.execute("DELETE FROM events WHERE chat_id NOT IN (SELECT id FROM chats)")

    # Delete messages with non-existent chat_id
    op.execute("DELETE FROM messages WHERE chat_id NOT IN (SELECT id FROM chats)")

    # Delete enriched messages with non-existent chat_id
    op.execute("DELETE FROM messages_enriched WHERE chat_id NOT IN (SELECT id FROM chats)")

    # Add foreign key constraints to chat_id columns

    # Messages table
    op.create_foreign_key("fk_messages_chat_id", "messages", "chats", ["chat_id"], ["id"], ondelete="CASCADE")

    # Messages enriched table
    op.create_foreign_key("fk_messages_enriched_chat_id", "messages_enriched", "chats", ["chat_id"], ["id"], ondelete="CASCADE")

    # Events table
    op.create_foreign_key("fk_events_chat_id", "events", "chats", ["chat_id"], ["id"], ondelete="CASCADE")

    # Chat configs table
    op.create_foreign_key("fk_chat_configs_chat_id", "chat_configs", "chats", ["chat_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraints

    # Chat configs table
    op.drop_constraint("fk_chat_configs_chat_id", "chat_configs", type_="foreignkey")

    # Events table
    op.drop_constraint("fk_events_chat_id", "events", type_="foreignkey")

    # Messages enriched table
    op.drop_constraint("fk_messages_enriched_chat_id", "messages_enriched", type_="foreignkey")

    # Messages table
    op.drop_constraint("fk_messages_chat_id", "messages", type_="foreignkey")
