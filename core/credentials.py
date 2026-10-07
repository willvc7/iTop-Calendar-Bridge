from playwright.sync_api import Page, expect
from loguru import logger
import keyring

def _prompt_gui_input(title: str, prompt: str, is_password: bool = False, parent=None) -> str:
    """封裝 Tkinter 呼叫，確保資源回收"""
    try:
        import tkinter as tk
        from tkinter import simpledialog
    except Exception as e:
        logger.error(f"無法開啟輸入框（缺少 GUI 環境）: {e}")
        return ""

    if parent is not None:
        try:
            parent.update()
        except Exception:
            pass
        try:
            val = simpledialog.askstring(title, prompt, show='*' if is_password else None, parent=parent)
        except Exception as e:
            logger.error(f"開啟輸入框失敗: {e}")
            return ""
        return val.strip() if val else ""

    try:
        root = tk.Tk()
    except Exception as e:
        logger.error(f"無法開啟輸入框（缺少 GUI 環境）: {e}")
        return ""
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass

    try:
        val = simpledialog.askstring(title, prompt, show='*' if is_password else None)
    except Exception as e:
        logger.error(f"開啟輸入框失敗: {e}")
        return ""
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return val.strip() if val else ""

def ensure_username(parent=None) -> str:
    """username 為空時彈框補上並寫回 config"""
    from core.settings import settings
    if settings.username and settings.username.strip():
        return settings.username.strip()
    val = _prompt_gui_input("首次設定", "請輸入 iTop 帳號：", parent=parent)
    if val:
        settings.username = val.strip()
        try:
            settings.save()
        except Exception as e:
            logger.warning(f"帳號暫存記憶體，寫檔失敗: {e}")
        logger.info("已設定 iTop 帳號")
        return settings.username
    return ""

def clear_saved_password() -> None:
    """密碼錯誤時清除舊憑證，下次自動重問"""
    from core.settings import settings
    try:
        if settings.username:
            keyring.delete_password(settings.itop_url, settings.username)
            logger.info("已清除舊密碼，下次將重新輸入")
    except Exception:
        pass

def ask_password_reset(parent=None) -> bool:
    """登入失敗時問是否重設密碼（只在互動模式呼叫，自動化不彈窗）"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        if parent is not None:
            return bool(messagebox.askyesno("登入失敗", "帳號或密碼錯誤（可能已變更密碼）。\n是否清除舊密碼並重新輸入？", parent=parent))
        try:
            root = tk.Tk()
        except Exception as e:
            logger.error(f"無法開啟確認框（缺少 GUI 環境）: {e}")
            return False
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        try:
            ans = messagebox.askyesno("登入失敗", "帳號或密碼錯誤（可能已變更密碼）。\n是否清除舊密碼並重新輸入？")
        finally:
            try:
                root.destroy()
            except Exception:
                pass
        return bool(ans)
    except Exception:
        return False

def get_credentials(parent=None):
    """取得憑證並確保配置同步"""
    from core.settings import settings
    login_url = settings.itop_url
    username = ensure_username(parent=parent)
    if not username:
        logger.error("尚未設定帳號")
        return None, None, None
    password = keyring.get_password(login_url, username)
    if not password:
        password = _prompt_gui_input("安全驗證", f"{username} 請輸入密碼：", is_password=True, parent=parent)
        if not password:
            logger.error("使用者取消輸入")
            return None, None, None

        keyring.set_password(login_url, username, password)
        logger.info("密碼已安全儲存至 Windows 認證管理員")

    return login_url, username, password

def ensure_credentials(parent=None) -> bool:
    """主執行緒預檢：帳號不存在則彈框補，密碼不存在則彈框要；回傳是否齊備"""
    login_url, username, password = get_credentials(parent=parent)
    return bool(all([login_url, username, password]))

def login_itop(page: Page, parent=None) -> bool:
    """ 執行 iTop 登入邏輯 """

    login_url, username, password = get_credentials(parent=parent)

    if not all([login_url, username, password]):
        return False

    try:
        # 導向登入頁
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)

        # 填寫資料
        page.locator("input[name='auth_user']").fill(username)
        page.locator("input[name='auth_pwd']").fill(password)

        # 提交並等待導向
        page.locator("input[type='submit']").click()

        # 等待成功進入主頁面
        user_menu = page.locator("#ibo-navigation-menu")

        try:
            expect(user_menu).to_be_visible(timeout=10000)
            logger.info("iTop 登入成功")
            return True
        except AssertionError:
            logger.error(f"{username} iTop 登入失敗：請檢查帳號密碼是否正確")
            return False

    except Exception as e:
        logger.exception(f"登入過程發生異常: {str(e)}")
        return False


def login_itop_interactive(page: Page, parent=None) -> bool:
    """互動版登入：失敗時詢問是否清除舊密碼並重試一次（自動化請續用 login_itop）"""
    if login_itop(page, parent=parent):
        return True
    try:
        if ask_password_reset(parent=parent):
            clear_saved_password()
            return login_itop(page, parent=parent)
    except Exception:
        pass
    return False