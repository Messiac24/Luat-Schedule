from pathlib import Path
import unittest


class GithubActionsTests(unittest.TestCase):
    def test_scheduled_scrape_workflow_uses_daily_cron_and_required_secrets(self):
        workflow_path = Path("..") / ".github" / "workflows" / "scrape-schedule.yml"
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn("0 22 * * *", workflow)
        self.assertIn("DLU_USERNAME", workflow)
        self.assertIn("DLU_PASSWORD", workflow)
        self.assertIn("TARGET_CLASSES", workflow)
        self.assertIn("GOOGLE_SHEETS_ID", workflow)
        self.assertIn("GOOGLE_SERVICE_ACCOUNT_JSON", workflow)
        self.assertIn("playwright install chromium", workflow)
        self.assertIn("python scraper.py", workflow)


if __name__ == "__main__":
    unittest.main()
