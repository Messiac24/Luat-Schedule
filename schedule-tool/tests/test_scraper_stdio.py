import io
import unittest

import scraper


class ReconfigurableTextIO(io.StringIO):
    def __init__(self):
        super().__init__()
        self.encoding_value = None
        self.errors_value = None

    def reconfigure(self, encoding=None, errors=None):
        self.encoding_value = encoding
        self.errors_value = errors


class ConfigureUtf8OutputTests(unittest.TestCase):
    def test_reconfigures_streams_to_utf8_with_replace_errors(self):
        stdout = ReconfigurableTextIO()
        stderr = ReconfigurableTextIO()

        scraper.configure_utf8_output(stdout=stdout, stderr=stderr)

        self.assertEqual(stdout.encoding_value, "utf-8")
        self.assertEqual(stdout.errors_value, "replace")
        self.assertEqual(stderr.encoding_value, "utf-8")
        self.assertEqual(stderr.errors_value, "replace")


if __name__ == "__main__":
    unittest.main()
