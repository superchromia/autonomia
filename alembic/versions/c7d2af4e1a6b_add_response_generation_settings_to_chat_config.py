"""add_response_generation_settings_to_chat_config

Revision ID: c7d2af4e1a6b
Revises: f31c2be91a4d
Create Date: 2026-02-17 13:00:00.000000

"""

# pylint: disable=no-member

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d2af4e1a6b"
down_revision: Union[str, Sequence[str], None] = "f31c2be91a4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "chat_configs",
        sa.Column(
            "response_max_tokens",
            sa.BigInteger(),
            nullable=True,
            server_default="450",
        ),
    )
    op.add_column(
        "chat_configs",
        sa.Column(
            "response_temperature",
            sa.Float(),
            nullable=True,
            server_default="0.85",
        ),
    )
    op.add_column(
        "chat_configs",
        sa.Column(
            "response_presence_penalty",
            sa.Float(),
            nullable=True,
            server_default="0.2",
        ),
    )
    op.add_column(
        "chat_configs",
        sa.Column(
            "response_frequency_penalty",
            sa.Float(),
            nullable=True,
            server_default="0.2",
        ),
    )

    op.execute(
        sa.text(
            """
            UPDATE chat_configs
            SET
                response_max_tokens = COALESCE(response_max_tokens, 450),
                response_temperature = COALESCE(response_temperature, 0.85),
                response_presence_penalty = GREATEST(
                    COALESCE(response_presence_penalty, 0.2),
                    0
                ),
                response_frequency_penalty = GREATEST(
                    COALESCE(response_frequency_penalty, 0.2),
                    0
                )
            """
        )
    )

    op.alter_column("chat_configs", "response_max_tokens", nullable=False)
    op.alter_column("chat_configs", "response_temperature", nullable=False)
    op.alter_column(
        "chat_configs",
        "response_presence_penalty",
        nullable=False,
    )
    op.alter_column(
        "chat_configs",
        "response_frequency_penalty",
        nullable=False,
    )

    op.create_check_constraint(
        "ck_chat_configs_response_max_tokens_positive",
        "chat_configs",
        "response_max_tokens > 0",
    )
    op.create_check_constraint(
        "ck_chat_configs_response_temperature_range",
        "chat_configs",
        "response_temperature >= 0 AND response_temperature <= 2",
    )
    op.create_check_constraint(
        "ck_chat_configs_response_presence_penalty_positive",
        "chat_configs",
        "response_presence_penalty >= 0",
    )
    op.create_check_constraint(
        "ck_chat_configs_response_frequency_penalty_positive",
        "chat_configs",
        "response_frequency_penalty >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_chat_configs_response_frequency_penalty_positive",
        "chat_configs",
        type_="check",
    )
    op.drop_constraint(
        "ck_chat_configs_response_presence_penalty_positive",
        "chat_configs",
        type_="check",
    )
    op.drop_constraint(
        "ck_chat_configs_response_temperature_range",
        "chat_configs",
        type_="check",
    )
    op.drop_constraint(
        "ck_chat_configs_response_max_tokens_positive",
        "chat_configs",
        type_="check",
    )
    op.drop_column("chat_configs", "response_frequency_penalty")
    op.drop_column("chat_configs", "response_presence_penalty")
    op.drop_column("chat_configs", "response_temperature")
    op.drop_column("chat_configs", "response_max_tokens")
