@echo off
setlocal
cd /d "%~dp0..\..\.."
echo Bounded smoke tests. Official test files are NOT used (see configs/smoke_*.yaml).
python run.py --config configs/smoke_unsw_groupdisjoint.yaml --suite single --seeds 1
if errorlevel 1 exit /b 1
python run.py --config configs/smoke_ciciot_filegroup.yaml --suite single --seeds 1
if errorlevel 1 exit /b 1
pause
