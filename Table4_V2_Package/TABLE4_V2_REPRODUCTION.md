# Table 4 v2: reproduction guide

Everything below runs on CPU (Python 3.11, torch 2.15.0+cpu, numpy 2.4.6, pandas 2.3.3, scikit-learn, PyYAML, scipy, matplotlib). The reserved test files are never opened by any step.

## 0. Code and branch
* Branch `table4-controlled-v2` (not pushed). Code commit `cc14511` (independent path-assignment control, arm configs, orchestrator, tests); manifest commit `b5e0430` (locked 40-run manifest, code fingerprint `c8cf7c0c52c34ad0…`).
* New switch: `routing.path_policy: default | routed | random` (default = historical behaviour; verified bit-identical by golden fixtures generated from the unmodified code, `tests/test_table4_path_policy.py`). `random` draws each (round, client) edge from a dedicated stream derived from (seed, round, client) and never consumes the shared network generator, so link evolution, client selection, attackers and failure draws are identical to the routed run.

## 1. Environment and data
1. Create a Python 3.11 environment with `requirements.txt` (torch CPU build).
2. Data (not redistributed): `data/UNSW_NB15_training-set.csv` and the file-group-prepared CICIoT2023 set `data/CICIoT2023/prepared_verified_v2_filegroup/` (train/validation/preparation_metadata only are needed). Their hashes are recorded in `docs/phase6c/EXPERIMENT_MANIFEST.json` and re-verified by the preflight.

## 2. Build, verify, run
```
python scripts/table4_v2/build_configs.py            # configs/table4_v2/*.yaml + docs/table4_v2/TABLE4_V2_METHOD_MATRIX.csv (refuses to overwrite)
python scripts/table4_v2/build_manifest.py           # docs/table4_v2/EXPERIMENT_MANIFEST.json (refuses to overwrite; run BEFORE training)
python scripts/table4_v2/orchestrator.py preflight   # manifest hash, code fingerprint, config hashes, dataset hashes, environment, no active runner
python scripts/table4_v2/orchestrator.py run         # 40 runs, resumable; add --resume after an interruption
python scripts/table4_v2/orchestrator.py status      # verified/pending/failed counts
python scripts/table4_v2/analyse.py                  # Table4_V2_Package/ (refuses to overwrite a non-empty directory)
```
Safety properties of the runner: one global runner lock and one lock per run id (a second process cannot start a run that a live process holds; stale locks of dead processes are replaced and logged); an unfinished or failed run directory is moved aside as `*.incomplete.<utc>` / `*.failed.<utc>` and never reused or mixed with a new attempt; a run is complete only if `COMPLETE.json` and all hashed artifacts verify and `run_metadata.json` records `test_data_loaded=false`, 30 executed rounds and satisfied metric-accounting invariants; all state and logs are under `results_table4_controlled_v2/` (`_state`, `_logs`).

## 3. Tests
`pytest -q` (215 passed, 1 skipped before the manifest existed; the skipped manifest-integrity test runs once the manifest is present). Relevant: `tests/test_table4_path_policy.py` (golden backward compatibility of network decisions and of tiny end-to-end runs for three historical configurations; single-factor behaviour of the new switch), `tests/test_table4_v2_protocol.py` (each arm differs from its locked parent only in the declared fields; manifest integrity; lock and resume semantics).

## 4. Reused (not re-run) evidence
Existing locked Phase 6C runs (`results_phase6c/`, manifest `docs/phase6c/EXPERIMENT_MANIFEST.json`) are reused as comparators: `scenario_fedavg_random`, `scenario_fedavg_topk`, `robust_random_no_imputation`, `reference`, `reference_gaussian`. Their detection metrics are taken from the audited ledger (`Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv`), which applies the threshold/tie correction; the new runs already use the corrected rule. Average precision of reused runs comes from the original run output (not audited).

## 5. Where each deliverable comes from
| File | Produced by |
|---|---|
| `TABLE4_V2_PER_SEED.csv`, `TABLE4_V2_SUMMARY.csv`, `TABLE4_V2_PAIRED_EFFECTS.csv`, `TABLE4_V2_FINAL_TABLE.tex`, `TABLE4_V2_PROVENANCE.json` | `scripts/table4_v2/analyse.py` |
| `TABLE4_V2_METHOD_MATRIX.csv` | `scripts/table4_v2/build_configs.py` |
| `TABLE4_V2_EXPERIMENT_QA.md` | automatic checks of `analyse.py` plus the narrative review |

## 6. Known limitations to carry into the manuscript
Five paired seeds (minimum exact two-sided sign-flip p = 0.0625); validation-only evidence on one simulated network and one attack family; the per-event delivery uniform is not a common random number across different path assignments (the binomial packet draw that precedes it consumes a probability-dependent number of variates), which adds noise but no bias to path-assignment contrasts; epsilon values are diagnostic RDP estimates (`subsampling_amplification_valid=false`), not certified differential-privacy guarantees.
