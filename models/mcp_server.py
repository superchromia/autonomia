# pylint: disable=not-callable

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    String,
    Text,
)
from sqlalchemy.sql import func

from models.base import Base


class MCPServer(Base):
    """Database-configured MCP server settings."""

    __tablename__ = "mcp_servers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    transport = Column(String(20), nullable=False, default="sse")
    address = Column(String(500), nullable=False)
    auth_type = Column(String(30), nullable=False, default="none")
    auth_token = Column(Text, nullable=True)
    usage_description = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_mcp_servers_enabled", "enabled"),
        Index("ix_mcp_servers_transport", "transport"),
    )

    def __repr__(self):
        return (
            f"<MCPServer(id={self.id}, name='{self.name}', "
            f"transport='{self.transport}', enabled={self.enabled})>"
        )
