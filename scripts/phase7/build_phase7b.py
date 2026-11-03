"""Build the Phase 7b manifest: identical experimental design and configs as Phase 7, but locked to the repaired metrics code.

usage: python scripts/phase7/build_phase7b.py
Phase 7 (docs/phase7, configs/phase7, results_phase7) is only READ. Config files are byte-copies (same SHA-256 as Phase 7), so the
only difference between Phase 7 and Phase 7b is src/metrics.py (decision-rule fix). Results go to results_phase7b/.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import code_fingerprint, git_head, manifest_hash, now_utc, sha256_text_file  # noqa: E402

m7 = json.loads((ROOT / "docs" / "phase7" / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
dst = ROOT / "configs" / "phase7b"
dst.mkdir(exist_ok=True)
for src in sorted((ROOT / "configs" / "phase7").glob("*.yaml")):
    shutil.copyfile(src, dst / src.name)
globs = [g.replace("configs/phase7/", "configs/phase7b/") for g in m7["code_fingerprint_globs"]]
runs = []
for r in m7["runs"]:
    r = dict(r)
    r["config"] = r["config"].replace("phase7/", "phase7b/")
    r["out_dir"] = r["out_dir"].replace("results_phase7/", "results_phase7b/")
    assert sha256_text_file(ROOT / r["config"]) == r["config_sha256"]          # byte-identical to Phase 7
    runs.append(r)
m = dict(m7)
m.update({"schema": "iot-fl/phase7b-manifest/1", "created_utc": now_utc(), "git_commit_at_build": git_head(),
          "purpose": "Phase 7b: Phase 7 design re-run under the repaired decision rule (src/metrics.py); same seeds 17-21, same configs",
          "code_fingerprint_globs": globs, "code_fingerprint": code_fingerprint(ROOT, globs), "runs": runs,
          "supersedes": {"phase7_manifest_sha256": m7["manifest_sha256"], "phase7_code_fingerprint": m7["code_fingerprint"],
                         "reason": "confirmed inconsistency: threshold selected on raw scores but applied to scores clipped to 1-1e-7 (false F1=0 at threshold 1.0; AUC ties)",
                         "disclosure": "Phase 7 seed 17 (and part of seed 18) outcomes were inspected while diagnosing the bug; seeds are kept, pre-registered criteria unchanged"}})
m.pop("manifest_sha256", None)
m["manifest_sha256"] = manifest_hash(m)
out = ROOT / "docs" / "phase7b"
out.mkdir(exist_ok=True)
(out / "EXPERIMENT_MANIFEST.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
(out / "EXPERIMENT_MANIFEST.sha256").write_text(m["manifest_sha256"] + "\n", encoding="utf-8")
print(f"Phase 7b manifest: {len(runs)} runs ({m['n_runs_mandatory']} mandatory) sha256 {m['manifest_sha256'][:16]}... fingerprint {m['code_fingerprint'][:12]}")
