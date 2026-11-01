"""Selection-only simulation (NO training): network benefit of each selection policy and delivery model, 200 seeds."""
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.config import RoutingConfig  # noqa: E402
from src.network import DynamicEdgeCloudNetwork  # noqa: E402

N, K, R = 50, 10, 30
out = {}
for model in ("independent_draws", "packet_coupled"):
    for policy in ("top_k", "coverage_aware", "uniform_random"):
        deliv, pdr, delay, wire = [], [], [], []
        for seed in range(1, 201):
            net = DynamicEdgeCloudNetwork(N, replace(RoutingConfig(), trace_mode="matched", delivery_model=model), seed + 3000)
            counts = np.zeros(N)
            rows = []
            for r in range(1, R + 1):
                net.update_round(True)
                if policy == "top_k":
                    chosen = net.select_clients(K)
                elif policy == "coverage_aware":
                    chosen = net.select_clients_coverage_aware(K, counts, r, 0.5)
                else:
                    chosen = np.random.default_rng([seed, 5000, r]).choice(N, K, replace=False).tolist()
                for c in chosen:
                    counts[c] += 1
                    rows.append(net.simulate_transfer(c, 170_000))
            deliv.append(np.mean([x["update_delivered"] for x in rows]))
            pdr.append(np.mean([x["pdr"] for x in rows]))
            delay.append(np.mean([x["end_to_end_delay_ms"] for x in rows]))
            wire.append(np.mean([x["bytes_on_wire"] for x in rows]) / 170_000)
        out[f"{model}|{policy}"] = {"delivery_ratio_mean": float(np.mean(deliv)), "delivery_ratio_sd_across_seeds": float(np.std(deliv)),
                                    "pdr_first_tx_mean": float(np.mean(pdr)), "delay_ms_mean": float(np.mean(delay)),
                                    "wire_bytes_over_update_bytes": float(np.mean(wire))}
(ROOT / "docs" / "phase6b" / "network_advantage_simulation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
for k, v in out.items():
    print(f"{k:32s} delivery={v['delivery_ratio_mean']:.3f}±{v['delivery_ratio_sd_across_seeds']:.3f} pdr={v['pdr_first_tx_mean']:.3f} delay={v['delay_ms_mean']:.1f} ms wire/update={v['wire_bytes_over_update_bytes']:.3f}")
