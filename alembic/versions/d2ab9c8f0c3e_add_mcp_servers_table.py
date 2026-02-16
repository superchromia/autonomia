"""add_mcp_servers_table

Revision ID: d2ab9c8f0c3e
Revises: 6f42f0d9a1b7
Create Date: 2026-02-16 17:00:00.000000

"""

# pylint: disable=no-member

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2ab9c8f0c3e"
down_revision: Union[str, Sequence[str], None] = "6f42f0d9a1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "transport",
            sa.String(length=20),
            nullable=False,
            server_default="sse",
        ),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column(
            "auth_type",
            sa.String(length=30),
            nullable=False,
            server_default="none",
        ),
        sa.Column("auth_token", sa.Text(), nullable=True),
        sa.Column("usage_description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        "ix_mcp_servers_name",
        "mcp_servers",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_mcp_servers_enabled",
        "mcp_servers",
        ["enabled"],
        unique=False,
    )
    op.create_index(
        "ix_mcp_servers_transport",
        "mcp_servers",
        ["transport"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_mcp_servers_transport", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_enabled", table_name="mcp_servers")
    op.drop_index("ix_mcp_servers_name", table_name="mcp_servers")
    op.drop_table("mcp_servers")
