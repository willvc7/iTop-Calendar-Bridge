# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包設定（onedir）：產出 dist/iTop-Calendar-Bridge/ 資料夾。
再用 installer.iss 包成單一 Setup.exe。建置：pyinstaller app.spec
注意：dist/、*.exe 不上 GitHub（見 .gitignore）。

依賴現況（已驗證才敢這樣寫）：
- pandas / numpy / playwright：套件自帶 PyInstaller hook，無需額外處理。
- tkinter：PyInstaller 內建 hook。
- datas 為空：執行期不需要隨附資料檔（config 缺檔會用內建預設值自動播種）。
- console=False：GUI 不開黑窗（log 照寫 logs/，右側日誌區照顯示）。
- upx=False：UPX 常觸發防毒誤報，關掉。
"""

block_cipher = None


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # keyring 用 entry points 找後端，打包時抓不到；Windows 只需這一個。
        # 首包煙霧測試必須驗證「密碼存取」正常；若失敗再加 copy_metadata("keyring")。
        "keyring.backends.Windows",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="iTop-Calendar-Bridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="iTop-Calendar-Bridge",
)
