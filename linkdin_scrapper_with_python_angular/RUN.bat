@echo off
REM Simple Start Script

echo Starting LinkedIn Scraper...
echo.

REM Backend
cd backend
if not exist ".env" (
    copy .env.example .env
    echo Please edit backend\.env with your credentials
    notepad .env
    pause
)
start "Backend" cmd /k "venv\Scripts\activate & uvicorn app.main:app --reload"
cd ..

REM Frontend  
cd frontend
start "Frontend" cmd /k "npm start"
cd ..

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:4200
echo.
echo Two windows opened - keep them running
pause
