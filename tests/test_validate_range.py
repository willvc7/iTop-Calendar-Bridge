"""起迄日期驗證測試：不可空、格式、起<=訖。"""
import unittest

from ui.widgets import validate_date_range


class TestValidateDateRange(unittest.TestCase):
    def test_empty_start(self):
        with self.assertRaises(ValueError):
            validate_date_range("", "2026-10-16")

    def test_empty_end(self):
        with self.assertRaises(ValueError):
            validate_date_range("2026-10-01", "  ")

    def test_bad_format(self):
        with self.assertRaises(ValueError):
            validate_date_range("2026/10/01", "2026-10-16")

    def test_start_after_end(self):
        with self.assertRaises(ValueError):
            validate_date_range("2026-10-17", "2026-10-16")

    def test_single_day_ok(self):
        self.assertEqual(validate_date_range("2026-10-01", "2026-10-01"),
                         ("2026-10-01 00:00", "2026-10-01 23:59"))

    def test_range_ok_and_trimmed(self):
        self.assertEqual(validate_date_range(" 2026-10-01 ", "2026-10-16 "),
                         ("2026-10-01 00:00", "2026-10-16 23:59"))


if __name__ == "__main__":
    unittest.main()