@echo off
setlocal enabledelayedexpansion

echo ================================================
echo LinkedIn Profile Scraper
echo ================================================
echo.

REM Backend
echo [1/2] Backend
cd backend

if not exist "venv\Scripts\uvicorn.exe" (
    echo Installing backend, please wait...
    call install_windows.bat
    if errorlevel 1 exit /b 1
)

if not exist ".env" (
    copy .env.example .env
    echo.
    echo Edit backend\.env with your LinkedIn credentials
    notepad .env
    pause
    exit /b 1
)

set BACKEND_DIR=%CD%
start "Backend" cmd /k "cd /d "%BACKEND_DIR%" && venv\Scripts\activate && uvicorn app.main:app --reload"
echo Backend: http://localhost:8000
cd ..

REM Frontend
echo [2/2] Frontend
cd frontend

if not exist "node_modules\.bin\ng.cmd" (
    echo Installing frontend, please wait...
    npm install --legacy-peer-deps
    if errorlevel 1 (
        echo.
        echo Install Node.js from: https://nodejs.org/
        pause
        exit /b 1
    )
)

set FRONTEND_DIR=%CD%
start "Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm start"
echo Frontend: http://localhost:4200
cd ..

echo.
echo ================================================
echo Started! Opening in 30 seconds
echo ================================================
timeout /t 30 /nobreak >nul
start http://localhost:4200
