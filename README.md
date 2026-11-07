# Routing-Aware, Privacy-Aware, and Fault-Tolerant Federated Learning for Edge–Cloud IoT Intrusion Detection

This repository contains the implementation of a routing-aware, privacy-aware, and fault-tolerant federated learning (FL) framework for intrusion detection in Edge–Cloud Internet of Things (IoT) systems.

The implementation supports the experiments reported for **CICIoT2023** and **UNSW-NB15**, including routing-aware client/path selection, failed-update recovery, MAD-based robust filtering, clipping, capped weighting, central Gaussian differential privacy (DP), privacy accounting, server momentum, ablation studies, and plotting/metric utilities.

## Main components

- Federated client partitioning with IID and Dirichlet non-IID settings
- Routing-aware client and path selection using latency, path stability, and path-security indicators
- Sign-flip attack simulation and unstable communication simulation
- Failed-update recovery using coordinate-wise median reconstruction
- MAD-based robust filtering for suspicious or highly deviating updates
- Clipping and capped weighted aggregation
- Central Gaussian DP at the released aggregated update level
- Estimated privacy-budget tracking with a privacy accountant
- Server momentum for global model updating
- Ablation experiments and sweep utilities
- Metric calculation for IDS, routing, privacy, communication cost, and resilience analysis

## Repository structure

```text
.
├── configs/                     # YAML configuration files
├── data/                        # Local dataset folder; raw data are not redistributed
├── docs/                        # Extra protocol notes and dataset preparation notes
├── scripts/windows/             # Optional Windows helper scripts
├── src/                         # Core implementation
├── tests/                       # Unit tests
├── run.py                       # Main experiment launcher
├── prepare_ciciot2023.py        # CICIoT2023 preparation script
├── inspect_ciciot2023.py        # Quick CICIoT2023 raw-data checker
├── requirements.txt
├── CITATION.cff
└── LICENSE
```

## Installation

Python 3.10 or newer is recommended.

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the unit tests:

```bash
pytest -q
```

## Datasets

The raw datasets are not included in this repository because of dataset size and licensing restrictions.

### UNSW-NB15

Place the official files in:

```text
data/UNSW_NB15_training-set.csv
data/UNSW_NB15_testing-set.csv
```

### CICIoT2023

Place the official CICIoT2023 raw CSV release under:

```text
data/CICIoT2023/raw_csv/
```

The preparation script supports both common CICIoT2023 layouts: CSV files with an explicit label column and folder-per-class CSV files where the attack class is inferred from the parent folder name.

Optional raw-data inspection:

```bash
python inspect_ciciot2023.py --raw-dir data/CICIoT2023/raw_csv --label-col auto
```

Prepare the reproducible paper split:

```bash
python prepare_ciciot2023.py \
  --raw-dir data/CICIoT2023/raw_csv \
  --output-dir data/CICIoT2023/prepared_paper \
  --train-rows 1000000 \
  --val-rows 200000 \
  --test-rows 300000 \
  --train-benign-fraction 0.50 \
  --train-attack-sampling uniform_category \
  --seed 2023 \
  --force
```

> **Split protocol.** The command above uses the default `--split-mode row_stratified`, the *legacy* historical protocol in which rows of one capture file can fall into several splits. The controlled studies reported in the current manuscript (Table 4 v2, ablation) use the verified **file-group-disjoint** split, prepared with `--split-mode file_group` (see `docs/data_integrity/README.md`) into `data/CICIoT2023/prepared_verified_v2_filegroup/` (926,133 training and 146,626 validation records; the 300,000-row test partition is reserved and never used by these studies). Do not use the row-stratified split to reproduce the controlled results.

The prepared files are expected at:

```text
data/CICIoT2023/prepared_paper/train.csv.gz
data/CICIoT2023/prepared_paper/validation.csv.gz
data/CICIoT2023/prepared_paper/test.csv.gz
data/CICIoT2023/prepared_paper/preparation_metadata.json
```

## Reproducing the main experiments

> **Two different protocols.** The commands in the subsections below (`--seeds 2,3,4,5,6` and `--seeds 2,3,4`) are the **legacy** runs from earlier development phases. They are *not* the controlled Table 4 v2 protocol, which uses **seeds 12-16**, the file-group-disjoint split, matched network traces, validation-only evaluation and the locked manifest in `docs/table4_v2/EXPERIMENT_MANIFEST.json`. Reproduce Table 4 v2 with `python scripts/table4_v2/orchestrator.py preflight|run|status|validate` and `python scripts/table4_v2/analyse.py`; see `Table4_V2_Package/TABLE4_V2_REPRODUCTION.md`. Results of the two protocols must not be mixed.

### CICIoT2023 proposed configurations

Proposed epsilon approximately 10:

```bash
python run.py --config configs/ciciot2023_eps10.yaml --suite single --seeds 2,3,4,5,6 --skip-existing
```

Proposed epsilon approximately 20:

```bash
python run.py --config configs/ciciot2023_eps20.yaml --suite single --seeds 2,3,4,5,6 --skip-existing
```

Baselines and proposed variants:

```bash
python run.py --config configs/ciciot2023_core.yaml --suite core --seeds 2,3,4,5,6 --skip-existing
```

Ablation study:

```bash
python run.py --config configs/ciciot2023_core.yaml --suite ablation --seeds 2,3,4 --skip-existing
```

Failure-rate sweep:

```bash
python run.py --config configs/ciciot2023_core.yaml --suite failure_sweep --seeds 2,3,4 --skip-existing
```

### UNSW-NB15 experiments

```bash
python run.py --config configs/full.yaml --suite core --seeds 2,3,4,5,6 --skip-existing
```

Additional sweep examples:

```bash
python run.py --config configs/full.yaml --suite failure_sweep --seeds 2,3,4 --skip-existing
python run.py --config configs/full.yaml --suite privacy_sweep --seeds 2,3,4 --skip-existing
python run.py --config configs/full.yaml --suite heterogeneity_sweep --seeds 2,3,4 --skip-existing
```

## Windows helper scripts (optional)

The main reproduction path is platform-independent and uses the Python commands above. For Windows users, optional batch wrappers are provided under:

```text
scripts/windows/
```

Main helper scripts include:

```text
install_requirements.bat
check_ciciot2023_dataset.bat
prepare_ciciot2023_paper.bat
run_main_ciciot2023_eps10_eps20_5seeds.bat
run_ciciot2023_baselines_5seeds.bat
run_ciciot2023_ablations_3seeds.bat
run_ciciot2023_key_sweeps_3seeds.bat
```

These files only wrap the Python commands documented in this README and are not required for reproducing the experiments.

## Output files

Each run writes results under the configured `results/` directory. Important output files include:

```text
final_test_metrics.csv
round_metrics.csv
aggregation_diagnostics.csv
recovery_events.csv
network_metrics.csv
dataset_summary.csv
client_distribution.csv
standard_operating_points.csv
calibrated_operating_points.csv
per_attack_metrics_standard.csv
per_attack_metrics_calibrated.csv
confusion_matrix_standard.csv
confusion_matrix_calibrated.csv
```

## Privacy note

The privacy mechanism is implemented as central Gaussian DP applied to the released aggregated update after robust filtering, clipping, and capped weighted aggregation. The reported epsilon values should be interpreted as **estimated privacy budgets** tracked by the privacy accountant under a trusted or semi-trusted server assumption. They should not be interpreted as a formal end-to-end privacy guarantee against a fully untrusted server.

## Code availability statement

The source code, configuration files, experimental scripts, ablation scripts and plotting utilities are publicly available in this repository. Release `v1.0.4` is archived on Zenodo, DOI [10.5281/zenodo.24031823](https://doi.org/10.5281/zenodo.24031823). The archive contains the code, locked configurations, the Table 4 v2 manifest and the published Table 4 v2 per-seed, summary and paired-effect tables (`Table4_V2_Package/`). The raw per-run output directories (`results_table4_controlled_v2/`, `results_ablation_controlled_v2/`) are **not** published or archived. The raw CICIoT2023 and UNSW-NB15 datasets are not redistributed because of dataset size and licensing restrictions.

## Citation

If you use this repository, please cite the associated paper and the archived Zenodo release (v1.0.4, DOI 10.5281/zenodo.24031823).
