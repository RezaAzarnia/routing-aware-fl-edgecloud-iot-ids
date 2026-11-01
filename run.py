from __future__ import annotations

import argparse
from pathlib import Path

from src.config import Config
from src.experiment import run_experiment
from src.suites import build_suite
from src.summary import (
    create_clip_sweep_report,
    create_pilot_report,
    create_pilot_stage1_report,
    summarize_experiment,
)


SUITES = [
    "single",
    "smoke",
    "preflight",  # backward-compatible alias for smoke
    "pilot_stage1",
    "pilot_stage2",
    "pilot",
    "baselines",
    "baselines_only",
    "ablation",
    "core",
    "attack_sweep",
    "attack_type_sweep",
    "failure_sweep",
    "heterogeneity_sweep",
    "privacy_sweep",
    "clip_sweep",
    "full",
]


def parse_seeds(text: str) -> list[int]:
    seeds = [int(item.strip()) for item in text.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required")
    return seeds


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Federated learning IDS experiments for UNSW-NB15 and CICIoT2023"
    )
    parser.add_argument("--config", default="configs/pilot.yaml")
    parser.add_argument("--suite", default="pilot_stage1", choices=SUITES)
    parser.add_argument("--seeds", default="1", help="Comma-separated seeds, e.g. 1,2,3,4,5")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip runs that already contain final_test_metrics.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List planned runs without training",
    )
    args = parser.parse_args()

    base = Config.from_yaml(args.config)
    seeds = parse_seeds(args.seeds)
    variants = build_suite(base, args.suite)
    planned = len(variants) * len(seeds)

    print(f"Planned suite: {args.suite}")
    print(f"Variants: {len(variants)} | Seeds: {seeds} | Total runs: {planned}")
    for variant in variants:
        print(f"  - {variant.experiment.method_name}")
    if args.dry_run:
        return

    completed = 0
    skipped = 0
    for variant in variants:
        for seed in seeds:
            cfg = variant.clone()
            cfg.experiment.seed = seed
            target = (
                Path(cfg.experiment.output_dir)
                / cfg.experiment.name
                / cfg.experiment.method_name
                / f"seed_{seed}"
                / "final_test_metrics.json"
            )
            if args.skip_existing and target.exists():
                skipped += 1
                print(f"SKIP existing: {target}")
                continue
            print("=" * 80)
            print(
                f"Experiment={cfg.experiment.name} | method={cfg.experiment.method_name} | seed={seed}"
            )
            print("=" * 80)
            output = run_experiment(cfg)
            completed += 1
            print(f"Saved run outputs to: {output}")

    experiment_dir = Path(base.experiment.output_dir) / base.experiment.name
    if base.experiment.validation_only:
        print("Validation-only run: suite summary (which requires final test metrics) is skipped.")
        print(f"Completed={completed} | Skipped=0")
        return
    summary = summarize_experiment(
        experiment_dir, create_plots=base.experiment.create_plots
    )
    print(f"Saved suite summary to: {summary}")

    report = None
    if args.suite == "pilot_stage1":
        report = create_pilot_stage1_report(experiment_dir)
    elif args.suite in {"pilot_stage2", "pilot"}:
        report = create_pilot_report(experiment_dir)
    elif args.suite == "clip_sweep":
        report = create_clip_sweep_report(experiment_dir)

    if report is not None:
        print(f"Saved decision report to: {report}")
        print(report.read_text(encoding="utf-8"))
    print(f"Completed={completed} | Skipped={skipped}")


if __name__ == "__main__":
    main()
