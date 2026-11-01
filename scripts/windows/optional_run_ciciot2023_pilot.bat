@echo off
setlocal
cd /d "%~dp0..\.."
echo Running one-seed CICIoT2023 full-scenario pilot...
python run.py --config configs/ciciot2023_pilot.yaml --suite single --seeds 2
if errorlevel 1 goto :error
echo.
echo Pilot completed. Review results\ciciot2023_pilot_v5 before paper runs.
pause
exit /b 0
:error
echo.
echo ERROR: pilot failed.
pause
exit /b 1
