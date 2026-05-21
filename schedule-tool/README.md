# Schedule Tool

Flask application for viewing, editing, exporting, and refreshing DLU class schedules.

This directory is the deployable app root. Use the repository root README for the product overview; use this file when setting up local development, deployment, secrets, and scheduled scraping.

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Public read-only schedule page. |
| `/admin` | Admin edit workspace. Requires login. |
| `/admin?mode=view` | Admin preview mode that renders like the public user view. |
| `/login` | Admin login. |
| `/api/export.xlsx` | Excel export using the current schedule/filter state. |
| `/manifest.webmanifest` | PWA manifest. |
| `/service-worker.js` | PWA service worker. |

## Local Development

```cmd
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
python app.py
```

Default local URL:

```text
http://localhost:5001
```

## Environment Variables

Use `.env.example` as the template:

```env
DLU_USERNAME=
DLU_PASSWORD=
TARGET_CLASSES=
GOOGLE_SHEETS_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
ADMIN_PASSWORD=
SECRET_KEY=
```

Notes:

- `TARGET_CLASSES` is a comma-separated list, for example `LHK50DL,LH26B2DL,LLT50DLCĐ,LLT50DLTC`.
- `GOOGLE_SERVICE_ACCOUNT_JSON` should contain the full Google service account JSON content in deployed environments.
- Local development can also use `credentials.json` beside `sheets.py`, but that file must not be committed.
- `ADMIN_PASSWORD` is required in production.
- `SECRET_KEY` must be a strong random value in production.

## Data Flow

```text
scraper.py
  -> load current data from Google Sheets
  -> scrape DLU Online
  -> filter to Saturday/Sunday morning/afternoon
  -> merge while preserving admin edits
  -> sync merged data back to Google Sheets
```

Admin-owned fields preserved during scrape merges:

- `trang_thai`
- `thoi_gian`
- `phong_hoc`
- `updated_at`

`data.json` is a local fallback. Do not treat it as the production database on serverless hosting.

## GitHub Actions

The scheduled workflow lives at:

```text
../.github/workflows/scrape-schedule.yml
```

It runs every 3 days and supports manual dispatch. Configure these repository secrets:

- `DLU_USERNAME`
- `DLU_PASSWORD`
- `TARGET_CLASSES`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

## Vercel Deployment

Use these settings:

- Root Directory: `schedule-tool`
- Framework Preset: Other
- Build/runtime: configured by `vercel.json`
- Environment Variables: set in Vercel Project Settings, not in Git

Required Vercel variables:

- `ADMIN_PASSWORD`
- `SECRET_KEY`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

Add scraper variables too if the deployed admin scrape button should work:

- `DLU_USERNAME`
- `DLU_PASSWORD`
- `TARGET_CLASSES`

## Tests

Run from this directory:

```cmd
python -m unittest discover tests
python -m py_compile app.py auto_scrape.py scraper.py sheets.py
node tests\static_app_js.test.js
```

## Security Checklist

- Keep `.env` local.
- Rotate any credential that was ever committed before history cleanup.
- Store production secrets in Vercel Environment Variables and GitHub Actions Secrets.
- Do not commit `credentials.json`, logs, debug HTML, pycache, or scraper dumps.
