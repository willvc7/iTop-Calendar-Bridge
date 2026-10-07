"""共用小元件：日期選擇器、檔案對話框、起迄日期驗證。"""
import calendar as _cal
import datetime
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from ui import DAY_FMT
from core.files import with_timestamp


def validate_date_range(start: str, end: str) -> tuple:
    """驗證階段一起迄日期：不可為空、格式 YYYY-MM-DD、起須早於或等於訖。
    """
    s, e = (start or "").strip(), (end or "").strip()
    if not s:
        raise ValueError("開始日期不可為空")
    if not e:
        raise ValueError("結束日期不可為空")
    try:
        sd = datetime.datetime.strptime(s, DAY_FMT)
    except ValueError:
        raise ValueError(f"開始日期格式錯誤：{s}（應為 YYYY-MM-DD）")
    try:
        ed = datetime.datetime.strptime(e, DAY_FMT)
    except ValueError:
        raise ValueError(f"結束日期格式錯誤：{e}（應為 YYYY-MM-DD）")
    if sd > ed:
        raise ValueError("開始日期不可晚於結束日期（起須早於或等於訖）")
    return f"{s} 00:00", f"{e} 23:59"


class DatePicker:
    """日期選擇器"""

    def __init__(self, parent: tk.Tk, var: tk.StringVar) -> None:
        self.var = var
        self.top = tk.Toplevel(parent)
        self.top.title("選擇日期")
        self.top.resizable(False, False)
        try:
            self.top.attributes("-topmost", True)
        except Exception:
            pass
        try:
            cur = datetime.datetime.strptime(var.get().strip(), DAY_FMT)
        except ValueError:
            cur = datetime.datetime.now()
        self.y, self.m = cur.year, cur.month
        nav = ttk.Frame(self.top)
        nav.pack(padx=8, pady=(8, 4))
        ttk.Button(nav, text="<", width=3, command=self._shift(-1)).pack(side="left")
        self.title = ttk.Label(nav, width=14, anchor="center")
        self.title.pack(side="left")
        ttk.Button(nav, text=">", width=3, command=self._shift(1)).pack(side="left")
        self.cells = ttk.Frame(self.top)
        self.cells.pack(padx=8, pady=(0, 8))
        self._draw()
        self.top.transient(parent)
        self.top.grab_set()

    def _shift(self, delta: int):
        def _go() -> None:
            m, y = self.m + delta, self.y
            if m < 1:
                m, y = 12, y - 1
            elif m > 12:
                m, y = 1, y + 1
            self.m, self.y = m, y
            self._draw()
        return _go

    def _draw(self) -> None:
        for w in self.cells.winfo_children():
            w.destroy()
        self.title.config(text=f"{self.y} 年 {self.m} 月")
        for c, h in enumerate("一二三四五六日"):
            ttk.Label(self.cells, text=h, width=4, anchor="center").grid(row=0, column=c)
        first, days = _cal.monthrange(self.y, self.m)  # Monday=0
        r, c = 1, first
        for day in range(1, days + 1):
            ttk.Button(self.cells, text=str(day), width=3,
                       command=lambda d=day: self._pick(d)).grid(row=r, column=c, padx=0, pady=0, ipady=0)
            c += 1
            if c > 6:
                c, r = 0, r + 1

    def _pick(self, day: int) -> None:
        self.var.set(f"{self.y:04d}-{self.m:02d}-{day:02d}")
        self.top.destroy()


def ask_save_path(parent: tk.Tk, initialdir: str = "") -> str:
    return filedialog.asksaveasfilename(
        parent=parent, title="請選擇行事曆輸出路徑",
        defaultextension=".csv", filetypes=[("CSV", "*.csv")],
        initialdir=initialdir or None,
        initialfile=Path(with_timestamp("raw_calendar.csv")).name,
    ) or ""


def ask_open_path(parent: tk.Tk) -> str:
    return filedialog.askopenfilename(
        parent=parent, title="請選擇已人工確認的 CSV",
        filetypes=[("CSV", "*.csv"), ("全部", "*.*")],
    ) or ""


def ask_cache_save_path(parent: tk.Tk) -> str:
    return filedialog.asksaveasfilename(
        parent=parent, title="請選擇對照表輸出路徑",
        defaultextension=".csv", filetypes=[("CSV", "*.csv")],
        initialfile=Path(with_timestamp("request_list.csv")).name,
    ) or ""