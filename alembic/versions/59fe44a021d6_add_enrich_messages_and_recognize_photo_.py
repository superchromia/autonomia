"""add_enrich_messages_and_recognize_photo_to_chat_config

Revision ID: 59fe44a021d6
Revises: 894ff7a7479b
Create Date: 2025-07-31 12:24:50.268401

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "59fe44a021d6"
down_revision: Union[str, Sequence[str], None] = "894ff7a7479b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to chat_configs table
    op.add_column("chat_configs", sa.Column("enrich_messages", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("chat_configs", sa.Column("recognize_photo", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove new columns from chat_configs table
    op.drop_column("chat_configs", "recognize_photo")
    op.drop_column("chat_configs", "enrich_messages")
