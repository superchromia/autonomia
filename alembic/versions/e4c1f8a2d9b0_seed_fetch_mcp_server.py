"""seed_fetch_mcp_server

Revision ID: e4c1f8a2d9b0
Revises: d2ab9c8f0c3e
Create Date: 2026-02-16 18:00:00.000000

"""

# pylint: disable=no-member

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4c1f8a2d9b0"
down_revision: Union[str, Sequence[str], None] = "d2ab9c8f0c3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            """
            INSERT INTO mcp_servers (
                name,
                enabled,
                transport,
                address,
                auth_type,
                auth_token,
                usage_description
            )
            SELECT
                :name,
                :enabled,
                :transport,
                :address,
                :auth_type,
                :auth_token,
                :usage_description
            WHERE NOT EXISTS (
                SELECT 1
                FROM mcp_servers
                WHERE name = :name
            )
            """
        ).bindparams(
            name="fetch",
            enabled=False,
            transport="stdio",
            address="mcp-server-fetch",
            auth_type="none",
            auth_token=None,
            usage_description=(
                "HTTP fetch MCP server "
                "(pip package mcp-server-fetch)"
            ),
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DELETE FROM mcp_servers
            WHERE name = :name
              AND address = :address
            """
        ).bindparams(
            name="fetch",
            address="mcp-server-fetch",
        )
    )
