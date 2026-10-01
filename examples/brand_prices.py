"""Market prices per filler brand: search Avito, open listings that mention the brand, parse 'brand — price' lines."""

import asyncio
import json
import re
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]  # repository root
BRANDS = {
    "Neuramis": (["увеличение губ нейрамис", "neuramis губы"], r"neuramis|нейрамис|нейромис"),
    "Stylage": (["stylage губы", "увеличение губ стилаж"], r"stylage|стилаж"),
    "Belotero": (["belotero lips", "белотеро губы"], r"belotero|белотеро"),
    "Juvederm": (["juvederm губы", "ювидерм губы"], r"juvederm|ювидерм|juviderm|ювидерм"),
    "Растворение": (["растворение филлера", "лонгидаза растворение филлера"], r"растворени|гиалуронидаз|лонгидаз|удалени\w* филлер|выведени\w* филлер"),
}
PRICE = re.compile(r"(\d{1,2}[\s ]?\d{3})\s*(?:₽|р\.|руб|р\b)", re.I)


async def main(out: Path, per_brand: int) -> None:
    params = StdioServerParameters(command=str(ROOT / ".venv/bin/python"), args=["-m", "avito_mcp"])
    result = {}
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        for brand, (queries, pat) in BRANDS.items():
            urls = []
            for q in queries:
                d = json.loads((await s.call_tool("avito_search", {"query": q, "category": "predlozheniya_uslug"})).content[0].text)
                if d.get("blocked"):
                    print("BLOCKED"); return
                for c in d["items"]:
                    blob = " ".join([c["title"], c["description"], c["price_list"]]).lower()
                    if re.search(pat, blob) and c["url"] not in urls:
                        urls.append(c["url"])
                for c in d["items"][:15]:  # also top results: brands often only in the full text
                    if c["url"] not in urls:
                        urls.append(c["url"])
            hits = []
            opened = 0
            for url in urls:
                if opened >= per_brand:
                    break
                d = json.loads((await s.call_tool("avito_listing", {"url": url})).content[0].text)
                opened += 1
                if d.get("blocked"):
                    print("BLOCKED"); break
                text = (d.get("description") or "") + "\n" + "\n".join(d.get("price_list") or [])
                lines = [ln for ln in re.split(r"\n|(?<=₽)\s", text) if re.search(pat, ln.lower()) and PRICE.search(ln)]
                if lines:
                    hits.append({"url": url, "title": d.get("title"), "lines": [ln.strip()[:140] for ln in lines]})
                    print(brand, "|", d.get("title", "")[:50], "|", lines[0].strip()[:100])
            result[brand] = hits
            out.write_text(json.dumps(result, ensure_ascii=False, indent=1))


asyncio.run(main(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 14))
