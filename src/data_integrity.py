"""Read-only dataset-integrity helpers (no FL / model code).

Canonical feature representation used for every identity comparison:
  * values are parsed/cast to float64;
  * ``-0.0`` is normalised to ``+0.0`` (adding 0.0);
  * NaN is kept as NaN (two NaNs in the same position compare equal);
  * no rounding is applied, so rows are identical only if all float64 bits agree;
  * rows are hashed to 64 bits with ``pandas.util.hash_pandas_object``
    (collision probability for n rows is about n^2 / 2^65).
"""
from __future__ import annotations

from typing import Dict, Iterable, Sequence

import numpy as np
import pandas as pd


def canonical_feature_hash(frame: pd.DataFrame, columns: Sequence[str]) -> np.ndarray:
    values = frame[list(columns)].to_numpy(dtype=np.float64) + 0.0
    canonical = pd.DataFrame(values, columns=list(columns))
    return pd.util.hash_pandas_object(canonical, index=False).to_numpy(dtype=np.uint64)


def _group_label_stats(hashes: np.ndarray, labels: np.ndarray) -> pd.DataFrame:
    table = pd.DataFrame({"h": hashes, "y": labels.astype(np.int64)})
    return table.groupby("h")["y"].agg(["size", "nunique"])


def within_split_report(
    frame: pd.DataFrame,
    feature_cols: Sequence[str],
    label_col: str = "label",
    category_col: str | None = "attack_category",
) -> Dict[str, int]:
    """Classify repeated rows inside one split."""
    hashes = canonical_feature_hash(frame, feature_cols)
    labels = frame[label_col].to_numpy()
    stats = _group_label_stats(hashes, labels)
    repeated_groups = stats[stats["size"] > 1]
    feature_dup_rows = int(len(frame) - len(stats))
    conflicting = repeated_groups[repeated_groups["nunique"] > 1]
    report = {
        "rows": int(len(frame)),
        "unique_feature_vectors": int(len(stats)),
        "feature_only_duplicate_rows": feature_dup_rows,
        "same_label_repeat_groups": int(len(repeated_groups) - len(conflicting)),
        "conflicting_label_groups": int(len(conflicting)),
        "rows_in_conflicting_label_groups": int(conflicting["size"].sum()) if len(conflicting) else 0,
    }
    full_cols = list(feature_cols) + ([category_col] if category_col and category_col in frame else []) + [label_col]
    report["exact_full_row_duplicate_rows"] = int(frame[full_cols].duplicated().sum())
    return report


def cross_split_report(
    reference: pd.DataFrame,
    evaluated: pd.DataFrame,
    feature_cols: Sequence[str],
    label_col: str = "label",
    category_col: str | None = "attack_category",
) -> Dict[str, int]:
    """Rows of ``evaluated`` whose feature vector also occurs in ``reference``."""
    ref_hash = canonical_feature_hash(reference, feature_cols)
    ref = pd.DataFrame({"h": ref_hash, "y": reference[label_col].to_numpy()})
    if category_col and category_col in reference:
        ref["c"] = reference[category_col].astype(str).to_numpy()
    ref_labels = ref.groupby("h")["y"].agg(lambda s: frozenset(s.unique()))
    ev = pd.DataFrame({"h": canonical_feature_hash(evaluated, feature_cols),
                       "y": evaluated[label_col].to_numpy()})
    if category_col and category_col in evaluated:
        ev["c"] = evaluated[category_col].astype(str).to_numpy()
    mask = ev["h"].isin(ref_labels.index)
    shared = ev[mask]
    same_label = conflicting = 0
    if len(shared):
        ref_sets = ref_labels.reindex(shared["h"]).to_numpy()
        for y, labels in zip(shared["y"].to_numpy(), ref_sets):
            if y in labels and len(labels) == 1:
                same_label += 1
            elif y in labels:
                conflicting += 1  # reference itself ambiguous
            else:
                conflicting += 1
    out = {
        "evaluated_rows": int(len(evaluated)),
        "rows_with_feature_vector_in_reference": int(mask.sum()),
        "distinct_shared_vectors": int(shared["h"].nunique()),
        "same_binary_label": int(same_label),
        "conflicting_binary_label": int(conflicting),
    }
    return out


def conflicting_label_groups(
    frame: pd.DataFrame,
    feature_cols: Sequence[str],
    label_col: str = "label",
) -> pd.DataFrame:
    """Feature vectors that occur with more than one binary label."""
    hashes = canonical_feature_hash(frame, feature_cols)
    table = pd.DataFrame({"h": hashes, "y": frame[label_col].to_numpy().astype(np.int64)})
    grouped = table.groupby("h")["y"].agg(rows="size", labels="nunique", benign=lambda s: int((s == 0).sum()))
    return grouped[grouped["labels"] > 1].reset_index()


def feature_columns(frame: pd.DataFrame, exclude: Iterable[str] = ("label", "attack_category")) -> list[str]:
    skip = set(exclude)
    return [c for c in frame.columns if c not in skip]
