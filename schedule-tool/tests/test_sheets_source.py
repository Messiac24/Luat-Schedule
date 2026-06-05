import unittest
from unittest.mock import Mock, patch

import scraper
import app
import sheets


class SheetsSourceTests(unittest.TestCase):
    def test_sync_to_sheets_accepts_service_account_json_from_env(self):
        sheet = Mock()
        sheet.get_all_values.return_value = [sheets.SHEET_HEADERS]
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
                                "last_scraped": "2026-05-25T05:39:00+07:00",
                                "hoc_ky": "Học kỳ I",
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
        self.assertIn("HỌC KỲ", rows[0])
        self.assertEqual(rows[1][-2], "2026-05-25T05:39:00+07:00")
        self.assertEqual(rows[1][-1], "Học kỳ I")

    def test_sync_to_sheets_rejects_implicit_local_fallback(self):
        with patch.object(sheets, "GOOGLE_SHEETS_ID", "sheet-id"):
            self.assertFalse(sheets.sync_to_sheets(None))

    def test_sync_to_sheets_rejects_older_payload_than_current_sheet(self):
        sheet = Mock()
        sheet.get_all_values.return_value = [
            sheets.SHEET_HEADERS,
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
                "Chưa học",
                "2026-06-05T17:00:00+07:00",
                "2026-05-25T05:39:00+07:00",
                "Học kỳ I",
            ],
        ]
        client = Mock()
        client.open_by_key.return_value.sheet1 = sheet
        older_data = {
            "subjects": [
                {
                    "stt": 1,
                    "ma_hp": "LAW101",
                    "ten_hoc_phan": "Mon A",
                    "lop_hoc": ["LH26B2DL"],
                    "updated_at": "2026-05-21T08:00:00+07:00",
                    "last_scraped": "2026-05-21T08:00:00+07:00",
                }
            ]
        }

        with patch.object(sheets, "GOOGLE_SHEETS_ID", "sheet-id"), patch.object(
            sheets, "GOOGLE_SERVICE_ACCOUNT_JSON", '{"client_email":"x","token_uri":"x"}'
        ), patch.object(sheets.Credentials, "from_service_account_info"), patch.object(
            sheets.gspread, "authorize", return_value=client
        ):
            self.assertFalse(sheets.sync_to_sheets(older_data))

        sheet.clear.assert_not_called()
        sheet.update.assert_not_called()

    def test_validate_sync_payload_rejects_missing_current_subject(self):
        candidate_subjects = [
            {"id": "LAW101", "updated_at": "2026-06-05T17:00:00+07:00"}
        ]
        current_subjects = [
            {"id": "LAW101", "updated_at": "2026-06-05T17:00:00+07:00"},
            {"id": "LAW102", "updated_at": "2026-06-05T17:00:00+07:00"},
        ]

        is_valid, message = sheets.validate_sync_payload(
            candidate_subjects, current_subjects
        )

        self.assertFalse(is_valid)
        self.assertTrue("thiếu môn" in message or "ít môn" in message)

    def test_sheets_main_refuses_local_sync_without_explicit_env(self):
        with patch.dict(sheets.os.environ, {}, clear=True), patch.object(
            sheets, "sync_to_sheets"
        ) as sync_to_sheets:
            self.assertFalse(sheets.main())

        sync_to_sheets.assert_not_called()

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
                "2026-05-25T05:39:00+07:00",
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

        self.assertEqual(data["last_updated"], "2026-05-25T05:39:00")
        self.assertEqual(data["subjects"][0]["hoc_ky"], "Học kỳ I")


if __name__ == "__main__":
    unittest.main()
