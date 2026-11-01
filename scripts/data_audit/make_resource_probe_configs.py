"""Create 1-round, full-size probe configs (validation-side; official test NOT opened)."""
import yaml

FG = "data/CICIoT2023/prepared_verified_v2_filegroup"
for src, dst, name, test_slot in (
    ("configs/unsw_nb15_groupdisjoint_v2.yaml", "configs/probe_unsw_fullsize_1round.yaml", "probe_unsw_fullsize_1round",
     "data/UNSW_NB15_training-set.csv"),
    ("configs/ciciot2023_filegroup_v2_eps10.yaml", "configs/probe_ciciot_fullsize_1round.yaml", "probe_ciciot_fullsize_1round",
     f"{FG}/validation.csv.gz"),
):
    cfg = yaml.safe_load(open(src, encoding="utf-8"))
    cfg["fl"]["rounds"] = 1
    cfg["data"]["test_csv"] = test_slot
    cfg["data"]["enable_calibrated_evaluation"] = False
    cfg["data"]["max_test_samples"] = 5000
    cfg["experiment"].update({"name": name, "output_dir": "results_smoke_no_official_test", "method_name": "probe",
                              "early_stopping_patience": None, "create_plots": False, "device": "cpu", "seed": 1})
    open(dst, "w", encoding="utf-8").write(
        "# RESOURCE PROBE: 1 round, full data size and full client counts. Official test NOT opened.\n"
        + yaml.safe_dump(cfg, sort_keys=False))
