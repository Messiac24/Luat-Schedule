import unittest
from unittest.mock import Mock, patch

import scraper
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
                            }
                        ]
                    }
                )
            )

        from_info.assert_called_once()
        sheet.clear.assert_called_once()
        sheet.update.assert_called_once()

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


if __name__ == "__main__":
    unittest.main()
