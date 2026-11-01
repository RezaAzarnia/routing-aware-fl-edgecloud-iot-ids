from __future__ import annotations

import json
from pathlib import Path

import yaml


REPORT = Path("results/pilot_unsw_v4/PILOT_REPORT.json")
CONFIG = Path("configs/full.yaml")


APPROVED_VERDICTS = {
    "GO_CORE",
    "GO_CORE_WITH_CALIBRATION_SHIFT",
    "GO_CORE_EPS20",
    "GO_CORE_EPS20_WITH_CALIBRATION_SHIFT",
}


def main() -> None:
    if not REPORT.exists():
        raise SystemExit(
            f"Missing {REPORT}. Run the complete one-seed pilot before the five-seed core suite."
        )
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    verdict = report.get("verdict")
    epsilon = report.get("recommended_privacy_target")
    if verdict not in APPROVED_VERDICTS or epsilon is None:
        raise SystemExit(
            f"Pilot verdict is {verdict!r}; no five-seed run should be started yet."
        )

    raw = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    raw["privacy"]["target_epsilon"] = float(epsilon)
    CONFIG.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Updated {CONFIG}: privacy.target_epsilon={float(epsilon)}")


if __name__ == "__main__":
    main()
