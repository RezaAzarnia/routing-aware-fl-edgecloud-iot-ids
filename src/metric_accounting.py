"""Explicit numerator / denominator / population definitions for the network and
update-accounting metrics, with invariants that fail loudly on inconsistency.

Event population E: one row of ``network_metrics.csv`` per (round, selected client).
  explicit_failure  X : the client failed by the explicit failure draw
  delivered         D : ``update_delivered`` (the update-delivery Bernoulli outcome)
  network_failure   N : not D, counted as a failure only when the failure model is enabled
  failed            F : X or N                   (the update never reaches aggregation)
  received          R : E minus F                (real update reaches the server)
Reported ratios and their populations:
  update_delivery_ratio   = |D| / |E|   (unconditional, all selected clients)
  received_ratio          = |R| / |E|
  failure_ratio           = |F| / |E|
  mean_pdr                = mean over E of packets_received / packets_sent (a link-level
                            quantity; in the historical simulator it is an INDEPENDENT draw
                            from the delivery outcome)
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd


def reconcile_network_events(
    network: pd.DataFrame,
    rounds: pd.DataFrame,
    failure_enabled: bool,
    atol: float = 1e-9,
) -> Dict[str, float | int | bool]:
    rounds = rounds[rounds["round"] >= 1]
    explicit = network["explicit_client_failure"].astype(bool)
    delivered = network["update_delivered"].astype(bool)
    received = network["received_by_server"].astype(bool)
    n_events = int(len(network))
    network_failure = (~delivered) if failure_enabled else pd.Series(False, index=network.index)
    failed = explicit | network_failure

    out: Dict[str, float | int | bool] = {
        "events_selected": n_events,
        "explicit_failures": int(explicit.sum()),
        "delivery_draw_failures": int((~delivered).sum()),
        "network_failures_counted": int(network_failure.sum()),
        "both_explicit_and_network": int((explicit & network_failure).sum()),
        "failed_union": int(failed.sum()),
        "received": int(received.sum()),
        "delivered_draw_successes": int(delivered.sum()),
        "delivered_but_explicit_failure": int((delivered & explicit).sum()),
        "update_delivery_ratio__delivered_over_selected": float(delivered.mean()),
        "received_ratio__received_over_selected": float(received.mean()),
        "failure_ratio__failed_over_selected": float(failed.mean()),
        "mean_pdr__over_selected": float(network["pdr"].mean()),
        "mean_pdr__given_delivered": float(network.loc[delivered, "pdr"].mean()) if delivered.any() else float("nan"),
        "mean_pdr__given_not_delivered": float(network.loc[~delivered, "pdr"].mean()) if (~delivered).any() else float("nan"),
        "update_delivery_ratio__given_not_explicit": float(delivered[~explicit].mean()) if (~explicit).any() else float("nan"),
    }

    # ---- invariants -------------------------------------------------------
    assert int(received.sum()) == n_events - int(failed.sum()), "received != selected - failed"
    assert int(failed.sum()) == int(explicit.sum()) + int(network_failure.sum()) - int((explicit & network_failure).sum()), \
        "inclusion-exclusion violated"
    assert not bool((received & failed).any()), "an event is both received and failed"
    if failure_enabled:
        assert int(received.sum()) == int((delivered & ~explicit).sum()), "received != delivered and not explicit"
    assert int(rounds["selected_clients"].sum()) == n_events, "round selected_clients does not sum to the event count"
    assert int(rounds["received_updates"].sum()) == int(received.sum()), "round received_updates mismatch"
    assert int(rounds["failed_clients"].sum()) == int(failed.sum()), "round failed_clients mismatch"
    if "mean_update_delivered" in rounds:
        per_round = network.groupby("round")["update_delivered"].apply(lambda s: s.astype(bool).mean())
        merged = rounds.set_index("round")["mean_update_delivered"].reindex(per_round.index)
        assert np.allclose(merged.to_numpy(float), per_round.to_numpy(float), atol=atol), "per-round delivery mismatch"
    if "imputed_clients" in rounds:
        assert int(rounds["imputed_clients"].sum()) <= int(failed.sum()), "more imputed updates than failures"
    out["invariants_hold"] = True
    return out
