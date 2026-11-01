"""Read-only verification of data/CICIoT2023/prepared_verified_v2_filegroup.

Writes a JSON verification report and a conflicting-label group manifest.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT))
from prepare_ciciot2023 import sha256_gzip_content  # noqa: E402
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402
from src.data_integrity import conflicting_fingerprint_groups, predictor_fingerprint  # noqa: E402

D = ROOT / "data" / "CICIoT2023" / "prepared_verified_v2_filegroup"
OUT = ROOT / "docs" / "data_integrity"
BENIGN = {"Benign_Final"}
meta = json.loads((D / "preparation_metadata.json").read_text(encoding="utf-8"))
report: dict = {"dataset": str(D.relative_to(ROOT))}

frames = {s: pd.read_csv(D / f"{s}.csv.gz") for s in ("train", "validation", "test")}
prov = {s: pd.read_csv(D / f"{s}_provenance.csv.gz") for s in frames}
feats = [c for c in frames["train"].columns if c not in ("label", "attack_category")]
report["n_features"] = len(feats)

# 1 hashes
report["content_sha256_matches_metadata"] = {
    s: sha256_gzip_content(D / f"{s}.csv.gz") == meta["split_content_sha256"][s] for s in frames}
# 2 labels
report["label_category_consistent"] = {
    s: bool(((f["label"] == 0) == f["attack_category"].isin(BENIGN)).all()) for s, f in frames.items()}
report["sizes"] = {s: len(f) for s, f in frames.items()}
report["benign_prevalence"] = {s: round(float((f["label"] == 0).mean()), 4) for s, f in frames.items()}
report["class_counts"] = {s: {k: int(v) for k, v in f["attack_category"].value_counts().items()} for s, f in frames.items()}
# 3 zero exact predictor overlap
fp = {s: predictor_fingerprint(f, feats) for s, f in frames.items()}
report["cross_split_exact_predictor_overlap_rows"] = {
    "train_vs_validation": int(np.isin(fp["validation"], fp["train"]).sum()),
    "train_vs_test": int(np.isin(fp["test"], fp["train"]).sum()),
    "validation_vs_test": int(np.isin(fp["test"], fp["validation"]).sum()),
}
# 4 file-group exclusivity
assignment = meta["file_group_assignment"]
grouped_files = set(assignment)
violations = 0
for s in frames:
    srcs = set(prov[s]["_src_file"].str.replace("\\", "/", regex=False))
    violations += sum(1 for f in srcs & grouped_files if assignment[f] != s)
report["file_group_exclusivity"] = {
    "eligible_classes": 17, "eligible_files": len(grouped_files), "violations": int(violations)}
ungrouped = meta["ungrouped_classes_row_stratified"]
rows_ungrouped = {
    s: int(frames[s]["attack_category"].isin(ungrouped).sum()) for s in frames}
report["residual_limitation"] = {
    "ungrouped_classes": ungrouped,
    "ungrouped_class_rows_per_split": rows_ungrouped,
    "ungrouped_fraction_of_test": round(rows_ungrouped["test"] / len(frames["test"]), 4),
    "statement": "For these classes rows of the same capture file occur in several splits; capture-level independence is NOT established. Grouped classes are only file-disjoint, not device-disjoint.",
}
# 5 conflicting-label groups (no relabeling; manifest only)
rows = []
for s, f in frames.items():
    m = conflicting_fingerprint_groups(fp[s], f["label"].to_numpy())
    m.insert(0, "split", s)
    rows.append(m)
manifest = pd.concat(rows, ignore_index=True)
manifest["fingerprint"] = manifest["fingerprint"].astype("uint64")
manifest.to_csv(OUT / "conflict_manifest_filegroup_v2.csv", index=False)
report["conflicting_label_groups"] = {
    s: {"groups": int((manifest["split"] == s).sum()),
        "rows": int(manifest.loc[manifest["split"] == s, "rows"].sum())} for s in frames}
# 6 finite model inputs after the documented preprocessing
cfg = Config.from_yaml(ROOT / "configs" / "ciciot2023_filegroup_v2_eps10.yaml")
bundle = load_dataset(cfg.data, seed=2)
report["model_input"] = {
    "feature_dim": int(bundle.X_train.shape[1]),
    "all_finite": bool(np.isfinite(bundle.X_train).all() and np.isfinite(bundle.X_val).all()
                       and np.isfinite(bundle.X_test).all()),
    "shapes": {"train": list(bundle.X_train.shape), "validation": list(bundle.X_val.shape),
               "test": list(bundle.X_test.shape)},
    "raw_nan_cells": {s: int(f[feats].isna().sum().sum()) for s, f in frames.items()},
}
# 7 manifests preserved
report["manifests_present"] = {n: (D / n).exists() for n in (
    "source_files_manifest.csv", "split_manifest.csv", "preparation_metadata.json",
    "train_provenance.csv.gz", "validation_provenance.csv.gz", "test_provenance.csv.gz")}
report["claim"] = "Capture-level independence is NOT claimed."
(OUT / "filegroup_protocol_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=1)[:5500])
