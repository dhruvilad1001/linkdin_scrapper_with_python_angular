@echo off
echo Starting Backend...
call venv\Scripts\activate
uvicorn app.main:app --reload
pause
