"""Read-only UNSW-NB15 duplicate / partition-overlap audit (official files are never modified).

Identity definitions
  full_row_all_columns   : all 45 columns incl. ``id``
  full_row_without_id    : all columns except ``id``      (features + attack_cat + label)
  predictor_only         : the 42 predictors (no id, attack_cat, label)
  predictor_and_label    : predictors + binary label
Numeric columns are compared as float64 with -0.0 -> 0.0; strings exactly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def hash_rows(frame: pd.DataFrame, columns: list[str]) -> np.ndarray:
    sub = frame[columns].copy()
    for col in sub.columns:
        if pd.api.types.is_numeric_dtype(sub[col]):
            sub[col] = sub[col].astype("float64") + 0.0
    return pd.util.hash_pandas_object(sub, index=False).to_numpy(dtype=np.uint64)


def main(out_json: str) -> None:
    train = pd.read_csv(DATA / "UNSW_NB15_training-set.csv")
    test = pd.read_csv(DATA / "UNSW_NB15_testing-set.csv")
    all_cols = list(train.columns)
    predictors = [c for c in all_cols if c not in ("id", "attack_cat", "label")]
    identities = {
        "full_row_all_columns": all_cols,
        "full_row_without_id": [c for c in all_cols if c != "id"],
        "predictor_only": predictors,
        "predictor_and_label": predictors + ["label"],
    }
    result: dict = {"rows": {"train": len(train), "test": len(test)}, "identities": {}}
    train_pred = hash_rows(train, predictors)
    test_pred = hash_rows(test, predictors)
    for name, cols in identities.items():
        ht, he = hash_rows(train, cols), hash_rows(test, cols)
        shared = np.isin(he, ht)
        result["identities"][name] = {
            "train_internal_duplicate_rows": int(len(ht) - len(np.unique(ht))),
            "test_internal_duplicate_rows": int(len(he) - len(np.unique(he))),
            "test_rows_also_in_train": int(shared.sum()),
            "distinct_shared_vectors": int(len(np.intersect1d(ht, he))),
        }
    # label relation among predictor-identical cross-partition rows
    tr_lab = pd.DataFrame({"h": train_pred, "y": train["label"].to_numpy()}).groupby("h")["y"].agg(
        lambda s: frozenset(s.unique()))
    shared_mask = np.isin(test_pred, tr_lab.index.to_numpy())
    sh = pd.DataFrame({"h": test_pred[shared_mask], "y": test["label"].to_numpy()[shared_mask],
                       "cat": test["attack_cat"].to_numpy()[shared_mask]})
    same = conflicting = 0
    for h, y in zip(sh["h"].to_numpy(), sh["y"].to_numpy()):
        labels = tr_lab[h]
        if labels == frozenset([y]):
            same += 1
        else:
            conflicting += 1
    result["predictor_identical_cross_partition"] = {
        "test_rows": int(shared_mask.sum()),
        "same_binary_label_in_train": same,
        "conflicting_or_ambiguous_label": conflicting,
        "by_test_attack_cat": {k: int(v) for k, v in sh["cat"].value_counts().items()},
        "fraction_of_test": round(float(shared_mask.mean()), 4),
    }
    # conflicting labels inside each official file (predictor identical, labels differ)
    for name, frame, h in (("train", train, train_pred), ("test", test, test_pred)):
        g = pd.DataFrame({"h": h, "y": frame["label"].to_numpy()}).groupby("h")["y"].agg(["size", "nunique"])
        result[f"conflicting_label_groups_within_{name}"] = {
            "groups": int((g["nunique"] > 1).sum()),
            "rows": int(g.loc[g["nunique"] > 1, "size"].sum()),
        }
    # duplicate-controlled sensitivity subset (mask only; the official test file is untouched)
    keep = ~shared_mask
    sub = test.loc[keep]
    result["duplicate_controlled_test_subset"] = {
        "rule": "test rows whose predictor vector does NOT occur in the official training file",
        "rows": int(keep.sum()),
        "benign": int((sub["label"] == 0).sum()),
        "attack": int((sub["label"] == 1).sum()),
        "attack_cat_counts": {k: int(v) for k, v in sub["attack_cat"].value_counts().items()},
        "note": "Evaluation-time mask only; standard benchmark on the full 82,332-row test file remains primary.",
    }
    # train/validation leakage created by the loader's random 15% validation split
    from sklearn.model_selection import train_test_split

    y = train["label"].to_numpy()
    leaks = {}
    for seed in (2, 3, 4, 5, 6):
        idx_tr, idx_val = train_test_split(np.arange(len(y)), test_size=0.15, random_state=seed, stratify=y)
        in_train = np.isin(train_pred[idx_val], train_pred[idx_tr])
        leaks[str(seed)] = {"validation_rows": int(len(idx_val)),
                            "validation_rows_with_predictor_vector_in_fit_train": int(in_train.sum()),
                            "fraction": round(float(in_train.mean()), 4)}
    result["loader_validation_split_leakage_by_seed"] = leaks
    # unseen categorical levels in test
    result["categorical_levels_unseen_in_train"] = {
        c: sorted(set(test[c]) - set(train[c])) for c in ("proto", "service", "state")}
    Path(out_json).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=1)[:5000])


if __name__ == "__main__":
    main(sys.argv[1])
