"""Save search results for several queries through the MCP server."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main(out: Path, queries: list[str], pages: int = 2) -> None:
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    res = {}
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for q in queries:
            res[q] = []
            for p in range(1, pages + 1):
                r = await session.call_tool("avito_search", {"query": q, "category": "predlozheniya_uslug", "page": p})
                d = json.loads(r.content[0].text)
                if d.get("blocked"):
                    print("blocked on", q, p)
                    break
                res[q] += d["items"]
                print(q, p, d["count"])
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))


asyncio.run(main(Path(sys.argv[1]), sys.argv[2:]))
