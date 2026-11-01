"""Phase-6B regression tests: metric accounting invariants, frozen reference defaults,
matched exogenous traces, event-coupled delivery, selection policies, surrogate cap,
weight-cap feasibility, threshold-calibration protocol and the sensitivity counter-example."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
import yaml

from src.aggregation import true_median
from src.config import Config, RoutingConfig
from src.experiment import run_experiment
from src.metric_accounting import reconcile_network_events
from src.network import DynamicEdgeCloudNetwork
from src.privacy import capped_normalized_weights, clip_update

ROOT = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ accounting
def _events(n_rounds=3, per_round=4, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(1, n_rounds + 1):
        for c in range(per_round):
            explicit = bool(rng.random() < 0.3)
            delivered = bool(rng.random() < 0.7)
            rows.append({"round": r, "client_id": c, "explicit_client_failure": explicit,
                         "update_delivered": delivered, "pdr": float(rng.random()),
                         "received_by_server": (not explicit) and delivered})
    net = pd.DataFrame(rows)
    rounds = [{"round": 0, "selected_clients": 0, "received_updates": 0, "failed_clients": 0,
               "imputed_clients": 0, "mean_update_delivered": np.nan}]
    for r, g in net.groupby("round"):
        rounds.append({"round": r, "selected_clients": len(g), "received_updates": int(g.received_by_server.sum()),
                       "failed_clients": int((~g.received_by_server).sum()), "imputed_clients": int((~g.received_by_server).sum()),
                       "mean_update_delivered": float(g.update_delivered.mean())})
    return net, pd.DataFrame(rounds)


def test_metric_accounting_invariants_hold_and_detect_corruption():
    net, rounds = _events()
    out = reconcile_network_events(net, rounds, failure_enabled=True)
    assert out["invariants_hold"]
    assert out["received"] == out["events_selected"] - out["failed_union"]
    bad = rounds.copy()
    bad.loc[bad["round"] == 1, "received_updates"] += 1
    with pytest.raises(AssertionError):
        reconcile_network_events(net, bad, failure_enabled=True)
    bad_net = net.copy()
    bad_net.loc[0, "received_by_server"] = not bad_net.loc[0, "received_by_server"]
    with pytest.raises(AssertionError):
        reconcile_network_events(bad_net, rounds, failure_enabled=True)


def test_phase6a_logs_reconcile_to_documented_numbers():
    run = ROOT / "docs" / "phase6a" / "runs" / "phase6a_unsw_no_dp"
    if not run.exists():
        pytest.skip("archived phase-6A run not present")
    out = reconcile_network_events(pd.read_csv(run / "network_metrics.csv"), pd.read_csv(run / "round_metrics.csv"), True)
    assert (out["events_selected"], out["received"], out["failed_union"]) == (300, 217, 83)
    assert out["delivered_draw_successes"] == 241 and out["delivered_but_explicit_failure"] == 24
    assert abs(out["update_delivery_ratio__delivered_over_selected"] - 241 / 300) < 1e-12
    assert abs(out["mean_pdr__over_selected"] - 0.84236667) < 1e-6


# ------------------------------------------------------------------ frozen reference
def test_reference_configs_equal_phase6a_except_names():
    for d in ("unsw", "ciciot"):
        ref = yaml.safe_load((ROOT / "configs" / "phase6b" / f"reference_{d}_no_dp.yaml").read_text(encoding="utf-8"))
        old = yaml.safe_load((ROOT / "configs" / f"phase6a_{d}_no_dp.yaml").read_text(encoding="utf-8"))
        for section in old:
            for key, value in old[section].items():
                if section == "experiment" and key in {"name", "output_dir"}:
                    continue
                assert ref[section][key] == value, (section, key)
        assert ref["experiment"]["variant_name"] == "reference_6a"


def test_historical_defaults_are_unchanged():
    cfg = Config()
    assert cfg.routing.selection_policy == "top_k" and cfg.routing.delivery_model == "independent_draws"
    assert cfg.routing.trace_mode == "sequential" and cfg.fl.weighting == "sample_proportional"
    assert cfg.failure.surrogate_total_weight_cap is None and cfg.data.threshold_calibration_fraction == 0.0


def test_non_default_selection_policy_requires_routing():
    cfg = Config()
    cfg.routing.enabled = False
    cfg.routing.selection_policy = "uniform_random"
    with pytest.raises(ValueError):
        cfg.validate()


# ------------------------------------------------------------------ matched traces & delivery
def _net(model="independent_draws", trace="matched", seed=9, clients=20, **kw):
    cfg = replace(RoutingConfig(), delivery_model=model, trace_mode=trace, **kw)
    return DynamicEdgeCloudNetwork(clients, cfg, seed)


def test_matched_trace_draws_do_not_depend_on_who_else_is_selected():
    a, b = _net(), _net()
    for _ in range(4):
        a.update_round(True)
        b.update_round(True)
        for c in (3, 7, 11, 5):
            ra = a.simulate_transfer(c, 100_000)
            _ = [b.simulate_transfer(x, 100_000) for x in (1, 2)]  # extra, different transfers first
            rb = b.simulate_transfer(c, 100_000)
            for key in ("pdr", "update_delivered", "end_to_end_delay_ms", "packets_received"):
                assert ra[key] == rb[key], key
    # the network evolution itself must also be identical
    assert np.allclose(a.client_edge_latency, b.client_edge_latency)


def test_packet_coupled_delivery_semantics_and_statistics():
    net = _net("packet_coupled", clients=40, max_retransmissions=2)
    rows = []
    for _ in range(60):
        net.update_round(True)
        rows += [net.simulate_transfer(c, 150_000) for c in range(40)]
    frame = pd.DataFrame(rows)
    delivered = frame["update_delivered"].astype(bool)
    # delivered iff no packet remained unrecovered, i.e. iff the after-retransmission PDR is 1
    assert (delivered == (frame["packets_unrecovered"] == 0)).all()
    assert (delivered == (frame["pdr_after_arq"] == 1.0)).all()
    assert (frame["pdr"] <= frame["pdr_after_arq"] + 1e-12).all()   # first-attempt receptions are a subset
    # PDR (first-transmission reception) estimates the link probability
    assert abs(frame["pdr"].mean() - frame["expected_pdr"].mean()) < 0.01
    # empirical delivery probability matches the analytic (1-(1-p)^A)^K
    p = frame["expected_pdr"].to_numpy()
    analytic = np.mean((1 - (1 - p) ** 3) ** 100)
    assert abs(delivered.mean() - analytic) < 0.03
    # PDR and delivery now derive from the same packet events -> strongly coupled
    assert np.corrcoef(frame["pdr"], delivered.astype(float))[0, 1] > 0.5
    # retransmissions cost bytes and delay
    assert (frame["bytes_on_wire"] >= 150_000).all()
    assert (frame["retransmission_rounds"] >= 0).all() and (frame["retransmission_rounds"] <= 2).all()
    slow = frame[frame["retransmission_rounds"] == 2]["end_to_end_delay_ms"].mean()
    fast = frame[frame["retransmission_rounds"] == 0]["end_to_end_delay_ms"].mean()
    assert slow > fast


def _residual_corr(model):
    """corr(pdr - expected_pdr, delivered): conditional on the link quality, how much does the
    packet-level outcome inform the delivery outcome?"""
    net = _net(model, clients=40)
    rows = []
    for _ in range(250):
        net.update_round(True)
        rows += [net.simulate_transfer(c, 150_000) for c in range(40)]
    frame = pd.DataFrame(rows)
    residual = frame["pdr"] - frame["expected_pdr"]
    return float(np.corrcoef(residual, frame["update_delivered"].astype(float))[0, 1])


def test_independent_draw_model_is_conditionally_independent_while_coupled_is_not():
    """Marginal PDR/delivery correlation is positive in both models (both depend on the link's
    expected PDR), so it cannot discriminate them. Conditional on link quality the historical
    model has NO dependence by construction; the coupled model does."""
    independent = _residual_corr("independent_draws")
    coupled = _residual_corr("packet_coupled")
    assert abs(independent) < 0.05
    assert coupled > 0.03   # weak but real: delivery is limited by the worst packet, not the average


# ------------------------------------------------------------------ selection policies
def test_selection_policies_participation():
    def run(policy):
        cfg = replace(RoutingConfig(), selection_policy=policy, trace_mode="matched")
        net = DynamicEdgeCloudNetwork(50, cfg, 4)
        counts = np.zeros(50)
        for r in range(1, 31):
            net.update_round(True)
            if policy == "top_k":
                chosen = net.select_clients(10)
            elif policy == "coverage_aware":
                chosen = net.select_clients_coverage_aware(10, counts, r, 0.5)
            else:
                chosen = np.random.default_rng([4, 5000, r]).choice(50, 10, replace=False).tolist()
            assert len(set(chosen)) == 10
            for c in chosen:
                counts[c] += 1
        return counts

    top, cov, uni = run("top_k"), run("coverage_aware"), run("uniform_random")
    assert (cov > 0).sum() > (top > 0).sum()
    assert cov.max() < top.max()
    assert (uni > 0).sum() >= (top > 0).sum()


# ------------------------------------------------------------------ tiny end-to-end runs
def _tiny_unsw(path: Path):
    rng = np.random.default_rng(11)
    n = 900
    y = rng.integers(0, 2, n)
    pd.DataFrame({
        "id": np.arange(1, n + 1), "dur": rng.normal(0, 1, n) + 1.5 * y, "sbytes": rng.normal(0, 3, n) + 2 * y,
        "proto": rng.choice(["tcp", "udp"], n), "service": rng.choice(["-", "http"], n),
        "state": rng.choice(["FIN", "CON"], n), "attack_cat": np.where(y == 1, "Generic", "Normal"), "label": y,
    }).to_csv(path / "train.csv", index=False)


def _cfg(path: Path, **over) -> Config:
    cfg = Config()
    cfg.data.train_csv = str(path / "train.csv")
    cfg.data.test_csv = ""
    cfg.data.validation_split = "group_disjoint"
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 8, 6, 3
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.privacy.mode = "none"
    cfg.failure.client_failure_probability = 0.5
    cfg.routing.trace_mode = "matched"
    cfg.experiment.output_dir = str(path / "out")
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    cfg.experiment.seed = 3
    for k, v in over.items():
        section, key = k.split("__")
        setattr(getattr(cfg, section), key, v)
    return cfg


def test_threshold_calibration_partition_is_disjoint_and_used(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, data__threshold_calibration_fraction=0.5)))
    info = json.loads((run / "validation_split_info.json").read_text())["threshold_calibration"]
    assert info["shared_predictor_vectors"] == 0 and info["calibration_rows"] > 0 and info["evaluation_rows"] > 0
    rounds = pd.read_csv(run / "round_metrics.csv")
    assert "val_calibration_fpr" in rounds.columns
    final = json.loads((run / "final_validation_metrics.json").read_text())
    assert final["threshold_source"] == "separate_calibration_partition"
    diag = final["threshold_diagnostics"]
    assert set(diag) == {"1pct", "5pct", "15pct"}
    assert "independent_evaluation" in diag["5pct"] and "same_observation_optimistic" in diag["5pct"]
    # the historical protocol selects and reports on the same observations
    run2 = Path(run_experiment(_cfg(tmp_path, experiment__name="hist")))
    assert json.loads((run2 / "final_validation_metrics.json").read_text())["threshold_source"] == "same_validation_observations"


def test_surrogate_cap_bounds_the_retained_surrogate_share(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, failure__surrogate_total_weight_cap=0.10, failure__recovery_enabled=True,
                                   failure__client_failure_probability=0.3, fl__rounds=6, experiment__name="cap")))
    rounds = pd.read_csv(run / "round_metrics.csv").query("round>=1")
    with_real = rounds[rounds["real_weight_share"] > 0]
    assert len(with_real) > 0
    # whenever at least one real update is retained the collective surrogate share obeys the cap
    assert with_real["surrogate_weight_share"].max() <= 0.10 + 1e-9


def test_surrogate_majority_makes_the_mad_filter_reject_every_real_update():
    """Documented DEFECT of the reference algorithm: identical surrogate copies dominate the
    coordinate median and collapse the MAD to ~0, so when surrogates outnumber real updates the
    robust filter rejects all real updates and keeps only the surrogates."""
    from src.aggregation import distance_filter_indices

    torch.manual_seed(1)
    real = [torch.randn(40) * 0.5 for _ in range(4)]
    surrogate = true_median(torch.stack(real), dim=0)
    updates = [{"w": u} for u in real] + [{"w": surrogate}] * 6
    keep, _ = distance_filter_indices(updates, 2.5)
    assert [i for i in keep if i < 4] == []
    assert len([i for i in keep if i >= 4]) == 6
    # with fewer surrogates than real updates the real updates are retained
    updates_ok = [{"w": u} for u in [torch.randn(40) * 0.5 for _ in range(7)]]
    updates_ok += [{"w": true_median(torch.stack([u["w"] for u in updates_ok]), dim=0)}] * 3
    keep_ok, _ = distance_filter_indices(updates_ok, 2.5)
    assert len([i for i in keep_ok if i < 7]) == 7


def test_no_imputation_variant_has_no_surrogate_weight(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, failure__recovery_enabled=False, experiment__name="noimp")))
    rounds = pd.read_csv(run / "round_metrics.csv").query("round>=1")
    assert rounds["surrogate_weight_share"].sum() == 0 and rounds["imputed_clients"].sum() == 0
    assert json.loads((run / "run_metadata.json").read_text())["algorithm_spec"]["imputation"] == "none"


def test_weight_cap_feasibility_is_logged_and_never_claimed_when_impossible(tmp_path):
    _tiny_unsw(tmp_path)
    cfg = _cfg(tmp_path, privacy__mode="central_client", privacy__target_epsilon=10.0, experiment__name="cap_dp")
    run = Path(run_experiment(cfg))
    rounds = pd.read_csv(run / "round_metrics.csv").query("round>=1")
    # with < 10 retained updates a strict 0.1 cap is mathematically impossible
    assert (rounds["retained_for_weighting"] < 10).all()
    assert rounds["weight_cap_infeasible_strict"].astype(bool).all()
    assert (rounds["max_applied_weight_share"] >= 1.0 / rounds["retained_for_weighting"] - 1e-9).all()
    assert (rounds["weight_cap_effective"] >= rounds["weight_cap_min_feasible"] - 1e-12).all()


def test_capped_normalized_weights_cannot_beat_one_over_n():
    for n in (3, 5, 8, 9):
        weights, maximum = capped_normalized_weights(np.arange(1, n + 1, dtype=float), 0.1)
        assert maximum >= 1.0 / n - 1e-12 and abs(sum(weights) - 1) < 1e-9


def test_uniform_weighting_and_variant_name_are_recorded(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, fl__weighting="uniform", experiment__variant_name="uniform_weights",
                                   experiment__name="uw")))
    meta = json.loads((run / "run_metadata.json").read_text())
    assert meta["variant_name"] == "uniform_weights" and meta["algorithm_spec"]["weighting"] == "uniform"
    agg = pd.read_csv(run / "aggregation_diagnostics.csv")
    assert set(agg.loc[~agg["is_recovered_update"].astype(bool), "raw_weight"]) == {1.0}


def test_metric_accounting_file_written_by_every_run(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, experiment__name="acct")))
    assert json.loads((run / "metric_accounting.json").read_text())["invariants_hold"] is True


# ------------------------------------------------------------------ privacy sensitivity counter-example
def test_surrogate_imputation_violates_the_assumed_add_remove_sensitivity():
    """The accountant assumes that adding/removing one client changes the released aggregate by
    at most clip * max_weight_share. With coordinate-median surrogate imputation, removing a
    client ALSO changes every surrogate row (their median is recomputed), so the true influence
    is larger. Add/remove adjacency is used so the replace-vs-add/remove factor of two is not
    what is being demonstrated."""
    clip, dim = 1.0, 50

    def clipv(u):
        return u * min(1.0, clip / (float(u.norm()) + 1e-12))

    def pipeline(real, n_missing, factor=0.5):
        clipped = [clipv(u) for u in real]
        surrogate = true_median(torch.stack(clipped), dim=0)
        updates = clipped + [surrogate] * n_missing
        weights = [1.0] * len(clipped) + [factor] * n_missing
        total = sum(weights)
        weights = [w / total for w in weights]
        return sum(w * u for w, u in zip(weights, updates)), max(weights)

    torch.manual_seed(0)
    violations = 0
    trials = 100
    for _ in range(trials):
        real = [torch.randn(dim) for _ in range(5)]
        with_client, share_a = pipeline(real, n_missing=3)
        without_client, share_b = pipeline(real[1:], n_missing=4)  # client 0 absent -> also imputed
        observed = float((with_client - without_client).norm())
        if observed > clip * max(share_a, share_b):
            violations += 1
    assert violations == trials
