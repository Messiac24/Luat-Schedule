import json
import unittest

import app


class PwaTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.app.test_client()

    def test_index_links_manifest_and_registers_service_worker(self):
        response = self.client.get("/")
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('rel="manifest"', html)
        self.assertIn("/manifest.webmanifest", html)
        self.assertIn("serviceWorker.register", html)
        self.assertIn("/service-worker.js", html)

    def test_manifest_is_installable(self):
        response = self.client.get("/manifest.webmanifest")
        manifest = json.loads(response.get_data(as_text=True))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "/")
        self.assertTrue(manifest["icons"])

    def test_service_worker_served_at_root_scope(self):
        response = self.client.get("/service-worker.js")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("CACHE_NAME", body)
        self.assertIn("/static/css/style.css", body)
        self.assertIn("/static/js/app.js", body)


if __name__ == "__main__":
    unittest.main()
