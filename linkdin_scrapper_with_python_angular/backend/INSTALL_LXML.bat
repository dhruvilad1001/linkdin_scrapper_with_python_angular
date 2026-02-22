@echo off
echo Installing lxml parser...
call venv\Scripts\activate
pip install lxml
echo.
echo lxml installed successfully!
echo Now restart the backend with START.bat
pause