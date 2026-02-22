@echo off
echo Fixing frontend installation...
echo.

if exist "node_modules" (
    echo Removing old installation...
    rmdir /s /q node_modules
)

if exist "package-lock.json" (
    del package-lock.json
)

echo Installing with legacy peer deps...
npm install --legacy-peer-deps

if errorlevel 1 (
    echo.
    echo Installation failed!
    pause
    exit /b 1
)

echo.
echo Success! Frontend is ready.
pause
