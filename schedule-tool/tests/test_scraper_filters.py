import unittest

import scraper


class ScraperScheduleFilterTests(unittest.TestCase):
    def test_keeps_only_weekend_morning_and_afternoon_entries(self):
        entries = [
            {"DayOfWeek": 5, "BeginTime": "1", "name": "friday morning"},
            {"DayOfWeek": 6, "BeginTime": "1", "name": "saturday morning"},
            {"DayOfWeek": 6, "BeginTime": "7", "name": "saturday afternoon"},
            {"DayOfWeek": 6, "BeginTime": "11", "name": "saturday evening"},
            {"DayOfWeek": 7, "BeginTime": "1", "name": "sunday morning"},
            {"DayOfWeek": 7, "BeginTime": "7", "name": "sunday afternoon"},
            {"DayOfWeek": 7, "BeginTime": "11", "name": "sunday evening"},
            {"DayOfWeek": 8, "BeginTime": "1", "name": "invalid day"},
        ]

        filtered = scraper.filter_weekend_daytime_entries(entries)

        self.assertEqual(
            [entry["name"] for entry in filtered],
            [
                "saturday morning",
                "saturday afternoon",
                "sunday morning",
                "sunday afternoon",
            ],
        )


if __name__ == "__main__":
    unittest.main()
