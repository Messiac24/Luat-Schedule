from pathlib import Path
import unittest


class ResponsiveCssTests(unittest.TestCase):
    def test_class_badges_do_not_stretch_in_card_layouts(self):
        css = Path("static/css/style.css").read_text(encoding="utf-8")

        self.assertIn(".col-classes {\n        display: flex;", css)
        self.assertIn("align-items: flex-start;", css)
        self.assertIn(".col-classes::before {\n        flex: 0 0 100%;", css)
        self.assertIn(".col-classes .badge-class {\n        flex: 0 0 auto;", css)
        self.assertIn("align-self: flex-start;", css)


if __name__ == "__main__":
    unittest.main()
