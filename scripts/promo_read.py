"""Read (not change) the pay-per-view promotion settings of listings."""
import asyncio, json, re, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]
async def main(ids):
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        for i in ids:
            await s.call_tool("avito_open", {"url": f"/cpxpromo/{i}"})
            d = json.loads((await s.call_tool("avito_read", {"mode": "text", "max_chars": 4000, "wait_for_text": "Диапазон"})).content[0].text)
            t = d["text"]
            a = t.find("Как настраивать"); b = t.find("Помощь\nБезопасность")
            snap = json.loads((await s.call_tool("avito_read", {"mode": "snapshot", "viewport_only": False})).content[0].text)["elements"].split("\n")
            sel = [l for l in snap if ("selected" in l and ("tab" in l or "radio" in l)) or "budget" in l]
            print("=====", i); print(" ".join(t[a:b].split())[:700]); print("   ", sel[:6])
asyncio.run(main(sys.argv[1:]))
