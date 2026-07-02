@echo off
setlocal
cd /d "%~dp0..\.."
echo Preparing a small reproducible CICIoT2023 pilot sample...
python prepare_ciciot2023.py ^
  --raw-dir data/CICIoT2023/raw_csv ^
  --output-dir data/CICIoT2023/prepared_pilot ^
  --train-rows 100000 ^
  --val-rows 20000 ^
  --test-rows 30000 ^
  --train-benign-fraction 0.50 ^
  --train-attack-sampling uniform_category ^
  --seed 2023 ^
  --force
if errorlevel 1 goto :error
echo.
echo Pilot data preparation completed.
pause
exit /b 0
:error
echo.
echo ERROR: pilot data preparation failed.
pause
exit /b 1
