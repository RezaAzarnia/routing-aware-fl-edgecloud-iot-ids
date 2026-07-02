@echo off
setlocal
cd /d "%~dp0..\.."
echo Running CICIoT2023 ablations with three seeds...
python run.py --config configs/ciciot2023_core.yaml --suite ablation --seeds 2,3,4 --skip-existing
if errorlevel 1 goto :error
echo.
echo Ablation runs completed.
pause
exit /b 0
:error
echo.
echo ERROR: ablation suite failed.
pause
exit /b 1
