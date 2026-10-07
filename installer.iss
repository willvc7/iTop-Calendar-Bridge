; Inno Setup 6 腳本：把 dist\iTop-Calendar-Bridge\ + ms-playwright\ 包成單一 Setup.exe。
;
; 建置機前置作業（做一次）：
;   1. uv sync
;   2. pyinstaller app.spec
;   3. 準備 Chromium（擇一）：
;      a. set PLAYWRIGHT_BROWSERS_PATH=<repo>\ms-playwright
;         playwright install chromium
;      b. 把既有瀏覽器目錄複製為 ms-playwright\
;      結構應為：ms-playwright\chromium-<版本>\chrome-win\...
;   4. 以 Inno Setup 編譯本檔 → installer-output\iTop-Calendar-Bridge-Setup-*.exe
;
; 注意：Setup.exe、dist\、ms-playwright\ 不上 GitHub（見 .gitignore）。
; 本安裝包為 per-user 安裝（免管理員權限），與 exe 寫入 %LOCALAPPDATA% 的設計一致。

#define MyAppName "iTop-Calendar-Bridge"
#define MyAppVersion "0.1.0"
#define MyAppExeName "iTop-Calendar-Bridge.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
PrivilegesRequired=lowest
OutputDir=installer-output
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "ms-playwright\*"; DestDir: "{app}\ms-playwright"; Flags: recursesubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "建立桌面捷徑"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即啟動"; Flags: nowait postinstall skipifsilent unchecked
