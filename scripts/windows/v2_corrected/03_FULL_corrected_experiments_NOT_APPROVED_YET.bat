@echo off
setlocal
cd /d "%~dp0..\..\.."
echo These are the full five-seed corrected runs. They must only be started after the data and smoke gates are reviewed.
choice /m "Start full corrected experiments"
if errorlevel 2 exit /b 0
python run.py --config configs/unsw_nb15_groupdisjoint_v2.yaml --suite core --seeds 2,3,4,5,6 --skip-existing
python run.py --config configs/ciciot2023_filegroup_v2_eps10.yaml --suite single --seeds 2,3,4,5,6 --skip-existing
python run.py --config configs/ciciot2023_filegroup_v2_eps20.yaml --suite single --seeds 2,3,4,5,6 --skip-existing
pause
