"""Collect full listing data through the MCP server and save it as JSON."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main(out: Path, urls: list[str]) -> None:
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    results = []
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for url in urls:
            r = await session.call_tool("avito_listing", {"url": url})
            data = json.loads(r.content[0].text)
            results.append(data)
            print(data.get("id"), data.get("title"), "| photos:", len(data.get("photos", [])), "| blocked:", data.get("blocked"))
            if data.get("photos"):
                await session.call_tool(
                    "avito_save_images",
                    {"urls": data["photos"], "dest_dir": str(out / "photos" / str(data["id"]))},
                )
    (out / "listings.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))


asyncio.run(main(Path(sys.argv[1]), sys.argv[2:]))
