@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Starting Backend Service Test
echo ========================================
echo.

cd backend

echo [1/3] Checking Python syntax...
python -m py_compile app/services/chat_service.py
if %errorlevel% neq 0 (
    echo [ERROR] Syntax check failed
    pause
    exit /b 1
)
echo [OK] Syntax check passed
echo.

echo [2/3] Testing imports...
python -c "from app.services.chat_service import ChatService; from app.services.judge_service import JudgeService; print('[OK] All imports successful')"
if %errorlevel% neq 0 (
    echo [ERROR] Import test failed
    pause
    exit /b 1
)
echo.

echo [3/3] Starting backend service...
echo Press Ctrl+C to stop the service
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
