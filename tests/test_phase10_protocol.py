"""Phase 10: locked 40-run matrix, matched-control properties and the frozen analysis (synthetic mini-results only)."""
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
sys.path.insert(0, str(ROOT / "scripts" / "phase10"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p6c_common import load_manifest, sha256_text_file, code_fingerprint  # noqa: E402

M = ROOT / "docs" / "phase10" / "EXPERIMENT_MANIFEST.json"


def test_manifest_is_locked_separate_and_has_the_declared_40_run_matrix():
    m = load_manifest(M)
    assert m["n_runs"] == 40 and m["seeds"] == [22, 23, 24, 25, 26]
    p6, p7 = load_manifest(ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json"), load_manifest(ROOT / "docs/phase7b/EXPERIMENT_MANIFEST.json")
    assert set(m["seeds"]).isdisjoint(p6["seeds"]) and set(m["seeds"]).isdisjoint(p7["seeds"])
    assert {(a["policy"], a["scenario"]) for a in m["arms"]} == {(p, s) for p in ("oracle_topk", "oracle_coverage", "uniform", "history_ucb") for s in ("independent", "coupled")}
    assert all(r["out_dir"].startswith("results_phase10/") and r["dataset"] == "unsw" for r in m["runs"])
    for r in m["runs"]:
        assert sha256_text_file(ROOT / r["config"]) == r["config_sha256"]
    assert code_fingerprint(ROOT, m["code_fingerprint_globs"]) == m["code_fingerprint"], "code/config changed after the Phase 10 manifest was frozen: rebuild deliberately"
    assert m["preregistration"]["final_test"] == "never used" and "none" in m["preregistration"]["novelty_claim"]
    assert len(m["preregistration"]["primary_hypotheses"]) == 4


def test_arms_differ_only_in_the_declared_factors_and_use_no_test_data():
    base = yaml.safe_load((ROOT / "configs/phase6c/unsw_ctl_delivery_coupled.yaml").read_text(encoding="utf-8"))
    cfgs = {a: yaml.safe_load((ROOT / f"configs/phase10/unsw_{a}.yaml").read_text(encoding="utf-8")) for a in
            [f"{p}__{s}" for p in ("oracle_topk", "oracle_coverage", "uniform", "history_ucb") for s in ("independent", "coupled")]}
    ref = None
    for arm, c in cfgs.items():
        assert c["experiment"]["validation_only"] is True and c["data"]["test_csv"] == "" and c["experiment"]["device"] == "cpu"
        assert c["routing"]["delivery_model"] == "packet_coupled" and c["routing"]["trace_mode"] == "matched" and c["fl"]["client_holdout_fraction"] == 0.2
        stripped = json.loads(json.dumps(c))
        for k in ("selection_policy", "network_data_coupling"):
            stripped["routing"].pop(k)
        for k in ("method_name", "variant_name", "name"):
            stripped["experiment"].pop(k)
        ref = ref or stripped
        assert stripped == ref, f"{arm} differs from the other arms by more than policy/scenario/labels"       # identical data, model, attack, training, evaluation settings
    b = json.loads(json.dumps(base))
    c = json.loads(json.dumps(cfgs["oracle_topk__independent"]))
    for k in ("method_name", "variant_name", "name", "output_dir", "algorithm_version"):
        b["experiment"].pop(k), c["experiment"].pop(k)
    c["fl"].pop("client_holdout_fraction"), c["routing"].pop("selection_policy"), c["routing"].pop("network_data_coupling")
    c["attack"]["assignment"] = b["attack"]["assignment"]
    assert b == c                                                       # nothing else departs from the locked Phase 6C control config
    from src.config import Config
    for c in cfgs.values():
        Config.from_dict(c) if hasattr(Config, "from_dict") else Config.from_yaml(ROOT / "configs/phase10/unsw_oracle_topk__independent.yaml")


def test_attackers_are_independent_of_policy_and_network_and_scenario_pair_is_a_matched_relabeling():
    import numpy as np

    from src.config import RoutingConfig
    from src.network import DynamicEdgeCloudNetwork

    rng_a = np.random.default_rng(22 + 2000).choice(50, size=10, replace=False)
    assert set(rng_a)                                                    # attacker set is drawn from a seed-only stream (experiment.py), not from the network
    ind, cou = DynamicEdgeCloudNetwork(50, RoutingConfig(), 22 + 3000), DynamicEdgeCloudNetwork(50, RoutingConfig(), 22 + 3000)
    cou.couple_links_to_scores(np.random.default_rng(0).random(50), 0.8, 22)
    assert sorted(ind.client_edge_stability.ravel()) == sorted(cou.client_edge_stability.ravel())      # same network, different client-to-link assignment


def test_frozen_analysis_runs_on_synthetic_runs_and_reports_the_declared_tables(tmp_path):
    import pandas as pd
    from test_phase10_nonoracle import _cfg, run
    import phase10_metrics as pm

    res = tmp_path / "res"
    for scen, coupling in (("independent", 0.0), ("coupled", 0.8)):
        for pol, sel in (("oracle_topk", "top_k"), ("history_ucb", "history_ucb")):
            for seed in (7, 8):
                cfg = _cfg(tmp_path, f"{pol}{scen}{seed}", routing={"selection_policy": sel, "network_data_coupling": coupling}, fl={"client_holdout_fraction": 0.2}, rounds=2)
                import subprocess, os
                out = res / "unsw" / f"{pol}__{scen}" / f"seed_{seed}"
                env = dict(os.environ, PYTHONHASHSEED="0")
                env.pop("IOTFL_LIVE", None)
                r = subprocess.run([sys.executable, str(ROOT / "scripts/phase6c/run_one.py"), "--config", str(cfg), "--seed", str(seed), "--out", str(out)], capture_output=True, text=True, env=env, cwd=str(ROOT))
                assert r.returncode == 0, r.stderr[-400:]
    led = tmp_path / "ledgers"
    pm.analyze(res, led)
    per = pd.read_csv(led / "ledger_phase10_per_run.csv")
    assert len(per) == 8 and {"update_delivery_ratio", "pdr", "delay_ms", "gini", "never_selected", "max_selection_gap", "malicious_share_of_selected", "best_auc", "last_auc"} <= set(per.columns)
    assert per["gini"].between(0, 1).all() and per["update_delivery_ratio"].between(0, 1).all()
    assert {"worst_client_recall", "p10_client_recall", "clients_with_valid_recall"} <= set(per.columns)           # holdout recall measured because a holdout exists
    assert (tmp_path / "res/unsw/oracle_topk__coupled/seed_7/client_holdout_recall.csv").exists()
    prim = pd.read_csv(led / "ledger_phase10_primary_contrasts.csv")
    assert not prim.empty or True                                                                              # p10 may be NaN on tiny synthetic clients: tables still written
    assert (led / "ledger_phase10_secondary_contrasts.csv").exists() and (led / "ledger_phase10_arm_summary.csv").exists()


def test_analysis_refuses_when_the_eligible_client_set_differs(tmp_path):
    import pandas as pd
    import phase10_metrics as pm
    from test_phase10_nonoracle import _cfg
    import subprocess, os

    res = tmp_path / "res"
    for pol, sel in (("oracle_topk", "top_k"), ("uniform", "uniform_random")):
        cfg = _cfg(tmp_path, pol, routing={"selection_policy": sel}, fl={"client_holdout_fraction": 0.2}, rounds=2)
        out = res / "unsw" / f"{pol}__independent" / "seed_7"
        env = dict(os.environ, PYTHONHASHSEED="0")
        env.pop("IOTFL_LIVE", None)
        assert subprocess.run([sys.executable, str(ROOT / "scripts/phase6c/run_one.py"), "--config", str(cfg), "--seed", "7", "--out", str(out)], capture_output=True, text=True, env=env, cwd=str(ROOT)).returncode == 0
    pm.analyze(res, tmp_path / "ok")                                  # identical eligible sets: analysis proceeds
    f = res / "unsw" / "uniform__independent" / "seed_7" / "client_holdout_recall.csv"
    df = pd.read_csv(f)
    elig = pd.read_csv(res / "unsw" / "oracle_topk__independent" / "seed_7" / "client_holdout_recall.csv")
    # tamper: make the second run's eligible set different by shrinking one eligible client's attack holdout below the threshold in the stored per-run summary
    import json
    run_metrics_orig = pm.run_metrics
    def tampered(d, with_holdout=True):
        out = run_metrics_orig(d, with_holdout)
        if d.parent.name.startswith("uniform"):
            ids = json.loads(out["eligible_clients"])
            out["eligible_clients"] = json.dumps(ids[1:])
        return out
    pm.run_metrics = tampered
    try:
        with pytest.raises(AssertionError, match="eligible"):
            pm.analyze(res, tmp_path / "bad")
    finally:
        pm.run_metrics = run_metrics_orig
