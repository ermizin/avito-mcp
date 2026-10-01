import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]
async def main(urls):
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        for u in urls:
            d = json.loads((await s.call_tool("avito_listing", {"url": u})).content[0].text)
            print("==", d.get("title"), "|", d.get("price"))
            for row in d.get("price_list", []): print("   ", row)
            if d.get("owner_stats_7d"): print("   stats7d:", d["owner_stats_7d"][:160])
asyncio.run(main(sys.argv[1:]))
