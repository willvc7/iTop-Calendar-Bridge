"""路徑錨點：原始碼模式用 repo 根目錄；打包成 exe（frozen）時改用可寫入目錄。"""
import os
import sys
from pathlib import Path

APP_DIR_NAME = "iTop-Calendar-Bridge"


def is_frozen() -> bool:
    """是否為 PyInstaller 打包後的 exe。"""
    return bool(getattr(sys, "frozen", False))


def repo_root() -> Path:
    """原始碼根目錄（core/ 上兩層）。"""
    return Path(__file__).resolve().parent.parent


def writable_root() -> Path:
    """可寫入根目錄：frozen → %LOCALAPPDATA%/iTop-Calendar-Bridge；否則 repo 根目錄。"""
    if is_frozen():
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / APP_DIR_NAME
    return repo_root()


def bundle_root() -> Path:
    """唯讀資源根目錄：frozen → PyInstaller 解包目錄；否則 repo 根目錄。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", str(writable_root())))
    return repo_root()


def configure_frozen_runtime() -> None:
    """exe 啟動時呼叫一次：若隨附 Chromium 且呼叫端未自訂，補上瀏覽器路徑。"""
    if not is_frozen():
        return
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return
    bundled = Path(sys.executable).resolve().parent / "ms-playwright"
    if bundled.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)