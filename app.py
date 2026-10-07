"""主控視窗：帳號設定 + 階段執行。
執行：uv run python app.py
標準庫 tkinter，無需新增依賴。
長時間工作放背景執行緒，UI 不凍結；所有 tkinter 對話框只在主執行緒。
右側訊息區即時呈現 loguru 日誌（含背景執行緒，經 queue 轉回主執行緒）。
UI 子模組見 ui/（theme、widgets、logpanel）；階段管線見 stages/。
"""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from loguru import logger

from core.settings import settings
from core.logging_setup import setup_logger
from core.paths import bundle_root, configure_frozen_runtime
from ui.theme import BG, MUTED, apply_style
from ui.widgets import DatePicker, ask_cache_save_path, ask_open_path, ask_save_path, validate_date_range
from ui.logpanel import LogPanel, log_section


def _keyring_status(username: str = "", url: str = "") -> str:
    """依傳入的帳號/網址查密碼狀態（UI 連動用，避免與欄位脫鉤）"""
    username = username or settings.username
    url = url or settings.itop_url
    try:
        import keyring
        pw = keyring.get_password(url, username) if username else None
        return "已儲存" if pw else "未儲存（首次上傳會彈框要密碼）"
    except Exception as e:
        return f"讀取失敗: {e}"


def stage1_job(start: str, end: str, out: str, send_mail: bool) -> tuple:
    """階段一【匯出行事曆】工作"""
    from stages.stage1_calendar import fetch_outlook_calendar
    events, mailed = fetch_outlook_calendar(start, end, out, send_mail)
    if mailed:
        suffix = "（已寄信）"
    elif events:
        suffix = "（未寄信）"
    else:
        suffix = "（無行程未寄信）"
    return True, f"【匯出行事曆】已完成：{len(events)} 筆{suffix}"


def stage2_job(out_csv: str, send_mail: bool) -> tuple:
    """階段二【更新對照表】工作函式：整理 itop_data.json 並匯出 Request/Title CSV"""
    from stages.sync_requests import export_cache_csv, update_request_cache
    n = update_request_cache()
    if n == "auth_failed":
        return False, "AUTH_FAILED"
    if n is None or (isinstance(n, int) and n < 0):
        return False, "對照表更新失敗，已中止匯出"
    m = export_cache_csv(out_csv)
    if m is None:
        from core.files import display_path
        return False, f"對照表 CSV 匯出失敗：{display_path(out_csv)}"
    suffix = "（未寄信）"
    if send_mail:
        from core.mailer import mail_cache_csv
        ok = mail_cache_csv(out_csv, m)
        suffix = "（已寄信）" if ok else "（寄信失敗）"
    return True, f"【更新對照表】已完成：{m} 筆{suffix}"


def stage3_job(csv_path: str) -> tuple:
    """階段三【上傳工單】工作函式"""
    from stages.stage3_upload import main as run_upload
    result = run_upload(csv_override=csv_path)
    if result is True:
        return True, ""
    if result == "auth_failed":
        return False, "AUTH_FAILED"
    return False, "上傳作業已中止，詳見執行日誌"


def _record_output_path(path: str) -> None:
    """輸出路徑一旦選定就記入設定檔"""
    import yaml
    settings.calendar_output = path
    try:
        cfg = settings.config_path
        data = {}
        if cfg.exists():
            with open(cfg, "r", encoding="utf-8-sig") as f:
                data = yaml.safe_load(f) or {}
        data["calendar_output"] = path
        with open(cfg, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise RuntimeError(f"記錄輸出路徑失敗: {e}")


def main() -> None:
    setup_logger()
    configure_frozen_runtime()

    try:
        root = tk.Tk()
    except Exception as e:
        try:
            print(f"無法開啟設定視窗（需要桌面 GUI 環境）: {e}")
            print("請改用文字編輯器直接修改 config/config.yaml（格式見 config.example.yaml）。")
        except Exception:
            pass
        return
    root.title("iTop-Calendar-Bridge")
    root.minsize(940, 432)
    root.configure(background=BG)
    try:  # 視窗圖示：缺檔也不影響啟動
        _icon = bundle_root() / "assets" / "app.ico"
        if _icon.exists():
            root.iconbitmap(str(_icon))
    except Exception:
        pass

    try:
        root.state("zoomed")
    except Exception:
        pass

    apply_style(root)

    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="both", expand=True)
    frm.columnconfigure(0, weight=0, minsize=430)
    frm.columnconfigure(1, weight=1)
    frm.rowconfigure(3, weight=1)

    # ---- 頂欄 ----
    head = ttk.Frame(frm)
    head.grid(row=0, column=0, columnspan=2, sticky="we", padx=4, pady=(0, 6))
    ttk.Label(head, text="iTop-Calendar-Bridge", font=("", 13, "bold")).pack(side="left")
    ttk.Label(head, text="行事曆 → 人工確認 → 批次建單",
              foreground=MUTED).pack(side="left", padx=(10, 0))

    # ---- 帳號卡 ----
    acc = ttk.LabelFrame(frm, text="帳號", padding=8)
    acc.grid(row=1, column=0, sticky="we", padx=4, pady=4)
    ttk.Label(acc, text="iTop 帳號").pack(anchor="w")
    username_var = tk.StringVar(value=settings.username)
    ttk.Entry(acc, textvariable=username_var, width=40).pack(fill="x")
    ttk.Label(acc, text="iTop 網址").pack(anchor="w", pady=(6, 0))
    url_var = tk.StringVar(value=settings.itop_url)
    ttk.Entry(acc, textvariable=url_var, width=40).pack(fill="x")
    status_var = tk.StringVar()
    row3 = ttk.Frame(acc)
    row3.pack(fill="x", pady=(6, 0))
    ttk.Label(row3, textvariable=status_var, style="Pill.TLabel").pack(side="left")

    def on_clear_pw() -> None:
        try:
            from core.credentials import clear_saved_password
            if messagebox.askyesno("確認", "確定清除已存密碼？\n下次上傳會重新要求輸入。", parent=root):
                clear_saved_password()
                refresh_status()
                logger.info("已清除已存密碼")
        except Exception as e:
            messagebox.showerror("失敗", str(e), parent=root)

    ttk.Button(row3, text="清除已存密碼", style="Ghost.TButton",
               command=on_clear_pw).pack(side="right")

    def refresh_status(*_args) -> None:
        status_var.set(f"密碼狀態：{_keyring_status(username_var.get().strip(), url_var.get().strip())}")

    username_var.trace_add("write", refresh_status)
    url_var.trace_add("write", refresh_status)
    refresh_status()

    # ---- 階段選擇 ----
    sel = ttk.Frame(frm)
    sel.grid(row=2, column=0, sticky="we", padx=4, pady=2)
    ttk.Label(sel, text="階段").pack(side="left")
    stage_var = tk.StringVar(value="請選擇…")
    combo = ttk.Combobox(sel, textvariable=stage_var,
                         values=["階段一：匯出行事曆", "階段二：更新對照表", "階段三：上傳工單"],
                         state="readonly", width=26)
    combo.pack(side="left", padx=8)

    # ---- 階段卡片容器 ----
    stage_container = ttk.Frame(frm, height=160)
    stage_container.grid(row=3, column=0, sticky="new", padx=4, pady=4)
    stage_container.grid_propagate(False)
    stage_container.columnconfigure(0, weight=1)
    stage_container.rowconfigure(0, weight=1)

    # ---- 階段【匯出行事曆】卡片（選擇後才出現；起迄日期不可為空且須起<=訖） ----
    s1 = ttk.LabelFrame(stage_container, text="階段一：匯出行事曆", padding=8)
    sdate_var = tk.StringVar(value=settings.calendar_start)
    edate_var = tk.StringVar(value=settings.calendar_end)
    dr = ttk.Frame(s1)
    dr.pack(fill="x", pady=2)
    ttk.Label(dr, text="開始").pack(side="left")
    ttk.Button(dr, textvariable=sdate_var, width=12, style="Date.TButton",
               command=lambda: DatePicker(root, sdate_var)).pack(side="left", padx=4)
    ttk.Label(dr, text="結束").pack(side="left", padx=(10, 0))
    ttk.Button(dr, textvariable=edate_var, width=12, style="Date.TButton",
               command=lambda: DatePicker(root, edate_var)).pack(side="left", padx=4)

    sendmail_var = tk.BooleanVar(value=bool(settings.send_mail))
    ttk.Checkbutton(s1, text="同步寄給自己", variable=sendmail_var).pack(anchor="w", pady=(8, 4))
    stage1_btn = ttk.Button(s1, text="▶ 匯出行事曆", style="Accent.TButton")
    stage1_btn.pack(side="bottom", anchor="se", pady=(4, 2))

    # ---- 階段二【更新對照表】（選擇後才出現） ----
    s2 = ttk.LabelFrame(stage_container, text="階段二：更新對照表", padding=8)
    sendcache_var = tk.BooleanVar(value=bool(settings.send_cache_mail))
    ttk.Checkbutton(s2, text="同步寄給自己", variable=sendcache_var).pack(anchor="w", pady=(8, 4))
    stage2_btn = ttk.Button(s2, text="▶ 更新對照表", style="Accent.TButton")
    stage2_btn.pack(side="bottom", anchor="se", pady=(4, 2))

    # ---- 階段三【上傳工單】（選擇後才出現） ----
    s3 = ttk.LabelFrame(stage_container, text="階段三：上傳工單", padding=8)
    ttk.Label(s3, text="請先確認 CSV 已人工補完 Request 欄", foreground=MUTED).pack(anchor="w", pady=(8, 4))
    stage3_btn = ttk.Button(s3, text="▶ 上傳工單", style="Accent.TButton")
    stage3_btn.pack(side="bottom", anchor="se", pady=(4, 2))

    s1.grid(row=0, column=0, sticky="nsew")
    s2.grid(row=0, column=0, sticky="nsew")
    s3.grid(row=0, column=0, sticky="nsew")
    s1.grid_remove()
    s2.grid_remove()
    s3.grid_remove()

    def _show_stage(*_args) -> None:
        v = stage_var.get()
        if v.startswith("階段一"):
            s2.grid_remove()
            s3.grid_remove()
            s1.grid()
        elif v.startswith("階段二"):
            s1.grid_remove()
            s3.grid_remove()
            s2.grid()
        elif v.startswith("階段三"):
            s1.grid_remove()
            s2.grid_remove()
            s3.grid()

    combo.bind("<<ComboboxSelected>>", _show_stage)

    # ---- 自動儲存機制 ----
    _save_timer = None

    def trigger_auto_save(*_args) -> None:
        nonlocal _save_timer
        if _save_timer is not None:
            root.after_cancel(_save_timer)

        def _do_save():
            try:
                settings.username = username_var.get().strip()
                settings.itop_url = url_var.get().strip()
                settings.send_mail = bool(sendmail_var.get())
                settings.send_cache_mail = bool(sendcache_var.get())
                settings.calendar_start = sdate_var.get().strip()
                settings.calendar_end = edate_var.get().strip()
                settings.save()
            except Exception:
                pass
        _save_timer = root.after(400, _do_save)

    username_var.trace_add("write", trigger_auto_save)
    url_var.trace_add("write", trigger_auto_save)
    sendmail_var.trace_add("write", trigger_auto_save)
    sendcache_var.trace_add("write", trigger_auto_save)
    sdate_var.trace_add("write", trigger_auto_save)
    edate_var.trace_add("write", trigger_auto_save)

    # ---- 日誌區 ----
    logpanel = LogPanel(frm)
    logpanel.grid(row=1, column=1, rowspan=4, sticky="nsew", padx=4, pady=4)
    logpanel.attach()

    # ---- 背景執行 ----
    jobs: queue.Queue = queue.Queue()
    pending_retry = None

    def poll() -> None:
        logpanel.drain()
        try:
            ok, text = jobs.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        try:
            if not ok and text == "AUTH_FAILED":
                _handle_auth_failed()
            elif text:
                logger.info(("" if ok else "失敗：") + text)
        finally:
            stage1_btn.config(state="normal")
            stage2_btn.config(state="normal")
            stage3_btn.config(state="normal")
            root.after(100, poll)

    def _handle_auth_failed() -> None:
        """登入失敗（主執行緒）：問是否清除已存密碼並即時重輸；成功則自動接續原工作"""
        nonlocal pending_retry
        logger.error("登入失敗：請檢查帳號密碼是否正確")
        try:
            root.attributes("-topmost", True)
            try:
                want = messagebox.askyesno("登入失敗", "帳號或密碼錯誤（可能是密碼已變更）。\n是否清除已存密碼並重新輸入？", parent=root)
            finally:
                root.attributes("-topmost", False)
        except Exception:
            pending_retry = None
            return
        if not want:
            pending_retry = None
            logger.info("已保留舊密碼設定，未重試")
            return
        try:
            from core.credentials import clear_saved_password, ensure_credentials
            clear_saved_password()
            if ensure_credentials(parent=root):
                job, pending_retry = pending_retry, None
                refresh_status()
                if job is not None:
                    logger.info("已更新密碼，自動繼續執行作業")
                    launch(job[0], *job[1])
                else:
                    logger.info("已更新密碼，請重新執行作業")
            else:
                pending_retry = None
                logger.warning("未完成密碼更新，已取消")
        except Exception as e:
            pending_retry = None
            messagebox.showerror("失敗", str(e), parent=root)
        refresh_status()

    def launch(worker, *args) -> None:
        nonlocal pending_retry
        pending_retry = (worker, args)
        stage1_btn.config(state="disabled")
        stage2_btn.config(state="disabled")
        stage3_btn.config(state="disabled")

        def _w() -> None:
            try:
                jobs.put(worker(*args))
            except Exception as e:
                jobs.put((False, f"執行異常：{e}"))

        threading.Thread(target=_w, daemon=True).start()

    def start_stage1() -> None:
        log_section("開始【匯出行事曆】")
    
        try:
            start_dt, end_dt = validate_date_range(sdate_var.get(), edate_var.get())
        except ValueError as ve:
            messagebox.showerror("格式錯誤", str(ve), parent=root)
            return

        out = ask_save_path(root, initialdir=str(settings.resolve(settings.calendar_output).parent))
        if not out:
            logger.warning("未選擇輸出路徑，已取消作業")
            return
        try:
            _record_output_path(out)
        except Exception as re_:
            messagebox.showerror("記錄失敗", str(re_), parent=root)
            return

        launch(stage1_job, start_dt, end_dt, out, bool(sendmail_var.get()))

    def start_stage2() -> None:
        log_section("開始【更新對照表】")

        from core.credentials import ensure_credentials
        out = ask_cache_save_path(root)
        if not out:
            logger.warning("未選擇輸出路徑，已取消作業")
            return
        if not ensure_credentials(parent=root):
            logger.warning("帳密未設定完成，已取消作業")
            return
        refresh_status()

        launch(stage2_job, out, bool(sendcache_var.get()))

    def start_stage3() -> None:
        log_section("開始【上傳工單】")

        from core.credentials import ensure_credentials
        csv_path = ask_open_path(root)
        if not csv_path:
            logger.warning("未選擇輸入檔，已取消作業")
            return
        if not ensure_credentials(parent=root):
            logger.warning("帳密未設定完成，已取消作業")
            return
        refresh_status()

        launch(stage3_job, csv_path)

    stage1_btn.config(command=start_stage1)
    stage2_btn.config(command=start_stage2)
    stage3_btn.config(command=start_stage3)

    def on_close() -> None:
        logpanel.detach()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    logger.info("就緒")
    root.after(100, poll)
    root.mainloop()


if __name__ == "__main__":
    main()