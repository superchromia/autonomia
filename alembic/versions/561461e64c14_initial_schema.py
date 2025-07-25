"""initial_schema

Revision ID: 561461e64c14
Revises:
Create Date: 2025-07-22 08:15:57.738327

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "561461e64c14"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "chat_configs",
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("save_messages", sa.Boolean(), nullable=False),
        sa.Column("load_from_date", sa.DateTime(), nullable=True),
        sa.Column("system_prompt", sa.String(), nullable=True),
        sa.Column("answer_threshold", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("chat_id"),
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("chat_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("is_scam", sa.Boolean(), nullable=True),
        sa.Column("is_fake", sa.Boolean(), nullable=True),
        sa.Column("member_count", sa.Integer(), nullable=True),
        sa.Column(
            "raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chats_chat_type"), "chats", ["chat_type"], unique=False
    )
    op.create_index(op.f("ix_chats_title"), "chats", ["title"], unique=False)
    op.create_index(
        "ix_chats_type_verified",
        "chats",
        ["chat_type", "is_verified"],
        unique=False,
    )
    op.create_index(
        op.f("ix_chats_username"), "chats", ["username"], unique=False
    )
    op.create_table(
        "events",
        sa.Column(
            "event_id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "event_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_events_chat_id", "events", ["chat_id"], unique=False)
    op.create_index(
        "ix_events_message_id", "events", ["message_id"], unique=False
    )
    op.create_table(
        "messages",
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column(
            "raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
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
        sa.PrimaryKeyConstraint("message_id", "chat_id"),
    )
    op.create_index(
        "ix_messages_chat_date", "messages", ["chat_id", "date"], unique=False
    )
    op.create_index(
        op.f("ix_messages_date"), "messages", ["date"], unique=False
    )
    op.create_index(
        op.f("ix_messages_is_read"), "messages", ["is_read"], unique=False
    )
    op.create_index(
        op.f("ix_messages_message_type"),
        "messages",
        ["message_type"],
        unique=False,
    )
    op.create_index(
        "ix_messages_sender_date",
        "messages",
        ["sender_id", "date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_messages_sender_id"), "messages", ["sender_id"], unique=False
    )
    op.create_index(
        "ix_messages_type_date",
        "messages",
        ["message_type", "date"],
        unique=False,
    )
    op.create_index(
        "ix_messages_unread", "messages", ["chat_id", "is_read"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("is_scam", sa.Boolean(), nullable=True),
        sa.Column("is_fake", sa.Boolean(), nullable=True),
        sa.Column("is_bot", sa.Boolean(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=True),
        sa.Column(
            "raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_users_bot_verified",
        "users",
        ["is_bot", "is_verified"],
        unique=False,
    )
    op.create_index(op.f("ix_users_is_bot"), "users", ["is_bot"], unique=False)
    op.create_index("ix_users_premium", "users", ["is_premium"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_premium", table_name="users")
    op.drop_index(op.f("ix_users_is_bot"), table_name="users")
    op.drop_index("ix_users_bot_verified", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_messages_unread", table_name="messages")
    op.drop_index("ix_messages_type_date", table_name="messages")
    op.drop_index(op.f("ix_messages_sender_id"), table_name="messages")
    op.drop_index("ix_messages_sender_date", table_name="messages")
    op.drop_index(op.f("ix_messages_message_type"), table_name="messages")
    op.drop_index(op.f("ix_messages_is_read"), table_name="messages")
    op.drop_index(op.f("ix_messages_date"), table_name="messages")
    op.drop_index("ix_messages_chat_date", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_events_message_id", table_name="events")
    op.drop_index("ix_events_chat_id", table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_chats_username"), table_name="chats")
    op.drop_index("ix_chats_type_verified", table_name="chats")
    op.drop_index(op.f("ix_chats_title"), table_name="chats")
    op.drop_index(op.f("ix_chats_chat_type"), table_name="chats")
    op.drop_table("chats")
    op.drop_table("chat_configs")
    # ### end Alembic commands ###
