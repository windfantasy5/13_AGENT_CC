@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Testing Judge Service
echo ========================================
echo.

cd backend
python tests/test_judge_service.py

echo.
echo ========================================
echo Test Complete
echo ========================================
pause
