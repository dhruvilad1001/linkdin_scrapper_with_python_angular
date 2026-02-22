@echo off
REM Windows-specific installation script for LinkedIn Scraper Backend

echo ================================================
echo LinkedIn Scraper - Windows Installation
echo ================================================
echo.

REM Check if virtual environment exists
if exist "venv" (
    echo Virtual environment already exists
    echo Activating...
    call venv\Scripts\activate
) else (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        echo Make sure Python is installed and in PATH
        pause
        exit /b 1
    )
    echo Activating virtual environment...
    call venv\Scripts\activate
)

echo.
echo ================================================
echo Installing Dependencies
echo ================================================
echo.

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install packages one by one to avoid conflicts
echo.
echo Installing core packages...
pip install fastapi==0.109.0
pip install uvicorn==0.27.0
pip install python-multipart==0.0.9
pip install python-dotenv==1.0.1

echo.
echo Installing database packages...
pip install pymongo==4.6.1
pip install motor==3.4.0

echo.
echo Installing web scraping packages...
pip install selenium==4.17.2
pip install beautifulsoup4==4.12.3
pip install webdriver-manager==4.0.1

echo.
echo Installing data processing packages...
pip install pandas==2.2.0
pip install xlsxwriter==3.2.0
pip install openpyxl==3.1.2

echo.
echo Installing pydantic (this may take a moment)...
pip install pydantic==2.6.1
pip install pydantic-settings==2.2.1

echo.
echo Installing other utilities...
pip install requests==2.31.0

echo.
echo ================================================
echo Installation Complete!
echo ================================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo.
    echo [IMPORTANT] Please edit .env file with your credentials:
    echo   - LINKEDIN_EMAIL
    echo   - LINKEDIN_PASSWORD
    echo   - SECRET_KEY
    echo.
)

echo Installation successful!
echo.
echo Next steps:
echo 1. Edit .env file with your LinkedIn credentials
echo 2. Make sure MongoDB is running
echo 3. Run: python -m app.main
echo.

pause
