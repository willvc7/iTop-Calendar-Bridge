from pathlib import Path
from playwright.sync_api import sync_playwright
from core.credentials import login_itop
from loguru import logger
from core.settings import settings
from core.files import display_path, with_timestamp
from core.paths import writable_root

def scrape_request_list(page, url):
    page.goto(url)
    page.wait_for_selector("table tbody tr td", timeout=10000)

    data = page.locator("table tbody tr").evaluate_all("""
        rows => rows.map(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length === 0) return null;

            const request = cells[0];
            const requestID = request.querySelector('span.object-ref');
            const title = cells[1];

            return {
                Request: request.innerText.trim(),
                ID: requestID ? requestID.getAttribute('title') : "",
                Title: title.innerText.trim()
            };
        }).filter(item => item !== null)
    """)
    return data


def resolve_cache_output(out: str = "") -> "Path":
    """新路徑優先；預設寫入 settings.request_cache，同事共用 data/"""
    from pathlib import Path as _Path
    if out:
        return _Path(out)
    try:
        return settings.resolve(settings.request_cache)
    except Exception:
        return _Path("itop_data.json")


def update_request_cache(out: str = "", parent=None):
    """抓取 Request→Activity ID 對照表並存檔。回傳筆數；寫檔失敗回傳 -1；登入失敗回傳 "auth_failed"。"""
    import json as _json
    output = resolve_cache_output(out)
    urls = [item.strip() for item in settings.request_list.split(',') if item.strip()]
    all_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.headless, slow_mo=500)
        page = browser.new_page()
        try:
            if not login_itop(page, parent=parent):
                logger.error("登入失敗，取消更新對照表")
                return "auth_failed"
            for target_url in urls:
                try:
                    page_data = scrape_request_list(page, f"{settings.itop_url}?{target_url}")
                    all_results.extend(page_data)
                except Exception as e:
                    logger.error(f"抓取 {target_url} 時出錯: {e}")
        finally:
            browser.close()

    for item in all_results:
        if item.get('ID'):
            item['ID'] = item['ID'].replace(" ", "").replace("::", " #")

    # 直接覆寫（不做新舊合併；同 Request 去重保序，取第一筆）
    seen = set()
    deduped = []
    for item in all_results:
        req = str(item.get('Request', '')).strip()
        if req and req not in seen:
            seen.add(req)
            deduped.append(item)

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            _json.dump(deduped, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"寫入對照表失敗 {display_path(output)}: {e}")
        return -1

    return len(deduped)


def export_cache_csv(csv_path: str = "") -> int | None:
    """把對照表匯出成僅含 Request/Title 的 CSV（給 user 人工查閱）。回傳筆數，失敗回傳 None。"""
    import csv as _csv
    from pathlib import Path as _Path
    cache_file = settings.resolve_request_cache()
    try:
        import json as _json
        with open(cache_file, 'r', encoding='utf-8') as f:
            entries = _json.load(f) or []
    except Exception as e:
        logger.error(f"讀取對照表失敗 {display_path(cache_file)}: {e}")
        return None

    out = _Path(csv_path) if csv_path else _Path(with_timestamp(str(writable_root() / "data" / "request_list.csv")))
    try:
        if str(out.parent) not in ("", "."):
            out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', encoding='utf-8-sig', newline='') as f:
            w = _csv.DictWriter(f, fieldnames=["Request", "Title"])
            w.writeheader()
            for item in entries:
                w.writerow({"Request": item.get("Request", ""), "Title": item.get("Title", "")})
    except Exception as e:
        logger.error(f"對照表 CSV 匯出失敗 {display_path(out)}: {e}")
        return None

    logger.success(f"共取得 {len(entries)} 筆 Request")
    logger.success(f"已匯出至：{display_path(out)}")
    return len(entries)


if __name__ == "__main__":
    import argparse as _argparse
    _ap = _argparse.ArgumentParser(description="更新 iTop Request 對照表（執行：python -m stages.sync_requests）")
    _ap.add_argument("--out", default="", help="輸出 JSON 路徑，預設 settings.request_cache")
    _ap.add_argument("--export-csv", default="", help="加匯出僅含 Request/Title 的 CSV（預設 data/request_list.csv）")
    _ap.add_argument("--send-mail", dest="send_mail", action="store_true", help="將匯出的 CSV 經 Outlook 寄給自己")
    _args = _ap.parse_args()
    n = update_request_cache(out=_args.out)
    if isinstance(n, int) and n >= 0 and _args.export_csv is not None and (_args.export_csv or _args.send_mail):
        csv_path = _args.export_csv or with_timestamp(str(writable_root() / "data" / "request_list.csv"))
        m = export_cache_csv(csv_path)
        if m is not None and _args.send_mail:
            from core.mailer import mail_cache_csv
            mail_cache_csv(csv_path, m)