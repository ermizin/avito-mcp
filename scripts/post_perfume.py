"""Fill an Avito goods listing (perfume) step by step via the MCP; publish only with --publish."""
import asyncio, json, re, sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT = Path(__file__).resolve().parents[1]

async def call(s, name, args):
    r = await s.call_tool(name, args); t = r.content[0].text if r.content else ""
    if r.isError: raise RuntimeError(f"{name} {args}: {t}")
    return json.loads(t) if t.startswith("{") else t

async def snap(s, vp=False):
    return (await call(s, "avito_read", {"mode": "snapshot", "viewport_only": vp}))["elements"].split("\n")

def ref(snapl, pred):
    for l in snapl:
        if pred(l): return l.split()[0]
    raise RuntimeError("not found")

async def main(item, publish):
    p = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    async with stdio_client(p) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        if not publish:
            await call(s, "avito_open", {"url": "/additem"})
            await call(s, "avito_read", {"mode": "text", "max_chars": 50, "wait_for_text": "Личные вещи"})
            L = await snap(s, True)
            await call(s, "avito_click", {"ref": ref(L, lambda l: "'Личные вещи'" in l and "category-wizard" in l)})
            await asyncio.sleep(1.5)
            L = await snap(s)
            await call(s, "avito_type", {"ref": ref(L, lambda l: "#title-field" in l), "text": item["title"]})
            await call(s, "avito_read", {"mode": "text", "max_chars": 50, "wait_for_text": "Духи и туалетная вода"})
            L = await snap(s)
            await call(s, "avito_click", {"ref": ref(L, lambda l: "Духи и туалетная вода" in l and "#category-title" in l)})
            await call(s, "avito_read", {"mode": "text", "max_chars": 50, "wait_for_text": "Описание объявления"})
            L = await snap(s)
            await call(s, "avito_click", {"ref": ref(L, lambda l: "'Б/у'" in l and "option" in l)})
            await call(s, "avito_click", {"ref": ref(L, lambda l: "'Унисекс'" in l and "option" in l)})
            await call(s, "avito_click", {"ref": ref(L, lambda l: "#type_of_trade" in l and "combobox" in l)})
            L = await snap(s)
            await call(s, "avito_click", {"ref": ref(L, lambda l: "'Продаю своё'" in l)})
            await call(s, "avito_upload", {"paths": [item["photo"]]})
            L = await snap(s)
            await call(s, "avito_click", {"ref": ref(L, lambda l: "#gruppa_aromata" in l and "combobox" in l)})
            L = await snap(s)
            await call(s, "avito_type", {"ref": ref(L, lambda l: "#gruppa_aromata" in l and "search-input" in l), "text": item["group"][:4]})
            await asyncio.sleep(1)
            L = await snap(s)
            await call(s, "avito_click", {"ref": ref(L, lambda l: f"'{item['group']}'" in l and "custom-option" in l)})
            await call(s, "avito_press", {"key": "Escape"})
            L = await snap(s)
            brand = ref(L, lambda l: "#params[192650]/input" in l)
            await call(s, "avito_type", {"ref": brand, "text": ""}); await call(s, "avito_type", {"ref": brand, "text": item["brand"], "clear": False})
            await asyncio.sleep(1.5)
            L = await snap(s)
            opt = [l for l in L if l.split()[1:2] == ["button"] and item["brand"].lower() in l.lower() and "#" not in l]
            if opt: await call(s, "avito_click", {"ref": opt[0].split()[0]})
            L = await snap(s)
            await call(s, "avito_type", {"ref": ref(L, lambda l: "textarea" in l), "text": item["desc"]})
            await call(s, "avito_type", {"ref": ref(L, lambda l: "#price" in l and "input" in l), "text": str(item["price"])})
            geo = ref(L, lambda l: "#geo/search-input" in l)
            await call(s, "avito_type", {"ref": geo, "text": ""}); await call(s, "avito_type", {"ref": geo, "text": "Санкт-Петербург, Лесной проспект, 77", "clear": False})
            await call(s, "avito_read", {"mode": "text", "max_chars": 50, "wait_for_text": "Лесной проспект, 77 Санкт"})
            L = await snap(s)
            await call(s, "avito_click", {"ref": ref(L, lambda l: "'Лесной проспект, 77 Санкт-Петербург'" in l)})
            await asyncio.sleep(2)
        L = await snap(s)
        keep = lambda l: any(k in l for k in ["#title-field-23/input", "selected", "#params[192650]/input", "#obyom", "#price ", "#geo/search-input", "deliveryToggles", "delivery-subsidy"]) and "radio 'Звонки" not in l
        print("\n".join(l for l in L if keep(l)))
        if publish:
            await call(s, "avito_click", {"ref": ref(L, lambda l: "#item-edit/button-next" in l), "confirm": True})
            await asyncio.sleep(3)
            st = await call(s, "avito_read", {"mode": "text", "max_chars": 300})
            m = re.search(r"/(\d{8,})", st["url"]); print("PUBLISHED:", st["url"], m.group(1) if m else "")
            if "performance" in st["url"]:
                L = await snap(s, True)
                await call(s, "avito_click", {"ref": ref(L, lambda l: "'Пропустить'" in l)}); print("promo skipped")

items = json.loads(Path(sys.argv[1]).read_text())
asyncio.run(main(items[sys.argv[2]], "--publish" in sys.argv))
