@echo off
setlocal
cd /d "%~dp0..\.."
echo Running one-seed clip-norm screen on CICIoT2023...
python run.py --config configs/ciciot2023_clip_screen.yaml --suite clip_sweep --seeds 2 --skip-existing
if errorlevel 1 goto :error
python apply_clip_recommendation.py
if errorlevel 1 goto :review
echo.
echo Clip recommendation applied to CICIoT2023 configs.
pause
exit /b 0
:review
echo.
echo The clip screen completed but did not produce an automatically usable verdict.
echo Inspect results\ciciot2023_clip_screen_v5\CLIP_SWEEP_REPORT.json
pause
exit /b 2
:error
echo.
echo ERROR: clip screen failed.
pause
exit /b 1
