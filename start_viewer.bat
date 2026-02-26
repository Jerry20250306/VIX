@echo off
chcp 65001 >nul
echo ===================================================
echo   正在啟動 VIX 驗證檢視器 (VIX Verification Viewer)
echo ===================================================
echo.
echo 正在檢查並安裝必要套件 (Flask, Pandas)...
pip install flask pandas >nul 2>&1
if %errorlevel% neq 0 (
    echo 安裝套件失敗，請手動執行: pip install flask pandas
    pause
    exit /b
)

:: 設定允許外部連線 (綁定 0.0.0.0)
set FLASK_HOST=0.0.0.0

echo.
echo ===================================================
echo   您的區域網路連線位址為: http://192.168.23.136:5000
echo ===================================================
echo.

:: 先嘗試關閉舊的 Server (避免重複開啟或 Port 被佔用)
taskkill /f /im python.exe /fi "WINDOWTITLE eq VIX_SERVER_WINDOW" >nul 2>&1
:: 或者是根據 Port 5000 來清理 (較為保險)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1

:: 啟動瀏覽器
start http://localhost:5000

:: 啟動 Python Server (設定視窗標題方便後續清理)
title VIX_SERVER_WINDOW
python Viewer/app.py

pause
