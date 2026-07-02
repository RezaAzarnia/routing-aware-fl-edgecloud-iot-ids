# Data directory

Raw datasets are not redistributed with this repository.

Expected paths:

```text
data/UNSW_NB15_training-set.csv
data/UNSW_NB15_testing-set.csv
data/CICIoT2023/raw_csv/
data/CICIoT2023/prepared_paper/
```

For CICIoT2023, place the official raw CSV release under `data/CICIoT2023/raw_csv/` and run:

```bash
python prepare_ciciot2023.py --raw-dir data/CICIoT2023/raw_csv --output-dir data/CICIoT2023/prepared_paper --train-rows 1000000 --val-rows 200000 --test-rows 300000 --train-benign-fraction 0.50 --train-attack-sampling uniform_category --seed 2023 --force
```
