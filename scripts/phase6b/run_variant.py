"""Run one Phase-6B variant (validation-only) and compute participation/fairness diagnostics.

usage: python scripts/phase6b/run_variant.py <config.yaml>
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "phase6a"))
from run_validation_only import diagnostics, max_gap, peak_working_set_mb  # noqa: E402
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402
from src.experiment import run_experiment, _model_factory  # noqa: E402
from src.partitioning import make_partitions  # noqa: E402


def gini(values) -> float:
    v = np.sort(np.asarray(values, dtype=float))
    n = len(v)
    if v.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum()))


def client_fairness(run_dir: Path, cfg: Config, selection_counts: np.ndarray) -> dict:
    """Recall/FPR of the best global model on each client's own training data at the threshold
    selected on the calibration partition (training data of never-selected clients was never
    used for training, so their recall is an out-of-participation measure)."""
    bundle = load_dataset(cfg.data, seed=cfg.experiment.seed, load_test=False)
    partitions = make_partitions(bundle.y_train, num_clients=cfg.fl.num_clients, strategy=cfg.fl.partition,
                                 seed=cfg.experiment.seed, dirichlet_alpha=cfg.fl.dirichlet_alpha,
                                 min_client_samples=cfg.fl.min_client_samples)
    model = _model_factory(cfg, bundle.X_train.shape[1])()
    model.load_state_dict(torch.load(run_dir / "best_model_state.pt"))
    model.eval()
    final = json.loads((run_dir / "final_validation_metrics.json").read_text())
    threshold = float(final["selected_operating_point"]["threshold"])
    rows = []
    with torch.no_grad():
        for client_id, idx in enumerate(partitions):
            prob = torch.softmax(model(torch.from_numpy(bundle.X_train[idx]).float()), 1)[:, 1].numpy()
            y = bundle.y_train[idx]
            pred = prob >= threshold
            rows.append({
                "client_id": client_id, "samples": int(len(idx)),
                "attack_samples": int((y == 1).sum()), "benign_samples": int((y == 0).sum()),
                "recall": float(pred[y == 1].mean()) if (y == 1).sum() >= 20 else float("nan"),
                "fpr": float(pred[y == 0].mean()) if (y == 0).sum() >= 20 else float("nan"),
                "times_selected": int(selection_counts[client_id]),
            })
    frame = pd.DataFrame(rows)
    frame.to_csv(run_dir / "client_level_recall.csv", index=False)
    never = frame[frame["times_selected"] == 0]
    ever = frame[frame["times_selected"] > 0]
    return {
        "threshold_used": threshold,
        "worst_client_recall": float(frame["recall"].min()),
        "worst_client_recall_client": int(frame.loc[frame["recall"].idxmin(), "client_id"]) if frame["recall"].notna().any() else None,
        "mean_client_recall_ever_selected": float(ever["recall"].mean()),
        "mean_client_recall_never_selected": float(never["recall"].mean()) if len(never) else None,
        "worst_client_recall_never_selected": float(never["recall"].min()) if len(never) and never["recall"].notna().any() else None,
        "clients_with_evaluable_recall": int(frame["recall"].notna().sum()),
    }


def main(config_path: str) -> None:
    cfg = Config.from_yaml(config_path)
    assert cfg.experiment.validation_only and cfg.data.test_csv == ""
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    start, cpu = time.perf_counter(), time.process_time()
    run_dir = Path(run_experiment(cfg))
    usage = {"config": config_path, "config_sha256": hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
             "git_commit": commit, "seed": cfg.experiment.seed, "variant": cfg.experiment.variant_name,
             "wall_seconds": round(time.perf_counter() - start, 1), "cpu_seconds": round(time.process_time() - cpu, 1),
             "peak_working_set_mb": round(peak_working_set_mb(), 1)}
    (run_dir / "resource_usage.json").write_text(json.dumps(usage, indent=2), encoding="utf-8")
    diag = diagnostics(run_dir, cfg)
    net = pd.read_csv(run_dir / "network_metrics.csv")
    counts = np.array([int((net["client_id"] == c).sum()) for c in range(cfg.fl.num_clients)])
    diag["participation"]["selection_gini"] = gini(counts)
    diag["participation"]["clients_ever_selected_fraction"] = float((counts > 0).mean())
    diag["fairness"] = client_fairness(run_dir, cfg, counts)
    rm = pd.read_csv(run_dir / "round_metrics.csv")
    rm = rm[rm["round"] >= 1]
    diag["weights"] = {
        "retained_updates_mean": float(rm["retained_for_weighting"].mean()),
        "min_feasible_cap_mean": float(rm["weight_cap_min_feasible"].mean()),
        "max_applied_weight_share_mean": float(rm["max_applied_weight_share"].mean()),
        "requested_cap": (None if rm["weight_cap_requested"].isna().all() else float(rm["weight_cap_requested"].iloc[0])),
        "rounds_strict_cap_infeasible": int(rm["weight_cap_infeasible_strict"].astype(bool).sum()),
        "mean_surrogate_weight_share": float(rm["surrogate_weight_share"].mean()),
    }
    diag["round_stability"] = {
        "val_roc_auc_min_after_round3": float(rm.loc[rm["round"] >= 3, "val_roc_auc"].min()),
        "val_roc_auc_std_last10": float(rm["val_roc_auc"].iloc[-10:].std()),
        "rounds_with_auc_below_0.9_after_round3": int((rm.loc[rm["round"] >= 3, "val_roc_auc"] < 0.9).sum()),
    }
    diag["resources"] = usage
    (run_dir / "phase6b_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    print(json.dumps({k: diag[k] for k in ("learning", "participation", "fairness", "weights", "round_stability")}, indent=1)[:3500])


if __name__ == "__main__":
    main(sys.argv[1])
