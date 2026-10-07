"""郵件包裝測試：主旨/內文集中於 mailer，不靠 Outlook 實體（mock 發送層）。"""
import unittest
from unittest import mock

from core import mailer


class TestMailContent(unittest.TestCase):
    def test_calendar_subject_body(self):
        self.assertEqual(mailer.calendar_subject("2026-10-01 00:00", "2026-10-07 23:59"),
                         "行事曆匯出報表 (2026-10-01 00:00 ~ 2026-10-07 23:59)")
        self.assertIn("行事曆", mailer.calendar_body())

    def test_cache_subject_body(self):
        self.assertEqual(mailer.CACHE_MAIL_SUBJECT, "iTop 對照表匯出")
        self.assertIn("16 筆", mailer.cache_mail_body(16))


class TestMailWrappers(unittest.TestCase):
    def test_mail_calendar_csv_forwards(self):
        with mock.patch.object(mailer, "send_file_to_self", return_value=True) as m:
            self.assertTrue(mailer.mail_calendar_csv("C:/x/a.csv", "S", "E"))
            m.assert_called_once_with("C:/x/a.csv",
                                      subject=mailer.calendar_subject("S", "E"),
                                      body=mailer.calendar_body())

    def test_mail_cache_csv_forwards(self):
        with mock.patch.object(mailer, "send_file_to_self", return_value=False) as m:
            self.assertFalse(mailer.mail_cache_csv("C:/x/b.csv", 5))
            m.assert_called_once_with("C:/x/b.csv",
                                      subject=mailer.CACHE_MAIL_SUBJECT,
                                      body=mailer.cache_mail_body(5))


if __name__ == "__main__":
    unittest.main()