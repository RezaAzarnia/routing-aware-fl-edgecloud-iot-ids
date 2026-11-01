@echo off
setlocal
cd /d "%~dp0..\.."
echo Running malicious-client sweep...
python run.py --config configs/ciciot2023_core.yaml --suite attack_sweep --seeds 2,3,4 --skip-existing
if errorlevel 1 goto :error
echo Running failure-probability sweep...
python run.py --config configs/ciciot2023_core.yaml --suite failure_sweep --seeds 2,3,4 --skip-existing
if errorlevel 1 goto :error
echo Running heterogeneity sweep...
python run.py --config configs/ciciot2023_core.yaml --suite heterogeneity_sweep --seeds 2,3,4 --skip-existing
if errorlevel 1 goto :error
echo.
echo Key sweeps completed.
pause
exit /b 0
:error
echo.
echo ERROR: a sweep failed.
pause
exit /b 1
