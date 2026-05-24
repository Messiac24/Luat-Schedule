import unittest
from unittest.mock import Mock, patch

import scraper
import app
import sheets


class SheetsSourceTests(unittest.TestCase):
    def test_sync_to_sheets_accepts_service_account_json_from_env(self):
        sheet = Mock()
        client = Mock()
        client.open_by_key.return_value.sheet1 = sheet

        with patch.object(sheets, "GOOGLE_SHEETS_ID", "sheet-id"), patch.object(
            sheets, "GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email":"x","token_uri":"x"}'
        ), patch.object(sheets.Credentials, "from_service_account_info") as from_info, patch.object(
            sheets.gspread, "authorize", return_value=client
        ):
            self.assertTrue(
                sheets.sync_to_sheets(
                    {
                        "subjects": [
                            {
                                "stt": 1,
                                "ma_hp": "LAW101",
                                "ten_hoc_phan": "Mon A",
                                "lop_hoc": ["LH26B2DL"],
                                "last_scraped": "2026-05-24T05:39:00",
                            }
                        ]
                    }
                )
            )

        from_info.assert_called_once()
        sheet.clear.assert_called_once()
        sheet.update.assert_called_once()
        rows = sheet.update.call_args.args[1]
        self.assertIn("LAST_SCRAPED", rows[0])
        self.assertEqual(rows[1][-1], "2026-05-24T05:39:00")

    def test_scraper_prefers_google_sheets_existing_data_before_local_json(self):
        sheets_data = {
            "subjects": [
                {
                    "id": "LAW101",
                    "ma_hp": "LAW101",
                    "trang_thai": "Học bù",
                    "thoi_gian": "Admin time",
                    "phong_hoc": "Admin room",
                }
            ]
        }

        with patch.object(scraper, "load_from_sheets", return_value=sheets_data):
            self.assertEqual(scraper.load_existing_data(), sheets_data)

    def test_app_load_data_uses_latest_sheet_scrape_or_updated_at(self):
        sheet = Mock()
        sheet.get_all_values.return_value = [
            app.SHEET_HEADERS,
            [
                "1",
                "LAW101",
                "Mon A",
                "3",
                "GV A",
                "A101",
                "01/06/2026 - Sang",
                "01/06/2026 - Sang",
                "LH26B2DL",
                "Chua hoc",
                "2026-05-20T08:00:00",
                "2026-05-24T05:39:00",
            ],
            [
                "2",
                "LAW102",
                "Mon B",
                "2",
                "GV B",
                "A102",
                "02/06/2026 - Sang",
                "02/06/2026 - Sang",
                "LH26B2DL",
                "Chua hoc",
                "2026-05-22T09:30:00",
                "2026-05-23T05:39:00",
            ],
        ]

        with patch.object(app, "sheets_enabled", return_value=True), patch.object(
            app, "get_sheet", return_value=sheet
        ), patch.object(app, "cache_local_data", return_value=True):
            data = app.load_data()

        self.assertEqual(data["last_updated"], "2026-05-24T05:39:00")


if __name__ == "__main__":
    unittest.main()
