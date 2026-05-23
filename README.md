# Luat Schedule

Mobile-first schedule viewer and admin tool for DLU weekend classes.

Luat Schedule gives students a clean public page to check class schedules, while admins can update status, makeup sessions, rooms, times, and scrape the latest DLU Online data. The production direction is a free responsive web app/PWA backed by Google Sheets.

## What It Does

- Public schedule page at `/`, optimized for phone users.
- Admin workspace at `/admin`, protected by `ADMIN_PASSWORD`.
- Admin preview mode at `/admin?mode=view`, so admins can see what students see.
- Excel export that respects the current filters.
- PWA install support through browser "Add to Home Screen".
- Google Sheets sync for a shared production data source.
- GitHub Actions scraper that runs daily at 05:00 Vietnam time and can be triggered manually.

## Architecture

```text
DLU Online
   |
   |  scheduled scrape, daily at 05:00 Vietnam time
   v
GitHub Actions ---- merge rules ---- Google Sheets
                                      ^
                                      |
Admin /admin -------------------------+
                                      |
Public / and PWA ---------------------+
```

Merge rules preserve admin-managed fields when fresh DLU data arrives:

- `trang_thai`
- `thoi_gian`
- `phong_hoc`
- `updated_at`

The scraper also keeps the app's business rule: only Saturday/Sunday morning and afternoon schedules are retained.

## Tech Stack

- Flask
- Playwright
- Google Sheets API via `gspread`
- XlsxWriter
- GitHub Actions
- Vercel Python runtime

`schedule-tool/requirements.txt` is intentionally lightweight for Vercel. Scraper-only dependencies live in `schedule-tool/requirements-scraper.txt`.

## Quick Start

```cmd
cd schedule-tool
pip install -r requirements.txt
pip install -r requirements-scraper.txt
playwright install chromium
copy .env.example .env
python app.py
```

Open `http://localhost:5001`.

## Environment

Create `schedule-tool/.env` locally from `schedule-tool/.env.example`.

Required variables for deployed usage:

```env
DLU_USERNAME=
DLU_PASSWORD=
TARGET_CLASSES=
GOOGLE_SHEETS_ID=
GOOGLE_SERVICE_ACCOUNT_JSON=
ADMIN_PASSWORD=
SECRET_KEY=
```

Never commit real `.env`, Google service account files, logs, debug dumps, or generated cache files. They are ignored by `.gitignore`.

## Deploy

Recommended free path:

1. Push this repository to GitHub.
2. Import it into Vercel.
3. Set Vercel Root Directory to `schedule-tool`.
4. Add the environment variables in Vercel Project Settings.
5. Add the scraper secrets in GitHub repository secrets.

GitHub Actions uses `.github/workflows/scrape-schedule.yml` to refresh Google Sheets daily at 05:00 Vietnam time.

## Validation

Run the current checks from `schedule-tool`:

```cmd
python -m unittest discover tests
python -m py_compile app.py auto_scrape.py scraper.py sheets.py
node tests\static_app_js.test.js
```

## Security Notes

This repository is prepared so secrets stay out of Git. If real credentials were ever committed before history cleanup, rotate them anyway:

- DLU password
- Admin password
- Flask `SECRET_KEY`
- Google service account key

## Project Layout

```text
.
├── .github/workflows/scrape-schedule.yml
├── README.md
└── schedule-tool/
    ├── app.py
    ├── scraper.py
    ├── sheets.py
    ├── auto_scrape.py
    ├── static/
    ├── templates/
    └── tests/
```
