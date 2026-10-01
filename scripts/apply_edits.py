"""Apply approved title/description edits on an Avito edit form (no saving) and print the result."""
import asyncio, json, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]

async def call(s, name, args):
    r = await s.call_tool(name, args)
    t = r.content[0].text if r.content else ""
    if r.isError:
        raise RuntimeError(f"{name}: {t}")
    return json.loads(t) if t.startswith("{") else t

async def main(plan):
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        await call(s, "avito_open", {"url": f"/items/edit/{plan['item_id']}"})
        await call(s, "avito_read", {"mode": "text", "max_chars": 50, "wait_for_text": "Описание"})
        snap = (await call(s, "avito_read", {"mode": "snapshot"}))["elements"].split("\n")
        title = next(l.split()[0] for l in snap if "#title-field" in l and "input[text]" in l)
        desc = next(l.split()[0] for l in snap if l.split()[1] == "textbox")
        if plan.get("title"):
            v = await call(s, "avito_type", {"ref": title, "text": plan["title"]})
            print("TITLE:", v["value"])
        original = await call(s, "avito_read", {"mode": "text", "selector": "[role=textbox]", "max_chars": 20000})
        expected = original["text"]
        text = None
        for find, repl, drop in plan.get("replace", []):
            expected = expected.replace(find + "\n", "") if (drop and not repl) else expected.replace(find, repl)
            text = (await call(s, "avito_replace_text", {"ref": desc, "find": find, "replace": repl, "drop_empty_line": drop}))["text"]
            print("ok:", find[:50], "->", repl[:50])
        now = (await call(s, "avito_read", {"mode": "text", "selector": "[role=textbox]", "max_chars": 20000}))["text"]
        norm = lambda t: "\n".join(x.strip() for x in t.split("\n") if x.strip())
        print("MATCHES EXPECTED:", norm(now) == norm(expected))
        if norm(now) != norm(expected):
            import difflib
            print("\n".join(difflib.unified_diff(norm(expected).split("\n"), norm(now).split("\n"), "expected", "now", lineterm="")))
        print("----- DESCRIPTION NOW -----")
        print(now)

asyncio.run(main(json.loads(Path(sys.argv[1]).read_text())))
