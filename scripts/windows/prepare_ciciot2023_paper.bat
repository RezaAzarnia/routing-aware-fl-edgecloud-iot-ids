@echo off
setlocal
cd /d "%~dp0..\.."
echo Preparing the reproducible CICIoT2023 paper sample.
echo This scans the official CSV release twice and may take a long time.
python prepare_ciciot2023.py ^
  --raw-dir data/CICIoT2023/raw_csv ^
  --output-dir data/CICIoT2023/prepared_paper ^
  --train-rows 1000000 ^
  --val-rows 200000 ^
  --test-rows 300000 ^
  --train-benign-fraction 0.50 ^
  --train-attack-sampling uniform_category ^
  --seed 2023 ^
  --force
if errorlevel 1 goto :error
echo.
echo Paper data preparation completed.
echo Keep preparation_metadata.json and split_manifest.csv for the article archive.
pause
exit /b 0
:error
echo.
echo ERROR: paper data preparation failed.
pause
exit /b 1
