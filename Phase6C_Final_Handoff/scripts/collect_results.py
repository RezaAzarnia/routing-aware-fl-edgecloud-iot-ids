"""Collect and verify all Phase 6C results (read-only on the experiment outputs).

usage: python collect_results.py --repo <repo root> --out <handoff dir>
Writes tables/*.csv, provenance/run_inventory.csv and provenance/verification.json.
Never writes into results_phase6c and never touches final-test files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gini(x):
    x = np.sort(np.asarray(x, float))
    if x.sum() == 0:
        return float("nan")
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


ROUND_COLS = ["round", "selected_clients", "received_updates", "kept_updates", "rejected_updates", "failed_clients",
              "recovered_clients", "malicious_selected", "malicious_received", "mean_train_loss", "communication_bytes",
              "communication_bytes_on_wire", "mean_end_to_end_delay_ms", "mean_pdr", "mean_expected_pdr",
              "mean_update_delivered", "imputed_clients", "retained_for_weighting", "real_weight_share",
              "surrogate_weight_share", "max_applied_weight_share", "server_applied_update_l2_norm",
              "aggregate_signal_l2_norm", "privacy_epsilon_estimate", "privacy_noise_std", "val_roc_auc", "val_f1",
              "val_fpr", "val_precision", "val_recall_adr", "val_rep_roc_auc", "val_rep_f1", "val_rep_fpr",
              "val_rep_recall_adr", "val_rep_precision"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    repo, out = Path(a.repo), Path(a.out)
    (out / "tables").mkdir(parents=True, exist_ok=True)
    (out / "provenance").mkdir(parents=True, exist_ok=True)
    mpath = repo / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    runs = sorted(manifest["runs"], key=lambda r: r["order"])
    problems, inv, rows, rounds, nets, csel = [], [], [], [], [], []
    ids = [r["run_id"] for r in runs]
    if len(set(ids)) != len(ids):
        problems.append("duplicate run_id in manifest")
    for r in runs:
        d = repo / r["out_dir"]
        rec = {"run_id": r["run_id"], "dataset": r["dataset"], "arm": r["arm"], "seed": r["seed"], "out_dir": r["out_dir"]}
        ok = True
        if (d / "FAILED.json").exists():
            problems.append(f"{r['run_id']}: FAILED.json present"); ok = False
        if not (d / "COMPLETE.json").exists():
            problems.append(f"{r['run_id']}: COMPLETE.json missing"); inv.append({**rec, "verified": False}); continue
        c = json.loads((d / "COMPLETE.json").read_text(encoding="utf-8"))
        rec["config_sha256_expected"] = r["config_sha256"]
        rec["config_sha256_recorded"] = c.get("config_sha256")
        rec["config_hash_match"] = c.get("config_sha256") == r["config_sha256"]
        rec["manifest_hash_match"] = c.get("manifest_sha256") == manifest["manifest_sha256"]
        rec["code_fingerprint_match"] = c.get("code_fingerprint") == manifest["code_fingerprint"]
        bad = []
        for name, h in c.get("artifact_sha256", {}).items():
            p = d / name
            if not p.exists() or sha256(p) != h:
                bad.append(name)
        rec["artifacts_checked"] = len(c.get("artifact_sha256", {}))
        rec["artifacts_bad"] = ";".join(bad)
        for req in manifest["required_artifacts"]:
            if not (d / req).exists():
                bad.append("missing:" + req)
        if not (rec["config_hash_match"] and rec["manifest_hash_match"] and rec["code_fingerprint_match"]) or bad:
            ok = False
            problems.append(f"{r['run_id']}: integrity {rec['config_hash_match']}/{rec['manifest_hash_match']}/{rec['code_fingerprint_match']} bad={bad}")
        rec["verified"] = ok
        rec["duration_seconds"] = c.get("duration_seconds")
        rec["completed_utc"] = c.get("completed_utc")
        inv.append(rec)
        # ---- metrics ----
        fin = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
        rp, lp = fin["report_partition_at_selected_threshold"], fin["last_round_report_partition"]
        rm = pd.read_csv(d / "round_metrics.csv")
        diag = json.loads((d / "phase6c_diagnostics.json").read_text(encoding="utf-8"))
        acc = json.loads((d / "metric_accounting.json").read_text(encoding="utf-8"))
        ag = pd.read_csv(d / "aggregation_diagnostics.csv")
        cl = pd.read_csv(d / "client_level_recall.csv")
        part = diag.get("participation", {})
        t_cl = cl[["client_id", "samples", "times_selected"]].copy()
        t_cl.insert(0, "seed", r["seed"]); t_cl.insert(0, "arm", r["arm"]); t_cl.insert(0, "dataset", r["dataset"]); csel.append(t_cl)
        loss = rm["mean_train_loss"].dropna()
        row = {"run_id": r["run_id"], "dataset": r["dataset"], "arm": r["arm"], "seed": r["seed"],
               "test_data_loaded": fin.get("test_data_loaded"), "protocol": fin.get("protocol"),
               "best_round": fin.get("best_round"), "threshold_source": fin.get("threshold_source"),
               "report_rows": fin["partitions"].get("report_rows"),
               "best_auc": rp["roc_auc"], "best_pr_auc": rp.get("pr_auc"), "best_f1": rp["f1"], "best_precision": rp["precision"],
               "best_recall_adr": rp["recall_adr"], "best_fpr": rp["fpr"], "best_threshold": rp["threshold"],
               "last_auc": lp["roc_auc"], "last_pr_auc": lp.get("pr_auc"), "last_f1": lp["f1"], "last_precision": lp["precision"],
               "last_recall_adr": lp["recall_adr"], "last_fpr": lp["fpr"],
               "final5_val_auc_mean": rm["val_rep_roc_auc"].tail(5).mean() if "val_rep_roc_auc" in rm else np.nan,
               "final5_val_f1_mean": rm["val_rep_f1"].tail(5).mean() if "val_rep_f1" in rm else np.nan,
               "auc_drop_best_minus_last": rp["roc_auc"] - lp["roc_auc"],
               "train_loss_first": loss.iloc[0] if len(loss) else np.nan, "train_loss_last": loss.iloc[-1] if len(loss) else np.nan,
               "train_loss_max": loss.max() if len(loss) else np.nan,
               "first_round_loss_gt10": int(rm.loc[rm["mean_train_loss"] > 10, "round"].min()) if (rm["mean_train_loss"] > 10).any() else np.nan,
               "diverged_loss_gt100": bool((rm["mean_train_loss"] > 100).any()),
               "nonfinite_core_metrics": int((~np.isfinite(rm[["val_roc_auc", "val_f1", "val_fpr"]].astype(float))).sum().sum()),
               "selected_total": rm["selected_clients"].sum(), "received_total": rm["received_updates"].sum(),
               "kept_total": rm["kept_updates"].sum(), "rejected_total": rm["rejected_updates"].sum(),
               "failed_total": rm["failed_clients"].sum(), "recovered_total": rm["recovered_clients"].sum(),
               "malicious_selected_total": rm["malicious_selected"].sum(), "malicious_received_total": rm["malicious_received"].sum(),
               "malicious_accepted_total": int((ag["effective_malicious_update"] & ag["kept"]).sum()) if len(ag) else 0,
               "malicious_rejected_total": int((ag["effective_malicious_update"] & ~ag["kept"]).sum()) if len(ag) else 0,
               "real_kept_per_round_mean": ag[(~ag["is_recovered_update"]) & ag["kept"]].groupby("round").size().reindex(range(1, 31), fill_value=0).mean() if len(ag) else np.nan,
               "rounds_le1_real_kept": int((ag[(~ag["is_recovered_update"]) & ag["kept"]].groupby("round").size().reindex(range(1, 31), fill_value=0) <= 1).sum()) if len(ag) else np.nan,
               "surrogate_updates_total": int(ag["is_recovered_update"].sum()) if len(ag) else 0,
               "surrogate_weight_share_mean": rm["surrogate_weight_share"].mean(),
               "real_weight_share_mean": rm["real_weight_share"].mean(),
               "update_norm_pre_clip_mean": ag["pre_clip_l2_norm"].mean() if len(ag) else np.nan,
               "update_norm_pre_clip_max": ag["pre_clip_l2_norm"].max() if len(ag) else np.nan,
               "server_update_norm_max": rm["server_applied_update_l2_norm"].max(),
               "mean_pdr": rm["mean_pdr"].mean(), "mean_delay_ms": rm["mean_end_to_end_delay_ms"].mean(),
               "mean_update_delivered": rm["mean_update_delivered"].mean(),
               "update_delivery_ratio": acc.get("update_delivery_ratio__delivered_over_selected"),
               "received_ratio": acc.get("received_ratio__received_over_selected"),
               "failure_ratio": acc.get("failure_ratio__failed_over_selected"),
               "explicit_failures": acc.get("explicit_failures"), "delivery_draw_failures": acc.get("delivery_draw_failures"),
               "communication_bytes_total": rm["communication_bytes"].sum(),
               "communication_bytes_on_wire_total": rm["communication_bytes_on_wire"].sum(),
               "clients_ever_selected": part.get("clients_ever_selected"), "clients_never_selected": part.get("longest_exclusion_gap_rounds_selection", {}).get("clients_never_selected"),
               "selection_gini_reported": part.get("selection_gini"), "top5_selection_share": part.get("top5_client_selection_share"),
               "selection_gini_recomputed": gini(cl["times_selected"]),
               "privacy_epsilon_final_diagnostic": rm["privacy_epsilon_estimate"].iloc[-1], "privacy_noise_std": rm["privacy_noise_std"].iloc[-1],
               "duration_seconds": c.get("duration_seconds")}
        rows.append(row)
        keep = [x for x in ROUND_COLS if x in rm.columns]
        t = rm[keep].copy()
        t.insert(0, "seed", r["seed"]); t.insert(0, "arm", r["arm"]); t.insert(0, "dataset", r["dataset"])
        rounds.append(t)
        nm = pd.read_csv(d / "network_metrics.csv")
        rcv = nm[nm["selected"]] if "selected" in nm else nm
        def col(name, how="mean", q=None):
            if name not in rcv.columns:
                return float("nan")          # unavailable for this arm (not inferred)
            v = rcv[name]
            if v.dtype == bool or v.dtype == object:
                v = v.astype(float)
            return v.quantile(q) if how == "q" else getattr(v, how)()
        nets.append({"dataset": r["dataset"], "arm": r["arm"], "seed": r["seed"], "events_selected": len(rcv),
                     "pdr_mean": col("pdr"), "pdr_after_arq_mean": col("pdr_after_arq"),
                     "delay_ms_mean": col("end_to_end_delay_ms"), "delay_ms_p95": col("end_to_end_delay_ms", "q", 0.95),
                     "jitter_ms_mean": col("jitter_ms"), "retransmission_rounds_mean": col("retransmission_rounds"),
                     "packets_lost_total": col("packets_lost", "sum"), "packets_unrecovered_total": col("packets_unrecovered", "sum"),
                     "update_delivered_rate": col("update_delivered"), "received_by_server_rate": col("received_by_server"),
                     "bytes_on_wire_total": col("bytes_on_wire", "sum"), "link_stability_mean": col("link_stability"),
                     "route_score_mean": col("route_score"), "security_score_mean": col("security_score"),
                     "transfer_efficiency_mbps_mean": col("transfer_efficiency_mbps"),
                     "explicit_client_failure_rate": col("explicit_client_failure")})
    # extra / unexpected directories
    expected = {str((repo / r["out_dir"]).resolve()) for r in runs}
    found = {str(p.parent.resolve()) for p in (repo / "results_phase6c").glob("*/*/seed_*/COMPLETE.json")}
    extra = sorted(found - expected)
    if extra:
        problems.append(f"unexpected completed dirs: {extra}")
    final_test = repo / "results_phase6c" / "_final_test"
    verified = sum(1 for x in inv if x.get("verified"))
    by_ds = pd.DataFrame(inv).query("verified").groupby("dataset").size().to_dict() if verified else {}
    summary = {"manifest_sha256": manifest["manifest_sha256"], "code_fingerprint": manifest["code_fingerprint"],
               "n_manifest_runs": len(runs), "verified_complete": verified, "by_dataset": by_ds,
               "failed_or_corrupt_problems": problems, "unexpected_dirs": extra,
               "final_test_results_dir_exists": final_test.exists(),
               "any_run_test_data_loaded": bool(any(x["test_data_loaded"] for x in rows)),
               "protocols": sorted({x["protocol"] for x in rows}), "complete": verified == 240 and not problems}
    (out / "provenance" / "verification.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(inv).to_csv(out / "provenance" / "run_inventory.csv", index=False)
    if not summary["complete"]:
        print("NOT COMPLETE / PROBLEMS:", json.dumps(summary, indent=2)); return 2
    pd.DataFrame(rows).to_csv(out / "tables" / "all_runs.csv", index=False)
    pd.concat(rounds).to_csv(out / "tables" / "round_metrics.csv", index=False)
    pd.DataFrame(nets).to_csv(out / "tables" / "network_metrics.csv", index=False)
    pd.concat(csel).to_csv(out / "tables" / "client_selection.csv", index=False)
    arms = pd.DataFrame(manifest["arms"]); arms.to_csv(out / "tables" / "arm_definitions.csv", index=False)
    (out / "provenance" / "experiment_manifest.json").write_text(mpath.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
