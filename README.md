# Luat Schedule

Responsive Flask/PWA app for viewing and managing DLU weekend class schedules.

## Current Deployment Direction

- Public users use `/` to view schedules on mobile or desktop.
- Admin uses `/admin` after login to update status, makeup schedules, room/time edits, scrape, and sync.
- The app is installable as a PWA through the browser's "Add to Home Screen".
- Google Sheets is the shared data store for deployed usage.
- GitHub Actions runs the scraper every 3 days and syncs the merged result to Google Sheets.

## Required Secrets

Configure these in GitHub Actions and deployment environment:

- `DLU_USERNAME`
- `DLU_PASSWORD`
- `TARGET_CLASSES`
- `GOOGLE_SHEETS_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `ADMIN_PASSWORD`
- `SECRET_KEY`

Set the deploy root to `schedule-tool`.
