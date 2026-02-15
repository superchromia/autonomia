import asyncio
import json
from dataclasses import dataclass
from urllib.parse import urljoin

import aiohttp

from .config import MCPServerConfig


def _sanitize_function_name(value: str) -> str:
    allowed = []
    for ch in value:
        if ch.isalnum() or ch in {"_", "-"}:
            allowed.append(ch)
        else:
            allowed.append("_")
    return "".join(allowed)[:64]


def format_tool_result(result: dict) -> str:
    """Convert MCP tools/call result to text content for LLM tool message."""
    content = result.get("content")
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
            elif isinstance(item, str):
                chunks.append(item)
        text = "\n".join(part for part in chunks if part)
        if text:
            return text

    if "result" in result:
        value = result["result"]
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    return json.dumps(result, ensure_ascii=False)


@dataclass
class MCPFunctionTool:
    function_name: str
    server_name: str
    remote_tool_name: str
    description: str
    parameters: dict

    def to_openai_tool(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.function_name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class SSEMCPClient:
    def __init__(self, server: MCPServerConfig):
        self.server = server
        self._http: aiohttp.ClientSession | None = None
        self._sse_resp: aiohttp.ClientResponse | None = None
        self._reader: aiohttp.StreamReader | None = None
        self._message_endpoint: str | None = None
        self._request_id = 1

    async def connect(self):
        timeout = aiohttp.ClientTimeout(
            total=None,
            sock_connect=self.server.timeout_seconds,
        )
        self._http = aiohttp.ClientSession(
            timeout=timeout,
            headers=self.server.headers,
        )
        self._sse_resp = await self._http.get(self.server.url)
        self._sse_resp.raise_for_status()
        self._reader = self._sse_resp.content

        while True:
            event, data = await self._read_event()
            if event == "endpoint":
                self._message_endpoint = urljoin(self.server.url, data)
                break

        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "autonomia", "version": "1.0"},
            },
        )
        await self._send_notification("notifications/initialized", {})

    async def close(self):
        if self._sse_resp is not None:
            self._sse_resp.close()
        if self._http is not None:
            await self._http.close()

    async def list_tools(self) -> list[dict]:
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        return await self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    async def _send_notification(self, method: str, params: dict):
        await self._post_json(
            {"jsonrpc": "2.0", "method": method, "params": params}
        )

    async def _send_request(self, method: str, params: dict) -> dict:
        req_id = self._request_id
        self._request_id += 1
        await self._post_json(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params,
            }
        )
        return await self._wait_response(req_id)

    async def _post_json(self, payload: dict):
        if not self._http or not self._message_endpoint:
            raise RuntimeError("MCP client is not connected")
        resp = await self._http.post(self._message_endpoint, json=payload)
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"MCP POST failed ({resp.status}): {text}")

    async def _wait_response(self, req_id: int) -> dict:
        while True:
            event, data = await self._read_event()
            if event != "message":
                continue
            payload = json.loads(data)
            if payload.get("id") != req_id:
                continue
            if "error" in payload:
                raise RuntimeError(f"MCP error: {payload['error']}")
            return payload.get("result", {})

    async def _read_event(self) -> tuple[str, str]:
        if not self._reader:
            raise RuntimeError("MCP SSE stream is not initialized")

        event_name = "message"
        data_parts: list[str] = []
        while True:
            line = await self._reader.readline()
            if not line:
                await asyncio.sleep(0.01)
                continue

            text = line.decode("utf-8", errors="ignore").rstrip("\r\n")
            if not text:
                if data_parts:
                    return event_name, "\n".join(data_parts)
                continue
            if text.startswith(":"):
                continue
            if text.startswith("event:"):
                event_name = text[len("event:"):].strip()
                continue
            if text.startswith("data:"):
                data_parts.append(text[len("data:"):].strip())
