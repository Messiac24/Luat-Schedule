# DLU Schedule Tracker

Flask app for public schedule viewing, admin updates, Google Sheets sync, PWA install, and automated DLU scraping.

## App Areas

- `/`: public read-only schedule for students.
- `/admin`: admin edit mode, protected by `ADMIN_PASSWORD`.
- `/admin?mode=view`: admin preview that renders like the public user view without logging out.
- `/manifest.webmanifest` and `/service-worker.js`: PWA install support.

## Local Setup

```cmd
cd schedule-tool
pip install -r requirements.txt
playwright install chromium
python app.py
```

Local URL: `http://localhost:5001`

## Environment Variables

Required for deployed app and GitHub Actions:

- `ADMIN_PASSWORD`: password for admin login.
- `SECRET_KEY`: strong Flask session secret.
- `DLU_USERNAME`: DLU Online username for scraper.
- `DLU_PASSWORD`: DLU Online password for scraper.
- `TARGET_CLASSES`: comma-separated class ids, for example `LHK50DL,LH26B2DL,LLT50DLCĐ,LLT50DLTC`.
- `GOOGLE_SHEETS_ID`: Google Sheet id.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: full service account JSON content.

Local development may also use `credentials.json` beside `sheets.py` instead of `GOOGLE_SERVICE_ACCOUNT_JSON`.

## Deployment

Use Vercel with root directory `schedule-tool` and the env vars above.

Google Sheets is the durable data store in deployment. Do not rely on `data.json` for production persistence on serverless hosting.

## Automatic Scraping

The workflow `.github/workflows/scrape-schedule.yml` runs every 3 days and can also be triggered manually.

The scraper:

- logs into DLU Online using GitHub secrets,
- reads the current Google Sheet before merging,
- preserves admin-managed fields (`trang_thai`, `thoi_gian`, `phong_hoc`, `updated_at`),
- keeps only Saturday/Sunday morning and afternoon schedules,
- syncs the merged result back to Google Sheets.
