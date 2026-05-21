import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import auto_scrape


class AutoScrapeTests(unittest.TestCase):
    def test_scrape_is_due_after_three_days(self):
        now = datetime(2026, 5, 21, 8, 0, 0)
        last_success = (now - timedelta(days=3)).isoformat()

        self.assertTrue(auto_scrape.is_scrape_due(last_success, now=now))

    def test_scrape_is_not_due_before_three_days(self):
        now = datetime(2026, 5, 21, 8, 0, 0)
        last_success = (now - timedelta(days=2, hours=23)).isoformat()

        self.assertFalse(auto_scrape.is_scrape_due(last_success, now=now))

    def test_run_if_due_calls_scraper_and_persists_success_timestamp(self):
        now = datetime(2026, 5, 21, 8, 0, 0)
        calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"

            result = auto_scrape.run_if_due(
                state_path=state_path,
                scrape_func=lambda: calls.append("scraped") or True,
                now=now,
            )

            state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(calls, ["scraped"])
        self.assertTrue(result["ran"])
        self.assertTrue(result["success"])
        self.assertEqual(state["last_success"], now.isoformat())

    def test_run_if_due_skips_when_last_success_is_fresh(self):
        now = datetime(2026, 5, 21, 8, 0, 0)
        calls = []

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            state_path.write_text(
                json.dumps({"last_success": (now - timedelta(days=1)).isoformat()}),
                encoding="utf-8",
            )

            result = auto_scrape.run_if_due(
                state_path=state_path,
                scrape_func=lambda: calls.append("scraped") or True,
                now=now,
            )

        self.assertEqual(calls, [])
        self.assertFalse(result["ran"])


if __name__ == "__main__":
    unittest.main()
