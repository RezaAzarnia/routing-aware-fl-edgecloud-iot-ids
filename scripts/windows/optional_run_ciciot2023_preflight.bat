@echo off
setlocal
cd /d "%~dp0..\.."
echo Running CICIoT2023 preflight (small clean run)...
python run.py --config configs/ciciot2023_preflight.yaml --suite single --seeds 2
if errorlevel 1 goto :error
echo.
echo Preflight completed. Check results\ciciot2023_preflight_v5
pause
exit /b 0
:error
echo.
echo ERROR: preflight failed.
pause
exit /b 1
