"""Public protocol regression: real server, native solvers and file dossiers."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def http_server(tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    url = f"http://127.0.0.1:{port}/mcp"
    with (tmp_path / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "server.py"), "--transport", "streamable-http", "--port", str(port)],
            cwd=tmp_path, env=dict(os.environ, PYTHONUTF8="1"), stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 40
            with httpx.Client(timeout=1, trust_env=False) as client:
                while time.monotonic() < deadline:
                    assert process.poll() is None, (tmp_path / "server.log").read_text(encoding="utf-8")
                    try:
                        client.get(url)
                        break
                    except (httpx.ConnectError, httpx.ConnectTimeout):
                        time.sleep(0.2)
                else:
                    pytest.fail("Local server did not start")
            yield url
        finally:
            if sys.platform == "win32" and process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
            elif process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


@pytest.mark.parametrize("transport", ["stdio", "streamable-http"])
def test_public_engineering_flow(transport, tmp_path, request):
    args = [sys.executable, str(ROOT / "scripts" / "verify_local_mcp.py"), "--output-dir", str(tmp_path / "dossiers")]
    if transport == "streamable-http":
        args += ["--url", request.getfixturevalue("http_server")]
    completed = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads((tmp_path / "dossiers" / "verification.json").read_text(encoding="utf-8"))
    assert summary["status"] == "LOCAL_MCP_VERIFIED"
    assert summary["public_tool_count"] >= 124
    assert summary["parent_workspace_preserved"] is True
    assert summary["all_dossier_hashes_verified"] is True


def test_http_single_workspace_and_dns_protection(http_server):
    async def check():
        async with streamable_http_client(http_server) as (read, write, session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                async with httpx.AsyncClient(trust_env=False) as client:
                    headers = {"Accept": "application/json, text/event-stream"}
                    message = {"jsonrpc": "2.0", "id": 10, "method": "initialize", "params": {
                        "protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "second-client", "version": "1"},
                    }}
                    busy = await client.post(http_server, headers=headers, json=message)
                    assert busy.status_code == 503
                    bad_host = await client.get(http_server, headers={"Host": "foreign.example", "Mcp-Session-Id": session_id()})
                    assert bad_host.status_code == 421
                    bad_origin = await client.get(http_server, headers={"Origin": "https://foreign.example", "Mcp-Session-Id": session_id()})
                    assert bad_origin.status_code == 403
                assert (await session.list_tools()).tools
        # A normal disconnect releases the single-owner slot.
        async with streamable_http_client(http_server) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                assert (await session.list_tools()).tools
    asyncio.run(check())


def test_cli_rejects_network_binding(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "server.py"), "--host", "0.0.0.0"], cwd=tmp_path, capture_output=True, timeout=40)
    assert result.returncode == 2
    assert b"invalid choice" in result.stderr
