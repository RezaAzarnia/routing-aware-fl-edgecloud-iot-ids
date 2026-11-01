# Phase 6C — how to run the five-seed experiments yourself (Windows PowerShell)

Open Windows PowerShell **in the repository folder** (`Desktop\New folder\routing-aware-fl-edgecloud-iot-ids`). Do not edit any file under `src/`, `scripts/phase6c/` or `configs/phase6c/` after the preflight passes
(the manifest locks them; the preflight will refuse a modified tree).

1. **Preflight + dry run (starts nothing):**
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\run_five_seeds.ps1`
2. **Start all 240 runs (sequential):**
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\run_five_seeds.ps1 -Execute`
   (add `-Detached` to keep it running even if you close the window)
3. **Live progress (read-only):**
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\monitor_five_seeds.ps1`
   (add `-Watch` for a refresh every 30 s)
4. **Resume after an interruption / failures:**
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\run_five_seeds.ps1 -Execute -Resume`
5. **Verify and summarise when finished:**
   `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\phase6c\validate_results.ps1`

Results: `results_phase6c\<dataset>\<arm>\seed_<n>\` (immutable once `COMPLETE.json` exists), logs in `results_phase6c\_logs\`,
state in `results_phase6c\_state\`, summaries in `results_phase6c\_summary\`.

The final test set is evaluated by a separate, explicitly authorised operation (`scripts\phase6c\final_test_evaluate.py`, see `docs/phase6b/FIVE_SEED_PROTOCOL.md` §9). Do not run it until all 240 runs validate and all decisions are frozen.
