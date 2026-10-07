import datetime
from loguru import logger

def process_itop(page, row, target_url, target_id):
    try:
        
        def to_dt(d, t):
            """ 日期處理：Date 取數字（20260922 / 2026-09-22 皆可）；Time 取數字補零（1300 / 900 / 9:00 皆可） """

            d_clean = ''.join(filter(str.isdigit, str(d)))
            t_digits = ''.join(filter(str.isdigit, str(t)))
            if len(t_digits) not in (3, 4):
                return f"Error: bad time '{t}' (need HHMM)"
            t_clean = t_digits.zfill(4)
            combined = d_clean + t_clean

            try:
                return datetime.datetime.strptime(combined, "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M:00")
            except ValueError as e:
                return f"Error: {e}"

        start_full = to_dt(row['Date'], row['StartTime'])
        end_full = to_dt(row['Date'], row['EndTime'])
        if start_full.startswith("Error") or end_full.startswith("Error"):
            logger.warning(f"日期格式錯誤，略過不送出：Date={row.get('Date')} Start={row.get('StartTime')} End={row.get('EndTime')}")
            return "失敗", f"日期格式錯誤: {start_full} / {end_full}"
        desc = str(row.get('Description', ''))
        act_id = str(target_id)

        # 前往目標頁面
        page.goto(target_url, wait_until="domcontentloaded")

        # 填表
        apply_btn = page.get_by_role("button", name="Apply")
        apply_btn.wait_for(state="visible")
        apply_btn.click()

        page.locator("input[name='attr_start_date']").fill(start_full)
        page.locator("input[name='attr_end_date']").fill(end_full)
        page.frame_locator('iframe[title*="Rich Text Editor"]').locator('body').fill(desc)
        page.locator("#label_2_activity_id").fill(act_id)

        menu_item = page.locator(".ui-menu-item", has_text=act_id).first
        menu_item.wait_for(state="visible", timeout=5000)
        menu_item.click()

        # 提交
        page.get_by_text("Create", exact=True).click()

        # 判斷成功
        try:
                success_msg = page.locator(".ibo-alert--body", has_text="created")
                success_msg.wait_for(state="visible", timeout=5000)

                # 獲取實際文字內容，紀錄在 Log 中方便後續核對
                actual_text = success_msg.inner_text().strip()

                return "成功", f"{actual_text}"

        except Exception:
            try:
                from core.paths import writable_root
                import datetime as _dt
                shot_dir = writable_root() / "logs"
                shot_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shot_dir / f"fail_{_dt.datetime.now():%Y%m%d_%H%M%S}.png"))
            except Exception:
                pass
            return "失敗", "提交後未偵測到成功訊息"

    except Exception as e:
        logger.error(f"處理失敗: {str(e)}")
        return "失敗", f"程式異常: {str(e)}"