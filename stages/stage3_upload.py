import datetime
from types import SimpleNamespace
from loguru import logger
from playwright.sync_api import sync_playwright

from core.settings import settings
from core.credentials import login_itop, login_itop_interactive
from core.jobs import execute_task
from core.paths import writable_root
import core.files as file_handler

# 配置日誌：每次執行一個 logs/app_*.log
try:
    from core.logging_setup import setup_logger
    setup_logger()
except Exception:
    pass


def _run_config(csv_override: str = "") -> SimpleNamespace:
    """執行期解析全部路徑與參數"""
    return SimpleNamespace(
        input_file=str(settings.resolve_upload_input(csv_override)) if csv_override else str(settings.resolve_upload_input()),
        log_file=str(writable_root() / "logs" / "Log.csv"),
        run_dir=writable_root() / "logs",
        encoding=settings.file_encoding,
        target_url=f"{settings.itop_url}?{settings.create_TimeSpent}",
        required_fields=[item.strip() for item in settings.required_fields.split(',')],
    )


def _choose_file_dialog() -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as e:
        logger.error(f"無法開啟檔案對話框（缺少 GUI 環境）: {e}")
        return ""
    try:
        root = tk.Tk()
    except Exception as e:
        logger.error(f"無法開啟檔案對話框（缺少 GUI 環境）: {e}")
        return ""
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    try:
        path = filedialog.askopenfilename(
            title="請選擇已人工確認的 CSV",
            filetypes=[("CSV", "*.csv"), ("全部", "*.*")],
        )
    except Exception as e:
        logger.error(f"檔案對話框異常: {e}")
        return ""
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return path or ""

def main(csv_override: str = "", ask_file: bool = False, interactive: bool = False):
    """回傳 True=跑完（含無事可做）；False=載入/檢查失敗已整批中止；"auth_failed"=登入失敗。"""
    cfg = _run_config(csv_override)

    if ask_file and not csv_override:
        picked = _choose_file_dialog()
        if not picked:
            logger.error("未選擇檔案，取消上傳")
            return False
        cfg = _run_config(picked)
    input_file = cfg.input_file

    # 1. 資料加載與校驗 (Fail Fast)
    reader_list = file_handler.load_csv_data(input_file, cfg.encoding)
    if reader_list is None:
        return False

    if not file_handler.validate_itop_format(reader_list, cfg.required_fields):
        return False

    list_file = str(settings.resolve_request_cache())
    id_lookup = file_handler.load_id_lookup(list_file)
    if id_lookup is None:
        return False

    # 2. 準備欄位與待處理清單
    fieldnames = list(reader_list[0].keys())
    for col in ["Status", "Message", "ProcessedTime"]:
        if col not in fieldnames:
            fieldnames.append(col)

    to_process_indices = [i for i, row in enumerate(reader_list) if row.get("Status") != "成功"]

    if not to_process_indices:
        logger.success("所有資料皆已處理完成")
        return True

    # 3. 上傳前檢查：必填欄位皆不可空白、Request 須存在於對照表，否則整批中止（不逐筆跳過）
    blanks, unknown = file_handler.validate_upload_rows(
        [(i + 2, reader_list[i]) for i in to_process_indices], cfg.required_fields, id_lookup)
    if blanks:
        detail = "、".join(f"列{r}:{c}" for r, c in blanks[:10]) + ("..." if len(blanks) > 10 else "")
        logger.error(f"必填欄位空白共 {len(blanks)} 筆（{detail}），已中止上傳；請補完後重跑")
        return False
    if unknown:
        detail = "、".join(f"列{r}:{q}" for r, q in unknown[:10]) + ("..." if len(unknown) > 10 else "")
        logger.error(f"對照表無此 ID 共 {len(unknown)} 筆（{detail}），已中止上傳；請先執行階段二更新對照表")
        return False

    total_pending = len(to_process_indices)
    logger.info(f"待處理: {total_pending} 筆 / 總計: {len(reader_list)} 筆")

    # 4. 啟動 Playwright 流程
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            if interactive:
                ok = login_itop_interactive(page)
            else:
                ok = login_itop(page)
            if not ok:
                logger.error("登入失敗，終止任務")
                return "auth_failed"

            success_count = 0
            for i, idx in enumerate(to_process_indices):
                row = reader_list[idx]

                # 上傳前檢查已保證：必填欄位齊全 + ID 必存在，此處不再逐筆跳過
                req_key = str(row.get('Request', '')).replace(chr(160), ' ').strip()
                clean_req_key = req_key.replace('#', '').replace(' ', '')
                target_id = id_lookup.get(req_key) or id_lookup.get(clean_req_key)

                log_prefix = f"[{i + 1:03d}]"
                logger.info(f"{log_prefix} 處理中: {row.get('Date')} {req_key}")
                try:
                    status, message = execute_task(page, row, cfg.target_url, target_id)
                    row["Status"], row["Message"] = status, message

                    if status == "成功":
                        success_count += 1
                        logger.info(f"{log_prefix} 成功")
                    else:
                        logger.warning(f"{log_prefix} 失敗: {message}")

                except Exception as e:
                    row["Status"] = "失敗"
                    row["Message"] = f"最終異常: {str(e)[:50]}"
                    logger.error(f"{log_prefix} 嚴重故障: {e}")

                # 無論成功失敗，更新時間並寫入 Log
                row["ProcessedTime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file_handler.append_to_log(cfg.log_file, fieldnames, row, cfg.encoding)

            logger.success(f"【上傳工單】已完成。成功: {success_count} / 失敗: {total_pending - success_count}")

            # 單次執行紀錄（logs/upload_*.csv），logs/Log.csv 累積檔照舊寫入
            try:
                import csv as _csv
                cfg.run_dir.mkdir(parents=True, exist_ok=True)
                per_run = cfg.run_dir / f"upload_{datetime.datetime.now():%Y%m%d_%H%M%S}.csv"
                with open(per_run, 'w', encoding=cfg.encoding, newline='') as f:
                    w = _csv.DictWriter(f, fieldnames=fieldnames)
                    w.writeheader()
                    for idx in to_process_indices:
                        w.writerow(reader_list[idx])
                logger.trace(f"單次紀錄已輸出: {file_handler.display_path(per_run)}")
            except Exception as e:
                logger.warning(f"單次紀錄寫入略過: {e}")

        finally:
            browser.close()

    return True

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="iTop TimeSpent 批次上傳（無參數 = 舊行為，不彈窗；執行：python -m stages.stage3_upload）")
    ap.add_argument("--csv", default="", help="指定輸入 CSV，預設 settings.upload_input / iTop.csv")
    ap.add_argument("--ask-file", action="store_true", help="強制跳檔選對話框）")
    ap.add_argument("--interactive", action="store_true", help="登入失敗時詢問重設密碼（自動化勿用）")
    args = ap.parse_args()
    main(csv_override=args.csv, ask_file=args.ask_file, interactive=args.interactive)