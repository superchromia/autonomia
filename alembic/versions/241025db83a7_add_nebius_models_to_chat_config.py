"""add_nebius_models_to_chat_config

Revision ID: 241025db83a7
Revises: ce944a100ecb
Create Date: 2025-01-20 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "241025db83a7"
down_revision: Union[str, Sequence[str], None] = "ce944a100ecb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add Nebius AI model configuration columns
    op.add_column(
        "chat_configs",
        sa.Column(
            "text_model",
            sa.String(),
            nullable=True,
            server_default="openai/gpt-oss-120b",
        ),
    )
    op.add_column(
        "chat_configs",
        sa.Column(
            "embeddings_model",
            sa.String(),
            nullable=True,
            server_default="Qwen/Qwen3-Embedding-8B",
        ),
    )
    op.add_column(
        "chat_configs",
        sa.Column("image_model", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove Nebius AI model configuration columns
    op.drop_column("chat_configs", "image_model")
    op.drop_column("chat_configs", "embeddings_model")
    op.drop_column("chat_configs", "text_model")
