"""Phase 10: history-feedback (non-oracle) selector, correlated network/data scenario, per-client holdout. Synthetic data only; no locked file is touched."""
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_phase7_guard import make_config, numeric_equal, run  # noqa: E402

from src.config import Config, RoutingConfig  # noqa: E402
from src.history_selector import HistorySelector  # noqa: E402
from src.network import DynamicEdgeCloudNetwork  # noqa: E402
from src.partitioning import split_client_holdout  # noqa: E402


# ---------------------------------------------------------------- selector: no oracle, causal, deterministic
def test_selector_module_cannot_reach_oracle_information():
    tree = ast.parse((ROOT / "src" / "history_selector.py").read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any(m and ("network" in m or "experiment" in m or "attacks" in m or "data" in m) for m in imported), imported
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not attrs & {"expected_pdr", "stability", "client_edge_stability", "security", "decisions", "malicious"}


def _simulate(true_p, rounds=30, count=10, seed=3):
    sel = HistorySelector(len(true_p), 0.4, 0.3, seed=seed)
    rng = np.random.default_rng(1)
    picks = []
    for t in range(1, rounds + 1):
        chosen = sel.select(count, t)
        picks.append(chosen)
        for c in chosen:
            ok = rng.random() < true_p[c]
            sel.observe(c, ok, float(50 + 100 * (1 - true_p[c])) if ok else None)
    return picks


def test_cold_start_tries_every_client_before_exploiting_and_selection_is_deterministic():
    true_p = np.linspace(0.3, 0.99, 50)
    a, b = _simulate(true_p), _simulate(true_p)
    assert a == b
    seen = set()
    for r in a[:5]:
        assert len(set(r)) == 10
        seen |= set(r)
    assert len(seen) == 50                                  # unknown clients get an optimistic index: all 50 explored in the first 5 rounds
    assert _simulate(true_p, seed=4) != a                   # seed changes tie-breaking


def test_learns_reliability_from_observations_only():
    true_p = np.concatenate([np.full(25, 0.35), np.full(25, 0.95)])
    picks = _simulate(true_p, rounds=40)
    late = [c for r in picks[20:] for c in r]
    assert np.mean(true_p[late]) > 0.75                     # hidden reliability is recovered purely from outcomes
    assert set(range(50)) <= {c for r in picks for c in r}  # and nobody is starved entirely


def test_no_future_observation_leakage_and_observe_only_current_round():
    sel = HistorySelector(20, 0.4, 0.3, seed=1)
    chosen = sel.select(5, 1)
    with pytest.raises(ValueError):
        sel.observe([c for c in range(20) if c not in chosen][0], True, 10.0)
    for c in chosen:
        sel.observe(c, c % 2 == 0, 20.0)
    twin = HistorySelector(20, 0.4, 0.3, seed=1)
    twin.select(5, 1)
    for c in chosen:
        twin.observe(c, c % 2 == 0, 20.0)
    assert sel.select(5, 2) == twin.select(5, 2)            # decision at round 2 is a function of history through round 1 only


# ---------------------------------------------------------------- correlated scenario
def _net(seed=5, n=50):
    return DynamicEdgeCloudNetwork(n, RoutingConfig(), seed)


def test_coupling_zero_is_bit_identical_and_marginals_are_preserved():
    a, b = _net(), _net()
    b.couple_links_to_scores(np.random.default_rng(0).random(50), 0.0, 5)
    for name in ("client_edge_latency", "client_edge_stability", "client_edge_security", "client_edge_bandwidth"):
        assert np.array_equal(getattr(a, name), getattr(b, name))
    c = _net()
    c.couple_links_to_scores(np.random.default_rng(0).random(50), 0.9, 5)
    for name in ("client_edge_latency", "client_edge_stability"):
        assert np.array_equal(np.sort(getattr(a, name), axis=0), np.sort(getattr(c, name), axis=0)) or sorted(getattr(a, name).ravel()) == sorted(getattr(c, name).ravel())
    assert np.array_equal(a.edge_cloud_latency, c.edge_cloud_latency)                         # same generated network, relabeled
    a._evolve(); c._evolve()                                                                  # later RNG consumption is identical
    assert np.allclose(np.sort(a.client_edge_stability.ravel()), np.sort(c.client_edge_stability.ravel()), atol=0.5)


@pytest.mark.parametrize("strength", [0.5, 0.9])
def test_coupling_creates_the_declared_negative_correlation(strength):
    from scipy.stats import spearmanr

    driver = np.random.default_rng(2).random(50)
    net = _net()
    net.couple_links_to_scores(driver, strength, 5)
    quality = net.client_edge_stability.mean(axis=1) - (net.client_edge_latency.mean(axis=1) - 5.0) / 75.0 * 0.25      # the composite link-quality index the coupling targets
    rho = spearmanr(driver, quality).correlation
    assert (rho < -0.3) if strength == 0.5 else (rho < -0.7)
    assert spearmanr(driver, net.client_edge_stability.mean(axis=1)).correlation < 0
    again = _net()
    again.couple_links_to_scores(driver, strength, 5)
    assert np.array_equal(net.client_edge_stability, again.client_edge_stability)            # reproducible


# ---------------------------------------------------------------- per-client holdout
def test_client_holdout_split_properties():
    parts = [np.arange(i * 100, i * 100 + n) for i, n in enumerate((100, 150, 3, 1))]
    t0, h0 = split_client_holdout(parts, 0.0, 1)
    assert all(np.array_equal(a, b) for a, b in zip(t0, parts)) and all(len(h) == 0 for h in h0)
    t, h = split_client_holdout(parts, 0.2, 1)
    t2, h2 = split_client_holdout(parts, 0.2, 1)
    for p, a, b, c, d in zip(parts, t, h, t2, h2):
        assert set(a) | set(b) == set(p) and not set(a) & set(b) and len(a) >= 1
        assert np.array_equal(a, c) and np.array_equal(b, d)
    assert len(h[0]) == 20 and len(h[3]) == 0


# ---------------------------------------------------------------- end to end on synthetic data
def _cfg(tmp_path, tag, routing=None, fl=None, rounds=3):
    base = make_config(tmp_path, min_real_updates=0)
    raw = yaml.safe_load(base.read_text(encoding="utf-8"))
    raw["fl"]["rounds"] = rounds
    raw["routing"].update({"selection_policy": "top_k", "delivery_model": "packet_coupled", "trace_mode": "matched"})
    raw["routing"].update(routing or {})
    raw["fl"].update(fl or {})
    out = tmp_path / f"cfg_{tag}.yaml"
    out.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return out


def test_defaults_are_historical_and_flags_off_equal_flags_omitted(tmp_path):
    c = Config()
    assert c.routing.network_data_coupling == 0.0 and c.fl.client_holdout_fraction == 0.0 and c.routing.selection_policy == "top_k"
    full = _cfg(tmp_path, "omitted")
    explicit = _cfg(tmp_path, "explicit", routing={"network_data_coupling": 0.0}, fl={"client_holdout_fraction": 0.0})
    numeric_equal(run(full, tmp_path / "a"), run(explicit, tmp_path / "b"))


def test_historical_behaviour_is_unchanged_against_the_frozen_phase9e_tree(tmp_path):
    ok = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "phase9e-frozen"], capture_output=True, cwd=ROOT).returncode == 0
    if not ok:
        pytest.skip("tag phase9e-frozen absent")
    tree = tmp_path / "tree"
    tar = tmp_path / "t.tar"
    subprocess.run(["git", "archive", "--format=tar", "-o", str(tar), "phase9e-frozen"], check=True, cwd=ROOT)
    shutil.unpack_archive(str(tar), str(tree))
    cfg = _cfg(tmp_path, "hist", routing={"selection_policy": "coverage_aware"})
    raw = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    for k in ("network_data_coupling", "ucb_c"):
        raw["routing"].pop(k, None)
    raw["fl"].pop("client_holdout_fraction", None)
    old_cfg = tmp_path / "cfg_old.yaml"
    old_cfg.write_text(yaml.safe_dump(raw), encoding="utf-8")
    env = dict(os.environ, PYTHONHASHSEED="0")
    env.pop("IOTFL_LIVE", None)
    r = subprocess.run([sys.executable, str(tree / "scripts" / "phase6c" / "run_one.py"), "--config", str(old_cfg), "--seed", "7", "--out", str(tmp_path / "old_out")],
                       capture_output=True, text=True, env=env, cwd=str(tree))
    assert r.returncode == 0, r.stderr[-600:]
    new = run(cfg, tmp_path / "new_out")
    old = pd.read_csv(tmp_path / "old_out" / "round_metrics.csv")
    numeric_equal(old, new)
    assert (tmp_path / "old_out" / "best_model_state.pt").read_bytes() == (tmp_path / "new_out" / "best_model_state.pt").read_bytes()


def test_three_round_smoke_non_oracle_policy_with_correlated_network_and_holdout(tmp_path):
    cfg = _cfg(tmp_path, "smoke", routing={"selection_policy": "history_ucb", "network_data_coupling": 0.8}, fl={"client_holdout_fraction": 0.2})
    out = tmp_path / "smoke"
    rm = run(cfg, out)
    assert len(rm) == 4 and (rm["selected_clients"].iloc[1:] == 8).all()                 # round 0 row + 3 rounds
    nm = pd.read_csv(out / "network_metrics.csv")
    assert nm.groupby("round")["client_id"].nunique().eq(8).all()                         # 8 distinct clients per round
    cd = pd.read_csv(out / "client_distribution.csv")
    base = tmp_path / "base"
    run(_cfg(tmp_path, "base"), base)
    cd0 = pd.read_csv(base / "client_distribution.csv")
    assert cd["num_samples"].sum() < cd0["num_samples"].sum() and abs(cd["num_samples"].sum() / cd0["num_samples"].sum() - 0.8) < 0.03   # 20% held out of training
    assert nm["round"].max() == 3


def test_phase9e_frozen_artifacts_are_unchanged():
    ok = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "phase9e-frozen"], capture_output=True, cwd=ROOT).returncode == 0
    if not ok:
        pytest.skip("tag phase9e-frozen absent")
    paths = ["docs/final_test", "scripts/final_test", "Phase9E_PreTest_Signoff", "Phase9C_Submission_Readiness", "scripts/phase6c", "configs/phase6c", "configs/phase7b", "docs/phase6c", "docs/phase7b"]
    diff = subprocess.run(["git", "diff", "--name-only", "phase9e-frozen", "--"] + paths, capture_output=True, text=True, cwd=ROOT).stdout.split()
    assert diff == [], diff
