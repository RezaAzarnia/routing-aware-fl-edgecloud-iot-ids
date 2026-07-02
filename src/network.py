from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np

from .config import RoutingConfig


@dataclass
class RouteDecision:
    client_id: int
    edge_id: int
    path_id: str
    score: float
    latency_ms: float
    stability: float
    security: float
    expected_pdr: float
    bandwidth_mbps: float
    route_persistence: float


class DynamicEdgeCloudNetwork:
    def __init__(self, num_clients: int, cfg: RoutingConfig, seed: int) -> None:
        self.num_clients = num_clients
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        edges = cfg.num_edges
        self.client_edge_latency = self.rng.uniform(5, 80, size=(num_clients, edges))
        self.client_edge_stability = self.rng.uniform(0.75, 0.99, size=(num_clients, edges))
        self.client_edge_security = self.rng.uniform(0.60, 0.98, size=(num_clients, edges))
        self.client_edge_bandwidth = self.rng.uniform(20, 150, size=(num_clients, edges))
        self.edge_cloud_latency = self.rng.uniform(5, 50, size=edges)
        self.edge_cloud_stability = self.rng.uniform(0.85, 0.995, size=edges)
        self.edge_cloud_security = self.rng.uniform(0.75, 0.99, size=edges)
        self.edge_cloud_bandwidth = self.rng.uniform(100, 1000, size=edges)
        self.previous_edge: Dict[int, int] = {}
        self.decisions: Dict[int, RouteDecision] = {}

    def _evolve(self) -> None:
        sigma = self.cfg.dynamic_sigma
        self.client_edge_latency *= np.clip(
            1 + self.rng.normal(0, sigma, self.client_edge_latency.shape), 0.8, 1.2
        )
        self.edge_cloud_latency *= np.clip(
            1 + self.rng.normal(0, sigma, self.edge_cloud_latency.shape), 0.8, 1.2
        )
        self.client_edge_stability = np.clip(
            self.client_edge_stability + self.rng.normal(0, sigma / 2, self.client_edge_stability.shape),
            0.05,
            0.999,
        )
        self.edge_cloud_stability = np.clip(
            self.edge_cloud_stability + self.rng.normal(0, sigma / 2, self.edge_cloud_stability.shape),
            0.05,
            0.999,
        )
        self.client_edge_security = np.clip(
            self.client_edge_security + self.rng.normal(0, sigma / 3, self.client_edge_security.shape),
            0.05,
            0.999,
        )
        self.edge_cloud_security = np.clip(
            self.edge_cloud_security + self.rng.normal(0, sigma / 3, self.edge_cloud_security.shape),
            0.05,
            0.999,
        )

        if self.cfg.link_outage_probability > 0:
            outages = self.rng.random(self.client_edge_stability.shape) < self.cfg.link_outage_probability
            self.client_edge_stability[outages] = np.minimum(
                self.client_edge_stability[outages], 0.05
            )

    @staticmethod
    def _normalize(values: np.ndarray, inverse: bool = False) -> np.ndarray:
        minimum = float(values.min())
        maximum = float(values.max())
        if maximum - minimum < 1e-12:
            normalized = np.ones_like(values)
        else:
            normalized = (values - minimum) / (maximum - minimum)
        return 1.0 - normalized if inverse else normalized

    def update_round(self, intelligent_routing: bool = True) -> Dict[int, RouteDecision]:
        self._evolve()
        decisions: Dict[int, RouteDecision] = {}
        for client_id in range(self.num_clients):
            latency = self.client_edge_latency[client_id] + self.edge_cloud_latency
            stability = self.client_edge_stability[client_id] * self.edge_cloud_stability
            security = np.minimum(
                self.client_edge_security[client_id], self.edge_cloud_security
            )
            bandwidth = np.minimum(
                self.client_edge_bandwidth[client_id], self.edge_cloud_bandwidth
            )
            latency_score = self._normalize(latency, inverse=True)
            stability_score = self._normalize(stability)
            security_score = self._normalize(security)
            scores = (
                self.cfg.alpha_latency * latency_score
                + self.cfg.beta_stability * stability_score
                + self.cfg.gamma_security * security_score
            )
            edge_id = int(np.argmax(scores)) if intelligent_routing else int(
                self.rng.integers(0, self.cfg.num_edges)
            )
            persistence = float(self.previous_edge.get(client_id, edge_id) == edge_id)
            decisions[client_id] = RouteDecision(
                client_id=client_id,
                edge_id=edge_id,
                path_id=f"client-{client_id}->edge-{edge_id}->cloud",
                score=float(scores[edge_id]),
                latency_ms=float(latency[edge_id]),
                stability=float(stability[edge_id]),
                security=float(security[edge_id]),
                expected_pdr=float(stability[edge_id]),
                bandwidth_mbps=float(bandwidth[edge_id]),
                route_persistence=persistence,
            )
            self.previous_edge[client_id] = edge_id
        self.decisions = decisions
        return decisions

    def select_clients(self, count: int) -> List[int]:
        if not self.decisions:
            self.update_round()
        ranked = sorted(
            self.decisions.values(),
            key=lambda decision: (decision.score, decision.security, -decision.latency_ms),
            reverse=True,
        )
        return [decision.client_id for decision in ranked[:count]]

    def simulate_transfer(
        self,
        client_id: int,
        update_bytes: int,
    ) -> Dict[str, float | int | bool | str]:
        decision = self.decisions[client_id]
        packets_sent = self.cfg.packets_per_update
        packets_received = int(self.rng.binomial(packets_sent, decision.expected_pdr))
        pdr = packets_received / max(packets_sent, 1)
        delivered = bool(self.rng.random() < decision.expected_pdr)
        serialization_ms = update_bytes * 8 / (decision.bandwidth_mbps * 1e6) * 1000
        jitter_ms = abs(float(self.rng.normal(0, max(1.0, decision.latency_ms * 0.05))))
        end_to_end_ms = decision.latency_ms + serialization_ms + jitter_ms
        delivered_bytes = update_bytes if delivered else 0
        efficiency_mbps = (
            delivered_bytes * 8 / (end_to_end_ms / 1000) / 1e6 if end_to_end_ms > 0 else 0.0
        )
        path_stability = 0.5 * decision.stability + 0.5 * decision.route_persistence
        return {
            "client_id": client_id,
            "edge_id": decision.edge_id,
            "path_id": decision.path_id,
            "route_score": decision.score,
            "end_to_end_delay_ms": end_to_end_ms,
            "link_stability": decision.stability,
            "route_persistence": decision.route_persistence,
            "path_stability": path_stability,
            "security_score": decision.security,
            "packets_sent": packets_sent,
            "packets_received": packets_received,
            "pdr": pdr,
            "update_delivered": delivered,
            "update_bytes": update_bytes,
            "transfer_efficiency_mbps": efficiency_mbps,
        }
