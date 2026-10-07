"""經本機 Outlook 把檔案寄給自己。"""
import os
from loguru import logger


def send_file_to_self(filepath: str, subject: str, body: str) -> bool:
    """寄送單一附件給目前 Outlook 登入者。成功回傳 True，失敗記 log 回傳 False。"""
    try:
        try:
            import pythoncom
            pythoncom.CoInitialize() 
        except Exception:
            pass
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        mail = outlook.CreateItem(0)
        try:
            mail.To = namespace.CurrentUser.Address
        except Exception:
            mail.To = ""
        mail.Subject = subject
        mail.Body = body
        mail.Attachments.Add(os.path.abspath(filepath))
        mail.Send()
        logger.success("郵件已寄出")
        return True
    except Exception as e:
        logger.error(f"寄送郵件失敗: {e}")
        return False


# ---- 階段一：行事曆匯出 ----
def calendar_subject(start_str: str, end_str: str) -> str:
    return f"行事曆匯出報表 ({start_str} ~ {end_str})"


def calendar_body() -> str:
    return "您好：\n\n這是自動匯出的 Outlook 行事曆 CSV 檔案，請查收。"


def mail_calendar_csv(filepath: str, start_str: str, end_str: str) -> bool:
    """寄出行事曆 CSV（階段一用）。"""
    return send_file_to_self(filepath, subject=calendar_subject(start_str, end_str), body=calendar_body())


# ---- 階段二：對照表匯出 ----
CACHE_MAIL_SUBJECT = "iTop 對照表匯出"


def cache_mail_body(count: int) -> str:
    return f"您好：\n\n這是自動匯出的 iTop 對照表 CSV（{count} 筆），請查收。"


def mail_cache_csv(filepath: str, count: int) -> bool:
    """寄出對照表 CSV（階段二 GUI/CLI 共用）。"""
    return send_file_to_self(filepath, subject=CACHE_MAIL_SUBJECT, body=cache_mail_body(count))