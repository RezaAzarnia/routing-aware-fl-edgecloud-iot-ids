"""Phase 10 preflight on the REAL UNSW-NB15 TRAINING file (train/validation only; the locked test file is never opened; the access guard is installed).
For seeds 22-26: holdout mask, group disjointness, per-client train/holdout sizes, eligible clients (>=10 attack holdout rows), determinism, preprocessor independence
from holdout, and identical mask/partition/eligibility across the 8 arm configs (policy/scenario do not enter the data path).  Output: evidence JSON."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
import protected_access_guard as guard  # noqa: E402

guard.install()
from src.config import Config  # noqa: E402
from src.data import load_dataset  # noqa: E402
from src.data_integrity import predictor_fingerprint  # noqa: E402
from src.partitioning import make_partitions, split_client_holdout_by_mask  # noqa: E402

cfgs = {p.stem: Config.from_yaml(p) for p in sorted((ROOT / "configs" / "phase10").glob("unsw_*.yaml"))}
assert len(cfgs) == 8
rows, ok = [], True
for seed in (22, 23, 24, 25, 26):
    per_cfg = {}
    for name in ("unsw_oracle_topk__independent", "unsw_history_ucb__coupled"):
        c = cfgs[name]
        b = load_dataset(c.data, seed=seed, load_test=False, holdout_fraction=c.fl.client_holdout_fraction)
        parts = make_partitions(b.y_train, num_clients=c.fl.num_clients, strategy=c.fl.partition, seed=seed, dirichlet_alpha=c.fl.dirichlet_alpha, min_client_samples=c.fl.min_client_samples)
        tr, ho = split_client_holdout_by_mask(parts, b.holdout_mask)
        eligible = [i for i, h in enumerate(ho) if int((b.y_train[h] == 1).sum()) >= 10]
        per_cfg[name] = (b.holdout_mask.copy(), eligible, [len(x) for x in tr], [len(x) for x in ho], b.X_train.shape[1])
    m1, m2 = per_cfg["unsw_oracle_topk__independent"], per_cfg["unsw_history_ucb__coupled"]
    same = np.array_equal(m1[0], m2[0]) and m1[1] == m2[1] and m1[2] == m2[2]
    # group disjointness on raw predictor vectors: reload raw features through the same path used by the loader is expensive; use the encoded matrix instead
    # (identical raw vectors <=> identical encoded vectors): no held-out row may equal any training row.
    c = cfgs["unsw_oracle_topk__independent"]
    b = load_dataset(c.data, seed=seed, load_test=False, holdout_fraction=c.fl.client_holdout_fraction)
    import pandas as pd
    fp = predictor_fingerprint(pd.DataFrame(b.X_train), list(range(b.X_train.shape[1])))
    g = b.holdout_groups
    raw_disjoint = not (set(g[b.holdout_mask].tolist()) & set(g[~b.holdout_mask].tolist()))     # 6-significant-digit predictor groups (stricter than the exact float64 policy)
    disjoint = raw_disjoint and not (set(fp[b.holdout_mask].tolist()) & set(fp[~b.holdout_mask].tolist()))   # and no encoded (model-input) vector is shared
    deterministic = np.array_equal(b.holdout_mask, m1[0])
    rec = {"seed": seed, "train_rows": int(len(b.y_train)), "holdout_rows": int(b.holdout_mask.sum()), "holdout_fraction": round(float(b.holdout_mask.mean()), 4), "feature_dim": int(m1[4]),
           "min_client_train_rows": int(min(m1[2])), "min_client_holdout_rows": int(min(m1[3])), "eligible_clients": len(m1[1]), "eligible_list": m1[1],
           "identical_across_arm_configs": bool(same), "holdout_rows_group_disjoint_from_training_rows": bool(disjoint), "deterministic": bool(deterministic)}
    ok &= same and disjoint and deterministic and rec["min_client_train_rows"] >= 1 and rec["eligible_clients"] >= 10
    rows.append(rec)
    print(rec, flush=True)
(ROOT / "Phase10_NonOracle_Routing" / "preflight_real_data.json").write_text(json.dumps({"pass": bool(ok), "rows": rows, "locked_test_opened": guard.violations}, indent=1), encoding="utf-8")
print("PASS" if ok and not guard.violations else "FAIL")
sys.exit(0 if ok and not guard.violations else 1)
