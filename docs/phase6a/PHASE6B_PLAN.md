# Phase 6B plan (NOT started) — dependency-ordered

All experiments below use the Phase-6A code (`integration/phase6a`), the group-disjoint UNSW split and
the CICIoT2023 file-group dataset. Legend: **M** mandatory, **O** optional, **R** requires algorithmic /
simulator redesign (needs an explicit decision before running).

## 0. Gates before any 6B run
1. **M** Tag the integrated code; freeze configs by hash (same practice as `PRESPECIFICATION.json`).
2. **M** Decide the final-test policy: a single, pre-registered, one-time test evaluation per frozen
   configuration (no test-based selection). A `final_test` execution mode that is only entered from a
   frozen config hash is needed (engineering, no science change).
3. **M** Decide on the CIC feature set (39 vs. official 46/47) and whether official UNB provenance is required.

## 1. Core comparison (M) — five seeds (2..6), paired exogenous traces
- Methods: centralized-clean, FedAvg-clean, FedAvg-scenario (attack+failure, no DP), FedAvg-DP, robust-no-DP,
  proposed (no DP), proposed (DP). Same seed ⇒ same network/failure/malicious traces (verified in 6A for
  DP vs. no-DP; must be re-verified for every pair where selection differs, because routing changes which
  clients are selected and therefore which draws are consumed).
- Report validation + (frozen) test, mean±SD, paired differences with bootstrap CIs; 5 seeds are descriptive.

## 2. Reviewer-driven controls
| # | Experiment | Reviewer topic | Class |
|---|---|---|---|
| 2.1 | Selection: top-k routing vs. uniform random vs. round-robin vs. coverage-constrained top-k; report coverage (clients ever selected, longest gap, sample coverage) | participation bias (comment 7) | M |
| 2.2 | Missing-update handling: drop / zero / previous-global / coordinate-median imputation; weight factor ∈ {0, 0.25, 0.5, 1} | recovery vs. imputation (5) | M |
| 2.3 | False-alarm analysis: report FPR/precision at natural prevalence; thresholds from validation only; CIC prevalence shift (54% vs. 3%) | thresholds (9) | M |
| 2.4 | Factorial ablation (routing × robust filter × imputation × DP) with matched traces | confounded ablations (14) | M |
| 2.5 | Failure sensitivity: explicit failure probability {0,.1,.2,.3} **and** link-level delivery separately | network model (4, 13) | M |
| 2.6 | Communication accounting: bytes attempted / delivered / imputed (=0) | (13) | M |
| 2.7 | Attack variants (sign-flip scale, Gaussian, model replacement; 10–30 % malicious) | attacker model (12) | M |
| 2.8 | Noise multiplier / clip-norm sensitivity (diagnostic only, ε not claimed) | privacy–utility (15, 17) | O |
| 2.9 | Dirichlet α ∈ {0.1, 0.5, 1, IID} | heterogeneity | O |
| 2.10 | Conflict-label exclusion sensitivity (config already exists) | label conflicts | O |
| 2.11 | UNSW duplicate-controlled test mask (no relabeling, evaluation-time only) | duplicate leakage | M (at final test) |
| 2.12 | Historical (7c75b2d, prepared_paper) vs. corrected pipeline, strictly separate output trees | historical comparison | O |

## 3. Requires redesign (decision needed, do not run silently)
- **Certified privacy:** deterministic top-k routing re-selects the same clients (measured: 3 clients in 30/30
  rounds, 24 clients never). Subsampling amplification is invalid; a client participating every round at
  noise multiplier 0.994 would have ε≈41.9 (q=1, 30 releases) under the same RDP routine, versus the reported 10.0.
  Options: secret random client sampling, per-client accounting by actual participation, or no-amplification accounting.
- **Weight cap:** a requested cap of 0.1 is infeasible with ~8 retained updates (cap is raised to 1/n); realized max share
  mean 0.118 / 0.130 (cap exceeded in 28/30 and 29/30 rounds).
- **Network coupling:** `update_delivered` and packet-level PDR are independent draws (measured corr 0.22, via the common
  expected PDR). If PDR should explain delivery, the simulator must be coupled — a behavioural change ⇒ new simulator version.
- **Surrogate weight:** failed clients' imputed updates carry 28–36 % of aggregation weight and use the failed client's
  true sample count; a design review of this is needed.
- **Participation fairness:** coverage-aware routing (new algorithm).
- **Capture/device independence for CIC:** needs device identifiers that the release does not provide.

## 4. Estimated resources (measured in 6A, CPU, 16 cores)
UNSW ≈ 53–68 s/run, ≈1.0 GB; CIC ≈ 157–205 s/run, ≈2.6 GB (validation-only, 30 rounds). 55 runs ≈ 1.0 h (UNSW) +
2.9 h (CIC) for a core suite; add ≈ 10–20 % for final-test evaluation. Disk per run: < 20 MB without probability dumps.
