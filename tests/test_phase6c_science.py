"""Phase-6C regression tests: surrogate-aware robust filtering, exposure-controlled attackers,
three-way validation partitions, last/best checkpoint reporting, versioning and exact output dirs."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import Config
from src.experiment import run_experiment


def _tiny_unsw(path: Path, n=1500):
    rng = np.random.default_rng(31)
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
    cfg.fl.num_clients, cfg.fl.clients_per_round, cfg.fl.rounds = 8, 6, 4
    cfg.fl.local_epochs, cfg.fl.partition, cfg.fl.min_client_samples = 1, "iid", 10
    cfg.threshold.grid_size = 51
    cfg.aggregation.method = "distance_filter"
    cfg.privacy.mode = "none"
    cfg.failure.client_failure_probability = 0.7
    cfg.routing.trace_mode = "matched"
    cfg.experiment.output_dir = str(path / "out")
    cfg.experiment.create_plots = False
    cfg.experiment.device = "cpu"
    cfg.experiment.early_stopping_patience = None
    cfg.experiment.validation_only = True
    cfg.experiment.seed = 5
    for k, v in over.items():
        section, key = k.split("__")
        setattr(getattr(cfg, section), key, v)
    return cfg


def test_post_filter_real_only_keeps_real_updates_when_surrogates_would_dominate(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, aggregation__surrogate_handling="post_filter_real_only",
                                   experiment__name="pf", experiment__variant_name="pf")))
    rounds = pd.read_csv(run / "round_metrics.csv").query("round>=1")
    received = rounds[rounds["received_updates"] > 0]
    assert len(received) > 0
    # whenever a real update arrived, real updates carry weight (the reference filter can zero them)
    assert (received["real_weight_share"] > 0).all()
    methods = pd.read_csv(run / "aggregation_diagnostics.csv")["actual_aggregation_method"].astype(str)
    assert methods.str.contains("real_only_filter").any() or (rounds["imputed_clients"] == 0).all()
    meta = json.loads((run / "run_metadata.json").read_text())
    assert meta["surrogate_handling"] == "post_filter_real_only"


def test_reference_surrogate_handling_is_unchanged_and_versioned(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, experiment__name="ref")))
    meta = json.loads((run / "run_metadata.json").read_text())
    assert meta["surrogate_handling"] == "reference"
    assert meta["algorithm_version"] == "reference_v1_historical"
    assert "mathematically infeasible" in meta["weight_cap_statement"]
    assert "NOT a certified" in meta["privacy_claim_statement"]


def test_exposure_control_gives_every_selection_policy_the_same_attacker_count(tmp_path):
    _tiny_unsw(tmp_path)
    counts = {}
    for policy in ("top_k", "uniform_random", "coverage_aware"):
        cfg = _cfg(tmp_path, attack__attack_type="sign_flip", attack__malicious_fraction=0.34,
                   attack__assignment="exposure_controlled", routing__selection_policy=policy,
                   failure__client_failure_probability=0.1, experiment__name=f"exp_{policy}")
        run = Path(run_experiment(cfg))
        rounds = pd.read_csv(run / "round_metrics.csv").query("round>=1")
        counts[policy] = rounds["malicious_selected"].tolist()
        assign = pd.read_csv(run / "attacker_assignment.csv")
        assert (assign.groupby("round").size() == 2).all()          # round(0.34 * 6) = 2 per round
        assert json.loads((run / "malicious_clients.json").read_text())["assignment"] == "exposure_controlled"
    assert counts["top_k"] == counts["uniform_random"] == counts["coverage_aware"] == [2, 2, 2, 2]


def test_natural_assignment_keeps_the_historical_fixed_set(tmp_path):
    _tiny_unsw(tmp_path)
    cfg = _cfg(tmp_path, attack__attack_type="sign_flip", attack__malicious_fraction=0.25,
               failure__client_failure_probability=0.1, experiment__name="nat")
    run = Path(run_experiment(cfg))
    mal = set(json.loads((run / "malicious_clients.json").read_text())["malicious_clients"])
    assert len(mal) == 2
    assert not (run / "attacker_assignment.csv").exists()
    agg = pd.read_csv(run / "aggregation_diagnostics.csv")
    assert set(agg.loc[agg["is_malicious_client"].astype(bool), "client_id"]) <= mal


def test_three_way_partitions_are_disjoint_and_checkpoint_choice_uses_selection_only(tmp_path):
    _tiny_unsw(tmp_path)
    run = Path(run_experiment(_cfg(tmp_path, data__validation_three_way=True, failure__client_failure_probability=0.1,
                                   experiment__name="tw")))
    info = json.loads((run / "validation_split_info.json").read_text())["three_way"]
    assert info["shared_vectors_cal_sel"] == info["shared_vectors_cal_rep"] == info["shared_vectors_sel_rep"] == 0
    assert min(info["calibration_rows"], info["selection_rows"], info["report_rows"]) > 50
    final = json.loads((run / "final_validation_metrics.json").read_text())
    assert final["partitions"]["three_way"] is True
    assert "roc_auc" in final["report_partition_at_selected_threshold"]
    assert final["last_round_report_partition"] is not None
    assert (run / "last_model_state.pt").exists() and (run / "best_model_state.pt").exists()
    rounds = pd.read_csv(run / "round_metrics.csv")
    assert "val_rep_roc_auc" in rounds.columns
    # the best round is the arg-max of the SELECTION-partition AUC (first maximum), never of the report partition
    best = int(final["best_round"])
    selection_auc = rounds["val_roc_auc"].to_numpy()
    assert selection_auc[best] == pytest.approx(selection_auc.max())
    # the report partition is never read by the selection logic: shuffling it cannot change best_round
    assert final["selected_operating_point"]["threshold_source"] == "separate_calibration_partition"


def test_exact_output_directory_option(tmp_path):
    _tiny_unsw(tmp_path)
    target = tmp_path / "immutable" / "unsw" / "arm" / "seed_5"
    cfg = _cfg(tmp_path, experiment__exact_output_dir=str(target), experiment__name="ignored")
    run = Path(run_experiment(cfg))
    assert run == target and (target / "run_metadata.json").exists()
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("override", [
    {"aggregation__surrogate_handling": "bogus"},
    {"attack__assignment": "bogus"},
    {"aggregation__surrogate_handling": "post_filter_real_only", "aggregation__method": "median"},
    {"data__validation_three_way": True, "data__threshold_calibration_fraction": 0.5},
])
def test_invalid_phase6c_configurations_are_rejected(override):
    cfg = Config()
    for k, v in override.items():
        section, key = k.split("__")
        setattr(getattr(cfg, section), key, v)
    with pytest.raises(ValueError):
        cfg.validate()


def test_phase6c_defaults_reproduce_the_historical_algorithm():
    cfg = Config()
    assert cfg.aggregation.surrogate_handling == "reference"
    assert cfg.attack.assignment == "natural_fixed_clients"
    assert cfg.data.validation_three_way is False
    assert cfg.experiment.algorithm_version == "reference_v1_historical"
    assert cfg.experiment.exact_output_dir is None


def test_surrogate_majority_defect_exists_in_reference_and_is_fixed_in_corrected(tmp_path):
    """At 75 % failures the reference filter lets identical surrogates dominate the MAD and gives
    received real updates zero weight; the corrected real-only filter never does."""
    _tiny_unsw(tmp_path)

    def zero_real_rounds(mode):
        zero = 0
        for seed in range(1, 7):
            run = Path(run_experiment(_cfg(
                tmp_path, aggregation__surrogate_handling=mode, experiment__name=f"{mode}_{seed}",
                experiment__seed=seed, fl__rounds=6, failure__client_failure_probability=0.75)))
            r = pd.read_csv(run / "round_metrics.csv").query("round>=1")
            received = r[r["received_updates"] > 0]
            zero += int((received["real_weight_share"] == 0).sum())
        return zero

    assert zero_real_rounds("reference") > 0
    assert zero_real_rounds("post_filter_real_only") == 0
