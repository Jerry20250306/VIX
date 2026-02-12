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

echo.
echo 1. 啟動 Python 後端伺服器...
echo 2. 等待伺服器就緒...
echo 3. 自動開啟瀏覽器...
echo.

:: 啟動瀏覽器 (稍等 2 秒讓 Server 先跑起來)
timeout /t 2 >nul
start http://localhost:5000

:: 啟動 Python Server
python Viewer/app.py

pause
