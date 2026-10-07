"""打包路徑錨點測試：原始碼模式等於 repo；frozen 模式轉向 %LOCALAPPDATA%。"""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from core.paths import bundle_root, configure_frozen_runtime, is_frozen, repo_root, writable_root


class TestPathsSourceMode(unittest.TestCase):
    def test_not_frozen(self):
        self.assertFalse(is_frozen())

    def test_writable_equals_repo(self):
        self.assertEqual(writable_root(), repo_root())

    def test_bundle_equals_repo(self):
        self.assertEqual(bundle_root(), repo_root())


class TestPathsFrozenMode(unittest.TestCase):
    def _frozen(self):
        m = mock.patch.object(sys, "frozen", True, create=True)
        m.start()
        self.addCleanup(m.stop)

    def test_writable_localappdata(self):
        self._frozen()
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:/Users/fake/AppData/Local"}):
            self.assertEqual(writable_root(),
                             Path("C:/Users/fake/AppData/Local/iTop-Calendar-Bridge"))

    def test_bundle_meipass(self):
        self._frozen()
        with mock.patch.object(sys, "_MEIPASS", "C:/bundle", create=True):
            self.assertEqual(bundle_root(), Path("C:/bundle"))

    def test_configure_browsers(self):
        self._frozen()
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            browsers = Path(tmp) / "ms-playwright"
            browsers.mkdir()
            with mock.patch.object(sys, "executable", str(Path(tmp) / "app.exe")):
                with mock.patch.dict(os.environ, {}, clear=True):
                    configure_frozen_runtime()
                    # 比 Path 不比字串：resolve() 在此機吐 8.3 短檔名，語義相同即可
                    self.assertEqual(Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH")), browsers.resolve())

    def test_configure_respects_existing_env(self):
        self._frozen()
        with mock.patch.dict(os.environ, {"PLAYWRIGHT_BROWSERS_PATH": "D:/custom"}):
            configure_frozen_runtime()
            self.assertEqual(os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), "D:/custom")


if __name__ == "__main__":
    unittest.main()