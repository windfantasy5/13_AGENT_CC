@echo off
chcp 65001 >nul
echo ========================================
echo 测试改进后的文档上传功能
echo 同时构建BM25索引和向量数据库
echo ========================================
echo.

cd /d "%~dp0backend"

echo 正在运行测试...
echo.

python tests/test_improved_upload.py

echo.
echo ========================================
echo 测试完成
echo ========================================
pause
