"""Forensics of the transient CICIoT2023 ROC-AUC collapse (round 28) from saved round states."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402
from src.model import ANN  # noqa: E402

run = Path(sys.argv[1])
out_path = Path(sys.argv[2])
cfg = Config.from_yaml(run / "resolved_config.yaml")
bundle = load_dataset(cfg.data, seed=cfg.experiment.seed, load_test=False)
diag = pd.read_csv(run / "round_diagnostics.csv")
rounds = pd.read_csv(run / "round_metrics.csv")
agg = pd.read_csv(run / "aggregation_diagnostics.csv")
X = torch.from_numpy(bundle.X_val).float()
y = bundle.y_val


def model_from(state):
    m = ANN(bundle.X_train.shape[1], tuple(cfg.model.hidden_dims), cfg.model.dropout) if hasattr(ANN, "__init__") else None
    m.load_state_dict(state)
    m.eval()
    return m


def evaluate(state):
    m = model_from(state)
    with torch.no_grad():
        logits = m(X)
        prob = torch.softmax(logits, 1)[:, 1].numpy()
        margin = (logits[:, 1] - logits[:, 0]).numpy()
    return prob, margin


states = {r: torch.load(run / "round_states" / f"round_{r:02d}.pt") for r in range(25, 31)}
report = {"round_table": [], "layer_change_27_to_28": {}, "interpolation_27_to_28": []}
for r in range(25, 31):
    prob, margin = evaluate(states[r])
    row = diag[diag["round"] == r].iloc[0]
    report["round_table"].append({
        "round": r,
        "val_auc_recomputed": float(roc_auc_score(y, prob)),
        "val_auc_logged": float(rounds.loc[rounds["round"] == r, "val_roc_auc"].iloc[0]),
        "mean_attack_prob": float(prob.mean()),
        "mean_margin_benign": float(margin[y == 0].mean()), "mean_margin_attack": float(margin[y == 1].mean()),
        "aggregate_norm": float(row.aggregate_norm), "applied_norm": float(row.applied_norm),
        "velocity_norm": float(row.velocity_norm),
        "cos_applied_vs_prev": float(row.cos_applied_vs_prev_applied),
        "cos_aggregate_vs_prev": float(row.cos_aggregate_vs_prev_aggregate),
        "cos_applied_vs_velocity": float(row.cos_applied_vs_velocity),
        "selected": row.selected_clients, "kept": row.kept_clients,
    })
d = {k: (states[28][k] - states[27][k]) for k in states[27]}
report["layer_change_27_to_28"] = {k: float(v.norm()) for k, v in d.items()}
for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
    mix = {k: states[27][k] + alpha * d[k] for k in d}
    prob, _ = evaluate(mix)
    report["interpolation_27_to_28"].append({"alpha": alpha, "val_auc": float(roc_auc_score(y, prob))})
# which clients were kept in 28 and their weight shares
a28 = agg[agg["round"] == 28][["client_id", "is_recovered_update", "effective_malicious_update", "kept", "pre_clip_l2_norm", "applied_weight_share", "raw_weight"]]
report["round28_aggregation_rows"] = a28.round(4).to_dict("records")
# is the collapse a sign inversion of the ranking? AUC of -margin
prob28, margin28 = evaluate(states[28])
report["auc_if_ranking_inverted_round28"] = float(roc_auc_score(y, -margin28))
report["selection_metric_best_round"] = int(rounds.loc[rounds["val_roc_auc"].iloc[1:].idxmax() if False else rounds[rounds["round"] >= 1]["val_roc_auc"].idxmax(), "round"])
out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({k: v for k, v in report.items() if k != "round28_aggregation_rows"}, indent=1)[:7000])
