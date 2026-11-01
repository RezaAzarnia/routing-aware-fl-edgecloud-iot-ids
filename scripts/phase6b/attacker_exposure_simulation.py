"""Selection-only simulation (NO training): attacker exposure of each selection policy across seeds.
Replicates how the experiment draws the malicious set (rng seed+2000) and the matched network (seed+3000)."""
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.config import RoutingConfig  # noqa: E402
from src.network import DynamicEdgeCloudNetwork  # noqa: E402

N, K, ROUNDS, FRACTION = 50, 10, 30, 0.2
out = {}
for policy in ("top_k", "coverage_aware", "uniform_random"):
    shares, majority_rounds, ever_selected = [], [], []
    for seed in range(1, 201):
        rng = np.random.default_rng(seed + 2000)
        malicious = set(rng.choice(N, size=int(round(N * FRACTION)), replace=False).tolist())
        net = DynamicEdgeCloudNetwork(N, replace(RoutingConfig(), trace_mode="matched"), seed + 3000)
        counts = np.zeros(N)
        sel_mal = []
        for r in range(1, ROUNDS + 1):
            net.update_round(True)
            if policy == "top_k":
                chosen = net.select_clients(K)
            elif policy == "coverage_aware":
                chosen = net.select_clients_coverage_aware(K, counts, r, 0.5)
            else:
                chosen = np.random.default_rng([seed, 5000, r]).choice(N, K, replace=False).tolist()
            for c in chosen:
                counts[c] += 1
            sel_mal.append(sum(c in malicious for c in chosen))
        shares.append(np.sum(sel_mal) / (ROUNDS * K))
        majority_rounds.append(int(np.sum(np.array(sel_mal) >= 5)))
        ever_selected.append(int((counts > 0).sum()))
    s = np.array(shares)
    out[policy] = {
        "seeds": 200, "malicious_share_mean": float(s.mean()), "malicious_share_sd": float(s.std()),
        "malicious_share_p10_p50_p90": [float(np.percentile(s, p)) for p in (10, 50, 90)],
        "malicious_share_max": float(s.max()),
        "fraction_of_seeds_with_any_majority_attacker_round": float(np.mean(np.array(majority_rounds) > 0)),
        "mean_rounds_with_majority_attackers": float(np.mean(majority_rounds)),
        "fraction_of_seeds_with_over_10_majority_rounds": float(np.mean(np.array(majority_rounds) > 10)),
        "clients_ever_selected_mean": float(np.mean(ever_selected)),
    }
(ROOT / "docs" / "phase6b" / "attacker_exposure_simulation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=1))
