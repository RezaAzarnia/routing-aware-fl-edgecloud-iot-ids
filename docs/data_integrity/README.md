# Data-integrity artefacts (phase 4)

* `historical_data_hashes.json` - SHA-256 of the ORIGINAL UNSW files and the historical `prepared_paper`/`prepared_pilot` outputs (never modify those).
* `ciciot2023_raw_manifest.csv` - per-file SHA-256/size/rows of the 310 supplied raw CSVs (309 unique; `Backdoor_Malware.pcap.csv` is byte-identical to `Backdoor_Malware/Backdoor_Malware.pcap.csv`).
* `ciciot2023_source_audit.json` - natural duplication and cross-class feature-identical vectors in the raw source.
* `unsw_overlap_audit.json` - UNSW-NB15 partition overlap under four identity definitions.
* `audit_historical_prepared_paper.json`, `audit_prepared_verified_v2*.json` - within/cross-split duplicate, conflict and prevalence audits.
* `prepared_verified_v2/`, `prepared_verified_v2_filegroup/` - metadata, source manifests and label counts of the two verified preparations (the data themselves stay under `data/CICIoT2023/`, git-ignored).

Reproduce:

    python prepare_ciciot2023.py --raw-dir data/CICIoT2023/raw_csv --output-dir data/CICIoT2023/prepared_verified_v2 \
        --train-rows 1000000 --val-rows 200000 --test-rows 300000 --train-benign-fraction 0.50 \
        --train-attack-sampling uniform_category --seed 2023 --force
    # capture-group aware variant: add  --split-mode file_group
    python scripts/data_audit/audit_ciciot_integrity.py splits data/CICIoT2023/prepared_verified_v2 out.json
    python scripts/data_audit/audit_unsw_overlap.py out_unsw.json
