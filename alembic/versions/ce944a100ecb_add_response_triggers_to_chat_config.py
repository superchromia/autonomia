"""add_response_triggers_to_chat_config

Revision ID: ce944a100ecb
Revises: b4e332b18255
Create Date: 2025-01-20 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ce944a100ecb"
down_revision: Union[str, Sequence[str], None] = "b4e332b18255"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add response_triggers JSONB column with default value
    op.add_column(
        "chat_configs",
        sa.Column(
            "response_triggers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text('\'{"on_every_message": false, "on_mention": true, "on_reply_to_bot": true}\'::jsonb'),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove response_triggers column
    op.drop_column("chat_configs", "response_triggers")
