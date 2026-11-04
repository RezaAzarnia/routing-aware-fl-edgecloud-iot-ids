# Continuing on the laptop
- Manuscript revision: use `reports/Manuscript_Claim_Evidence_Matrix.md` as the checklist; every number can be traced to `tables/*.csv` and `figures/data/*.csv`. Figure captions are in `figures/data/*.caption.txt`.
- Edit figures: change `scripts/generate_figures.py` (reads only `tables/`) and rerun; SVGs are text-editable.
- Retrieve the original full results only if needed (copy `results_phase6c/` from the original PC; never modify it). To re-verify from originals: `python scripts/collect_results.py --repo <original repo> --out <new empty dir>` and compare tables.
- New experiments (e.g. a corrected-v3 or leave-one-out ablations) require a new manifest/version and the repo (`git` branch `feature/gpu-live-logging`, commit in `provenance/repository_state.txt`); `source_snapshot/` is only a reference copy.
- Final-test evaluation: not performed; requires explicit authorization (see README rule 4).
