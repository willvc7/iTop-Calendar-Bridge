"""對照表載入測試：標準鍵、去(#/空白)鍵、缺檔。"""
import json
import tempfile
import unittest
from pathlib import Path

from core.files import load_id_lookup


class TestLoadIdLookup(unittest.TestCase):
    def _write(self, data) -> str:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(data, tmp, ensure_ascii=False)
        tmp.close()
        return tmp.name

    def test_basic_and_clean_keys(self):
        p = self._write([{"Request": "R-042022", "ID": "UserRequest #41079", "Title": "t"}])
        lk = load_id_lookup(p)
        self.assertEqual(lk.get("R-042022"), "UserRequest #41079")
        self.assertEqual(lk.get("R-042022".replace("#", "")), "UserRequest #41079")

    def test_nbsp_and_hash_normalized(self):
        p = self._write([{"Request": "R-1" + chr(160) + "#x", "ID": "UserRequest #1", "Title": "t"}])
        lk = load_id_lookup(p)
        self.assertIn("R-1 #x", lk)  # 不換行空白已轉一般空白
        self.assertEqual(lk.get("R-1x"), "UserRequest #1")  # 去(#/空白)鍵亦命中

    def test_missing_file_returns_none(self):
        self.assertIsNone(load_id_lookup(str(Path(tempfile.gettempdir()) / "no_such_cache.json")))


if __name__ == "__main__":
    unittest.main()