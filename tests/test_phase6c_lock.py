"""Guards on the REAL locked Phase-6C manifest: seeds, arm counts, hashes, test-path protection."""
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import code_fingerprint, load_manifest, manifest_hash, sha256_text_file  # noqa: E402

MANIFEST = ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"
pytestmark = pytest.mark.skipif(not MANIFEST.exists(), reason="manifest not built")


def test_manifest_is_internally_consistent_and_locked():
    m = load_manifest(MANIFEST)                       # raises if the hash does not verify
    assert m["manifest_sha256"] == manifest_hash(m)
    assert (ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.sha256").read_text().strip() == m["manifest_sha256"]
    assert m["seeds"] == [12, 13, 14, 15, 16] and m["rounds"] == 30
    assert m["n_runs"] == len(m["runs"]) == 240
    assert len({r["run_id"] for r in m["runs"]}) == 240
    assert len({r["out_dir"] for r in m["runs"]}) == 240
    arms = {a["arm"] for a in m["arms"]}
    assert len(arms) == 24
    for dataset in ("unsw", "ciciot"):
        sub = [r for r in m["runs"] if r["dataset"] == dataset]
        assert len(sub) == 120 and {r["seed"] for r in sub} == {12, 13, 14, 15, 16}
    assert {a["algorithm_version"] for a in m["arms"]} == {"reference_v1_historical", "corrected_v2_phase6c"}
    for a in m["arms"]:
        assert a["compare_with"] in (None, *arms)


def test_locked_configs_match_their_hashes_and_cannot_read_test_data(phase6c_tree):
    m = load_manifest(MANIFEST)
    assert code_fingerprint(phase6c_tree) == m["code_fingerprint"], "training code/configs changed after locking: rebuild the manifest deliberately"
    for run in m["runs"]:
        path = ROOT / run["config"]
        assert sha256_text_file(path) == run["config_sha256"]
    seen = set()
    for run in m["runs"]:
        if run["config"] in seen:
            continue
        seen.add(run["config"])
        raw = yaml.safe_load((ROOT / run["config"]).read_text(encoding="utf-8"))
        assert raw["experiment"]["validation_only"] is True
        assert raw["data"]["test_csv"] == ""
        assert raw["data"]["validation_three_way"] is True
        assert raw["data"]["enable_calibrated_evaluation"] is False
        assert raw["experiment"]["early_stopping_patience"] is None
        assert raw["routing"]["trace_mode"] == "matched"
        assert raw["fl"]["rounds"] == 30 and raw["experiment"]["device"] == "cpu"
    assert len(seen) == 48


def test_command_template_is_training_only_and_final_test_is_locked_separately():
    m = load_manifest(MANIFEST)
    assert "final_test" not in " ".join(m["command"])
    assert m["command"][1].endswith("run_one.py")
    assert set(m["locked_test"]) == {"unsw", "ciciot"}
    assert m["locked_test"]["unsw"]["sha256"].startswith("734fe664")


def test_arm_definitions_match_the_protocol():
    from src.config import Config

    def cfg(arm):
        return Config.from_yaml(ROOT / "configs" / "phase6c" / f"unsw_{arm}.yaml")

    ref, cor = cfg("reference"), cfg("corrected")
    assert (ref.routing.selection_policy, ref.routing.delivery_model, ref.aggregation.surrogate_handling) == ("top_k", "independent_draws", "reference")
    assert ref.fl.weighting == "sample_proportional" and ref.failure.surrogate_total_weight_cap is None
    assert (cor.routing.selection_policy, cor.routing.delivery_model, cor.aggregation.surrogate_handling) == ("coverage_aware", "packet_coupled", "post_filter_real_only")
    assert cor.failure.surrogate_total_weight_cap == 0.10
    assert ref.attack.assignment == cor.attack.assignment == "exposure_controlled"
    assert cfg("nat_reference").attack.assignment == "natural_fixed_clients"
    assert cfg("reference_gaussian").privacy.mode == "central_client" and ref.privacy.mode == "none"
    assert cfg("clean_centralized").fl.num_clients == 1
    assert ref.experiment.algorithm_version == "reference_v1_historical" and cor.experiment.algorithm_version == "corrected_v2_phase6c"
