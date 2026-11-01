"""Mock single-run workload used ONLY by the runner regression tests (no training happens here).

usage: python mock_p6c_run.py --config CFG --seed N --out DIR
Environment: MOCK_FAIL = comma-separated substrings of the run id that should fail (exit 7).
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
parser.add_argument("--seed", type=int, required=True)
parser.add_argument("--out", required=True)
args = parser.parse_args()

run_id = f"{Path(args.config).stem}__seed{args.seed}"
fail_patterns = [p for p in os.environ.get("MOCK_FAIL", "").split(",") if p]
if any(p in run_id for p in fail_patterns):
    print(f"mock failure for {run_id}")
    sys.exit(7)

x = int(hashlib.sha256(run_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
bonus = 0.03 if "corrected" in run_id else 0.0
out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)


def dump(name, obj):
    (out / name).write_text(json.dumps(obj), encoding="utf-8")


auc = 0.90 + 0.05 * x + bonus
report = {"roc_auc": auc, "pr_auc": auc, "f1": auc - 0.05, "fpr": 0.15, "recall_adr": auc - 0.02, "precision": 0.9,
          "tn": 1, "fp": 1, "fn": 1, "tp": 1, "threshold": 0.5}
diag = {k: {"independent_evaluation": {"fpr": 0.1, "recall_adr": 0.8}} for k in ("1pct", "5pct", "15pct")}
dump("final_validation_metrics.json", {
    "best_round": 7, "selected_operating_point": {"threshold": 0.5, "roc_auc": auc},
    "report_partition_at_selected_threshold": report,
    "last_round_report_partition": dict(report, roc_auc=auc - 0.01),
    "last_round_selection_partition": {"threshold": 0.5},
    "threshold_diagnostics": diag,
})
dump("threshold_diagnostics.json", diag)
dump("run_metadata.json", {"test_data_loaded": False, "rounds_executed": 30, "validation_only": True})
dump("metric_accounting.json", {"invariants_hold": True})
dump("run_record.json", {"seed": args.seed})
dump("privacy_plan.json", {})
dump("validation_split_info.json", {})
dump("phase6c_diagnostics.json", {"updates": {"malicious_received_total": 5}, "fairness": {"worst_client_recall": 0.5},
                                  "participation": {"selection_gini": 0.3, "clients_ever_selected": 20}})
(out / "resolved_config.yaml").write_text("mock: true\n", encoding="utf-8")
(out / "network_metrics.csv").write_text("round,client_id\n1,0\n", encoding="utf-8")
(out / "aggregation_diagnostics.csv").write_text("round,client_id\n1,0\n", encoding="utf-8")
(out / "best_model_state.pt").write_bytes(b"best" + run_id.encode())
(out / "last_model_state.pt").write_bytes(b"last" + run_id.encode())
rows = ["round,mean_train_loss,surrogate_weight_share,mean_update_delivered,communication_bytes_on_wire"]
rows += [f"{r},0.5,0.1,0.8,1000" for r in range(0, 31)]
(out / "round_metrics.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
print("mock run ok", run_id)
