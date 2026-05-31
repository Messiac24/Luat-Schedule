import unittest
from unittest.mock import patch

import scraper


class ScraperMergeTests(unittest.TestCase):
    def test_merge_preserves_admin_status_makeup_time_and_room_edits(self):
        existing_data = {
            "subjects": [
                {
                    "id": "LAW101",
                    "ma_hp": "LAW101",
                    "ten_hoc_phan": "Old name",
                    "tc": 2,
                    "giang_vien": "Old teacher",
                    "phong_hoc": "Admin edited room",
                    "thoi_gian": "Admin makeup schedule",
                    "thoi_gian_goc": "Old scraped schedule",
                    "lop_hoc": ["OLD"],
                    "trang_thai": "Học bù",
                    "updated_at": "2026-05-20T08:00:00",
                }
            ]
        }
        scraped_subjects = [
            {
                "id": "LAW101",
                "ma_hp": "LAW101",
                "stt": 1,
                "ten_hoc_phan": "New name",
                "tc": 3,
                "giang_vien": "New teacher",
                "phong_hoc": "Scraped room",
                "thoi_gian": "Scraped active schedule",
                "thoi_gian_goc": "New scraped original schedule",
                "lop_hoc": ["NEW"],
                "last_scraped": "2026-05-21T08:00:00",
            }
        ]

        merged = scraper.merge_data(existing_data, scraped_subjects)
        subject = merged["subjects"][0]

        self.assertEqual(subject["ten_hoc_phan"], "New name")
        self.assertEqual(subject["giang_vien"], "New teacher")
        self.assertEqual(subject["thoi_gian_goc"], "New scraped original schedule")
        self.assertEqual(subject["trang_thai"], "Học bù")
        self.assertEqual(subject["thoi_gian"], "Admin makeup schedule")
        self.assertEqual(subject["phong_hoc"], "Admin edited room")
        self.assertEqual(subject["updated_at"], "2026-05-20T08:00:00")
        self.assertEqual(subject["hoc_ky"], "Học kỳ I")

    def test_merge_uses_vietnam_timestamp_for_new_subjects(self):
        scraped_subjects = [
            {
                "id": "LAW102",
                "ma_hp": "LAW102",
                "stt": 1,
                "ten_hoc_phan": "New subject",
                "tc": 2,
                "giang_vien": "Teacher",
                "phong_hoc": "",
                "thoi_gian": "",
                "thoi_gian_goc": "",
                "lop_hoc": ["LH26B2DL"],
                "last_scraped": "2026-05-25T05:44:06+07:00",
            }
        ]

        with patch.object(
            scraper, "now_vietnam_iso", return_value="2026-05-25T05:44:06+07:00"
        ):
            merged = scraper.merge_data({"subjects": []}, scraped_subjects)

        self.assertEqual(merged["last_updated"], "2026-05-25T05:44:06+07:00")
        self.assertEqual(
            merged["subjects"][0]["updated_at"], "2026-05-25T05:44:06+07:00"
        )
        self.assertEqual(merged["subjects"][0]["hoc_ky"], "Học kỳ II")


if __name__ == "__main__":
    unittest.main()
