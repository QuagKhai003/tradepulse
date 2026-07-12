"""
settings.py — read local secrets/config (stdlib-only, no python-dotenv dep).
@context  The free UN Comtrade API key lives in etl/.env (gitignored). This loads it into the
          environment so the Comtrade source can pick the authenticated path automatically.
@done     load_env() (parse etl/.env), comtrade_key().
@limits   Never commit .env. Best-effort; missing file is fine (keyless fallback).
@affects  Used by pipeline.get_source.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"   # etl/.env


def load_env() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def comtrade_key() -> str | None:
    load_env()
    return os.environ.get("COMTRADE_SUBSCRIPTION_KEY") or None


def census_key() -> str | None:
    """US Census API key (free, api.census.gov/data/key_signup.html) — CENSUS_API_KEY in etl/.env."""
    load_env()
    return os.environ.get("CENSUS_API_KEY") or None


def estat_app_id() -> str | None:
    """Japan e-Stat appId (free, api.e-stat.go.jp) — ESTAT_APP_ID in etl/.env."""
    load_env()
    return os.environ.get("ESTAT_APP_ID") or None


def kcs_service_key() -> str | None:
    """Korea Customs data.go.kr serviceKey (Decoding form) — KCS_SERVICE_KEY in etl/.env."""
    load_env()
    return os.environ.get("KCS_SERVICE_KEY") or None
