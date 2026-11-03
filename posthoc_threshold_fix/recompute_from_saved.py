"""READ-ONLY post-hoc recomputation of report-partition metrics from saved validation_predictions.csv (best checkpoint).

Uses the saved calibrated threshold (selected on the calibration partition; selection logic is unchanged by Phase 7b) and the
consistent decision rule score >= threshold on RAW scores. Never reads or writes anything except the output files given.
usage: python recompute_from_saved.py --repo . --manifests docs/phase6c/EXPERIMENT_MANIFEST.json docs/phase7/EXPERIMENT_MANIFEST.json --out posthoc_threshold_fix
"""
import argparse, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix

ap = argparse.ArgumentParser(); ap.add_argument("--repo", default="."); ap.add_argument("--manifests", nargs="+"); ap.add_argument("--out", default="posthoc_threshold_fix")
a = ap.parse_args(); repo = Path(a.repo); rows = []
for mp in a.manifests:
    m = json.loads((repo / mp).read_text(encoding="utf-8")); phase = "phase6c" if "phase6c" in mp else "phase7"
    for r in m["runs"]:
        d = repo / r["out_dir"]
        if not (d / "COMPLETE.json").exists() or not (d / "validation_predictions.csv").exists(): continue
        f = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
        rp, lp = f["report_partition_at_selected_threshold"], f["last_round_report_partition"]
        v = pd.read_csv(d / "validation_predictions.csv"); y = v.y_true.to_numpy(int); p = v.probability_attack.to_numpy(float)
        thr = float(rp["threshold"]); clipped = np.clip(p, 1e-7, 1 - 1e-7)
        def conf(score, t):
            pred = (score >= t).astype(int); tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
            return pred, tn, fp, fn, tp
        pred_old, *_ = conf(clipped, thr); pred_new, tn, fp, fn, tp = conf(p, thr)
        rows.append(dict(phase=phase, run_id=r["run_id"], dataset=r["dataset"], arm=r["arm"], seed=r["seed"], best_round=f["best_round"],
            threshold_best=thr, threshold_last=float(lp["threshold"]), n_saturated_hi=int((p >= 1 - 1e-7).sum()), n_saturated_lo=int((p <= 1e-7).sum()), n_report=len(p),
            recorded_f1=rp["f1"], recorded_fpr=rp["fpr"], recorded_recall=rp["recall_adr"], recorded_precision=rp["precision"],
            recomputed_f1=f1_score(y, pred_new, zero_division=0), recomputed_fpr=fp / max(fp + tn, 1), recomputed_recall=recall_score(y, pred_new, zero_division=0),
            recomputed_precision=precision_score(y, pred_new, zero_division=0), tp=tp, fp=fp, fn=fn, tn=tn,
            recorded_auc=rp["roc_auc"], recomputed_auc_raw=roc_auc_score(y, p),
            predictions_changed=int((pred_old != pred_new).sum()),
            last_threshold_ge_clip=float(lp["threshold"]) >= 1 - 1e-7, last_recorded_f1=lp["f1"], last_recorded_auc=lp["roc_auc"],
            best_threshold_invalid=thr >= 1 - 1e-7 or thr <= 0.0))
df = pd.DataFrame(rows); df["auc_delta_raw_minus_recorded"] = df.recomputed_auc_raw - df.recorded_auc
df["f1_delta"] = df.recomputed_f1 - df.recorded_f1
out = Path(a.out); out.mkdir(exist_ok=True); df.to_csv(out / "posthoc_best_checkpoint_metrics.csv", index=False)
print("runs", len(df), "| best threshold>=1-1e-7 or ==0:", int(df.best_threshold_invalid.sum()), "| last-round threshold>=1-1e-7:", int(df.last_threshold_ge_clip.sum()),
      "| runs with changed predictions:", int((df.predictions_changed > 0).sum()), "| max |AUC delta|: %.2e" % df.auc_delta_raw_minus_recorded.abs().max(),
      "| max |F1 delta|: %.4f" % df.f1_delta.abs().max())
