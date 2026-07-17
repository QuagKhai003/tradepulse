#!/usr/bin/env bash
# refresh-baci.sh — FULL data refresh: rebuild the map + partner tables (from BACI) + Comtrade signals +
# the market feed, then deploy everything to Cloudflare. Run this rarely — when CEPII releases a new BACI
# (about once a year). The monthly GitHub Action (.github/workflows/refresh-feed.yml) handles the
# fast-changing feed on its own; this is only for the heavy annual trade data.
#
# Prereqs on your machine: wrangler (npm i -g wrangler) + `wrangler login`; python on PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1) BACI file must be present. Download the latest BACI (HS 2022) from CEPII — once per release:
#      https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37
#    Unzip BACI_HS22_V*.zip into data/baci/ so that data/baci/BACI_HS22_Y*.csv exist.
if ! ls "$ROOT"/data/baci/BACI_HS*_Y*.csv >/dev/null 2>&1; then
  echo "!! No BACI CSVs found in data/baci/."
  echo "   Download the latest BACI (HS 2022) zip from cepii.fr, unzip into data/baci/, then re-run."
  exit 1
fi

# 2) Full ETL: BACI (all-country annual) + Comtrade (quarterly focus) + national + the market feed.
#    Optional API keys (Comtrade / USDA / KONEPS) live in etl/.env and enrich the pull if present.
echo "-> running full ETL (BACI + Comtrade + procurement) — this takes a while…"
( cd "$ROOT/etl" && python -m tradepulse_etl --source baci,comtrade,census,eurostat,hmrc --freq A --tenders )

# 3) Deploy the CORE data (map + partner tables + curated content) to tradepulse-data. Content is nested
#    under content/ so the app's contentRef() URLs resolve.
echo "-> deploying core data to tradepulse-data…"
cp -r "$ROOT/content" "$ROOT/web/public/data/content"
wrangler pages deploy "$ROOT/web/public/data" --project-name tradepulse-data --branch main --commit-dirty=true
rm -rf "$ROOT/web/public/data/content"

# 4) Deploy the (freshly rebuilt) feed to tradepulse-feed too, so both stores stay in sync.
echo "-> deploying feed to tradepulse-feed…"
STAGE="$(mktemp -d)"
for pat in awards tenders sellers events forward psd; do
  cp "$ROOT"/web/public/data/${pat}-*.json "$STAGE/" 2>/dev/null || true
done
cp "$ROOT/web/public/data/cpv-match.json" "$STAGE/" 2>/dev/null || true
wrangler pages deploy "$STAGE" --project-name tradepulse-feed --branch main --commit-dirty=true
rm -rf "$STAGE"

echo "✓ full refresh done — tradepulse-data (map + partners) and tradepulse-feed (market feed) updated."
