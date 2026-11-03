# Non-oracle routing: gap analysis, novelty decision and minimal design (no code written, no training run)

## 1. Observable vs privileged inputs (from `src/network.py`, `src/experiment.py`)
| Input used by selection | Source in code | Class |
|---|---|---|
| route score s_i = 0.4·latency⁻¹ + 0.3·stability + 0.3·security (min-max over 3 edges) | `update_round`, current-round link state | **Privileged**: true latency, true stability (= `expected_pdr`, the delivery probability), simulated security attribute |
| tie-break (security, −latency) | `select_clients` | privileged |
| `selection_counts` (past selections), round index | `select_clients_coverage_aware` | **Observable** (server bookkeeping) |
| past outcomes: `update_delivered`, `received_by_server`, measured delay, first-transmission PDR | per-event rows, logged | **Observable after the fact, currently NOT used for selection** |
Delivery draws use an independent per-(seed, round, client) stream, so no future outcome leaks; the leak is the **true probability**, with no estimation noise or delay.

## 2. Does coverage-aware selection already solve it?
No. It adds a count penalty λ·n_i/(t−1) (λ=0.5, untuned) to the **oracle** score: it restores participation (Gini 0.73→0.49, never-selected 27.2→8.0) at PDR 0.851→0.833, but (a) still requires oracle probabilities, (b) its penalty is not tied to reliability uncertainty, (c) 8 clients stay unselected. Not tested anywhere: whether unreliable clients are *systematically* underrepresented **and** that matters for accuracy — in the simulator the network attributes are drawn independently of each client's data, so the correlated case is structurally absent (per-client recall showed no starvation penalty: 0.975 vs 0.976).

## 3. Closest prior work (searched in this phase; abstract/snippet level only, full texts NOT read)
* Cho et al., bandit-based communication-efficient client selection (UCB-CS), https://arxiv.org/abs/2012.08009 — bandit selection with fairness remarks.
* Zhu et al., asynchronous FL client selection as a multi-armed bandit with UCB and Lyapunov virtual queues for long-term fairness under unknown channels (IEEE TWC 2023; via https://kms.shanghaitech.edu.cn/handle/2MSLDSTB/241106) — closest match.
* Wang et al., FedCote, selection probabilities under transmission failures, https://arxiv.org/abs/2502.17260.
* Survey describing the failure-likelihood vs fairness trade-off solved with an adversarial-bandit scheduler, https://arxiv.org/abs/2207.03681; Nishio & Yonetani (FedCS), https://arxiv.org/abs/1804.08333.

## 4. Novelty decision: **NOT ESTABLISHED**
A mechanism that estimates per-client delivery success from history (EWMA/UCB) and trades it against participation is the standard bandit-with-fairness idea; at snippet level it already exists (UCB, Lyapunov fairness, failure-aware probabilities). A "minimal interpretable" estimator-plus-coverage rule would be an implementation variant, not a distinctive method, and no property (regret bound, new fairness notion, new causal identification) distinguishes it. **Per the instruction, no new method was implemented.** Claiming it as a contribution would be unsupported until the full texts above are read and a specific difference is demonstrated.

## 5. What *is* scientifically open and cheap (a measurement, not a method)
(i) **Oracle gap**: how much of top-k's PDR/delay advantage survives when ranking uses only history-estimated reliability (any standard estimator used as a plain baseline, cited, not claimed). (ii) **Correlated scenario**: tie network quality to data (e.g., clients with worse links hold a larger share of attack or of a minority class) to test whether starvation then hurts worst-client recall. These fit the paper's existing measurement framing and strengthen the "limits" findings; they do not add a method claim.

## 6. Minimal confirmatory design (independent versioned protocol; not added to the frozen Phase 9E hypotheses)
* Data: UNSW-NB15 only, train/validation only, **fresh seeds 22–26**, 30 rounds, exposure-controlled 20 % sign-flip, failure p=0.1, `packet_coupled` delivery (so reliability matters).
* Scenarios: S0 independent (current), S1 correlated (worse-link clients assigned the minority-attack share; requires a small data/network coupling option in the partitioner — one new default-off config flag).
* Arms (4 × 2 × 5 = **40 runs**): top-k oracle (existing), coverage-aware oracle (existing), uniform (existing), history-estimated top-k + coverage (the one new, default-off selector, using only past `update_delivered`/delay and `selection_counts`). Ablation isolating the mechanism = oracle vs estimated at identical coverage penalty (matched trace).
* Endpoints (pre-registered before running): PDR, delay, update-delivery ratio, Gini, never-selected, worst-client and p10 client recall, malicious share of selected, best/last AUC; paired by seed, exact sign-flip p (min 0.0625), exploratory.
* Cost (recorded UNSW means ≈ 90 s/run, CPU): 40 × 90 s ≈ **60 min**; with the estimator overhead negligible. Including CIC would add ≈ 2 h and is not justified (AUC ceiling).
* Code needed only if authorised: one default-off selector in `src/network.py`/`experiment.py`, one default-off partition-coupling flag, targeted unit tests, a 3-round synthetic smoke test, a locked manifest. Historical arms stay bit-identical (tested like Phase 7/8).

## 7. Does this strengthen novelty?
Not the method novelty (not established). It would strengthen the **measurement** contribution: it quantifies the cost of the oracle assumption — the paper's largest simulator limitation — and tests the untested starvation-versus-accuracy scenario. Recommended path: read the full texts of the bandit papers first (authors, browser access), then decide; do not describe any history-based selector as new.
