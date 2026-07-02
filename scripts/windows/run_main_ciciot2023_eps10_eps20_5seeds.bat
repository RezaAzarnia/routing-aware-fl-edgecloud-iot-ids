@echo off
setlocal
cd /d "%~dp0..\.."
echo Running Proposed Full epsilon 10 with five seeds...
python run.py --config configs/ciciot2023_eps10.yaml --suite single --seeds 2,3,4,5,6 --skip-existing
if errorlevel 1 goto :error
echo Running Proposed Full epsilon 20 with five seeds...
python run.py --config configs/ciciot2023_eps20.yaml --suite single --seeds 2,3,4,5,6 --skip-existing
if errorlevel 1 goto :error
echo.
echo Main five-seed runs completed.
pause
exit /b 0
:error
echo.
echo ERROR: a main run failed. Existing completed seeds can be resumed with this BAT.
pause
exit /b 1
