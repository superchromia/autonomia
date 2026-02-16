from fastapi import APIRouter

from dependency import dependency
from models.mcp_server import MCPServer

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/servers")
async def list_mcp_servers():
    from sqlalchemy.future import select

    async for session in dependency.get_session():
        result = await session.execute(
            select(MCPServer).order_by(MCPServer.name.asc())
        )
        servers = result.scalars().all()
        break

    return {
        "enabled": any(server.enabled for server in servers),
        "servers_count": len(servers),
        "servers": [
            {
                "id": server.id,
                "name": server.name,
                "enabled": server.enabled,
                "transport": server.transport,
                "address": server.address,
                "auth_type": server.auth_type,
                "has_token": bool(server.auth_token),
                "usage_description": server.usage_description,
            }
            for server in servers
        ],
    }
