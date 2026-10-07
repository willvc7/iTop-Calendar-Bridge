"""階段工作訊息測試。"""
import unittest
from unittest import mock

from app import stage1_job


class TestStage1JobMessage(unittest.TestCase):
    def _run(self, fetch_ret):
        with mock.patch("stages.stage1_calendar.fetch_outlook_calendar", return_value=fetch_ret):
            return stage1_job("2026-10-05 00:00", "2026-10-09 23:59", "C:/x/a.csv", True)

    def test_mailed(self):
        ok, msg = self._run(([{"Request": "R-1"}], True))
        self.assertTrue(ok)
        self.assertIn("1 筆（已寄信）", msg)

    def test_not_mailed(self):
        ok, msg = self._run(([{"Request": "R-1"}], False))
        self.assertTrue(ok)
        self.assertIn("1 筆（未寄信）", msg)

    def test_empty_never_claims_mailed(self):
        ok, msg = self._run(([], False))
        self.assertTrue(ok)
        self.assertIn("0 筆（無行程未寄信）", msg)
        self.assertNotIn("已寄信", msg)


if __name__ == "__main__":
    unittest.main()