"""Read-only verification of locked manifests against run folders (Phase 6C, 7, 7b). Never opens test data."""
import glob, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import load_manifest, verify_run_dir, sha256_text_file
for name, mp in (("6C", "docs/phase6c/EXPERIMENT_MANIFEST.json"), ("7", "docs/phase7/EXPERIMENT_MANIFEST.json"), ("7b", "docs/phase7b/EXPERIMENT_MANIFEST.json")):
    M = load_manifest(ROOT / mp)
    ok = bad = miss = 0
    for r in M["runs"]:
        d = ROOT / r["out_dir"]
        if not (d / "COMPLETE.json").exists():
            miss += 1
        elif verify_run_dir(d, r, M):
            bad += 1
        else:
            ok += 1
    cfg = sum(sha256_text_file(ROOT / r["config"]) == r["config_sha256"] for r in M["runs"])
    print(f"Phase {name}: runs={len(M['runs'])} verified={ok} corrupt={bad} not_complete={miss} config_hash_ok={cfg}")
n = 0
for c in glob.glob(str(ROOT / "configs" / "phase*" / "*.yaml")):
    y = yaml.safe_load(open(c, encoding="utf-8"))
    if "phase8" in c:
        continue
    assert y["data"].get("test_csv", "") == "" and y["experiment"].get("validation_only") is True, c
    n += 1
print("configs validation-only with empty test_csv:", n)
