"""Phase 10: history-feedback client selector (UCB1-style bandit; a STANDARD, literature-grounded baseline, not a new method).

Causality by construction: the class has no reference to the network simulator. Its only inputs are (a) ``observe`` calls made by the server AFTER a round with
what the server genuinely sees for a selected client (was the update received? what was the end-to-end delay of a received update?) and (b) the round number and
a seed. It never sees true stability/latency/security, attacker identity, labels or any not-yet-happened outcome.

Index for client i at round t (selections before t only):
  n_i = times selected, r_i = times its update was received, mean_i = r_i / n_i
  never selected (n_i = 0)  -> +inf (optimistic initialisation: every client is tried before any is exploited; ties broken by a seeded permutation)
  success_ucb_i = min(1, mean_i + c * sqrt(ln(t) / n_i))            (UCB1, c = sqrt(2) by default; not tuned)
  latency_i     = EWMA (alpha 0.3) of the observed delay of RECEIVED updates; clients with no observed delay get the neutral latency score 0.5
  latency_score_i = 1 - minmax(latency_i) over clients with an observed delay (0.5 if fewer than two distinct values)
  score_i = (w_lat * latency_score_i + w_succ * success_ucb_i) / (w_lat + w_succ), with w_lat, w_succ the routing weights alpha_latency, beta_stability;
            the security weight is dropped (the security indicator is not observable).
Selection: top ``count`` by (score desc, seeded random tiebreak); fully deterministic given (seed, history).
"""
from __future__ import annotations

import math
from typing import List

import numpy as np


class HistorySelector:
    def __init__(self, num_clients: int, w_latency: float, w_success: float, c: float = math.sqrt(2.0), ewma_alpha: float = 0.3, seed: int = 0) -> None:
        if num_clients <= 0 or w_latency < 0 or w_success < 0 or (w_latency + w_success) <= 0 or c < 0 or not 0 < ewma_alpha <= 1:
            raise ValueError("invalid HistorySelector parameters")
        self.n = num_clients
        self.w_lat, self.w_succ, self.c, self.alpha, self.seed = w_latency, w_success, c, ewma_alpha, seed
        self.selected = np.zeros(num_clients, dtype=np.int64)
        self.received = np.zeros(num_clients, dtype=np.int64)
        self.delay = np.full(num_clients, np.nan)
        self._pending: set = set()

    def select(self, count: int, round_number: int) -> List[int]:
        t = max(int(round_number), 1)
        mean = np.where(self.selected > 0, self.received / np.maximum(self.selected, 1), 0.0)
        bonus = self.c * np.sqrt(math.log(max(t, 2)) / np.maximum(self.selected, 1))
        succ = np.minimum(1.0, mean + bonus)
        observed = ~np.isnan(self.delay)
        lat = np.full(self.n, 0.5)
        if observed.sum() >= 2 and np.nanmax(self.delay) - np.nanmin(self.delay) > 1e-12:
            lo, hi = np.nanmin(self.delay), np.nanmax(self.delay)
            lat[observed] = 1.0 - (self.delay[observed] - lo) / (hi - lo)
        score = (self.w_lat * lat + self.w_succ * succ) / (self.w_lat + self.w_succ)
        score = np.where(self.selected == 0, np.inf, score)
        tiebreak = np.random.default_rng([self.seed, 7000, t]).permutation(self.n)
        order = sorted(range(self.n), key=lambda i: (-score[i], tiebreak[i]))
        chosen = [int(i) for i in order[:count]]
        self._pending = set(chosen)
        for i in chosen:
            self.selected[i] += 1
        return chosen

    def observe(self, client_id: int, received: bool, delay_ms: float | None = None) -> None:
        """Server-side observation about a client selected in the CURRENT round (call after the round, before the next select)."""
        if client_id not in self._pending:
            raise ValueError("observe() is only valid for a client selected in the current round")
        if received:
            self.received[client_id] += 1
            if delay_ms is not None and math.isfinite(delay_ms):
                self.delay[client_id] = delay_ms if math.isnan(self.delay[client_id]) else (1 - self.alpha) * self.delay[client_id] + self.alpha * delay_ms
