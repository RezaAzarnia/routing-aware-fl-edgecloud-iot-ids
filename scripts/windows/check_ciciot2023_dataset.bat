@echo off
setlocal
cd /d "%~dp0..\.."
echo Checking CICIoT2023 raw CSV files...
python inspect_ciciot2023.py --raw-dir data/CICIoT2023/raw_csv --sample-files 3 --rows-per-file 50000
if errorlevel 1 goto :error
echo.
echo Dataset schema check passed.
pause
exit /b 0
:error
echo.
echo ERROR: schema check failed. Read the message above.
pause
exit /b 1
