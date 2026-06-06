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

    def test_lh26b2dl_badge_uses_light_purple_background(self):
        css = Path("static/css/style.css").read_text(encoding="utf-8")

        self.assertIn(".badge-class.class-lh26b2dl,", css)
        self.assertIn("background: #F3E8FF;", css)
        self.assertIn("border-color: #D8B4FE;", css)
        self.assertIn("color: #6B21A8;", css)

    def test_makeup_status_uses_row_overlay_without_padding_changes(self):
        css = Path("static/css/style.css").read_text(encoding="utf-8")

        self.assertIn("--color-makeup-overlay: rgba(124, 58, 237, 0.08);", css)
        self.assertIn(".status-học-bù.subject-row {\n    background-color: var(--color-surface);", css)
        self.assertIn(
            "background-image: linear-gradient(var(--color-makeup-overlay), var(--color-makeup-overlay));",
            css,
        )
        self.assertIn(".status-học-bù td {\n    background-color: transparent;", css)
        self.assertNotIn(".status-học-bù td {\n    padding", css)


if __name__ == "__main__":
    unittest.main()
