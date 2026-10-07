"""右側執行日誌區：loguru 經 queue 轉回主執行緒顯示（執行緒安全）。"""
import queue
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from loguru import logger

from ui.theme import ACCENT, LOG_BG, LOG_COLORS, LOG_FG


def log_section(title: str) -> None:
    """階段分隔線。"""
    logger.info(f"━━━━━━━━ {title} ━━━━━━━━")


class LogPanel(ttk.LabelFrame):
    def __init__(self, parent) -> None:
        super().__init__(parent, text="執行日誌", padding=4)
        self.msg = ScrolledText(self, height=12, width=48, state="disabled", wrap="word",
                                background=LOG_BG, foreground=LOG_FG, insertbackground=LOG_FG,
                                selectbackground=ACCENT, relief="flat", borderwidth=0,
                                font=("Consolas", 9))
        self.msg.pack(fill="both", expand=True)
        for level, color in LOG_COLORS.items():
            self.msg.tag_config(level, foreground=color)
        self._q: queue.Queue = queue.Queue()
        self._sink_id = None

    def attach(self) -> None:
        """把 loguru 接進本面板；回傳前先掛載（呼叫方負責 detach）"""
        q = self._q

        def _sink(message) -> None:
            try:
                rec = message.record
                q.put((rec["level"].name, f"{rec['time']:%H:%M:%S} {rec['message']}"))
            except Exception:
                pass

        self._sink_id = logger.add(_sink, level="DEBUG")

    def detach(self) -> None:
        try:
            if self._sink_id is not None:
                logger.remove(self._sink_id)
        except Exception:
            pass
        self._sink_id = None

    def drain(self, limit: int = 200) -> None:
        """主執行緒定時呼叫，把佇列內容倒進文字區"""
        drained = 0
        while drained < limit:
            try:
                level, text = self._q.get_nowait()
            except queue.Empty:
                break
            self.msg.config(state="normal")
            self.msg.insert("end", f"{text}\n", (level if level in LOG_COLORS else "INFO",))
            self.msg.see("end")
            self.msg.config(state="disabled")
            drained += 1

    def info(self, text: str) -> None:
        """UI 端提示統一走 loguru（成功/警告等由呼叫方選 level，經 attach 即時顯示）"""
        logger.info(text)