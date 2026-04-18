@echo off
echo ========================================
echo Testing AI Agent System
echo ========================================
echo.

echo [1/4] Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found
    exit /b 1
)
echo OK
echo.

echo [2/4] Checking backend dependencies...
cd backend
python -c "import fastapi, uvicorn, sqlalchemy, langchain, chromadb; print('All backend dependencies OK')"
if %errorlevel% neq 0 (
    echo ERROR: Backend dependencies missing
    exit /b 1
)
cd ..
echo.

echo [3/4] Checking frontend build...
cd frontend
if not exist "dist\index.html" (
    echo Frontend not built, building now...
    call npm run build
    if %errorlevel% neq 0 (
        echo ERROR: Frontend build failed
        exit /b 1
    )
)
echo Frontend build OK
cd ..
echo.

echo [4/4] Checking configuration files...
if not exist "backend\.env" (
    echo ERROR: backend\.env not found
    exit /b 1
)
echo Configuration OK
echo.

echo ========================================
echo All checks passed!
echo ========================================
echo.
echo To start the system:
echo   1. Start backend: cd backend ^&^& uvicorn app.main:app --reload --port 8000
echo   2. Start frontend: cd frontend ^&^& npm run dev
echo.
