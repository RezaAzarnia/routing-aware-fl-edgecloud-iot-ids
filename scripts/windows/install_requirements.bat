@echo off
setlocal
cd /d "%~dp0..\.."
echo Installing Python requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo.
echo Installation completed.
pause
exit /b 0
:error
echo.
echo ERROR: installation failed. Make sure Python 3.10+ is installed and on PATH.
pause
exit /b 1
