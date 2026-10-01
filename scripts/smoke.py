"""Smoke test: start the server over stdio and call tools given on the command line.

Usage: python scripts/smoke.py 'avito_status' 'avito_my_items' 'avito_search:{"query":"ботокс"}'
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main(calls: list[str]) -> None:
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for call in calls:
            name, _, raw = call.partition(":")
            args = json.loads(raw) if raw else {}
            result = await session.call_tool(name, args)
            print(f"===== {name} {args} error={result.isError}")
            for block in result.content:
                if block.type == "text":
                    print(block.text[: int(os.environ.get("SMOKE_LIMIT", "6000"))])
                else:
                    print(f"[{block.type}]")


asyncio.run(main(sys.argv[1:]))
