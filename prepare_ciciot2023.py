from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

LABEL_CANDIDATES = ("label", "Label", "traffic_type", "Traffic_Type", "class", "Class")
DEFAULT_BENIGN_LABELS = (
    "BenignTraffic", "Benign_Final", "Benign", "BENIGN", "Normal", "normal", "0"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare reproducible CICIoT2023 binary train/validation/test CSV files "
            "from the official raw CSV release. Supports both variants: "
            "(1) CSV shards with a label column, and (2) official class-folder CSVs "
            "where the label is encoded by the parent folder name."
        )
    )
    parser.add_argument("--raw-dir", default="data/CICIoT2023/raw_csv")
    parser.add_argument("--output-dir", default="data/CICIoT2023/prepared")
    parser.add_argument("--glob", default="**/*.csv")
    parser.add_argument(
        "--label-col", default="auto",
        help=(
            "Label column name, 'auto', or 'path'. Use 'path' for the official "
            "folder-per-attack CSV.zip release when CSV files do not contain a label column."
        ),
    )
    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--val-fraction", type=float, default=0.10)
    parser.add_argument("--test-fraction", type=float, default=0.20)
    parser.add_argument("--train-rows", type=int, default=1_000_000)
    parser.add_argument("--val-rows", type=int, default=200_000)
    parser.add_argument("--test-rows", type=int, default=300_000)
    parser.add_argument("--chunk-size", type=int, default=200_000)
    parser.add_argument("--train-benign-fraction", type=float, default=0.50)
    parser.add_argument(
        "--train-attack-sampling",
        choices=("uniform_category", "natural"),
        default="uniform_category",
        help="How to distribute the attack half of the training sample.",
    )
    parser.add_argument(
        "--benign-label",
        action="append",
        default=None,
        help="May be repeated. Defaults cover Benign_Final/BenignTraffic/Benign/Normal/0.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def normalized_label(value: object) -> str:
    if pd.isna(value):
        return "Unknown"
    return str(value).strip()


def infer_label_from_path(path: Path, raw_dir: Path) -> str:
    """Infer CICIoT2023 class label from the top-level directory under raw_dir.

    Official CSV.zip often has this structure:
        raw_csv/Benign_Final/Benign_Final.pcap.csv
        raw_csv/DDoS-ACK_Fragmentation/DDoS-ACK_Fragmentation1.pcap.csv

    In that release, the CSV files are feature-only and the attack label is encoded
    by the parent directory. This function deliberately uses the first relative path
    part, not the filename, because filenames may contain numeric suffixes.
    """
    try:
        rel = path.resolve().relative_to(raw_dir.resolve())
    except Exception:
        rel = path
    if len(rel.parts) >= 2:
        return rel.parts[0].strip()
    # Fallback for flattened directories: remove common CICIoT suffixes.
    stem = path.name
    for suffix in (".pcap.csv", ".csv"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    # Remove trailing digits sometimes used in official filenames.
    return stem.rstrip("0123456789_").strip() or "Unknown"


def find_label_column(columns: Iterable[str], requested: str) -> str | None:
    """Return the label column, or None when labels should be inferred from paths."""
    columns = list(columns)
    if requested == "path":
        return None
    if requested != "auto":
        if requested not in columns:
            raise ValueError(f"Requested label column '{requested}' not found. Columns={columns}")
        return requested
    lowered = {str(column).strip().lower(): column for column in columns}
    for candidate in LABEL_CANDIDATES:
        found = lowered.get(candidate.lower())
        if found is not None:
            return found
    # Official CICIoT2023 CSV.zip class-folder release has no label column.
    return None


def assign_files(files: list[Path], seed: int, fractions: tuple[float, float, float]) -> dict[Path, str]:
    rng = np.random.default_rng(seed)
    order = np.arange(len(files))
    rng.shuffle(order)
    shuffled = [files[i] for i in order]
    n = len(files)
    n_train = max(1, int(round(n * fractions[0])))
    n_val = max(1, int(round(n * fractions[1])))
    if n_train + n_val >= n:
        n_val = max(1, n - n_train - 1)
    n_test = n - n_train - n_val
    if n_test < 1:
        raise ValueError("Not enough CSV files to create three split groups")
    mapping: dict[Path, str] = {}
    for path in shuffled[:n_train]:
        mapping[path] = "train"
    for path in shuffled[n_train:n_train + n_val]:
        mapping[path] = "validation"
    for path in shuffled[n_train + n_val:]:
        mapping[path] = "test"
    return mapping


def proportional_targets(counts: Counter[str], total_target: int) -> dict[str, int]:
    total_available = sum(counts.values())
    if total_available <= total_target:
        return dict(counts)
    raw = {key: total_target * count / total_available for key, count in counts.items()}
    targets = {key: min(counts[key], int(math.floor(value))) for key, value in raw.items()}
    remaining = total_target - sum(targets.values())
    ranking = sorted(counts, key=lambda key: (raw[key] - math.floor(raw[key]), counts[key]), reverse=True)
    for key in ranking:
        if remaining <= 0:
            break
        if targets[key] < counts[key]:
            targets[key] += 1
            remaining -= 1
    return targets


def uniform_targets(counts: Counter[str], total_target: int) -> dict[str, int]:
    if not counts or total_target <= 0:
        return {}
    targets = {key: 0 for key in counts}
    active = set(counts)
    remaining = min(total_target, sum(counts.values()))
    while active and remaining > 0:
        share = max(1, remaining // len(active))
        progressed = False
        for key in sorted(list(active)):
            capacity = counts[key] - targets[key]
            take = min(share, capacity, remaining)
            if take > 0:
                targets[key] += take
                remaining -= take
                progressed = True
            if targets[key] >= counts[key]:
                active.discard(key)
            if remaining <= 0:
                break
        if not progressed:
            break
    return targets


def training_targets(
    counts: Counter[str],
    benign_labels: set[str],
    total_target: int,
    benign_fraction: float,
    attack_sampling: str,
) -> dict[str, int]:
    benign_counts = Counter({key: value for key, value in counts.items() if key in benign_labels})
    attack_counts = Counter({key: value for key, value in counts.items() if key not in benign_labels})
    benign_target = min(sum(benign_counts.values()), int(round(total_target * benign_fraction)))
    attack_target = min(sum(attack_counts.values()), total_target - benign_target)
    missing = total_target - benign_target - attack_target
    if missing > 0:
        extra_benign = min(missing, sum(benign_counts.values()) - benign_target)
        benign_target += extra_benign
        missing -= extra_benign
    if missing > 0:
        attack_target += min(missing, sum(attack_counts.values()) - attack_target)

    targets = proportional_targets(benign_counts, benign_target)
    attack_targets = (
        uniform_targets(attack_counts, attack_target)
        if attack_sampling == "uniform_category"
        else proportional_targets(attack_counts, attack_target)
    )
    targets.update(attack_targets)
    return targets


def count_rows_csv(path: Path, chunk_size: int) -> int:
    total = 0
    for chunk in pd.read_csv(path, usecols=[0], chunksize=chunk_size):
        total += len(chunk)
    return total


def read_labels(path: Path, label_col: str | None, chunk_size: int, raw_dir: Path) -> Counter[str]:
    if label_col is None:
        return Counter({infer_label_from_path(path, raw_dir): count_rows_csv(path, chunk_size)})
    counts: Counter[str] = Counter()
    for chunk in pd.read_csv(path, usecols=[label_col], chunksize=chunk_size):
        labels = chunk[label_col].map(normalized_label)
        counts.update(labels.value_counts().to_dict())
    return counts


def schema_signature(path: Path) -> list[str]:
    return pd.read_csv(path, nrows=0).columns.astype(str).tolist()


def exact_sample_by_label(frame: pd.DataFrame, targets: dict[str, int], seed: int) -> pd.DataFrame:
    pieces = []
    for index, (label, target) in enumerate(sorted(targets.items())):
        subset = frame.loc[frame["attack_category"] == label]
        if len(subset) < target:
            raise RuntimeError(
                f"Sampling underflow for label={label}: collected={len(subset)}, target={target}. "
                "Increase oversampling or rerun."
            )
        if len(subset) > target:
            subset = subset.sample(n=target, random_state=seed + index)
        pieces.append(subset)
    result = pd.concat(pieces, ignore_index=True)
    return result.sample(frac=1.0, random_state=seed + 999).reset_index(drop=True)


def prepare_with_path_labels(
    args: argparse.Namespace,
    raw_dir: Path,
    output_dir: Path,
    files: list[Path],
    benign_labels: set[str],
    outputs: dict[str, Path],
    first_columns: list[str],
) -> None:
    """Prepare official folder-per-class CICIoT2023 CSV.zip release.

    This release has feature-only CSV files and no label column. The class label is
    encoded by the top-level folder name. Because some classes, including benign
    traffic in some mirrors, may appear as a small number of large files, a pure
    file-held-out split can put an entire class into only one split. Therefore this
    mode uses deterministic row-level stratified sampling within class folders.
    The generated metadata records this limitation explicitly.
    """
    print("Path-label mode enabled: labels are inferred from top-level folder names.")
    print("Split mode: deterministic class-stratified row sampling within class folders.")
    print("Pass 1/2: counting rows by inferred folder label...")

    global_counts: Counter[str] = Counter()
    file_counts: dict[Path, Counter[str]] = {}
    manifest_rows = []
    for index, path in enumerate(files, start=1):
        counts = read_labels(path, None, args.chunk_size, raw_dir)
        file_counts[path] = counts
        global_counts.update(counts)
        manifest_rows.append({
            "file": str(path.resolve()),
            "split": "row_stratified_all_splits",
            "rows": int(sum(counts.values())),
            "inferred_label": infer_label_from_path(path, raw_dir),
            "label_counts_json": json.dumps(dict(sorted(counts.items())), ensure_ascii=False),
        })
        print(f"  [{index:3d}/{len(files)}] {path.relative_to(raw_dir)} rows={sum(counts.values()):,} labels={dict(counts)}")

    binary_available = {
        0: sum(v for k, v in global_counts.items() if k in benign_labels),
        1: sum(v for k, v in global_counts.items() if k not in benign_labels),
    }
    if min(binary_available.values()) == 0:
        raise RuntimeError(
            "The raw directory does not contain both benign and attack rows. "
            f"Available inferred labels: {dict(global_counts)}. "
            "Check that Benign_Final is present and not renamed."
        )

    # Allocate evaluation targets first, then training targets from the remaining
    # per-class capacity. This prevents rare classes such as Uploading_Attack from
    # being over-requested when training uses uniform attack-category sampling.
    targets: dict[str, dict[str, int]] = {}
    targets["validation"] = proportional_targets(global_counts, args.val_rows)
    remaining_after_val = Counter({
        label: max(0, count - targets["validation"].get(label, 0))
        for label, count in global_counts.items()
    })
    targets["test"] = proportional_targets(remaining_after_val, args.test_rows)
    remaining_after_eval = Counter({
        label: max(0, remaining_after_val[label] - targets["test"].get(label, 0))
        for label in global_counts
    })
    targets["train"] = training_targets(
        remaining_after_eval, benign_labels, args.train_rows,
        args.train_benign_fraction, args.train_attack_sampling,
    )

    # Final safety check. A label can appear in at most as many prepared rows as
    # exist in the source release; deficits are acceptable only when the requested
    # overall split size is too large for the available source rows.
    for label, available in global_counts.items():
        requested = sum(targets[split].get(label, 0) for split in ("train", "validation", "test"))
        if requested > available:
            raise RuntimeError(
                f"Internal allocation error for label={label}: requested={requested}, available={available}."
            )

    print("Pass 2/2: collecting non-overlapping stratified row samples...")
    collected: dict[str, list[pd.DataFrame]] = defaultdict(list)
    oversample = 2.0
    file_index = {path: idx for idx, path in enumerate(files)}

    label_to_files: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        label_to_files[infer_label_from_path(path, raw_dir)].append(path)

    # For very small labels, or labels where the target consumes most available rows,
    # use exact deterministic allocation instead of probabilistic oversampling.
    # This avoids failures like requesting 1,254 rows from a 1,252-row class.
    exact_labels = {
        label for label, available in global_counts.items()
        if available <= 50_000 or (
            sum(targets[split].get(label, 0) for split in ("train", "validation", "test")) / max(available, 1)
        ) > 0.50
    }

    for label in sorted(exact_labels):
        pieces = []
        for path in label_to_files[label]:
            for chunk in pd.read_csv(path, chunksize=args.chunk_size):
                pieces.append(chunk)
        if not pieces:
            continue
        label_frame = pd.concat(pieces, ignore_index=True)
        pieces.clear()
        label_frame = label_frame.sample(frac=1.0, random_state=args.seed + abs(hash(label)) % 1_000_000).reset_index(drop=True)
        start = 0
        for split in ("validation", "test", "train"):
            take = targets[split].get(label, 0)
            if take <= 0:
                continue
            selected = label_frame.iloc[start:start + take].copy().reset_index(drop=True)
            start += take
            selected["attack_category"] = label
            selected["label"] = np.int8(0 if label in benign_labels else 1)
            collected[split].append(selected)
        print(f"  exact allocation for rare/small label={label}: requested={start:,}, available={len(label_frame):,}")
        del label_frame

    for path in files:
        inferred = infer_label_from_path(path, raw_dir)
        if inferred in exact_labels:
            continue
        available = max(global_counts[inferred], 1)
        p_train = min(1.0, oversample * targets["train"].get(inferred, 0) / available)
        p_val = min(1.0, oversample * targets["validation"].get(inferred, 0) / available)
        p_test = min(1.0, oversample * targets["test"].get(inferred, 0) / available)
        total_p = p_train + p_val + p_test
        if total_p > 0.98:
            scale = 0.98 / total_p
            p_train *= scale
            p_val *= scale
            p_test *= scale
        for chunk_index, chunk in enumerate(pd.read_csv(path, chunksize=args.chunk_size)):
            rng = np.random.default_rng(args.seed + file_index[path] * 1_000_003 + chunk_index)
            u = rng.random(len(chunk))
            masks = {
                "train": u < p_train,
                "validation": (u >= p_train) & (u < p_train + p_val),
                "test": (u >= p_train + p_val) & (u < p_train + p_val + p_test),
            }
            for split, keep in masks.items():
                if not keep.any():
                    continue
                selected = chunk.loc[keep].copy().reset_index(drop=True)
                selected["attack_category"] = inferred
                selected["label"] = np.int8(0 if inferred in benign_labels else 1)
                collected[split].append(selected)

    prepared: dict[str, pd.DataFrame] = {}
    for split in ("train", "validation", "test"):
        if not collected[split]:
            raise RuntimeError(f"No rows collected for {split}")
        candidate = pd.concat(collected[split], ignore_index=True)
        collected[split].clear()
        candidate = candidate.replace([np.inf, -np.inf], np.nan)
        for column in candidate.columns:
            if column in {"attack_category", "label"}:
                continue
            if not pd.api.types.is_numeric_dtype(candidate[column]):
                candidate[column] = pd.to_numeric(candidate[column], errors="coerce")
        prepared[split] = exact_sample_by_label(candidate, targets[split], args.seed + 20_000)
        if prepared[split]["label"].nunique() != 2:
            raise RuntimeError(f"Prepared {split} does not contain both binary classes")
        print(
            f"  {split:10s}: {len(prepared[split]):,} rows, "
            f"benign={(prepared[split]['label'] == 0).sum():,}, "
            f"attack={(prepared[split]['label'] == 1).sum():,}"
        )

    # Q1-safety step: remove exact duplicate prepared rows across splits.
    # The official class-folder release can contain exact duplicate feature vectors.
    # If an identical feature+attack_category row appears in train and test, it is
    # not necessarily the same packet, but for a conservative paper protocol we
    # remove cross-split duplicates. Priority is: test > validation > train.
    hash_cols = [c for c in prepared["train"].columns if c != "label"]

    def _hash_series(frame: pd.DataFrame) -> pd.Series:
        return pd.util.hash_pandas_object(frame[hash_cols], index=False).astype("uint64")

    hashes_before = {split: set(_hash_series(frame)) for split, frame in prepared.items()}
    overlaps_before = {
        "train_validation": len(hashes_before["train"] & hashes_before["validation"]),
        "train_test": len(hashes_before["train"] & hashes_before["test"]),
        "validation_test": len(hashes_before["validation"] & hashes_before["test"]),
    }

    rows_before_dedup = {split: int(len(frame)) for split, frame in prepared.items()}

    # Remove validation duplicates that appear in test.
    test_hashes = set(_hash_series(prepared["test"]))
    val_hash = _hash_series(prepared["validation"])
    prepared["validation"] = prepared["validation"].loc[~val_hash.isin(test_hashes)].reset_index(drop=True)

    # Remove training duplicates that appear in test or validation.
    protected_hashes = set(_hash_series(prepared["test"])) | set(_hash_series(prepared["validation"]))
    train_hash = _hash_series(prepared["train"])
    prepared["train"] = prepared["train"].loc[~train_hash.isin(protected_hashes)].reset_index(drop=True)

    hashes = {split: set(_hash_series(frame)) for split, frame in prepared.items()}
    overlaps = {
        "train_validation": len(hashes["train"] & hashes["validation"]),
        "train_test": len(hashes["train"] & hashes["test"]),
        "validation_test": len(hashes["validation"] & hashes["test"]),
    }
    rows_after_dedup = {split: int(len(frame)) for split, frame in prepared.items()}
    dedup_removed_rows = {
        split: int(rows_before_dedup[split] - rows_after_dedup[split])
        for split in ("train", "validation", "test")
    }

    for split in ("train", "validation", "test"):
        if prepared[split]["label"].nunique() != 2:
            raise RuntimeError(
                f"After cross-split duplicate removal, prepared {split} does not contain both binary classes. "
                "Reduce requested rows or adjust the split protocol."
            )

    for split, path in outputs.items():
        prepared[split].to_csv(path, index=False, compression="gzip")

    pd.DataFrame(manifest_rows).to_csv(output_dir / "split_manifest.csv", index=False)
    raw_count_rows = []
    prepared_count_rows = []
    for label, count in sorted(global_counts.items()):
        raw_count_rows.append({"split": "all_source", "attack_category": label, "count": count})
    for split in ("train", "validation", "test"):
        for label, count in sorted(prepared[split]["attack_category"].value_counts().items()):
            prepared_count_rows.append({"split": split, "attack_category": label, "count": int(count)})
    pd.DataFrame(raw_count_rows).to_csv(output_dir / "raw_label_counts.csv", index=False)
    pd.DataFrame(prepared_count_rows).to_csv(output_dir / "prepared_label_counts.csv", index=False)

    metadata = {
        "dataset": "CICIoT2023",
        "source_csv_files": len(files),
        "label_source": "path_parent_directory",
        "label_column_detected": None,
        "benign_labels": sorted(benign_labels),
        "split_unit": "deterministic row-level sampling within top-level class folders",
        "split_seed": args.seed,
        "requested_rows": {"train": args.train_rows, "validation": args.val_rows, "test": args.test_rows},
        "source_rows_by_label": dict(sorted(global_counts.items())),
        "prepared_rows_by_split": {split: int(len(frame)) for split, frame in prepared.items()},
        "training_sampling": {
            "binary_benign_fraction": args.train_benign_fraction,
            "attack_distribution": args.train_attack_sampling,
        },
        "validation_test_sampling": "natural class proportions first; training is allocated from remaining per-class capacity",
        "sampled_row_hash_overlap_before_dedup": overlaps_before,
        "sampled_row_hash_overlap": overlaps,
        "dedup_removed_rows": dedup_removed_rows,
        "feature_columns": [c for c in prepared["train"].columns if c not in {"label", "attack_category"}],
        "important_limitations": [
            "Official class-folder CSV.zip files do not contain a row-level label column; labels are inferred from folder names.",
            "Because several official class folders are single large files, strict file-held-out splitting would omit some classes from some splits.",
            "This preparation therefore uses deterministic class-stratified row sampling; exact split protocol and sample sizes must be reported.",
            "Exact duplicate feature rows are removed across prepared splits with priority test > validation > train.",
            "The official CSV files do not expose a device identifier; this is not a device-held-out split.",
        ],
    }
    (output_dir / "preparation_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Preparation complete.")
    for split, path in outputs.items():
        print(f"  {split}: {path}")
    print(f"  metadata: {output_dir / 'preparation_metadata.json'}")
    if any(overlaps.values()):
        print(f"WARNING: sampled duplicate hashes across splits: {overlaps}", file=sys.stderr)


def main() -> None:
    args = parse_args()
    fractions = (args.train_fraction, args.val_fraction, args.test_fraction)
    if not math.isclose(sum(fractions), 1.0, abs_tol=1e-9):
        raise ValueError("train/validation/test fractions must sum to 1")
    if not 0 < args.train_benign_fraction < 1:
        raise ValueError("--train-benign-fraction must be in (0, 1)")
    if min(args.train_rows, args.val_rows, args.test_rows) < 2:
        raise ValueError("Each requested split size must be at least 2")

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    files = sorted(path for path in raw_dir.glob(args.glob) if path.is_file())
    if not files:
        raise FileNotFoundError(
            f"No CSV files found under {raw_dir} with pattern {args.glob}. "
            "Extract the official CICIoT2023 CSV directory there."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "train": output_dir / "train.csv.gz",
        "validation": output_dir / "validation.csv.gz",
        "test": output_dir / "test.csv.gz",
    }
    if not args.force and any(path.exists() for path in outputs.values()):
        raise FileExistsError(f"Prepared files already exist in {output_dir}. Use --force to overwrite.")

    first_columns = schema_signature(files[0])
    label_col = find_label_column(first_columns, args.label_col)
    for path in files[1:]:
        columns = schema_signature(path)
        if columns != first_columns:
            raise ValueError(
                f"Schema mismatch in {path.name}. All official CSV shards must have identical columns."
            )

    benign_labels = set(args.benign_label or DEFAULT_BENIGN_LABELS)
    if label_col is None:
        prepare_with_path_labels(args, raw_dir, output_dir, files, benign_labels, outputs, first_columns)
        return

    file_split = assign_files(files, args.seed, fractions)
    label_source = "csv_column" if label_col is not None else "path_parent_directory"
    print(f"Found {len(files)} CSV shards; label_source='{label_source}'; label_column={label_col!r}")
    print("Pass 1/2: counting labels in each deterministic file split...")
    split_counts: dict[str, Counter[str]] = defaultdict(Counter)
    manifest_rows = []
    for index, path in enumerate(files, start=1):
        counts = read_labels(path, label_col, args.chunk_size, raw_dir)
        split = file_split[path]
        split_counts[split].update(counts)
        manifest_rows.append({
            "file": str(path.resolve()),
            "split": split,
            "rows": int(sum(counts.values())),
            "inferred_label": infer_label_from_path(path, raw_dir) if label_col is None else "",
            "label_counts_json": json.dumps(dict(sorted(counts.items())), ensure_ascii=False),
        })
        print(f"  [{index:3d}/{len(files)}] {split:10s} {path.name} rows={sum(counts.values()):,} labels={dict(counts)}")

    targets: dict[str, dict[str, int]] = {}
    targets["train"] = training_targets(
        split_counts["train"], benign_labels, args.train_rows,
        args.train_benign_fraction, args.train_attack_sampling,
    )
    targets["validation"] = proportional_targets(split_counts["validation"], args.val_rows)
    targets["test"] = proportional_targets(split_counts["test"], args.test_rows)

    for split in ("train", "validation", "test"):
        if sum(targets[split].values()) < 2:
            raise RuntimeError(f"Insufficient rows allocated for {split}")
        binary_available = {
            0: sum(v for k, v in split_counts[split].items() if k in benign_labels),
            1: sum(v for k, v in split_counts[split].items() if k not in benign_labels),
        }
        if min(binary_available.values()) == 0:
            raise RuntimeError(
                f"Split {split} does not contain both benign and attack rows. "
                "With folder-level labels, increase the number of files or use a different split seed."
            )

    print("Pass 2/2: collecting reproducible stratified samples...")
    collected: dict[str, list[pd.DataFrame]] = defaultdict(list)
    oversample = 1.15
    file_index = {path: idx for idx, path in enumerate(files)}
    for path in files:
        split = file_split[path]
        probabilities = {
            label: min(1.0, oversample * target / max(split_counts[split][label], 1))
            for label, target in targets[split].items()
        }
        for chunk_index, chunk in enumerate(pd.read_csv(path, chunksize=args.chunk_size)):
            if label_col is None:
                inferred = infer_label_from_path(path, raw_dir)
                labels = pd.Series([inferred] * len(chunk), index=chunk.index)
            else:
                labels = chunk[label_col].map(normalized_label)
            rng = np.random.default_rng(args.seed + file_index[path] * 1_000_003 + chunk_index)
            probabilities_array = labels.map(probabilities).fillna(0.0).to_numpy(dtype=float)
            keep = rng.random(len(chunk)) < probabilities_array
            if not keep.any():
                continue
            selected = chunk.loc[keep].copy()
            selected_labels = labels.loc[keep].reset_index(drop=True)
            selected = selected.reset_index(drop=True)
            if label_col is not None and label_col in selected.columns:
                selected = selected.drop(columns=[label_col])
            selected["attack_category"] = selected_labels
            selected["label"] = (~selected_labels.isin(benign_labels)).astype(np.int8)
            collected[split].append(selected)

    prepared: dict[str, pd.DataFrame] = {}
    for split in ("train", "validation", "test"):
        if not collected[split]:
            raise RuntimeError(f"No rows collected for {split}")
        candidate = pd.concat(collected[split], ignore_index=True)
        collected[split].clear()
        candidate = candidate.replace([np.inf, -np.inf], np.nan)
        for column in candidate.columns:
            if column in {"attack_category", "label"}:
                continue
            if not pd.api.types.is_numeric_dtype(candidate[column]):
                candidate[column] = pd.to_numeric(candidate[column], errors="coerce")
        prepared[split] = exact_sample_by_label(candidate, targets[split], args.seed + 10_000)
        if prepared[split]["label"].nunique() != 2:
            raise RuntimeError(f"Prepared {split} does not contain both binary classes")
        print(
            f"  {split:10s}: {len(prepared[split]):,} rows, "
            f"benign={(prepared[split]['label'] == 0).sum():,}, "
            f"attack={(prepared[split]['label'] == 1).sum():,}"
        )

    # Q1-safety step: remove exact duplicate prepared rows across splits.
    # The official class-folder release can contain exact duplicate feature vectors.
    # If an identical feature+attack_category row appears in train and test, it is
    # not necessarily the same packet, but for a conservative paper protocol we
    # remove cross-split duplicates. Priority is: test > validation > train.
    hash_cols = [c for c in prepared["train"].columns if c != "label"]

    def _hash_series(frame: pd.DataFrame) -> pd.Series:
        return pd.util.hash_pandas_object(frame[hash_cols], index=False).astype("uint64")

    hashes_before = {split: set(_hash_series(frame)) for split, frame in prepared.items()}
    overlaps_before = {
        "train_validation": len(hashes_before["train"] & hashes_before["validation"]),
        "train_test": len(hashes_before["train"] & hashes_before["test"]),
        "validation_test": len(hashes_before["validation"] & hashes_before["test"]),
    }

    rows_before_dedup = {split: int(len(frame)) for split, frame in prepared.items()}

    # Remove validation duplicates that appear in test.
    test_hashes = set(_hash_series(prepared["test"]))
    val_hash = _hash_series(prepared["validation"])
    prepared["validation"] = prepared["validation"].loc[~val_hash.isin(test_hashes)].reset_index(drop=True)

    # Remove training duplicates that appear in test or validation.
    protected_hashes = set(_hash_series(prepared["test"])) | set(_hash_series(prepared["validation"]))
    train_hash = _hash_series(prepared["train"])
    prepared["train"] = prepared["train"].loc[~train_hash.isin(protected_hashes)].reset_index(drop=True)

    hashes = {split: set(_hash_series(frame)) for split, frame in prepared.items()}
    overlaps = {
        "train_validation": len(hashes["train"] & hashes["validation"]),
        "train_test": len(hashes["train"] & hashes["test"]),
        "validation_test": len(hashes["validation"] & hashes["test"]),
    }
    rows_after_dedup = {split: int(len(frame)) for split, frame in prepared.items()}
    dedup_removed_rows = {
        split: int(rows_before_dedup[split] - rows_after_dedup[split])
        for split in ("train", "validation", "test")
    }

    for split in ("train", "validation", "test"):
        if prepared[split]["label"].nunique() != 2:
            raise RuntimeError(
                f"After cross-split duplicate removal, prepared {split} does not contain both binary classes. "
                "Reduce requested rows or adjust the split protocol."
            )

    for split, path in outputs.items():
        prepared[split].to_csv(path, index=False, compression="gzip")

    pd.DataFrame(manifest_rows).to_csv(output_dir / "split_manifest.csv", index=False)
    raw_count_rows = []
    prepared_count_rows = []
    for split in ("train", "validation", "test"):
        for label, count in sorted(split_counts[split].items()):
            raw_count_rows.append({"split": split, "attack_category": label, "count": count})
        for label, count in sorted(prepared[split]["attack_category"].value_counts().items()):
            prepared_count_rows.append({"split": split, "attack_category": label, "count": int(count)})
    pd.DataFrame(raw_count_rows).to_csv(output_dir / "raw_label_counts.csv", index=False)
    pd.DataFrame(prepared_count_rows).to_csv(output_dir / "prepared_label_counts.csv", index=False)

    metadata = {
        "dataset": "CICIoT2023",
        "source_csv_shards": len(files),
        "label_source": label_source,
        "label_column_detected": label_col,
        "benign_labels": sorted(benign_labels),
        "split_unit": "CSV file shard",
        "split_seed": args.seed,
        "requested_split_fractions": {
            "train": args.train_fraction,
            "validation": args.val_fraction,
            "test": args.test_fraction,
        },
        "raw_rows_by_split": {split: int(sum(split_counts[split].values())) for split in split_counts},
        "prepared_rows_by_split": {split: int(len(frame)) for split, frame in prepared.items()},
        "training_sampling": {
            "binary_benign_fraction": args.train_benign_fraction,
            "attack_distribution": args.train_attack_sampling,
        },
        "validation_test_sampling": "natural category proportions within each held-out shard split",
        "sampled_row_hash_overlap_before_dedup": overlaps_before,
        "sampled_row_hash_overlap": overlaps,
        "dedup_removed_rows": dedup_removed_rows,
        "feature_columns": [c for c in prepared["train"].columns if c not in {"label", "attack_category"}],
        "important_limitations": [
            "The official class-folder CSV.zip release does not expose a row-level label column; labels are inferred from folder names.",
            "The official CSV files do not expose a device identifier.",
            "The split is file/shard-held-out, not device-held-out or temporal-held-out.",
            "The prepared files are reproducible samples of the full release; exact sample sizes must be reported.",
        ],
    }
    (output_dir / "preparation_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Preparation complete.")
    for split, path in outputs.items():
        print(f"  {split}: {path}")
    print(f"  metadata: {output_dir / 'preparation_metadata.json'}")
    if any(overlaps.values()):
        print(f"WARNING: sampled duplicate hashes across splits: {overlaps}", file=sys.stderr)


if __name__ == "__main__":
    main()
