"""Fill an Avito listing's price list through the MCP server, without saving.

plan.json: {"item_id": ..., "remove": ["catalog name", ...],
            "catalog": [["name", price, "duration", initial], ...],
            "custom":  [["name", price, "duration", initial], ...]}
Prints the resulting price list. Saving is a separate, confirmed step.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def call(s, name, args):
    r = await s.call_tool(name, args)
    txt = r.content[0].text if r.content else ""
    if r.isError:
        raise RuntimeError(f"{name} {args}: {txt}")
    return json.loads(txt) if txt.startswith("{") else txt


async def snapshot(s, viewport_only=False):
    return (await call(s, "avito_read", {"mode": "snapshot", "viewport_only": viewport_only}))["elements"].split("\n")


def ref(line):
    return line.split()[0]


async def set_row(s, cost_ref, dur_ref, init_ref, price, duration, initial, init_selected, unit_line=None):
    v = await call(s, "avito_type", {"ref": cost_ref, "text": str(price)})
    if unit_line and "'за услугу'" not in unit_line:
        await call(s, "avito_click", {"ref": ref(unit_line)})
        opt = next(ref(l) for l in await snapshot(s, True) if "'за услугу'" in l and "custom-option" in l)
        await call(s, "avito_click", {"ref": opt})
    if duration:
        await call(s, "avito_click", {"ref": dur_ref})
        opt = next(ref(l) for l in await snapshot(s, True) if f"'{duration}'" in l and "custom-option" in l)
        await call(s, "avito_click", {"ref": opt})
    if bool(initial) != bool(init_selected):
        await call(s, "avito_click", {"ref": init_ref})
    return v["value"]


def row_after(snap, i):
    cost = dur = init = unit = None
    init_sel = False
    for l in snap[i + 1 : i + 12]:
        if "#service" in l and l.split()[1] == "checkbox":
            break
        if "#priceType" in l and not unit:
            unit = l
        if "#cost/input" in l and not cost:
            cost = ref(l)
        elif "#duration" in l and not dur:
            dur = ref(l)
        elif "#initial-cost" in l and not init:
            init, init_sel = ref(l), " selected" in l
    return cost, dur, init, init_sel, unit


async def main(plan):
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        if not plan.get("keep_open"):
            await call(s, "avito_open", {"url": f"/items/edit/{plan['item_id']}"})
        await call(s, "avito_read", {"mode": "text", "max_chars": 100, "wait_for_text": "Прайс-лист"})
        snap = await snapshot(s)
        for name in plan.get("remove", []):
            line = next((l for l in snap if f"checkbox '{name}'" in l and " selected" in l), None)
            if line:
                await call(s, "avito_click", {"ref": ref(line)})
                print("removed:", name)
        for name, price, duration, initial in plan.get("catalog", []):
            snap = await snapshot(s)
            i = next(k for k, l in enumerate(snap) if f"checkbox '{name}'" in l)
            if " selected" not in snap[i]:
                await call(s, "avito_click", {"ref": ref(snap[i])})
                snap = await snapshot(s)
                i = next(k for k, l in enumerate(snap) if f"checkbox '{name}'" in l)
            cost, dur, init, init_sel, unit = row_after(snap, i)
            val = await set_row(s, cost, dur, init, price, duration, initial, init_sel, unit)
            print("catalog:", name, "|", val)
        for name, price, duration, initial in plan.get("custom", []):
            snap = await snapshot(s)
            existing = next((k for k, l in enumerate(snap) if re.search(r"input\[text\] '" + re.escape(name) + "'", l)), None)
            if existing is None:
                add = [ref(l) for l in snap if "clickable 'Добавить' #field" in l][-1]
                await call(s, "avito_click", {"ref": add})
                snap = await snapshot(s)
                i = [k for k, l in enumerate(snap) if "'Своё название'" in l][-1]
                await call(s, "avito_type", {"ref": ref(snap[i]), "text": name})
                snap = await snapshot(s)
                i = next(k for k, l in enumerate(snap) if re.search(r"input\[text\] '" + re.escape(name) + "'", l))
            else:
                i = existing
            cost, dur, init, init_sel, unit = row_after(snap, i)
            val = await set_row(s, cost, dur, init, price, duration, initial, init_sel, unit)
            print("custom:", name, "|", val)
        if plan.get("main_price"):
            snap = await snapshot(s)
            main = next(ref(l) for l in snap if "#price" in l and "input[text]" in l and "#priceList" not in l and "#priceType" not in l)
            v = await call(s, "avito_type", {"ref": main, "text": str(plan["main_price"])})
            print("main price:", v["value"])
        # summary of what the form now holds
        snap = await snapshot(s)
        print("--- price list now:")
        for k, l in enumerate(snap):
            if ("#service" in l and " selected" in l) or "#cost/input" in l or "#priceType" in l or "#price " in l + " " or (re.match(r"e\d+ input\[text\] '", l) and "#" not in l):
                print("  ", l)


asyncio.run(main(json.loads(Path(sys.argv[1]).read_text())))
