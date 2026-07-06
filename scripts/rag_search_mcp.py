#!/usr/bin/env python3
"""MCP-сервер RAG-поиска TMKI для Cursor."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(RUNTIME))

from tmki_runtime.rag_env import load_rag_config

load_rag_config(override=False)


def _search(query: str) -> str:
    from tmki_demo.qa import ask_regulations

    llm = os.environ.get("TMKI_LLM_PROVIDER", "ollama")
    result = ask_regulations(query, llm_provider=llm)
    lines = [
        result.get("answer") or "(пустой ответ)",
        "",
        f"backend: {result.get('backend')} | confidence: {result.get('confidence')}",
        "",
        "Источники:",
    ]
    for i, cit in enumerate((result.get("citations") or [])[:5], start=1):
        lines.append(
            f"{i}. {cit.get('file_name') or cit.get('doc_id')} "
            f"(стр. {cit.get('page', '?')}) — {(cit.get('snippet') or '')[:200]}"
        )
    return "\n".join(lines)


async def _run_mcp() -> None:
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp import types
    except ImportError as exc:
        print("Установите MCP SDK: pip install mcp", file=sys.stderr)
        raise SystemExit(1) from exc

    server = Server("tmki-rag")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="rag_search",
                description="Поиск по индексу регламентов TMKI (pgvector + Ollama)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Вопрос на русском"},
                    },
                    "required": ["query"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name != "rag_search":
            raise ValueError(f"Unknown tool: {name}")
        query = (arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query required")
        return [types.TextContent(type="text", text=_search(query))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> int:
    asyncio.run(_run_mcp())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
