import unittest

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


if __name__ == "__main__":
    unittest.main()
