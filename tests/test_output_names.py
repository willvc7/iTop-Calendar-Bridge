"""路徑顯示與檔名時間戳測試：正斜線統一、防重加戳。"""
import unittest

from core.files import display_path, with_timestamp


class TestDisplayPath(unittest.TestCase):
    def test_backslash_to_forward(self):
        self.assertEqual(display_path("C:\\Users\\a\\b.csv"), "C:/Users/a/b.csv")

    def test_forward_unchanged(self):
        self.assertEqual(display_path("C:/Users/a/b.csv"), "C:/Users/a/b.csv")


class TestWithTimestamp(unittest.TestCase):
    def test_adds_stamp(self):
        out = with_timestamp("data/request_list.csv")
        self.assertRegex(out, r"request_list_\d{8}_\d{6}\.csv$")

    def test_no_double_stamp(self):
        once = with_timestamp("raw_calendar.csv")
        self.assertEqual(with_timestamp(once), once)


if __name__ == "__main__":
    unittest.main()