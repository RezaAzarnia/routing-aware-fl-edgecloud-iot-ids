# Phase 6C Final Handoff — START HERE

Project: *A Routing-Aware Federated Learning Framework for Secure and Resilient Edge–Cloud IoT Intrusion Detection*.
Status: Phase 6C finished — **240/240 runs verified** (UNSW-NB15 120, CICIoT2023 120; 24 arms x seeds 12-16, 30 rounds), locked manifest `c648b93590494fcf260d5f143fe30eabbec28ee61c6b782dbe5f8550e0c1f267`, code fingerprint `1273afef07015ca873f658b4087e1b5b25124ce08d8422dfb16e0c92f686b524`. Validation-only: **no final-test data were used or are included.**

## Read in this order
1. `reports/Executive_Report_FA.md` (Persian summary) → `reports/Scientific_Results_EN.md` (full results)
2. `reports/Manuscript_Claim_Evidence_Matrix.md` and `reports/Limitations_and_Open_Issues.md`
3. `reports/Statistical_Analysis.md` (methods; n=5 ⇒ min p=0.0625, everything exploratory)

## Headline findings (details in reports)
- Robust (MAD filter + momentum) aggregation protects against 20% sign-flip: UNSW AUC 0.984 vs 0.887 undefended (last-round 0.983 vs 0.604).
- **Corrected is not better than Reference**: UNSW ΔAUC −0.0090, worse in 5/5 seeds (exact p=0.0625); CIC −0.0003 (noise). Corrected also diverges more often and costs more delay.
- No measurable accuracy benefit of routing/selection policy; coverage-aware selection improves participation fairness (Gini 0.73→0.49) without AUC gain.
- Gaussian noise costs AUC 0.042 (UNSW) / 0.003 (CIC); ε≈10 is a *diagnostic* RDP estimate, **not certified DP**.
- CIC is at an AUC ceiling (≈0.996) with known split limitations; not independent-device evidence.

## Layout
`tables/` all_runs, aggregate_metrics, paired_comparisons, ablation_results, round_metrics, network_metrics, client_selection, arm_definitions · `figures/{PDF,SVG,PNG,data}` Figures 1-12 + plotted CSV + captions · `scripts/` collect_results.py (needs the original results folder), statistical_analysis.py, generate_figures.py, verify_handoff.py (need only `tables/`) · `provenance/` manifest, run_inventory.csv, verification.json, checksums.sha256, environment.txt, repository_state.txt · `source_snapshot/` src, phase6c scripts, configs, manifest docs (reference copy, not the full repo) · `laptop_setup/`.

## Reproduce statistics and figures (no training, no original folder needed)
```
python -m venv venv ; venv\Scripts\activate ; pip install -r laptop_setup\requirements.txt
python scripts\verify_handoff.py --handoff . --regenerate
python scripts\statistical_analysis.py --handoff .
python scripts\generate_figures.py --handoff .
```

## Rules for continuing
1. **Never edit or overwrite** `results_phase6c/` (original outputs), `docs/phase6c/EXPERIMENT_MANIFEST.json`, `configs/phase6c/*.yaml`, or the source files in the code fingerprint. They are locked; any change invalidates the manifest.
2. Changing an algorithm, hyperparameter, split, threshold rule or seed set = a **new experiment version** with a new manifest (e.g. Phase 7) — never silently rerun under the Phase 6C name.
3. Unfavorable results (Corrected < Reference, divergences, undefended collapse) must be kept and reported.
4. The locked final-test files (UNSW testing CSV, CICIoT2023 `test.csv.gz`) must not be opened until you explicitly authorize one final evaluation using the locked operation in `source_snapshot/docs/phase6c/USER_GUIDE.md`; do it once, with no tuning on it.
5. Do not call Gaussian perturbation differential privacy without a valid accountant; the existing ε is diagnostic only.
6. Full per-run artifacts (models, predictions; hundreds of MB) are **not** in this zip; they remain in `results_phase6c/` on the original machine. All numbers here come from them and are checksummed against COMPLETE.json (`provenance/run_inventory.csv`).
