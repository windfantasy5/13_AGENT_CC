@echo off
chcp 65001 >nul
echo ========================================
echo 混合检索系统测试
echo ========================================
echo.

cd /d "%~dp0backend"

echo 正在运行测试...
echo.

python tests/test_hybrid_search.py

echo.
echo ========================================
echo 测试完成
echo ========================================
pause
