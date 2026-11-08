"""Held-out per-client recall for the participation runs: V1 UNSW (25 runs) and V2 CICIoT2023 (30 runs) + V2 UNSW regression controls are NOT re-evaluated (V1 counterparts used).
Read-only: loads TRAINING data through the V2 overlay (never the reserved test set), the stored best model and the recorded threshold. Writes only into the package directory.
The holdout mask is recomputed and its sha256 must equal the one stored by the run (CIC) -> proves the evaluated rows are exactly the never-trained-on rows.
usage: python scripts/supp_final/holdout_eval.py [--out Supplementary_Experiments_Package]"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "supp_v2"))
sys.path.insert(0, str(ROOT))
import v2_overlay  # noqa: E402

v2_overlay.install()
sys.path.insert(0, str(ROOT / "scripts" / "phase10"))
import torch  # noqa: E402
from supp_common import MANIFEST, V1_MANIFEST, load_manifest  # noqa: E402
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402
from src.experiment import _model_factory  # noqa: E402
from src.partitioning import make_partitions, split_client_holdout_by_mask  # noqa: E402

MIN_POS = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Supplementary_Experiments_Package")
    out = ROOT / ap.parse_args().out
    M1, M2 = load_manifest(V1_MANIFEST), load_manifest(MANIFEST)
    jobs = [(r, "SUPP_V1") for r in M1["runs"] if r["family"] == "E_participation" and r["dataset"] == "unsw" and (ROOT / r["out_dir"] / "COMPLETE.json").exists()]
    jobs += [(r, "SUPP_V2") for r in M2["runs"] if r["family"] == "E_participation_cic"]
    rows, per_client = [], []
    cache = {}
    for r, ver in sorted(jobs, key=lambda x: (x[0]["dataset"], x[0]["seed"], x[0]["arm"])):
        d = ROOT / r["out_dir"]
        cfg = Config.from_yaml(d / "resolved_config.yaml")
        key = (r["dataset"], r["seed"])
        if key not in cache:
            cache.clear()
            cache[key] = load_dataset(cfg.data, seed=cfg.experiment.seed, load_test=False, holdout_fraction=cfg.fl.client_holdout_fraction)
        bundle = cache[key]
        if ver == "SUPP_V2":
            aud = json.loads((d / "client_holdout_audit.json").read_text())
            sha = hashlib.sha256(np.packbits(bundle.holdout_mask).tobytes()).hexdigest()
            assert sha == aud["holdout_mask_sha256"], f"holdout mask mismatch {r['run_id']}"
        parts = make_partitions(bundle.y_train, num_clients=cfg.fl.num_clients, strategy=cfg.fl.partition, seed=cfg.experiment.seed,
                                dirichlet_alpha=cfg.fl.dirichlet_alpha, min_client_samples=cfg.fl.min_client_samples)
        _, hold = split_client_holdout_by_mask(parts, bundle.holdout_mask)
        for ckpt, thr_key in (("selected", "best_model_state.pt"), ("last", "last_model_state.pt")):
            model = _model_factory(cfg, bundle.X_train.shape[1])()
            model.load_state_dict(torch.load(d / thr_key, map_location="cpu", weights_only=True))
            model.eval()
            fv = json.loads((d / "final_validation_metrics.json").read_text())
            thr = float(fv["selected_operating_point"]["threshold"]) if ckpt == "selected" else float(fv["last_round_selection_partition"]["threshold"])
            nm = pd.read_csv(d / "network_metrics.csv")
            times = nm[nm.selected == True].groupby("client_id").size().reindex(range(cfg.fl.num_clients), fill_value=0)  # noqa: E712
            recs = []
            with torch.no_grad():
                for cid, idx in enumerate(hold):
                    if len(idx) == 0:
                        recs.append(dict(client_id=cid, holdout_samples=0, holdout_attack=0, recall=np.nan, fpr=np.nan, times_selected=int(times[cid])))
                        continue
                    p = torch.softmax(model(torch.from_numpy(bundle.X_train[idx]).float()), 1)[:, 1].numpy()
                    y = bundle.y_train[idx]
                    pred = p >= thr
                    recs.append(dict(client_id=cid, holdout_samples=int(len(idx)), holdout_attack=int((y == 1).sum()),
                                     recall=float(pred[y == 1].mean()) if (y == 1).sum() >= MIN_POS else np.nan,
                                     fpr=float(pred[y == 0].mean()) if (y == 0).sum() >= MIN_POS else np.nan, times_selected=int(times[cid])))
            h = pd.DataFrame(recs)
            h["eligible"] = h.holdout_attack >= MIN_POS
            for _, x in h.iterrows():
                per_client.append(dict(version=ver, run_id=r["run_id"], dataset=r["dataset"], arm=r["arm"], seed=r["seed"], checkpoint=ckpt, **x.to_dict()))
            valid = h.loc[h.eligible, "recall"].dropna()
            never = h[(h.times_selected == 0) & h.eligible & h.recall.notna()]
            rows.append(dict(version=ver, run_id=r["run_id"], dataset=r["dataset"], arm=r["arm"], seed=r["seed"], checkpoint=ckpt,
                             worst_client_recall=float(valid.min()) if len(valid) else np.nan, p10_client_recall=float(valid.quantile(0.10)) if len(valid) else np.nan,
                             mean_client_recall=float(valid.mean()) if len(valid) else np.nan, mean_recall_never_selected=float(never.recall.mean()) if len(never) else np.nan,
                             n_never_selected_eligible=int(len(never)), clients_with_valid_recall=int(len(valid)), clients_without_valid_recall=int(len(h) - len(valid))))
        print("done", r["run_id"], flush=True)
    pd.DataFrame(rows).to_csv(out / "SUPPLEMENTARY_HOLDOUT_CLIENT_METRICS.csv", index=False)
    pd.DataFrame(per_client).to_csv(out / "SUPPLEMENTARY_HOLDOUT_PER_CLIENT.csv", index=False)
    print("HOLDOUT EVAL COMPLETE", len(rows))


if __name__ == "__main__":
    main()
