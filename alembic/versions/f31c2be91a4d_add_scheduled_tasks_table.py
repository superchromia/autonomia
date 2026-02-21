"""add_scheduled_tasks_table

Revision ID: f31c2be91a4d
Revises: e4c1f8a2d9b0
Create Date: 2026-02-17 12:00:00.000000

"""

# pylint: disable=no-member

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f31c2be91a4d"
down_revision: Union[str, Sequence[str], None] = "e4c1f8a2d9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("cron_expression", sa.String(length=120), nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "send_to_chat",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("planned_sender_id", sa.BigInteger(), nullable=True),
        sa.Column("reply_to_message_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "enabled",
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
        sa.CheckConstraint(
            "(cron_expression IS NOT NULL) <> (run_at IS NOT NULL)",
            name="ck_scheduled_tasks_trigger_mode",
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scheduled_tasks_chat_id",
        "scheduled_tasks",
        ["chat_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_enabled",
        "scheduled_tasks",
        ["enabled"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_planned_sender_id",
        "scheduled_tasks",
        ["planned_sender_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_reply_to_message_id",
        "scheduled_tasks",
        ["reply_to_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_scheduled_tasks_run_at",
        "scheduled_tasks",
        ["run_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_scheduled_tasks_run_at",
        table_name="scheduled_tasks",
    )
    op.drop_index(
        "ix_scheduled_tasks_reply_to_message_id",
        table_name="scheduled_tasks",
    )
    op.drop_index(
        "ix_scheduled_tasks_planned_sender_id",
        table_name="scheduled_tasks",
    )
    op.drop_index(
        "ix_scheduled_tasks_enabled",
        table_name="scheduled_tasks",
    )
    op.drop_index(
        "ix_scheduled_tasks_chat_id",
        table_name="scheduled_tasks",
    )
    op.drop_table("scheduled_tasks")
