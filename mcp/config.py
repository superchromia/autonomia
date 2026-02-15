import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger("mcp_config")

ENV_PATTERN = re.compile(r"\$\{([^}]+)\}|\$([A-Z0-9_]+)")


class MCPServerConfig(BaseModel):
    name: str
    enabled: bool = True
    transport: Literal["stdio", "sse", "http"] = "stdio"
    description: str | None = None
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    timeout_seconds: int = 30
    headers: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_transport_requirements(self):
        if self.transport == "stdio" and not self.command:
            raise ValueError(
                f"MCP server '{self.name}' with stdio transport "
                "requires 'command'"
            )
        if self.transport in {"sse", "http"} and not self.url:
            raise ValueError(
                f"MCP server '{self.name}' with {self.transport} "
                "transport requires 'url'"
            )
        return self

    def masked(self) -> dict[str, Any]:
        """Safe representation without secrets for API/logging."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "transport": self.transport,
            "description": self.description,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "timeout_seconds": self.timeout_seconds,
            "header_keys": sorted(list(self.headers)),
            "env_keys": sorted(list(self.env)),
        }


def _interpolate_env(value: str) -> str:
    def repl(match: re.Match) -> str:
        var_name = match.group(1) or match.group(2)
        return os.getenv(var_name, "")

    return ENV_PATTERN.sub(repl, value)


def _interpolate_obj(value: Any) -> Any:
    if isinstance(value, str):
        return _interpolate_env(value)
    if isinstance(value, list):
        return [_interpolate_obj(item) for item in value]
    if isinstance(value, dict):
        return {k: _interpolate_obj(v) for k, v in value.items()}
    return value


def _parse_servers_payload(raw: str) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("servers"), list):
        return payload["servers"]
    raise ValueError(
        "MCP payload must be a list "
        "or object with a 'servers' list"
    )


def _load_servers_from_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return _parse_servers_payload(path.read_text(encoding="utf-8"))


def _load_servers_from_env(raw_json: str | None) -> list[dict[str, Any]]:
    if not raw_json:
        return []
    return _parse_servers_payload(raw_json)


def load_mcp_servers(
    *,
    enabled: bool,
    servers_file: str | None,
    servers_json: str | None,
) -> list[MCPServerConfig]:
    """Load and validate MCP servers from file + env JSON.

    Merge strategy:
    - Load file entries first
    - Overlay with env JSON entries by server name
    """
    if not enabled:
        return []

    by_name: dict[str, dict[str, Any]] = {}

    if servers_file:
        file_path = Path(servers_file)
        for entry in _load_servers_from_file(file_path):
            by_name[entry["name"]] = entry

    for entry in _load_servers_from_env(servers_json):
        by_name[entry["name"]] = entry

    result: list[MCPServerConfig] = []
    for name, entry in by_name.items():
        try:
            interpolated = _interpolate_obj(entry)
            result.append(MCPServerConfig.model_validate(interpolated))
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Skipping invalid MCP server '%s': %s", name, exc)

    return result
