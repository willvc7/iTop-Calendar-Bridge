"""對照表 CSV 匯出測試：僅 Request/Title 欄、缺檔回 None。"""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from stages.sync_requests import export_cache_csv


class TestExportCacheCsv(unittest.TestCase):
    def _write_cache(self, entries) -> str:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(entries, tmp, ensure_ascii=False)
        tmp.close()
        return tmp.name

    def test_exports_request_title_only(self):
        cache = self._write_cache([
            {"Request": "R-042022", "ID": "UserRequest #41079", "Title": "內部專案"},
            {"Request": "R-000001", "ID": "UserRequest #1", "Title": ""},
        ])
        out = str(Path(tempfile.gettempdir()) / "test_request_list.csv")
        with mock.patch("stages.sync_requests.settings") as mock_settings:
            mock_settings.resolve_request_cache.return_value = Path(cache)
            n = export_cache_csv(out)
        self.assertEqual(n, 2)
        with open(out, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r for r in rows[0].keys()], ["Request", "Title"])
        self.assertEqual(rows[0], {"Request": "R-042022", "Title": "內部專案"})

    def test_missing_cache_returns_none(self):
        with mock.patch("stages.sync_requests.settings") as mock_settings:
            mock_settings.resolve_request_cache.return_value = Path(tempfile.gettempdir()) / "no_such.json"
            self.assertIsNone(export_cache_csv(str(Path(tempfile.gettempdir()) / "x.csv")))


if __name__ == "__main__":
    unittest.main()