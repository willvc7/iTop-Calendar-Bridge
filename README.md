# iTop-Calendar-Bridge

> 自動化時數填報橋接工具：串接 Outlook 行事曆與 iTop，透過三段式管線（匯出 → 更新對照表 → 上傳），減少人工填報 TimeSpent 的時間與手誤風險。

## 核心特色

- **雙模操作**：桌面主控視窗（GUI，背景執行緒不凍結）與完整 CLI 指令。
- **三段式管線**：
  1. **階段一**：抓取指定區間 Outlook 行事曆並匯出 CSV（可同步寄給自己）。
  2. **階段二**：更新對照表並匯出僅含 Request/Title 的 CSV（可同步寄給自己）。
  3. **階段三**：上傳 CSV 自動建 iTop TimeSpent（上傳前檢查全過才跑，否則整批中止；登入失敗可即時更新密碼並自動接續）。
- **安全與稽核**：密碼只存系統認證管理員；輸出檔名自動加日期時間防覆蓋；累積總帳 `logs/Log.csv` 跨次對帳。

## 專案架構

```text
iTop-Calendar-Bridge/
├── app.py                  # GUI 主控視窗
├── ui/                     # 視窗子模組
├── stages/                 # 三段式業務管線，CLI 可單獨跑
├── core/                   # 共用核心
├── tests/                  # unittest 測試套件
├── config/                 # config.yaml（每人一份）+ config.example.yaml（範本）
├── data/                   # 輸出入
└── logs/                   # app_*.log + upload_*.csv + Log.csv（累積總帳）
```

## 快速開始

### 1. 環境需求與安裝

Python 3.13＋[`uv`](https://github.com/astral-sh/uv)：

```bash
cd iTop-Calendar-Bridge
uv sync
uv run playwright install chromium
```

### 2. 設定檔初始化

首次執行缺檔會自動產生預設 `config/config.yaml`，也可手動複製範本：

```bash
copy config\config.example.yaml config\config.yaml
```

設定單一來源 `config/config.yaml`（每人一份）；對照表單一來源 `data/itop_data.json`。

## 使用指南

### 主控視窗（GUI）

```bash
uv run python app.py   # 填 iTop 帳號，其他留預設；密碼首次上傳才會問
```

- **帳號區**：改帳號即時連動密碼狀態。
- **階段選單**：下拉選單＋日期點選器，選後才出現該階段欄位。
- **即時日誌**：右側面板直接呈現 loguru（含背景工作）。
- **免手動儲存**：所有欄位異動自動寫入；執行各階段時直接跳出檔案選擇對話框。

### 日常使用 CLI

#### 階段一：匯出行事曆

```bash
# 預設只存檔不寄信；要寄信加 --send-mail
uv run python -m stages.stage1_calendar --start "2026-09-01 00:00" --end "2026-09-10 23:59" --out data/raw_calendar.csv
```

#### 階段二：更新對照表並匯出清單

```bash
# 直接覆寫；檔名自動加日期時間防覆蓋；加 --send-mail 經 Outlook 寄給自己
uv run python -m stages.sync_requests --export-csv data/request_list.csv
```

> 人工步驟：開產出的 CSV 補 `Request` 欄。階段三上傳前會檢查：必填欄位空白或對照表無此 ID 就整批中止（列號會印在日誌），不會逐筆跳過。

#### 階段三：上傳至 iTop

```bash
# 防呆：人工上傳請加 --ask-file 強制手選檔；自動化不要加
uv run python -m stages.stage3_upload --ask-file --interactive
```

> 密碼管理：登入失敗時 GUI 會問是否清除舊密碼並重輸（成功自動接續）；CLI 加 `--interactive` 有同等效果；或按設定窗「清除已存密碼」。

## 測試與檢查

```bash
uv run python -m unittest discover tests   # 標準庫，免裝依賴
uvx ruff check .                           # 需網路裝 ruff；規則見 ruff.toml
```

## 打包發佈（exe，維護者用）

```bash
uv sync
pyinstaller app.spec            # 產出 dist/iTop-Calendar-Bridge/
# 準備 Chromium（二擇一）：
# set PLAYWRIGHT_BROWSERS_PATH=<repo>\ms-playwright 後 playwright install chromium，
# 或直接複製既有瀏覽器目錄為 ms-playwright\
# 再以 Inno Setup 編譯 installer.iss → installer-output\*-Setup-*.exe（單一安裝檔）
```

exe 版寫入 `%LOCALAPPDATA%/iTop-Calendar-Bridge`（config/logs/data），原始碼版行為不變。`dist/`、`*.exe`、`ms-playwright/` 不上 GitHub；成品可掛 GitHub Releases 發佈。