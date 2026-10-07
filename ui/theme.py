"""設計語言：色票 + ttk 樣式。"""
import tkinter as tk
from tkinter import ttk

BG = "#eef1f6"          # 視窗底
CARD_BG = "#ffffff"     # 卡片底
ACCENT = "#2563eb"      # 主色（藍）
ACCENT_ACTIVE = "#1d4ed8"
INK = "#1f2937"         # 主文字
MUTED = "#6b7280"       # 次文字
LOG_BG = "#1c2230"      # 日誌底（深）
LOG_FG = "#e6e9ef"      # 日誌字
LOG_COLORS = {          # 日誌等級色
    "DEBUG": "#8b93a7",
    "INFO": "#e6e9ef",
    "SUCCESS": "#34d399",
    "WARNING": "#fbbf24",
    "ERROR": "#f87171",
    "CRITICAL": "#ef4444",
}


def apply_style(root: tk.Tk) -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    try:
        import tkinter.font as _font
        _font.nametofont("TkDefaultFont").configure(size=10)
        _font.nametofont("TkTextFont").configure(size=10)
    except Exception:
        pass
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK)
    style.configure("TLabelframe", background=CARD_BG, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=CARD_BG, foreground=ACCENT, font=("", 10, "bold"))
    style.configure("Pill.TLabel", background="#e0e7ff", foreground="#3730a3",
                    font=("", 9), padding=(8, 2))
    style.configure("TEntry", fieldbackground="#ffffff", padding=4,
                      bordercolor="#cbd5e1", lightcolor="#cbd5e1", darkcolor="#cbd5e1")
    style.map("TEntry",
              bordercolor=[("focus", ACCENT)],
              lightcolor=[("focus", ACCENT)],
              darkcolor=[("focus", ACCENT)])
    style.configure("TCombobox", fieldbackground="#ffffff", padding=3)
    style.configure("TCheckbutton", background=CARD_BG, foreground=INK)
    style.configure("TButton", padding=(10, 5))
    style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff", font=("", 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", ACCENT_ACTIVE), ("disabled", "#93c5fd")],
              foreground=[("disabled", "#eff6ff")])
    style.configure("Ghost.TButton", background=CARD_BG, foreground=INK,
                      bordercolor="#cbd5e1", lightcolor=CARD_BG, darkcolor=CARD_BG)
    style.map("Ghost.TButton",
              background=[("active", "#f1f5f9")],
              bordercolor=[("active", ACCENT)])
    style.configure("Date.TButton", padding=(4, 1), font=("", 9),
                      background="#f8fafc", bordercolor="#cbd5e1")
    style.map("Date.TButton",
              background=[("active", "#dbeafe")],
              bordercolor=[("active", ACCENT)])
    style.map("TCombobox",
              bordercolor=[("focus", ACCENT)],
              fieldbackground=[("readonly", "#ffffff")])