# Deploying TradePulse (Vercel + Cloudflare R2, free tier)

TradePulse runs on **Vercel** (the Next.js app) with its data on **Cloudflare R2** (object storage).
Both fit comfortably in free tiers, and **no sensitive data is exposed** — the deployed JSON is the same
public trade data that's already on GitHub; secrets stay out of the repo entirely.

## Why data lives on R2, not in the app

The app generates ~894 MB of per-product JSON (`snapshot-*`, `sourcing-*`, awards, …). That's far beyond
Vercel's serverless function limit (250 MB), and most of it is gitignored (regeneratable), so it isn't in
the repo. The app reads its data through one seam (`web/app/lib/jsoncache.js`) that has two modes:

- **Local (default):** read from `web/public/data` on disk. This is `npm run dev` / `npm start` on your box — unchanged.
- **Remote:** if `DATA_BASE_URL` is set, fetch `${DATA_BASE_URL}/<file>` over HTTP. This is how it runs on Vercel.

Flip between them with a single env var. Nothing else changes.

```
┌──────────────┐   fetch JSON over HTTP    ┌────────────────────────┐
│  Vercel      │ ────────────────────────▶ │  Cloudflare R2 bucket  │
│  (Next.js)   │   DATA_BASE_URL=…r2.dev    │  894 MB public JSON    │
└──────────────┘                           └────────────────────────┘
```

## Step 1 — Create the R2 bucket

1. Cloudflare dashboard → **R2** → *Create bucket* (e.g. `tradepulse-data`). Free tier: 10 GB storage, **zero egress fees**.
2. Bucket → **Settings** → enable **Public access** (the `r2.dev` subdomain), or attach a custom domain.
   You get a public base URL like `https://pub-xxxxxxxx.r2.dev`.
3. **R2 → Manage API Tokens** → create a token with *Object Read & Write*. Note the **Access Key ID**,
   **Secret Access Key**, and your **S3 endpoint** `https://<accountid>.r2.cloudflarestorage.com`.

## Step 2 — Upload the data

From your machine (where the generated files exist), with the [AWS CLI](https://aws.amazon.com/cli/) installed:

```bash
aws configure          # paste the R2 Access Key / Secret; region: auto; output: json

export R2_BUCKET=tradepulse-data
export R2_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
bash scripts/upload-data.sh
```

This syncs `web/public/data/*` to the bucket root and `content/*` to `content/` under it. Re-run it any
time you regenerate data (`--size-only` skips unchanged files, so repeat syncs are cheap).

> Prefer [rclone](https://rclone.org/)? Configure an R2 remote, then:
> `rclone copy web/public/data r2:tradepulse-data --transfers 32` and
> `rclone copy content r2:tradepulse-data/content --transfers 32`.

## Step 3 — Deploy on Vercel

1. Vercel → **Add New Project** → import the `QuagKhai003/TradePulse` GitHub repo.
2. **Root Directory:** set to `web` (the repo is a monorepo; the app lives in `web/`).
3. **Environment Variables:** add `DATA_BASE_URL` = your bucket's public URL (e.g. `https://pub-xxxxxxxx.r2.dev`, no trailing slash).
4. Deploy. Framework preset (Next.js), build command, and output are auto-detected.

That's it — every product, every layer works, served from R2.

## What to know

- **Local dev is unchanged.** Don't set `DATA_BASE_URL` locally and the app reads from disk exactly as now.
- **No secrets are deployed.** The app uses zero runtime secrets (data is pre-built). `etl/.env` and the raw
  `data/` dir are gitignored — never in the repo, never on Vercel. Your R2 API token is used only locally by
  the upload script; it never leaves your machine. `DATA_BASE_URL` is public by design (the data is public).
- **Watch / telemetry won't persist.** `/api/watch` and `/api/locked-click` append to a local file; on
  Vercel's read-only filesystem those writes fail-soft (return 200, no crash) — the UI still works, the
  events just aren't recorded. To persist them, back those two routes with Vercel KV / a database later.
- **The lazy per-product build is skipped on Vercel** (no Python, read-only FS). All products are pre-built
  on R2, so a missing product simply 404s and shows its "coming soon" state.
- **Refresh after an ETL run:** regenerate locally, re-run `scripts/upload-data.sh`, and redeploy (or just
  re-upload — the app fetches the new files; restart/redeploy to clear the in-instance cache).

## Alternatives to R2 (all work via the same `DATA_BASE_URL`)

- **jsDelivr + a public GitHub "data" repo** — zero storage account; set `DATA_BASE_URL` to the jsDelivr CDN URL. Simplest, but a ~1 GB git repo is heavy.
- **Vercel Blob** — one platform; check current free-tier storage limits against the 894 MB.
- **AWS S3 / Backblaze B2 / any static host** — the loader only needs a base URL that serves the files publicly.
