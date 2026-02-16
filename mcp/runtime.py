import asyncio
import json
import os
import shlex
import shutil
import sys
from dataclasses import dataclass
from typing import Any
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


class HTTPCPClient:
    def __init__(self, server: MCPServerConfig):
        self.server = server
        self._http: aiohttp.ClientSession | None = None
        self._request_id = 1
        self._session_id: str | None = None

    async def connect(self):
        timeout = aiohttp.ClientTimeout(total=self.server.timeout_seconds)
        headers = dict(self.server.headers or {})
        # Streamable HTTP MCP servers may require both media types.
        headers.setdefault("Accept", "application/json, text/event-stream")
        self._http = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        )
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
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        response = await self._post_json(payload)
        if response.get("id") != req_id:
            raise RuntimeError("MCP HTTP response id mismatch")
        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")
        return response.get("result", {})

    async def _post_json(self, payload: dict) -> dict:
        if not self._http or not self.server.url:
            raise RuntimeError("MCP HTTP client is not connected")

        request_headers = {}
        if self._session_id:
            request_headers["Mcp-Session-Id"] = self._session_id

        resp = await self._http.post(
            self.server.url,
            json=payload,
            headers=request_headers or None,
        )
        if resp.status >= 400:
            text = await resp.text()
            if (
                resp.status == 400
                and "Mcp-Session-Id header is required" in text
                and not self._session_id
            ):
                await self._establish_session_id()
                retry_headers = {"Mcp-Session-Id": self._session_id} if self._session_id else None
                resp = await self._http.post(
                    self.server.url,
                    json=payload,
                    headers=retry_headers,
                )
                if resp.status >= 400:
                    text = await resp.text()
                    raise RuntimeError(
                        f"MCP HTTP POST failed ({resp.status}): {text}"
                    )
            else:
                raise RuntimeError(f"MCP HTTP POST failed ({resp.status}): {text}")

        session_header = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if session_header:
            self._session_id = session_header

        content_type = (resp.content_type or "").lower()
        if "json" in content_type:
            return await resp.json(content_type=None)

        text = await resp.text()
        if not text.strip():
            return {}

        # Some MCP HTTP servers may return event-stream payloads.
        if "text/event-stream" in content_type:
            sse_payload = self._extract_sse_json_payload(text)
            if sse_payload is not None:
                return sse_payload

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "MCP HTTP returned non-JSON response "
                f"(content-type={resp.content_type}): {text[:200]!r}"
            ) from exc

    @staticmethod
    def _extract_sse_json_payload(body: str) -> dict | None:
        data_lines: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                if data_lines:
                    payload = "\n".join(data_lines)
                    try:
                        decoded = json.loads(payload)
                        if isinstance(decoded, dict):
                            return decoded
                    except json.JSONDecodeError:
                        pass
                    data_lines = []
                continue

            if line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())

        if data_lines:
            payload = "\n".join(data_lines)
            try:
                decoded = json.loads(payload)
                if isinstance(decoded, dict):
                    return decoded
            except json.JSONDecodeError:
                return None
        return None

    async def _establish_session_id(self):
        if not self._http or not self.server.url:
            raise RuntimeError("MCP HTTP client is not connected")
        resp = await self._http.get(
            self.server.url,
            headers={"Accept": "application/json, text/event-stream"},
        )
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(
                "Failed to establish MCP HTTP session: "
                f"{resp.status} {text}"
            )
        session_header = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if not session_header:
            text = await resp.text()
            raise RuntimeError(
                "MCP HTTP server did not return Mcp-Session-Id header "
                f"while establishing session. Response: {text[:200]!r}"
            )
        self._session_id = session_header


class StdioMCPClient:
    def __init__(self, server: MCPServerConfig):
        self.server = server
        self._process: Any | None = None
        self._request_id = 1
        self._io_lock = asyncio.Lock()
        self._stderr_task: asyncio.Task | None = None

    async def connect(self):
        if not self.server.command:
            raise RuntimeError("Stdio MCP server command is not configured")

        env = os.environ.copy()
        env.update(self.server.env or {})
        self._process = await self._spawn_process(env)
        self._stderr_task = asyncio.create_task(self._drain_stderr())

        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "autonomia", "version": "1.0"},
            },
        )
        await self._send_notification("notifications/initialized", {})

    async def _spawn_process(self, env: dict[str, str]):
        command = self.server.command
        args = self.server.args or []

        # Avoid local project package shadowing third-party "mcp" package
        # required by external MCP server processes.
        py_path = env.get("PYTHONPATH")
        if py_path:
            cleaned_parts = []
            for part in py_path.split(os.pathsep):
                normalized = os.path.abspath(part or ".")
                if normalized == "/app":
                    continue
                cleaned_parts.append(part)
            env["PYTHONPATH"] = os.pathsep.join(cleaned_parts)
            if not env["PYTHONPATH"]:
                env.pop("PYTHONPATH", None)

        # Allow storing a full command line in one DB field for stdio transport.
        if command and not args and " " in command:
            parts = shlex.split(command)
            command = parts[0]
            args = parts[1:]

        attempts: list[list[str]] = []
        if command:
            attempts.append([command, *args])

        # Fallback to Poetry-managed executable when app runs outside Poetry venv.
        if command and shutil.which("poetry"):
            attempts.append(["poetry", "run", command, *args])

        # Fallback for missing console_script wrappers in PATH.
        # Example: mcp-server-fetch -> python -m mcp_server_fetch
        if command:
            module_name = command.replace("-", "_")
            attempts.append([sys.executable, "-m", module_name, *args])

        first_error: FileNotFoundError | None = None
        for argv in attempts:
            try:
                return await asyncio.create_subprocess_exec(
                    *argv,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
            except FileNotFoundError as exc:
                if first_error is None:
                    first_error = exc
                continue

        if first_error:
            raise first_error
        raise RuntimeError("Failed to start stdio MCP server process")

    async def close(self):
        if self._stderr_task:
            self._stderr_task.cancel()
        if self._process:
            if self._process.stdin:
                self._process.stdin.close()
            if self._process.returncode is None:
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2)
                except TimeoutError:
                    self._process.kill()
                    await self._process.wait()

    async def list_tools(self) -> list[dict]:
        result = await self._send_request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        return await self._send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    async def _send_notification(self, method: str, params: dict):
        await self._write_message(
            {"jsonrpc": "2.0", "method": method, "params": params}
        )

    async def _send_request(self, method: str, params: dict) -> dict:
        req_id = self._request_id
        self._request_id += 1

        async with self._io_lock:
            await self._write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": method,
                    "params": params,
                }
            )
            while True:
                payload = await self._read_message()
                if payload.get("id") != req_id:
                    continue
                if "error" in payload:
                    raise RuntimeError(f"MCP error: {payload['error']}")
                return payload.get("result", {})

    async def _write_message(self, payload: dict):
        if not self._process or not self._process.stdin:
            raise RuntimeError("Stdio MCP client is not connected")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        self._process.stdin.write(header + body)
        await self._process.stdin.drain()

    async def _read_message(self) -> dict:
        if not self._process or not self._process.stdout:
            raise RuntimeError("Stdio MCP client is not connected")

        content_length = None
        while True:
            line = await self._process.stdout.readline()
            if not line:
                raise RuntimeError("Stdio MCP server closed stdout")
            decoded = line.decode("utf-8", errors="ignore").strip()
            if not decoded:
                break
            if decoded.lower().startswith("content-length:"):
                value = decoded.split(":", 1)[1].strip()
                content_length = int(value)

        if content_length is None:
            raise RuntimeError(
                "Missing Content-Length from stdio MCP response"
            )

        body = await self._process.stdout.readexactly(content_length)
        return json.loads(body.decode("utf-8"))

    async def _drain_stderr(self):
        if not self._process or not self._process.stderr:
            return
        while True:
            line = await self._process.stderr.readline()
            if not line:
                return
