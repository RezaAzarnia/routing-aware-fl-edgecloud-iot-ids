# Simulation, threshold and aggregation specification (Table 4 v2 protocol)

Verified against `src/network.py`, `src/attacks.py`, `src/metrics.py`, `src/privacy.py`, `src/experiment.py`, `src/data.py` and the locked configs in `configs/table4_v2/` at the time of writing. Nothing here describes an experiment that was not run.

## Network model (`src/network.py`; `routing.delivery_model = independent_draws`, `trace_mode = matched`)
* 50 clients, 3 edge nodes; each client has one candidate path per edge node (client -> edge -> cloud).
* Initial link attributes, uniform: client-edge latency 5-80 ms, stability 0.75-0.99, security 0.60-0.98, bandwidth 20-150 Mbit/s; edge-cloud latency 5-50 ms, stability 0.85-0.995, security 0.75-0.99, bandwidth 100-1000 Mbit/s.
* Each round: latencies x clip(1+N(0, 0.025), 0.8, 1.2); stabilities += N(0, 0.0125) and securities += N(0, 0.025/3), clipped to [0.05, 0.999]; each client-edge link independently drops with probability `link_outage_probability` = 0.01 to stability <= 0.05.
* Path: latency = client-edge + edge-cloud; stability = product; security = minimum; bandwidth = minimum.
* Route score = 0.4 * (1 - minmax(latency)) + 0.3 * minmax(stability) + 0.3 * minmax(security), min-max over the client's 3 paths (all-equal -> 1). The simulator's current link state is used directly (no measurement noise); security is a simulator attribute, not an observed detection signal. Routed path = argmax score; random path (`routing.path_policy: random`) draws the edge from a stream seeded by (seed, 7000, round, client). Top-k client selection ranks by (score, security, -latency).
* Transfer: 100 packets; packets received on first attempt ~ Binomial(100, path stability) (first-transmission PDR); update delivered ~ Bernoulli(path stability) (separate draw, so PDR and delivery are distinct events); delay = path latency + update_bytes*8/bandwidth + |N(0, max(1, 0.05*latency))| ms jitter. No queueing, congestion or retransmission is modelled in this delivery model. Transfer efficiency = delivered bytes * 8 / delay (Mbit/s), 0 for undelivered updates.
* Path stability metric = mean over selected paths of 0.5 * link stability + 0.5 * route persistence (1 if the client used the same edge in the previous round).
* Client failure: probability 0.1 per selected client and round (`explicit_failure_draw`).
* Known limitation: the delivery uniform is not a common random number across different path policies.

## Attack model (`src/attacks.py`)
Sign flip: a malicious client's update is replaced by -5.0 * update. `attack.assignment = exposure_controlled`: in each round exactly round(0.2 * 10) = 2 selected clients are malicious (per-(seed, round) stream), independent of network state and route scores. No other attack type, collusion or adaptive attacker was evaluated.

## Threshold and checkpoint selection (`src/metrics.py`, `src/data.py`)
* The validation pool is split into three predictor-group-disjoint, label-stratified partitions (calibration / selection / report; `StratifiedGroupKFold`, seed+23). CICIoT2023: about 48,875 records each, 1,564 benign each. UNSW-NB15: 8,350 / 8,350 / 8,348 (seed 12), 2,666-2,668 benign each.
* Threshold: 1,001 candidates on the calibration partition; feasible set FPR <= 0.15 and recall >= 0.60; choose maximum recall (ties: F1, balanced accuracy, closeness to 0.5); if infeasible, maximize recall subject to FPR <= 0.15 and flag `constraint_feasible = false`. The reported FPR (about 0.14-0.15) is therefore set by the cap. Operating points at 1%, 5% and 15% FPR caps are stored per run in `threshold_diagnostics.json` (raw run outputs, not published).
* Checkpoint: the round whose selection-partition ROC-AUC exceeds the incumbent by more than `early_stopping_min_delta` = 1e-4.

## Aggregation edge cases (`src/aggregation.py`, `src/privacy.py`, `src/experiment.py`)
* MAD filter: threshold = median(d) + k * (1.4826 * MAD(d) + 1e-12), k = 2.5; if no update passes, the update closest to the coordinate-wise median is kept.
* Surrogates: if >= 2 real updates arrived, each failed client receives the coordinate-wise median of the real updates, with raw weight scaled by 0.5; otherwise the client is excluded. If no update arrives, aggregation, noise and accounting are skipped (never occurred in the 1,200 rounds of the 40 controlled runs).
* Weight cap: raw weight proportional to local sample count; water-filling projection with cap max(0.1, 1/n). When fewer than 10 updates are retained the cap is infeasible.
* Measured in the proposed pipeline (E4, 2 datasets x 5 seeds x 30 rounds = 300 rounds): fewer than 10 retained updates in 92% of rounds (minimum 6); largest single weight 0.167; surrogate weight share mean 0.30, median 0.25, maximum 1.0; 10 rounds with only surrogate updates retained. The collective surrogate share is therefore NOT bounded by the 0.5 recovery coefficient or by the per-client cap in the reference ordering. The earlier-phase real-only / collectively capped variants (`ctl_imputation_*`, `corrected`) address this but were not part of the five-seed Table 4 v2 comparison.

## Data (CICIoT2023, `data/CICIoT2023/prepared_verified_v2_filegroup/`, git-ignored)
309 unique raw CSVs; requested 1,000,000 / 200,000 / 300,000 (train / validation / test); feature-identical duplicates removed (73,867 train, 53,374 validation); prepared 926,133 / 146,626 / 300,000 (test reserved, never opened); 39 numerical features; `split_mode = file_group` (17 of 34 classes with >= 3 source files are file-group separated, the other 17 are row-stratified). UNSW-NB15: 175,341 official training records -> 150,293 train + 25,048 validation pool; 42 raw features -> 194 encoded; official test (82,332) unused. Hashes: `docs/phase6c/EXPERIMENT_MANIFEST.json`.
