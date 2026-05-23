import sys
import unittest


class LightweightRuntimeTests(unittest.TestCase):
    def test_importing_app_does_not_load_scraper_or_playwright(self):
        sys.modules.pop("app", None)
        sys.modules.pop("scraper", None)
        for module_name in list(sys.modules):
            if module_name.startswith("playwright"):
                sys.modules.pop(module_name, None)

        import app  # noqa: F401

        self.assertNotIn("scraper", sys.modules)
        self.assertFalse(
            any(module_name.startswith("playwright") for module_name in sys.modules)
        )


if __name__ == "__main__":
    unittest.main()
