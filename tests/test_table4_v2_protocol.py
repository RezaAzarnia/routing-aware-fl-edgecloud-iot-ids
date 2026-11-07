"""Table 4 v2 protocol: arm definitions, single-factor derivation from locked parents, manifest integrity, duplicate-run locking, resume safety."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "table4_v2"))
import importlib.util  # noqa: E402

import t4_common as t4  # noqa: E402

# unique module name: other tests import scripts/phase6c/orchestrator.py as "orchestrator"
_spec = importlib.util.spec_from_file_location("t4_orchestrator", ROOT / "scripts" / "table4_v2" / "orchestrator.py")
orch = importlib.util.module_from_spec(_spec)
sys.modules["t4_orchestrator"] = orch
_spec.loader.exec_module(orch)


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict):
            o.update(flat(v, p + k + "."))
        else:
            o[p + k] = v
    return o


BOOK = {"experiment.name", "experiment.method_name", "experiment.variant_name", "experiment.output_dir", "experiment.algorithm_version"}


@pytest.mark.parametrize("ds", t4.DATASETS)
@pytest.mark.parametrize("arm", list(t4.NEW_ARMS))
def test_new_arm_differs_from_locked_parent_only_in_declared_fields(ds, arm):
    parent, role, desc, ch = t4.NEW_ARMS[arm]
    a = flat(yaml.safe_load((ROOT / f"configs/phase6c/{ds}_{parent}.yaml").read_text(encoding="utf-8")))
    b = flat(yaml.safe_load((t4.CFG_DIR / f"{ds}_{arm}.yaml").read_text(encoding="utf-8")))
    diff = {k for k in set(a) | set(b) if a.get(k) != b.get(k)} - BOOK
    assert diff == set(ch)
    assert b["data.test_csv"] == "" and b["experiment.validation_only"] is True and b["experiment.output_dir"] == t4.OUT_ROOT
    assert b["routing.trace_mode"] == "matched" and b["attack.assignment"] == "exposure_controlled"


def test_arm_semantics():
    cfg = lambda ds, arm: yaml.safe_load((t4.CFG_DIR / f"{ds}_{arm}.yaml").read_text(encoding="utf-8"))   # noqa: E731
    for ds in t4.DATASETS:
        e1, e2, e3, e4 = (cfg(ds, a) for a in t4.NEW_ARMS)
        assert e1["aggregation"]["method"] == "fedavg" and not e1["failure"]["recovery_enabled"] and e1["privacy"]["mode"] == "none"
        assert e1["routing"]["selection_policy"] == "uniform_random" and e1["routing"]["path_policy"] == "random"
        assert e2["aggregation"]["method"] == "distance_filter" and not e2["failure"]["recovery_enabled"] and e2["privacy"]["mode"] == "none"
        assert e3["aggregation"]["method"] == "fedavg" and e3["privacy"]["mode"] == "central_client" and e3["privacy"]["target_epsilon"] == 10.0
        assert e3["privacy"]["auto_calibrate_noise"] and e3["privacy"]["max_client_weight_share"] == 0.1
        assert e4["privacy"]["target_epsilon"] == 20.0 and e4["failure"]["recovery_enabled"] and e4["routing"].get("selection_policy", "top_k") == "top_k"
        assert e4["routing"].get("path_policy", "default") == "default"


def test_noise_calibration_matches_manuscript_values():
    from src.privacy import calibrate_noise_multiplier
    assert abs(calibrate_noise_multiplier(10.0, 30, 1e-5, 0.2) - 0.9939) < 5e-4
    assert abs(calibrate_noise_multiplier(20.0, 30, 1e-5, 0.2) - 0.6717) < 5e-4


@pytest.mark.skipif(not t4.MANIFEST.exists(), reason="manifest not built yet")
def test_manifest_integrity_and_scope():
    m = t4.load_manifest(t4.MANIFEST)                       # raises if modified after locking
    assert m["n_runs"] == 40 and len({r["run_id"] for r in m["runs"]}) == 40
    assert set(r["seed"] for r in m["runs"]) == set(t4.SEEDS) and m["rounds"] == 30
    assert {r["dataset"] for r in m["runs"]} == set(t4.DATASETS) and {r["arm"] for r in m["runs"]} == set(t4.NEW_ARMS)
    assert m["locked_test"] == {} and all(r["out_dir"].startswith(t4.OUT_ROOT + "/") for r in m["runs"])
    for r in m["runs"]:
        assert t4.sha256_text_file(ROOT / r["config"]) == r["config_sha256"]


def test_runner_lock_blocks_live_owner_and_replaces_stale(tmp_path):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        lock = orch.state_dir(tmp_path) / "locks" / "x.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"pid": child.pid}), encoding="utf-8")
        assert orch.acquire_run_lock(tmp_path, "x") is False           # live owner: no duplicate execution
    finally:
        child.kill(); child.wait()
    assert orch.acquire_run_lock(tmp_path, "x") is True                # owner dead: stale lock replaced and logged
    orch.release_run_lock(tmp_path, "x")
    assert orch.acquire_runner_lock(tmp_path) is True
    orch.release_runner_lock(tmp_path)
    events = (orch.state_dir(tmp_path) / "events.jsonl").read_text(encoding="utf-8")
    assert "stale_lock_removed" in events


def test_incomplete_and_failed_directories_are_never_reused(tmp_path):
    run = {"run_id": "r", "out_dir": "results_table4_controlled_v2/unsw/a/seed_12"}
    out = tmp_path / run["out_dir"]
    assert orch.run_status(run, {}, tmp_path)[0] == "pending"
    out.mkdir(parents=True)
    (out / "round_metrics.csv").write_text("x")
    assert orch.run_status(run, {}, tmp_path)[0] == "incomplete"
    (out / "FAILED.json").write_text("{}")
    assert orch.run_status(run, {}, tmp_path)[0] == "failed"
