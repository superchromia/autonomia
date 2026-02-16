import logging

from mcp.config import MCPServerConfig
from models.mcp_server import MCPServer

# pylint: disable=broad-exception-caught

logger = logging.getLogger("mcp_db_config")


def _build_auth_headers(
    auth_type: str,
    auth_token: str | None,
) -> dict[str, str]:
    token = (auth_token or "").strip()
    normalized = (auth_type or "none").strip().lower()

    if not token or normalized == "none":
        return {}
    if normalized == "bearer":
        return {"Authorization": f"Bearer {token}"}
    if normalized == "token":
        return {"Authorization": token}
    if normalized == "x_api_key":
        return {"X-API-Key": token}
    # Unknown auth types are ignored to keep config robust.
    return {}


async def load_mcp_servers_from_db(session) -> list[MCPServerConfig]:
    from sqlalchemy.future import select

    try:
        result = await session.execute(
            select(MCPServer)
            .where(MCPServer.enabled.is_(True))
            .order_by(MCPServer.name.asc())
        )
        rows = result.scalars().all()
    except Exception:
        logger.exception("Failed to load MCP servers from database")
        return []

    servers: list[MCPServerConfig] = []
    for row in rows:
        headers = _build_auth_headers(row.auth_type, row.auth_token)
        transport = (row.transport or "").strip().lower()
        command = row.address if transport == "stdio" else None
        url = row.address if transport in {"sse", "http"} else None
        try:
            servers.append(
                MCPServerConfig(
                    name=row.name,
                    enabled=row.enabled,
                    transport=transport,
                    description=row.usage_description,
                    command=command,
                    url=url,
                    headers=headers,
                )
            )
        except Exception:
            logger.exception(
                "Failed to parse MCP server row: id=%s name=%s",
                row.id,
                row.name,
            )
            # Skip invalid rows without failing full generation.
            continue
    return servers
