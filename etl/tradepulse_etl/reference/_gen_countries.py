"""
_gen_countries.py — one-off: fetch Comtrade reporter reference -> bundled code->name map.
@context  The /data rows carry only reporterCode (M49 numeric); this bundles code -> English name
          + ISO-alpha3 so the ETL needs no network for names, and the map can match world-atlas.
@limits   Dev tool; run occasionally. Writes countries.json next to it.
"""
import json
import urllib.request
from pathlib import Path

URL = "https://comtradeapi.un.org/files/v1/app/reference/Reporters.json"
req = urllib.request.Request(URL, headers={"User-Agent": "tradepulse/0.1"})
rows = json.loads(urllib.request.urlopen(req, timeout=40).read().decode())["results"]

out = {}
for r in rows:
    if r.get("isGroup"):
        continue
    code = r.get("reporterCode")
    if code in (None, "all"):
        continue
    out[str(code)] = {"name": r.get("text") or r.get("reporterDesc"),
                      "iso3": r.get("reporterCodeIsoAlpha3")}

path = Path(__file__).with_name("countries.json")
path.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print(f"wrote {len(out)} countries -> {path}")
