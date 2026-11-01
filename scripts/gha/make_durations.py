"""Derive per-(dataset, arm) wall-clock estimates (seconds) for a GitHub-hosted 2-vCPU runner.

Inputs (measured here): run time of the reference arm limited to 2 physical cores / 2 threads on the author's PC
(UNSW 76 s, CICIoT2023 165 s, incl. start-up) and the relative cost of arms from the 6 verified local UNSW runs.
Assumptions (explicit, NOT measured on GitHub): hosted vCPUs are ~2x slower than the author's cores, plus a 1.25x safety margin.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = {"unsw": 76.0, "ciciot": 165.0}
CLOUD_SLOWDOWN, SAFETY = 2.0, 1.25
FACTOR = {"clean_centralized": {"unsw": 2.2, "ciciot": 4.0}}
COUPLED = {"corrected", "corrected_gaussian", "ctl_delivery_coupled", "nat_corrected", "fail0p3_corrected"}
GAUSS = {"reference_gaussian", "corrected_gaussian"}
manifest = json.loads((ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
out = {"_derivation": "base 2-core wall seconds x arm factor x cloud slowdown 2.0 x safety 1.25; see scripts/gha/make_durations.py",
       "_base_seconds_measured_2cores": BASE, "_cloud_slowdown_assumed": CLOUD_SLOWDOWN, "_safety": SAFETY}
for a in manifest["arms"]:
    for ds in ("unsw", "ciciot"):
        f = FACTOR.get(a["arm"], {}).get(ds, 1.0)
        if a["arm"] in COUPLED:
            f *= 1.2
        if a["arm"] in GAUSS:
            f *= 1.05
        out[f"{ds}/{a['arm']}"] = round(BASE[ds] * f * CLOUD_SLOWDOWN * SAFETY, 1)
Path(ROOT / "scripts" / "gha" / "durations_gha.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
total = sum(out[f"{r['dataset']}/{r['arm']}"] for r in manifest["runs"])
print(f"estimated total run time for all {len(manifest['runs'])} runs: {total / 60:.0f} min ({total / 3600:.1f} h)")
