"""Read-only CICIoT2023 duplicate / leakage / conflicting-label audit.

Modes
-----
source  <raw_dir> <out_json>
    Hash every row of every UNIQUE raw file (byte-identical copies are skipped)
    and report natural duplication and cross-class feature-identical vectors.
splits  <prepared_dir> <out_json> [--raw-dir RAW]
    Within-split and cross-split duplicate / conflict analysis of a prepared
    train/validation/test triplet. If *_provenance.csv.gz sidecars exist, shared
    vectors are additionally classified as same-source-file or different-file.

Nothing in the data directories is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.data_integrity import (  # noqa: E402
    canonical_feature_hash,
    conflicting_label_groups,
    cross_split_report,
    feature_columns,
    within_split_report,
)

BENIGN = {"Benign_Final", "BenignTraffic", "Benign"}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 24), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_source(raw_dir: Path, out_json: Path) -> None:
    files = sorted(p for p in raw_dir.rglob("*.csv") if p.is_file())
    seen: dict[str, Path] = {}
    unique = []
    skipped = []
    for p in sorted(files, key=lambda q: (-len(q.relative_to(raw_dir).parts), str(q))):
        digest = _sha(p)
        if digest in seen:
            skipped.append(str(p.relative_to(raw_dir)))
        else:
            seen[digest] = p
            unique.append(p)
    unique.sort()
    class_names = sorted({p.relative_to(raw_dir).parts[0] for p in unique})
    class_id = {name: i for i, name in enumerate(class_names)}
    benign_ids = {class_id[c] for c in class_names if c in BENIGN}
    hashes, classes, file_ids = [], [], []
    columns = None
    for fi, p in enumerate(unique):
        cls = class_id[p.relative_to(raw_dir).parts[0]]
        for chunk in pd.read_csv(p, chunksize=500_000):
            if columns is None:
                columns = list(chunk.columns)
            h = canonical_feature_hash(chunk, columns)
            hashes.append(h)
            classes.append(np.full(len(h), cls, dtype=np.int16))
            file_ids.append(np.full(len(h), fi, dtype=np.int16))
    h = np.concatenate(hashes)
    c = np.concatenate(classes)
    f = np.concatenate(file_ids)
    del hashes, classes, file_ids
    order = np.argsort(h, kind="stable")
    hs, cs, fs = h[order], c[order], f[order]
    del h, c, f, order
    boundaries = np.flatnonzero(np.r_[True, hs[1:] != hs[:-1]])
    sizes = np.diff(np.r_[boundaries, len(hs)])
    cmin = np.minimum.reduceat(cs, boundaries)
    cmax = np.maximum.reduceat(cs, boundaries)
    is_benign = np.isin(cs, list(benign_ids))
    bmin = np.minimum.reduceat(is_benign.astype(np.int8), boundaries)
    bmax = np.maximum.reduceat(is_benign.astype(np.int8), boundaries)
    fmin = np.minimum.reduceat(fs, boundaries)
    fmax = np.maximum.reduceat(fs, boundaries)
    total = int(len(hs))
    unique_vectors = int(len(boundaries))
    multi_class = cmin != cmax
    binary_conflict = bmin != bmax
    # per-class natural duplication
    per_class = {}
    row_class_starts = np.repeat(np.arange(len(boundaries)), sizes)
    for name, idx in class_id.items():
        rows = int((cs == idx).sum())
        pairs = pd.DataFrame({"g": row_class_starts[cs == idx]})
        uniq = int(pairs["g"].nunique())
        per_class[name] = {"rows": rows, "unique_vectors": uniq,
                           "duplicate_rows": rows - uniq,
                           "duplicate_fraction": round((rows - uniq) / max(rows, 1), 4)}
    pair_counter: Counter = Counter()
    for gi in np.flatnonzero(multi_class)[:2_000_000]:
        pair_counter[(class_names[int(cmin[gi])], class_names[int(cmax[gi])])] += 1
    result = {
        "files_total_on_disk": len(files),
        "files_unique": len(unique),
        "files_skipped_as_byte_identical": skipped,
        "feature_columns": columns,
        "n_features": len(columns),
        "rows_total_unique_files": total,
        "unique_feature_vectors": unique_vectors,
        "duplicate_rows_total": total - unique_vectors,
        "duplicate_fraction": round((total - unique_vectors) / total, 4),
        "vectors_shared_by_multiple_classes": int(multi_class.sum()),
        "rows_in_multi_class_vectors": int(sizes[multi_class].sum()),
        "vectors_with_both_benign_and_attack": int(binary_conflict.sum()),
        "rows_in_benign_attack_conflict_vectors": int(sizes[binary_conflict].sum()),
        "multi_class_vectors_spanning_multiple_files": int((multi_class & (fmin != fmax)).sum()),
        "top_class_pairs_for_multi_class_vectors": [
            {"classes": list(k), "vectors": v} for k, v in pair_counter.most_common(15)],
        "per_class": per_class,
        "hashing": "canonical float64, -0.0->0.0, NaN kept, no rounding; 64-bit pandas row hash",
    }
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in ("per_class", "feature_columns")}, indent=1)[:3000])


def audit_splits(prepared: Path, out_json: Path) -> None:
    splits = {s: pd.read_csv(prepared / f"{s}.csv.gz") for s in ("train", "validation", "test")}
    feats = feature_columns(splits["train"])
    result: dict = {"prepared_dir": str(prepared), "n_features": len(feats), "within": {}, "cross": {},
                    "prevalence": {}, "class_counts": {}}
    for name, frame in splits.items():
        result["within"][name] = within_split_report(frame, feats)
        n = len(frame)
        benign = int((frame["label"] == 0).sum())
        result["prevalence"][name] = {"rows": n, "benign": benign, "attack": n - benign,
                                      "benign_fraction": round(benign / n, 4),
                                      "nan_cells": int(frame[feats].isna().sum().sum())}
        result["class_counts"][name] = {k: int(v) for k, v in frame["attack_category"].value_counts().items()}
    for ref, ev in (("train", "test"), ("validation", "test"), ("train", "validation")):
        result["cross"][f"{ev}_rows_found_in_{ref}"] = cross_split_report(splits[ref], splits[ev], feats)
    # same-category vs different-category among shared vectors (test vs train)
    for ref, ev in (("train", "test"),):
        rh = pd.DataFrame({"h": canonical_feature_hash(splits[ref], feats),
                           "c": splits[ref]["attack_category"].to_numpy()})
        eh = pd.DataFrame({"h": canonical_feature_hash(splits[ev], feats),
                           "c": splits[ev]["attack_category"].to_numpy()})
        ref_cats = rh.groupby("h")["c"].agg(lambda s: set(s))
        shared = eh[eh["h"].isin(ref_cats.index)]
        same_cat = diff_cat = 0
        pairs: Counter = Counter()
        for h, c in zip(shared["h"].to_numpy(), shared["c"].to_numpy()):
            cats = ref_cats[h]
            if c in cats:
                same_cat += 1
            else:
                diff_cat += 1
                pairs[(c, sorted(cats)[0])] += 1
        result["cross"]["test_vs_train_category_relation"] = {
            "shared_rows": int(len(shared)), "same_attack_category": same_cat,
            "different_attack_category": diff_cat,
            "top_different_category_pairs": [{"test": a, "train": b, "rows": n}
                                             for (a, b), n in pairs.most_common(10)]}
    result["conflicting_label_groups_within_train"] = int(len(conflicting_label_groups(splits["train"], feats)))
    # provenance-based same-capture analysis
    prov = {s: prepared / f"{s}_provenance.csv.gz" for s in splits}
    if all(p.exists() for p in prov.values()):
        pv = {s: pd.read_csv(p) for s, p in prov.items()}
        te = pd.DataFrame({"h": canonical_feature_hash(splits["test"], feats), "f": pv["test"]["_src_file"]})
        tr = pd.DataFrame({"h": canonical_feature_hash(splits["train"], feats), "f": pv["train"]["_src_file"]})
        merged = te.merge(tr, on="h", suffixes=("_test", "_train"))
        result["provenance_same_source_file_test_vs_train"] = {
            "shared_row_pairs": int(len(merged)),
            "same_source_file": int((merged["f_test"] == merged["f_train"]).sum()),
            "different_source_file": int((merged["f_test"] != merged["f_train"]).sum()),
        }
        # source-file sharing between splits (capture groups present in >1 split)
        files_by_split = {s: set(pv[s]["_src_file"]) for s in splits}
        result["source_files_present_in_multiple_splits"] = {
            "train_and_test": len(files_by_split["train"] & files_by_split["test"]),
            "train_and_validation": len(files_by_split["train"] & files_by_split["validation"]),
            "all_three": len(files_by_split["train"] & files_by_split["validation"] & files_by_split["test"]),
            "files_total": len(files_by_split["train"] | files_by_split["validation"] | files_by_split["test"]),
        }
    else:
        result["provenance"] = "NO provenance sidecars: same-capture leakage cannot be assessed for this dataset"
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=1)[:6000])


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("source")
    a.add_argument("raw_dir")
    a.add_argument("out_json")
    b = sub.add_parser("splits")
    b.add_argument("prepared_dir")
    b.add_argument("out_json")
    args = parser.parse_args()
    if args.mode == "source":
        audit_source(Path(args.raw_dir), Path(args.out_json))
    else:
        audit_splits(Path(args.prepared_dir), Path(args.out_json))


if __name__ == "__main__":
    main()
