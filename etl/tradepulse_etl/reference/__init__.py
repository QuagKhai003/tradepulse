"""
reference — bundled Comtrade reference data (country code -> name/ISO).
@context  The /data rows carry only numeric reporterCode; this maps them to names for the UI and
          to world-atlas ISO ids for the map. Regenerate with _gen_countries.py.
"""
import json
from pathlib import Path

_COUNTRIES = json.loads((Path(__file__).with_name("countries.json")).read_text(encoding="utf-8"))


def country_name(code) -> str:
    return (_COUNTRIES.get(str(code)) or {}).get("name") or str(code)


def country_iso3(code) -> str | None:
    return (_COUNTRIES.get(str(code)) or {}).get("iso3")
