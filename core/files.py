import os
import csv
import json
import datetime
from pathlib import Path
from loguru import logger

def display_path(p) -> str:
    """日誌/UI 顯示用路徑"""
    return Path(p).as_posix()

def with_timestamp(path: str) -> str:
    """輸出檔名自動加 _YYYYMMDD_HHMMSS。"""
    import re
    pp = Path(path)
    if re.search(r"_\d{8}_\d{6}$", pp.stem):
        return pp.as_posix()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return pp.with_name(f"{pp.stem}_{ts}{pp.suffix}").as_posix()

def load_csv_data(filepath, encoding):
    """檢查並讀取 CSV 資料"""
    if not os.path.exists(filepath):
        logger.error(f"找不到指定的 CSV 檔案: {display_path(os.path.abspath(filepath))}")
        return None

    # 檢查檔案是否被佔用 (嘗試以讀寫模式打開)
    try:
        with open(filepath, 'r+', encoding=encoding) as f:
            pass
    except PermissionError:
        logger.error(f"權限錯誤：{display_path(filepath)} 正被其他程式開啟中")
        return None

    try:
        with open(filepath, 'r', encoding=encoding, newline='') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.error(f"讀取 CSV 失敗: {e}")
        return None

def validate_itop_format(reader_list, required_fields):
    """驗證 CSV 必要欄位"""
    if not reader_list:
        return False

    fieldnames = reader_list[0].keys()

    for col in required_fields:
        if col not in fieldnames:
            logger.critical(f"CSV 格式錯誤：缺少必要欄位 '{col}'")
            return False
    return True

def validate_upload_rows(indexed_rows, required_fields, lookup) -> tuple:
    """上傳前檢查。"""
    blanks = []
    unknown = []
    for row_no, row in indexed_rows:
        req = str(row.get("Request", "")).replace(chr(160), " ").strip()
        if not req:
            blanks.append((row_no, "Request"))
            continue
        for col in required_fields:
            if col == "Request":
                continue
            if not str(row.get(col, "")).strip():
                blanks.append((row_no, col))
        clean_req = req.replace("#", "").replace(" ", "")
        if req not in lookup and clean_req not in lookup:
            unknown.append((row_no, req))
    return blanks, unknown

def load_id_lookup(filepath):
    """讀取 JSON 並建立預處理過的 lookup table。"""
    if not os.path.exists(filepath):
        logger.error(f"找不到對照表: {display_path(filepath)}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        lookup = {}
        for item in json_data:
            req = str(item.get('Request', '')).replace(chr(160), ' ').strip()
            if req:
                lookup[req] = item['ID']
                clean_req = req.replace('#', '').replace(' ', '')
                lookup[clean_req] = item['ID']
        return lookup
    except Exception as e:
        logger.error(f"JSON 讀取異常: {e}")
        return None

def append_to_log(filename, fieldnames, row, encoding):
    """使用 Append 模式寫入單筆進度，確保 UTF-8-BOM 相容性"""
    file_exists = os.path.isfile(filename)
    with open(filename, 'a', encoding=encoding, newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)