from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from prepare_ciciot2023 import find_label_column, infer_label_from_path, normalized_label


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick CICIoT2023 schema and sample check")
    parser.add_argument("--raw-dir", default="data/CICIoT2023/raw_csv")
    parser.add_argument("--glob", default="**/*.csv")
    parser.add_argument("--sample-files", type=int, default=8)
    parser.add_argument("--rows-per-file", type=int, default=50000)
    parser.add_argument(
        "--label-col", default="auto",
        help="Use 'auto' for CSV label column detection or path-based labels; use 'path' to force folder-name labels.",
    )
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    files = sorted(path for path in raw_dir.glob(args.glob) if path.is_file())
    if not files:
        raise SystemExit(f"No CSV files found under {raw_dir}. Extract the official CSV folder there.")

    print(f"CSV files found: {len(files)}")
    header = pd.read_csv(files[0], nrows=0)
    label_col = find_label_column(header.columns, args.label_col)
    label_source = "csv_column" if label_col is not None else "path_parent_directory"
    print(f"Label source: {label_source}")
    print(f"Detected label column: {label_col}")
    print(f"Columns: {len(header.columns)}")
    print("Column names:")
    for column in header.columns:
        print(f"  - {column}")

    counts: dict[str, int] = {}
    sampled_files = files[: max(1, args.sample_files)]
    print("\nSampled files:")
    for path in sampled_files:
        frame = pd.read_csv(path, nrows=args.rows_per_file)
        if list(frame.columns) != list(header.columns):
            raise SystemExit(f"Schema mismatch: {path}")
        if label_col is None:
            local_label = infer_label_from_path(path, raw_dir)
            local = {local_label: len(frame)}
        else:
            local = frame[label_col].map(normalized_label).value_counts().to_dict()
        print(f"\n{path.relative_to(raw_dir)}: sampled rows={len(frame):,}, labels={len(local)}")
        for key, value in sorted(local.items(), key=lambda item: item[1], reverse=True)[:15]:
            print(f"  {key}: {value:,}")
        for key, value in local.items():
            counts[key] = counts.get(key, 0) + int(value)

    print("\nCombined sampled-label counts:")
    for key, value in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        print(f"  {key}: {value:,}")

    top_level_dirs = sorted({p.relative_to(raw_dir).parts[0] for p in files if len(p.relative_to(raw_dir).parts) >= 2})
    print(f"\nTop-level label folders detected: {len(top_level_dirs)}")
    for label in top_level_dirs[:80]:
        print(f"  - {label}")
    if len(top_level_dirs) > 80:
        print(f"  ... {len(top_level_dirs) - 80} more")
    print("\nSchema check completed successfully.")


if __name__ == "__main__":
    main()
