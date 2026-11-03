"""Phase 7 manifest/config integrity: new seeds, comparators identical to Phase 6C, guard arms differ only by the guard."""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import code_fingerprint, load_manifest, sha256_text_file  # noqa: E402

M7 = ROOT / "docs" / "phase7" / "EXPERIMENT_MANIFEST.json"


def test_manifest_is_locked_and_uses_new_disjoint_seeds():
    m = load_manifest(M7)                                    # raises when the manifest was edited after locking
    p6 = load_manifest(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json")
    assert set(m["seeds"]).isdisjoint(p6["seeds"]) and m["seeds"] == [17, 18, 19, 20, 21]
    assert m["n_runs"] == 80 and m["n_runs_mandatory"] == 40
    assert {r["tier"] for r in m["runs"] if r["dataset"] == "unsw"} == {"mandatory"}
    assert code_fingerprint(ROOT, m["code_fingerprint_globs"]) == m["code_fingerprint"]
    for r in m["runs"]:
        assert sha256_text_file(ROOT / r["config"]) == r["config_sha256"]


def test_comparators_are_verbatim_phase6c_configs_and_guard_arms_differ_only_by_the_guard():
    m = load_manifest(M7)
    for r in m["runs"]:
        if r["phase6c_config_sha256"]:                         # unchanged comparator
            assert r["config_sha256"] == r["phase6c_config_sha256"]
        raw = yaml.safe_load((ROOT / r["config"]).read_text(encoding="utf-8"))
        assert raw["experiment"]["validation_only"] is True and raw["data"]["test_csv"] == "" and raw["fl"]["rounds"] == 30
        assert raw["experiment"]["device"] == "cpu"
    pairs = {"p7_corrected_guard": "corrected", "fail0p3_p7_corrected_guard": "fail0p3_corrected", "p7_delivery_guard": "ctl_delivery_coupled"}
    for guard_arm, base_arm in pairs.items():
        for ds in ("unsw", "ciciot"):
            g = yaml.safe_load((ROOT / f"configs/phase7/{ds}_{guard_arm}.yaml").read_text(encoding="utf-8"))
            b = yaml.safe_load((ROOT / f"configs/phase6c/{ds}_{base_arm}.yaml").read_text(encoding="utf-8"))
            assert g["aggregation"].pop("min_real_updates") == 3
            for k in ("algorithm_version", "variant_name", "method_name", "name"):
                g["experiment"].pop(k), b["experiment"].pop(k)
            assert g == b, f"{guard_arm}/{ds} differs from {base_arm} by more than the guard"
