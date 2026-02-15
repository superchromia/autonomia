from fastapi import APIRouter

from config import config

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/servers")
async def list_mcp_servers():
    servers = config.get_mcp_servers()
    return {
        "enabled": config.mcp_enabled,
        "servers_count": len(servers),
        "servers": [server.masked() for server in servers],
    }
