import datetime
from pathlib import Path
from loguru import logger
import pandas as pd
import win32com.client
from core.files import display_path, with_timestamp


def _ensure_logger():
    try:
        from core.logging_setup import setup_logger
        setup_logger()
    except Exception:
        pass


def fetch_calendar_df(start_str: str, end_str: str) -> list[dict]:
    """抓取 Outlook 行程並轉為 Request 空白的列。"""
    start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M")
    end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M")

    logger.info(f"查詢區間：從 {start_dt} 到 {end_dt}")

    try:
        import pythoncom
        pythoncom.CoInitialize()  # 背景執行緒呼叫 COM 前先初始化
    except Exception:
        pass
    outlook = win32com.client.Dispatch("Outlook.Application")
    namespace = outlook.GetNamespace("MAPI")

    calendar = namespace.GetDefaultFolder(9)
    items = calendar.Items

    items.IncludeRecurrences = True
    items.Sort("[Start]")

    restriction = f"[Start] >= '{start_dt.strftime('%m/%d/%Y %H:%M')}' AND [Start] <= '{end_dt.strftime('%m/%d/%Y %H:%M')}'"
    restricted_items = items.Restrict(restriction)

    event_list = []

    for item in restricted_items:
        try:
            if getattr(item, 'Class', None) != 26:
                continue

            subject = getattr(item, 'Subject', '無主旨')
            item_start = getattr(item, 'Start', None)
            item_end = getattr(item, 'End', None)

            if not item_start or not item_end:
                continue

            start_naive = datetime.datetime(
                item_start.year, item_start.month, item_start.day,
                item_start.hour, item_start.minute, item_start.second
            )
            end_naive = datetime.datetime(
                item_end.year, item_end.month, item_end.day,
                item_end.hour, item_end.minute, item_end.second
            )

            date_str = start_naive.strftime("%Y%m%d")
            start_time_str = start_naive.strftime("%H%M")
            end_time_str = end_naive.strftime("%H%M")

            event_data = {
                "Request": "",
                "Date": date_str,
                "StartTime": start_time_str,
                "EndTime": end_time_str,
                "Description": subject
            }
            event_list.append(event_data)

        except Exception as sub_e:
            logger.warning(f"解析單一行程時發生小錯誤（已跳過）: {sub_e}")
            continue

    return event_list


def fetch_outlook_calendar(start_str: str, end_str: str, output_filename: str = "my_calendar.csv", send_mail=None):
    """
    從本機 Outlook 抓取指定起訖區間內的行事曆，轉格式後匯出 CSV，並寄送給自己。

    :param start_str: 開始時間，格式例如 "2026-09-01 00:00"
    :param end_str: 結束時間，格式例如 "2026-09-10 23:59"
    :param output_filename: 輸出的 CSV 檔名（保持舊預設 my_calendar.csv 不破壞現行）
    :param send_mail: None 則讀 settings.send_mail；False 僅匯出不寄（開發預設）；True 才真寄
    :return: (events, mailed)，mailed 表示是否真的寄出（無行程或未勾選則為 False）
    """
    _ensure_logger()
    logger.info("準備連線至 Outlook 應用程式")

    if send_mail is None:
        try:
            from core.settings import settings as _settings
            send_mail = bool(_settings.send_mail)
        except Exception:
            send_mail = False

    try:
        event_list = fetch_calendar_df(start_str, end_str)
        count = len(event_list)
        logger.success(f"共取得 {count} 筆行程")

        if event_list:
            out_path = Path(output_filename)
            if str(out_path.parent) not in ("", "."):
                out_path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(event_list)
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            logger.success(f"已匯出至：{display_path(output_filename)}")

            if not send_mail:
                return event_list, False

            logger.info("準備將檔案寄給自己")
            from core.mailer import mail_calendar_csv
            mailed = mail_calendar_csv(output_filename, start_str, end_str)
            return event_list, mailed

        logger.warning("在指定的區間內沒有找到任何行程")
        return [], False

    except Exception as e:
        logger.exception(f"發生未預期的錯誤: {e}")
        raise e

if __name__ == "__main__":
    import argparse

    try:
        from core.settings import settings as _s
        _default_out = with_timestamp(_s.calendar_output or "my_calendar.csv")
    except Exception:
        _default_out = with_timestamp("my_calendar.csv")

    ap = argparse.ArgumentParser(description="Outlook 行事曆匯出")
    ap.add_argument("--start", required=True, help="開始時間，格式 YYYY-MM-DD HH:MM")
    ap.add_argument("--end", required=True, help="結束時間，格式 YYYY-MM-DD HH:MM")
    ap.add_argument("--out", default=_default_out)
    ap.add_argument("--send-mail", dest="send_mail", action="store_true", default=None)
    ap.add_argument("--no-send-mail", dest="send_mail", action="store_false")
    args = ap.parse_args()

    _ensure_logger()
    logger.info("=== 啟動 Outlook 行事曆同步工具 ===")

    fetch_outlook_calendar(
        start_str=args.start,
        end_str=args.end,
        output_filename=args.out,
        send_mail=args.send_mail,
    )

    logger.info("=== 程式執行完畢 ===")