"""READ-ONLY re-evaluation of SAVED checkpoints (best_model_state.pt, last_model_state.pt) with the repaired metrics code.

For every completed run of the given manifests it rebuilds the (seeded, deterministic) three-way validation split, loads each saved
checkpoint, selects the threshold on the CALIBRATION partition only, and evaluates on the REPORT partition with the single consistent
decision rule. Writes ONLY to --out (never into results folders). Final-test data are never read (validation_only configs, test_csv='').
Limits: per-round checkpoints were not saved, so best-checkpoint RE-SELECTION under the repaired AUC cannot be reproduced here.
usage: python reevaluate_checkpoints.py --manifest docs/phase6c/EXPERIMENT_MANIFEST.json --out posthoc_threshold_fix/phase6c.csv [--only-affected FILE]
"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
torch.set_num_threads(2)
from src.config import Config
from src.data import load_dataset
from src.experiment import _model_factory, _validation_metrics
from src.metrics import binary_classification_metrics
from src.server import Server

ap = argparse.ArgumentParser(); ap.add_argument("--manifest", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--datasets", default="unsw,ciciot"); a = ap.parse_args()
m = json.loads((ROOT / a.manifest).read_text(encoding="utf-8"))
runs = [r for r in m["runs"] if (ROOT / r["out_dir"] / "COMPLETE.json").exists() and r["dataset"] in a.datasets.split(",")]
rows, cache, t0 = [], {}, time.time()
for r in sorted(runs, key=lambda r: (r["dataset"], r["seed"], r["order"])):
    d = ROOT / r["out_dir"]
    cfg = Config.from_yaml(d / "resolved_config.yaml")
    assert cfg.experiment.validation_only and cfg.data.test_csv == ""
    key = (r["dataset"], r["seed"])
    if key not in cache:
        cache.clear()
        cache[key] = load_dataset(cfg.data, seed=r["seed"], preprocessor_output=Path("posthoc_threshold_fix/_tmp_preproc.joblib"), load_test=False)
        print(f"[{time.time()-t0:5.0f}s] bundle {key}: thr {len(cache[key].y_thr)} val {len(cache[key].y_val)} rep {len(cache[key].y_rep)}", flush=True)
    b = cache[key]
    f = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
    factory = _model_factory(cfg, b.X_train.shape[1])
    out = dict(phase=m.get("schema", ""), run_id=r["run_id"], dataset=r["dataset"], arm=r["arm"], seed=r["seed"], best_round_recorded=f["best_round"])
    for tag, fn, rec in (("best", "best_model_state.pt", f["report_partition_at_selected_threshold"]), ("last", "last_model_state.pt", f["last_round_report_partition"])):
        server = Server(factory(), device="cpu"); server.load_global_state(torch.load(d / fn, map_location="cpu"))
        prob = server.predict_probabilities          # same batching/code path as the original run
        _, cal = _validation_metrics(cfg, b.y_thr, prob(b.X_thr))            # threshold from CALIBRATION partition only
        thr = float(cal["threshold"])
        rep = binary_classification_metrics(b.y_rep, prob(b.X_rep), thr)
        sel = binary_classification_metrics(b.y_val, prob(b.X_val), thr)
        out.update({f"{tag}_threshold_recomputed": thr, f"{tag}_threshold_recorded": rec["threshold"],
                    f"{tag}_threshold_match": abs(thr - rec["threshold"]) < 1e-9,
                    f"{tag}_rep_auc_old": rec["roc_auc"], f"{tag}_rep_auc_new": rep["roc_auc"],
                    f"{tag}_rep_f1_old": rec["f1"], f"{tag}_rep_f1_new": rep["f1"],
                    f"{tag}_rep_recall_old": rec["recall_adr"], f"{tag}_rep_recall_new": rep["recall_adr"],
                    f"{tag}_rep_precision_old": rec["precision"], f"{tag}_rep_precision_new": rep["precision"],
                    f"{tag}_rep_fpr_old": rec["fpr"], f"{tag}_rep_fpr_new": rep["fpr"],
                    f"{tag}_sel_auc_new": sel["roc_auc"], f"{tag}_n_pred_pos_new": rep["tp"] + rep["fp"]})
    rows.append(out)
    if len(rows) % 10 == 0:
        pd.DataFrame(rows).to_csv(a.out, index=False)
pd.DataFrame(rows).to_csv(a.out, index=False)
df = pd.DataFrame(rows)
print("done", len(df), "runs in %.0fs" % (time.time() - t0), "| thresholds reproduced:", int(df.best_threshold_match.sum()), "/", len(df), "(best),", int(df.last_threshold_match.sum()), "(last)")
