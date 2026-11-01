from __future__ import annotations

import json
from pathlib import Path

import yaml


REPORT = Path("results/pilot_unsw_v4/CLIP_SWEEP_REPORT.json")
CONFIGS = [Path("configs/pilot.yaml"), Path("configs/full.yaml")]


def main() -> None:
    if not REPORT.exists():
        raise SystemExit(f"Missing {REPORT}. Run the one-seed clip sweep first.")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    verdict = report.get("verdict")
    clip_norm = report.get("recommended_clip_norm")
    if verdict != "USE_RECOMMENDED_CLIP" or clip_norm is None:
        raise SystemExit(
            f"Clip-sweep verdict is {verdict!r}; do not start the DP pilot yet."
        )

    for config in CONFIGS:
        raw = yaml.safe_load(config.read_text(encoding="utf-8"))
        raw["privacy"]["clip_norm"] = float(clip_norm)
        config.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"Updated {config}: privacy.clip_norm={float(clip_norm)}")


if __name__ == "__main__":
    main()
