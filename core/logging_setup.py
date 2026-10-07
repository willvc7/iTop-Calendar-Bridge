"""全域 loguru 單例：每次執行一個 logs/app_YYYY-MM-DD_HH-mm-ss.log。"""
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger
from core.paths import writable_root

_initialized = False


def setup_logger(log_dir: str = "logs", prefix: str = "app") -> Path:
    global _initialized
    log_path_dir = writable_root() / log_dir
    log_path_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_path_dir / f"{prefix}_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"

    if not _initialized:
        logger.remove()
        if sys.stdout is not None:
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan>:{line} <level>{message}</level>",
                level="INFO",
            )
        logger.add(
            str(log_file),
            rotation="10 MB",
            retention="14 days",
            encoding="utf-8",
            level="DEBUG",
        )
        _initialized = True
    else:
        logger.add(str(log_file), rotation="10 MB", retention="14 days", encoding="utf-8", level="DEBUG")

    return log_file