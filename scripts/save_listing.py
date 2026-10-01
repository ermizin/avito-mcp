"""Press «Сохранить изменения» on the open edit form (confirmed by the user) and report the result."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        snap = json.loads((await s.call_tool("avito_read", {"mode": "snapshot"})).content[0].text)["elements"].split("\n")
        btn = next(l.split()[0] for l in snap if "#item-edit/button-next" in l)
        res = await s.call_tool("avito_click", {"ref": btn, "confirm": True})
        print(res.content[0].text[:600])
        txt = json.loads((await s.call_tool("avito_read", {"mode": "text", "max_chars": 2500})).content[0].text)
        print("URL after save:", txt["url"])
        if "/cpxpromo/" in txt["url"] and "--stay" not in sys.argv:
            # post-save promotion step: leave promotion as it is
            snap = json.loads((await s.call_tool("avito_read", {"mode": "snapshot"})).content[0].text)["elements"].split("\n")
            skip = next(l.split()[0] for l in snap if "'Пропустить'" in l and "#action-buttons-primary" in l)
            r2 = json.loads((await s.call_tool("avito_click", {"ref": skip})).content[0].text)
            print("promotion step skipped ->", r2.get("url"))
        else:
            print(txt["text"][:1500])


asyncio.run(main())
