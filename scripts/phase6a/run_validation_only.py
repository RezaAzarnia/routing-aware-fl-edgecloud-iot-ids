"""Run one Phase-6A validation-only configuration and compute operational diagnostics.

usage: python scripts/phase6a/run_validation_only.py <config.yaml>
The seed is taken from the (prespecified) config; nothing is tuned here.
"""
import ctypes
import hashlib
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.config import Config  # noqa: E402
from src.experiment import run_experiment  # noqa: E402


def peak_working_set_mb() -> float:
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = PMC()
    counters.cb = ctypes.sizeof(PMC)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return float("nan")
    return counters.PeakWorkingSetSize / 2**20


def max_gap(rounds_present, total_rounds):
    """Longest run of consecutive rounds (1..total) in which the client is absent."""
    present = set(int(r) for r in rounds_present)
    best = cur = 0
    for r in range(1, total_rounds + 1):
        if r in present:
            cur = 0
        else:
            cur += 1
            best = max(best, cur)
    return best


def diagnostics(run_dir: Path, cfg: Config) -> dict:
    rounds = cfg.fl.rounds
    rm = pd.read_csv(run_dir / "round_metrics.csv")
    rm = rm[rm["round"] >= 1]
    net = pd.read_csv(run_dir / "network_metrics.csv")
    agg = pd.read_csv(run_dir / "aggregation_diagnostics.csv")
    cd = pd.read_csv(run_dir / "client_distribution.csv")
    n_clients = cfg.fl.num_clients
    selected_by_client = net.groupby("client_id")["round"].apply(list)
    received = net[net["received_by_server"].astype(bool)]
    received_by_client = received.groupby("client_id")["round"].apply(list)
    gaps_sel = {c: max_gap(selected_by_client.get(c, []), rounds) for c in range(n_clients)}
    gaps_rec = {c: max_gap(received_by_client.get(c, []), rounds) for c in range(n_clients)}
    sel_counts = np.array([len(selected_by_client.get(c, [])) for c in range(n_clients)], dtype=float)
    sizes = cd.set_index("client_id")["num_samples"]
    ever_selected = [c for c in range(n_clients) if sel_counts[c] > 0]
    delivered = net["update_delivered"].astype(bool)
    pdr = net["pdr"].astype(float)
    corr = float(np.corrcoef(pdr, delivered.astype(float))[0, 1]) if delivered.nunique() > 1 else float("nan")
    real_rows = agg[~agg["is_recovered_update"].astype(bool)]
    out = {
        "rounds_executed": int(len(rm)),
        "participation": {
            "clients_ever_selected": len(ever_selected), "clients_total": n_clients,
            "clients_ever_received": int(len(received_by_client)),
            "sample_coverage_of_ever_selected": float(sizes.loc[ever_selected].sum() / sizes.sum()),
            "selection_counts_min_max_mean": [float(sel_counts.min()), float(sel_counts.max()), float(sel_counts.mean())],
            "longest_exclusion_gap_rounds_selection": {"max": int(max(gaps_sel.values())),
                                                       "clients_never_selected": int(sum(1 for c in range(n_clients) if sel_counts[c] == 0))},
            "longest_exclusion_gap_rounds_received": int(max(gaps_rec.values())),
            "top5_client_selection_share": float(np.sort(sel_counts)[-5:].sum() / sel_counts.sum()),
        },
        "updates": {
            "selected_total": int(rm["selected_clients"].sum()), "received_total": int(rm["received_updates"].sum()),
            "failed_total": int(rm["failed_clients"].sum()), "imputed_total": int(rm["imputed_clients"].sum()),
            "kept_total": int(rm["kept_updates"].sum()), "rejected_total": int(rm["rejected_updates"].sum()),
            "mean_real_weight_share": float(rm["real_weight_share"].mean()),
            "mean_surrogate_weight_share": float(rm["surrogate_weight_share"].mean()),
            "malicious_received_total": int(rm["malicious_received"].sum()),
            # effective_malicious_update = a malicious client's REAL attacked update
            # (surrogate rows built for a malicious client are excluded)
            "effective_malicious_updates_kept": int(agg.loc[agg["effective_malicious_update"].astype(bool) & agg["kept"].astype(bool)].shape[0]),
            "effective_malicious_updates_rejected": int(agg.loc[agg["effective_malicious_update"].astype(bool) & ~agg["kept"].astype(bool)].shape[0]),
            "benign_real_rows_rejected": int(real_rows.loc[~real_rows["is_malicious_client"].astype(bool) & ~real_rows["kept"].astype(bool)].shape[0]),
        },
        "clipping_and_noise": {
            "mean_clipped_fraction": float(rm["privacy_clipped_fraction"].mean()),
            "mean_noise_std": float(rm["privacy_noise_std"].mean()),
            "mean_noise_l2_norm": float(rm["privacy_noise_l2_norm"].mean()),
            "mean_signal_l2_norm": float(rm["aggregate_signal_l2_norm"].mean()),
            "mean_noise_to_signal": float(rm["privacy_noise_to_signal_ratio"].mean()),
            "median_noise_to_signal": float(rm["privacy_noise_to_signal_ratio"].median()),
            "mean_max_weight_share": float(rm["privacy_max_weight_share"].mean()),
            "mean_server_applied_update_norm": float(rm["server_applied_update_l2_norm"].mean()),
            "final_epsilon_estimate": float(rm["privacy_epsilon_estimate"].iloc[-1]),
        },
        "network": {
            "mean_pdr": float(pdr.mean()), "mean_update_delivery_ratio": float(delivered.mean()),
            "mean_expected_pdr": float(net["expected_pdr"].mean()),
            "corr_pdr_vs_update_delivered": corr,
            "events": int(len(net)),
            "pdr_ge_0.95_but_not_delivered": int(((pdr >= 0.95) & ~delivered).sum()),
            "pdr_le_0.80_but_delivered": int(((pdr <= 0.80) & delivered).sum()),
            "failure_reasons": net["failure_reason"].value_counts().to_dict(),
            "explicit_failure_rate": float(net["explicit_client_failure"].astype(bool).mean()),
            "mean_end_to_end_delay_ms": float(net["end_to_end_delay_ms"].mean()),
            "mean_path_stability": float(net["path_stability"].mean()),
            "communication_bytes_attempted": int(net["update_bytes"].sum()),
            "communication_bytes_delivered_to_server": int(received["update_bytes"].sum()),
        },
        "learning": {
            "best_round": json.loads((run_dir / "final_validation_metrics.json").read_text())["best_round"],
            "final_round_val": {k: float(rm.iloc[-1][k]) for k in ("val_f1", "val_roc_auc", "val_precision", "val_recall_adr", "val_fpr", "mean_train_loss") if k in rm.columns},
            "val_roc_auc_first_last": [float(rm["val_roc_auc"].iloc[0]), float(rm["val_roc_auc"].iloc[-1])],
            "val_roc_auc_max_and_round": [float(rm["val_roc_auc"].max()), int(rm.loc[rm["val_roc_auc"].idxmax(), "round"])],
        },
    }
    return out


def main(config_path: str) -> None:
    cfg = Config.from_yaml(config_path)
    assert cfg.experiment.validation_only and cfg.data.test_csv == "", "Phase-6A requires validation-only configs"
    config_bytes = Path(config_path).read_bytes()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    start, cpu = time.perf_counter(), time.process_time()
    run_dir = Path(run_experiment(cfg))
    usage = {"config": config_path, "config_sha256": hashlib.sha256(config_bytes).hexdigest(), "git_commit": commit,
             "seed": cfg.experiment.seed, "wall_seconds": round(time.perf_counter() - start, 1),
             "cpu_seconds": round(time.process_time() - cpu, 1), "peak_working_set_mb": round(peak_working_set_mb(), 1),
             "device": cfg.experiment.device}
    (run_dir / "resource_usage.json").write_text(json.dumps(usage, indent=2), encoding="utf-8")
    diag = diagnostics(run_dir, cfg)
    diag["resources"] = usage
    (run_dir / "phase6a_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    print(json.dumps(diag, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
