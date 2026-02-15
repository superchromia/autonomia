import json

from mcp.config import load_mcp_servers


def test_load_mcp_servers_from_file(tmp_path):
    cfg_path = tmp_path / "mcp_servers.json"
    cfg_path.write_text(
        json.dumps(
            {
                "servers": [
                    {
                        "name": "fs",
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "server-filesystem"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    servers = load_mcp_servers(
        enabled=True,
        servers_file=str(cfg_path),
        servers_json=None,
    )

    assert len(servers) == 1
    assert servers[0].name == "fs"
    assert servers[0].command == "npx"


def test_load_mcp_servers_env_overrides_file(tmp_path):
    cfg_path = tmp_path / "mcp_servers.json"
    cfg_path.write_text(
        json.dumps(
            [
                {
                    "name": "fs",
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["old"],
                }
            ]
        ),
        encoding="utf-8",
    )

    override = json.dumps(
        {
            "servers": [
                {
                    "name": "fs",
                    "transport": "stdio",
                    "command": "uvx",
                    "args": ["new"],
                }
            ]
        }
    )

    servers = load_mcp_servers(
        enabled=True,
        servers_file=str(cfg_path),
        servers_json=override,
    )

    assert len(servers) == 1
    assert servers[0].command == "uvx"
    assert servers[0].args == ["new"]
