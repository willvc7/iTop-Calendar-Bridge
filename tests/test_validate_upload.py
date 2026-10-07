"""上傳前檢查測試：必填欄位空白與未知 Request 須全數揪出，否則整批中止。"""
import unittest

from core.files import validate_upload_rows

_LOOKUP = {"R-042022": "UserRequest #41079"}
_REQUIRED = ["Request", "Date", "StartTime", "EndTime", "Description"]
_FULL = {"Request": "R-042022", "Date": "20260922", "StartTime": "1300",
         "EndTime": "1800", "Description": "x"}


class TestValidateUploadRows(unittest.TestCase):
    def test_all_ok(self):
        rows = [(2, dict(_FULL)), (3, {**_FULL, "Request": "R-#042022"})]
        self.assertEqual(validate_upload_rows(rows, _REQUIRED, _LOOKUP), ([], []))

    def test_blank_request(self):
        rows = [(2, dict(_FULL)), (3, {**_FULL, "Request": "  "}), (4, {})]
        blanks, unknown = validate_upload_rows(rows, _REQUIRED, _LOOKUP)
        self.assertEqual(blanks, [(3, "Request"), (4, "Request")])
        self.assertEqual(unknown, [])

    def test_blank_other_fields(self):
        rows = [(5, {**_FULL, "Date": ""}), (6, {**_FULL, "StartTime": "  "})]
        blanks, unknown = validate_upload_rows(rows, _REQUIRED, _LOOKUP)
        self.assertEqual(blanks, [(5, "Date"), (6, "StartTime")])
        self.assertEqual(unknown, [])

    def test_unknown_rows(self):
        rows = [(2, dict(_FULL)), (5, {**_FULL, "Request": "R-999999"})]
        blanks, unknown = validate_upload_rows(rows, _REQUIRED, _LOOKUP)
        self.assertEqual(blanks, [])
        self.assertEqual(unknown, [(5, "R-999999")])

    def test_nbsp_treated_as_blank(self):
        rows = [(2, {**_FULL, "Request": chr(160)})]
        blanks, unknown = validate_upload_rows(rows, _REQUIRED, _LOOKUP)
        self.assertEqual(blanks, [(2, "Request")])


if __name__ == "__main__":
    unittest.main()