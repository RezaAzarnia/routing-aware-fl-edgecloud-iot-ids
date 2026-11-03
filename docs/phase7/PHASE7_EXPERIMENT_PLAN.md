# Phase 7 experiment plan (PROPOSED — nothing has been run; awaiting explicit approval)

## Do we need to rerun all 240 runs? No.
- The code change is default-off and bit-identical for historical arms (verified on the reference and corrected configs: 81 numeric columns and model bytes identical). Phase 6C results therefore remain **valid and reusable** as historical, exploratory comparators; no defect found invalidates them.
- They cannot serve as the confirmatory control for the new variant: seeds 12-16 were inspected and motivated the guard. A fair test needs **new seeds 17-21** and matched controls re-run on those seeds, under the same code.

## Minimum matrix (manifest `docs/phase7/EXPERIMENT_MANIFEST.json`, sha256 `a402c990…`)
8 arms × 5 seeds (17-21) = **40 runs on UNSW-NB15 (mandatory)**; the same 40 on CICIoT2023 are **optional** (CIC is at an AUC ceiling and costs ~70% of the time).

| arm | role |
|---|---|
| reference, corrected | unchanged historical comparators (re-run on new seeds) |
| p7_corrected_guard | new: corrected + abstain if <3 real updates |
| fail0p3_reference, fail0p3_corrected | comparators under 30% failures (where starvation is worst) |
| fail0p3_p7_corrected_guard | new: guard under 30% failures (**primary contrast vs fail0p3_corrected**) |
| ctl_delivery_coupled | channel-only control (reference + packet-coupled delivery) |
| p7_delivery_guard | new: guard isolated from the rest of the corrected bundle |

Not re-run (and not needed for this question): the other 16 arms (undefended baselines, Gaussian, imputation/momentum/weighting controls, natural-attacker arms). Mandatory vs optional: the 40 UNSW runs are mandatory; CIC (40) is optional confirmation; everything else is out of scope.

## Pre-registration (frozen when you approve; seeds 12-16 are exploratory)
- Primary: UNSW, `fail0p3_p7_corrected_guard` vs `fail0p3_corrected`, paired by seed: (a) collapse count (last-round AUC <0.90 or max loss >100), (b) mean paired Δ last-round AUC.
- Guard "supported" only if collapses do not increase, mean Δ last AUC ≥ +0.005 with the guarded arm better in ≥4/5 seeds, and best-checkpoint AUC drops ≤0.002. Otherwise report "not supported". n=5 cannot reach p<0.05 (min exact p=0.0625): conclusions rest on effect size and consistency, with exact Wilcoxon/sign-flip and t-intervals as description.
- Secondary: best AUC, F1, recall_adr, FPR; malicious accepted and honest rejected by number of real updates; abstained rounds; selection Gini, delay, update delivery ratio; reference-vs-corrected re-test on the new seeds.
- Reported always: best checkpoint **and** last round; all unfavorable runs kept; no final-test data; Gaussian ≠ certified DP.

## Expected execution time (CPU i5-14400F, sequential, from verified Phase 6C mean durations)
| tier | runs | est. time |
|---|---|---|
| mandatory UNSW | 40 | **≈ 0.96 h (~58 min)** |
| optional CIC | 40 | ≈ 2.19 h |
| both | 80 | ≈ 3.2 h |
| (full Phase 6C rerun, for comparison) | 240 | 11.35 h measured |
GPU is not used (benchmarked slower for this workload).

## Commands (nothing runs without `--execute`)
```powershell
# one-time (already done on this branch): python scripts\phase7\build_phase7.py
$PY = "C:\Users\R_Azarnia\Desktop\IoT-FL-Recovery\venv\Scripts\python.exe"
& $PY scripts\phase7\run_phase7.py plan                         # queue + time estimate
& $PY scripts\phase7\run_phase7.py run                          # dry run + preflight
& $PY scripts\phase7\run_phase7.py run --execute                # mandatory UNSW tier (40 runs, live per-round logs)
& $PY scripts\phase7\run_phase7.py run --execute --include-optional   # + CIC tier
& $PY scripts\phase7\run_phase7.py run --execute --resume       # after any interruption (verified runs are skipped)
& $PY scripts\phase7\run_phase7.py status
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\live\monitor_live.ps1 -Watch -Results results_phase7 -Manifest docs\phase7\EXPERIMENT_MANIFEST.json
```
Interruption safety: one immutable directory per run; a run counts only after `COMPLETE.json` + artifact-hash verification; incomplete directories are moved to `results_phase7/_attempts/`, never deleted; `--stop-after-minutes N` avoids starting a run that would exceed a time budget; a lock file prevents two runners and the runner refuses to start while the Phase 6C runner is active.
