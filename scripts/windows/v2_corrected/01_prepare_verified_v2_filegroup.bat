@echo off
setlocal
cd /d "%~dp0..\..\.."
set OUT=data/CICIoT2023/prepared_verified_v2_filegroup
if exist "%OUT%\train.csv.gz" (
  echo %OUT% already exists. Refusing to overwrite a verified dataset. Delete it manually if you really intend to regenerate.
  pause
  exit /b 1
)
echo Preparing CICIoT2023 file-group (capture-group aware) dataset. Historical prepared_paper is NOT touched.
python prepare_ciciot2023.py --raw-dir data/CICIoT2023/raw_csv --output-dir %OUT% --train-rows 1000000 --val-rows 200000 --test-rows 300000 --train-benign-fraction 0.50 --train-attack-sampling uniform_category --seed 2023 --split-mode file_group
if errorlevel 1 exit /b 1
pause
