@echo off
setlocal
cd /d "%~dp0..\.."
echo Running CICIoT2023 baseline suite with five seeds...
python run.py --config configs/ciciot2023_core.yaml --suite baselines_only --seeds 2,3,4,5,6 --skip-existing
if errorlevel 1 goto :error
echo.
echo Baseline runs completed.
pause
exit /b 0
:error
echo.
echo ERROR: baseline suite failed. Rerun to resume completed work.
pause
exit /b 1
