import unittest
from unittest.mock import patch

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

    def test_admin_edit_mode_hides_scrape_button_on_vercel(self):
        self.login()

        with patch.object(app, "is_vercel_runtime", return_value=True):
            response = self.client.get("/admin")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("btn-scrape", html)
        self.assertIn("status-select", html)

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

    def test_empty_state_points_to_github_actions_scrape(self):
        app.prepare_data_for_view = lambda: {"subjects": [], "last_updated": ""}

        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Scrape DLU schedule", html)
        self.assertIn("GitHub Actions", html)


if __name__ == "__main__":
    unittest.main()
