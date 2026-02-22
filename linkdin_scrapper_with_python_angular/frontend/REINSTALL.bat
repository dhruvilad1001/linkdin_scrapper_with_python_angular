@echo off
echo ================================================
echo Reinstalling Frontend with Correct TypeScript
echo ================================================
echo.

echo Step 1: Removing old installation...
if exist "node_modules" rmdir /s /q node_modules
if exist "package-lock.json" del package-lock.json

echo Step 2: Installing with correct TypeScript...
npm install --legacy-peer-deps

if errorlevel 1 (
    echo.
    echo Installation failed!
    pause
    exit /b 1
)

echo.
echo ================================================
echo Success! Frontend is ready.
echo ================================================
echo.
echo Now run: START.bat
pause
