import unittest
from unittest.mock import Mock, patch

import app


SAMPLE_DATA = {
    "subjects": [
        {
            "stt": 1,
            "id": "LAW101",
            "ma_hp": "LAW101",
            "ten_hoc_phan": "Mon A",
            "tc": 3,
            "giang_vien": "GV A",
            "phong_hoc": "A101",
            "thoi_gian": "01/06/2026 - Sang",
            "thoi_gian_goc": "01/06/2026 - Sang",
            "lop_hoc": ["LH26B2DL"],
            "trang_thai": "Chua hoc",
            "schedule_entries": [{"date": "01/06/2026", "periods": ["Sang"]}],
            "is_low_class_count": True,
        }
    ],
    "last_updated": "2026-05-21T08:00:00",
}


class AdminViewModeTests(unittest.TestCase):
    def setUp(self):
        self.original_prepare_data_for_view = app.prepare_data_for_view
        app.prepare_data_for_view = lambda: SAMPLE_DATA
        app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.app.test_client()

    def tearDown(self):
        app.prepare_data_for_view = self.original_prepare_data_for_view

    def login(self):
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True

    def test_admin_view_mode_requires_login(self):
        response = self.client.get("/admin?mode=view")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_admin_edit_mode_renders_admin_controls(self):
        self.login()

        response = self.client.get("/admin")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("status-select", html)
        self.assertIn("time-editor", html)
        self.assertIn("room-editor", html)
        self.assertIn("btn-save-row", html)
        self.assertIn("btn-scrape", html)
        self.assertIn("Xem như người dùng", html)
        self.assertIn("Thu chi Luật", html)

    def test_admin_edit_mode_hides_scrape_button_on_vercel(self):
        self.login()

        with patch.object(app, "is_vercel_runtime", return_value=True):
            response = self.client.get("/admin")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("btn-scrape", html)
        self.assertIn("status-select", html)

    def test_admin_header_actions_use_production_order(self):
        self.login()

        with patch.object(app, "is_vercel_runtime", return_value=True), patch.object(
            app, "sheets_enabled", return_value=True
        ):
            response = self.client.get("/admin")
        html = response.get_data(as_text=True)

        labels = [
            "Chuyển mã lớp",
            "Xem như người dùng",
            "Thu chi Luật",
            "Export Excel",
            "Đồng bộ lại Google Sheets",
            "Đăng xuất",
        ]
        positions = [html.index(label) for label in labels]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(positions, sorted(positions))
        self.assertIn("btn-finance", html)
        self.assertIn("btn-logout", html)

    def test_admin_view_mode_renders_like_public_but_keeps_admin_session_actions(self):
        self.login()

        response = self.client.get("/admin?mode=view")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("status-select", html)
        self.assertNotIn("time-editor", html)
        self.assertNotIn("room-editor", html)
        self.assertNotIn("btn-save-row", html)
        self.assertIn("status-badge", html)
        self.assertIn("Quay lại quản trị", html)
        self.assertIn("Đăng xuất", html)

    def test_public_route_never_renders_admin_controls(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("status-select", html)
        self.assertNotIn("btn-save-row", html)
        self.assertNotIn("Xem như người dùng", html)
        self.assertNotIn("Thu chi Luật", html)

    def test_update_rejects_invalid_status(self):
        self.login()

        response = self.client.post(
            "/api/update",
            json={"id": "LAW101", "trang_thai": "Invalid"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_update_reports_save_failure(self):
        self.login()
        original_load_data = app.load_data
        original_save_data = app.save_data
        app.load_data = lambda: {"subjects": [dict(SAMPLE_DATA["subjects"][0])]}
        app.save_data = lambda data: False

        try:
            response = self.client.post(
                "/api/update",
                json={"id": "LAW101", "trang_thai": "Chưa học"},
            )
        finally:
            app.load_data = original_load_data
            app.save_data = original_save_data

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.get_json()["success"])

    def test_update_writes_only_the_changed_sheet_row(self):
        self.login()
        sheet = Mock()
        current_data = {"subjects": [dict(SAMPLE_DATA["subjects"][0])]}

        with patch.object(app, "load_data", return_value=current_data), patch.object(
            app, "sheets_enabled", return_value=True
        ), patch.object(app, "get_sheet", return_value=sheet), patch.object(
            app, "save_data"
        ) as save_data:
            response = self.client.post(
                "/api/update",
                json={"id": "LAW101", "phong_hoc": "A202"},
            )

        self.assertEqual(response.status_code, 200)
        sheet.update.assert_called_once()
        self.assertEqual(sheet.update.call_args.args[0], "A2:M2")
        save_data.assert_not_called()

    def test_sync_uses_current_loaded_data_instead_of_local_fallback(self):
        self.login()
        current_data = {"subjects": [dict(SAMPLE_DATA["subjects"][0])]}

        with patch.object(app, "sheets_enabled", return_value=True), patch.object(
            app, "load_data", return_value=current_data
        ), patch.object(app, "sync_to_sheets", return_value=True) as sync_to_sheets:
            response = self.client.post("/api/sync")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        sync_to_sheets.assert_called_once_with(current_data)

    def test_prepare_view_sorts_unstarted_subjects_by_first_schedule_date(self):
        original_load_data = app.load_data
        app.load_data = lambda: {
            "subjects": [
                {
                    "id": "20LH1204",
                    "ma_hp": "20LH1204",
                    "thoi_gian": "13/06/2026 (Thứ Bảy) - Sáng",
                    "lop_hoc": ["LHK50DL"],
                    "trang_thai": "Chưa học",
                },
                {
                    "id": "LC101X",
                    "ma_hp": "LC101X",
                    "thoi_gian": "06/06/2026 (Thứ Bảy) - Sáng",
                    "lop_hoc": ["LHK50DL"],
                    "trang_thai": "Chưa học",
                },
                {
                    "id": "20LH1105D",
                    "ma_hp": "20LH1105D",
                    "thoi_gian": "27/06/2026 (Thứ Bảy) - Sáng",
                    "lop_hoc": ["LHK50DL"],
                    "trang_thai": "Chưa học",
                },
                {
                    "id": "20LH1103",
                    "ma_hp": "20LH1103",
                    "thoi_gian": "04/07/2026 (Thứ Bảy) - Sáng",
                    "lop_hoc": ["LHK50DL"],
                    "trang_thai": "Chưa học",
                },
                {
                    "id": "21LH1105CĐ",
                    "ma_hp": "21LH1105CĐ",
                    "thoi_gian": "06/06/2026 (Thứ Bảy) - Sáng",
                    "lop_hoc": ["LLT50DLCĐ"],
                    "trang_thai": "Chưa học",
                },
                {
                    "id": "LH1104CĐ",
                    "ma_hp": "LH1104CĐ",
                    "thoi_gian": "20/06/2026 (Thứ Bảy) - Sáng",
                    "lop_hoc": ["LLT50DLCĐ"],
                    "trang_thai": "Chưa học",
                },
                {
                    "id": "MAKEUP",
                    "ma_hp": "MAKEUP",
                    "thoi_gian": "01/06/2026 (Thứ Hai) - Sáng",
                    "lop_hoc": ["LHK50DL"],
                    "trang_thai": "Học bù",
                    "updated_at": "2026-05-20T08:00:00+07:00",
                },
            ],
            "last_updated": "",
        }

        try:
            data = self.original_prepare_data_for_view()
        finally:
            app.load_data = original_load_data

        self.assertEqual(
            [subject["id"] for subject in data["subjects"]],
            [
                "LC101X",
                "21LH1105CĐ",
                "20LH1204",
                "LH1104CĐ",
                "20LH1105D",
                "20LH1103",
                "MAKEUP",
            ],
        )

    def test_empty_state_points_to_github_actions_scrape(self):
        app.prepare_data_for_view = lambda: {"subjects": [], "last_updated": ""}

        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Scrape DLU schedule", html)
        self.assertIn("GitHub Actions", html)


if __name__ == "__main__":
    unittest.main()
