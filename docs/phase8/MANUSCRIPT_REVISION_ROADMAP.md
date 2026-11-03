# Manuscript revision roadmap (no rewrite performed)

Manuscript source reviewed: `main paper.zip` → `main.tex` (14 Oct 2026). It reports the pre-Phase-6C protocol (official test sets, row-level CIC split, "Proposed ε≈20"). All numeric results must be regenerated from the validation-only Phase 6C/7b outputs; historical numbers in the PDF are not edited here.

## 1. Narrowest defensible contribution
A **reproducible simulation-and-evaluation study** of how routing-aware client selection, a packet-level delivery model, surrogate imputation and median/MAD filtering interact in federated IDS training under failures and sign-flip attackers, with hash-locked protocols and preserved negative findings. It is **not** a new aggregation algorithm, **not** a privacy theorem, and **not** a demonstrated security improvement beyond the tested attacker.

| Candidate contribution | Verdict | Evidence |
|---|---|---|
| Distinctive integration of existing mechanisms | NOT ESTABLISHED. Combination alone is not novelty; related-work coverage (Table 1, named systems) was not verified in Phase 8 (no source checking performed). | ISSUE_RESOLUTION #16 |
| Robustness under sign-flip attacks | PARTLY SUPPORTED, one attack only: UNSW best AUC 0.976-0.984 (robust arms) vs 0.887 (`scenario_fedavg_topk`, no filter). But 14-24% of effective malicious updates are retained and the filter is powerless with ≤2 genuine updates. | T5b, T1 |
| Reliability-vs-participation fairness trade-off | **SUPPORTED, measurable** (strongest finding): top-k Gini 0.731, 27.2/50 clients never selected, PDR 0.851; coverage-aware Gini 0.486, 8.0 never selected, PDR 0.833 (−2.1% relative), best AUC 0.9829 vs 0.9838; uniform Gini 0.205, PDR 0.782. No recall penalty for never-selected clients. | T4, T3, route metrics |
| Behaviour under missing updates | SUPPORTED as a *negative/qualified* result: 30% failures leave Reference stable (last AUC 0.976±0.006) but make Corrected unstable (0.840±0.227; 2/5 collapses); the Phase 7 guard did not reliably fix it; imputation gives no measurable gain (`ctl_imputation_none` 0.9822 vs reference 0.9838). | Phase 7b, Phase 6C |
| Reproducible systems contribution | SUPPORTED: locked manifests with SHA-256, resumable runners, 155 tests, separate original/audited tables, three code-state tags. | repository |

## 2. Claim-versus-evidence matrix
| Manuscript claim (main.tex) | Status | Action |
|---|---|---|
| Abstract: CIC delay −26.6%, PDR +13.4%, path stability +62.8%, transfer efficiency +46.0% | NOT REPRODUCED. Phase 6C, top-k vs uniform-random selection, same simulator: CIC delay −7.5% (65.9 vs 71.3 ms), PDR +8.8% (0.851 vs 0.782), path stability +7.9%, transfer efficiency +16.6%. The manuscript's baseline definition is unknown. | Recompute against a named, matched baseline; report from Phase 6C. |
| "Improved communication reliability" for the *proposed (Corrected)* framework | CONTRADICTED for Corrected: packet-coupled delivery gives delay 255-268 ms vs 66-77 ms (Reference), transfer efficiency 2.3-3.9 vs 10.9-17.2 Mbit/s, update delivery 0.626 vs 0.848. | Qualify; separate the routing effect (top-k vs random) from the delivery model. |
| UNSW F1 +8.3%, AUC +6.6% over FedAvg | NOT MATCHED. Phase 6C: best AUC 0.984 (reference) vs 0.887 (`scenario_fedavg_topk`) = +11%; baseline definitions differ. | Recompute; define the FedAvg arm (no filter, same selection). |
| NSR −69.7% vs DP+FedAvg | NOT ESTABLISHED: compares different ε regimes; no DP+FedAvg arm in Phase 6C. | Remove or re-run matched. |
| "Estimated central-DP budget" / "privacy-aware" / "Secure" | Qualify: ε is diagnostic (`subsampling_amplification_valid=false`), trusted server, adaptive filter unaccounted. | Reword title/abstract; add threat model and adjacency. |
| "Failure recovery" (73 mentions) | Rename to median-based surrogate imputation; no utility gain shown. | Rename; report surrogate weight shares (0.096; 0.476 under DP before the Phase 8 variant). |
| "Complementary benefits / balanced trade-off" | UNSUPPORTED by ablations (single-factor controls differ by ≤0.002 AUC; no interaction test). | Remove. |
| "Generalization" across CIC and UNSW | Qualify: two separate benchmarks; CIC at AUC ceiling 0.993-0.996, file-group split, provenance unverified. | Replace with "evaluated on two benchmarks". |
| Row-level CIC split; official test sets; threshold FPR≤0.15 transfer | OBSOLETE protocol. Phase 6C/7b are validation-only (final test locked). | Describe the validation-only protocol; validation FPR ≈0.15 (Phase 7b 0.146-0.155); keep test claims out until unlocked. |
| Seed means only | Insufficient | Add per-seed values, paired differences, intervals (T2); state n=5 and min p=0.0625. |
| Reference vs Corrected | Reference ≥ Corrected: Phase 7b best AUC 0.9798 vs 0.9694 (Δ −0.010, 95% CI −0.045…+0.024), last-round 0.966 vs 0.950; fail0p3 0.976 vs 0.840. | Present Reference as the stronger and more stable arm; keep Corrected as a fairness-oriented variant. |

## 3. Claims to remove / qualify / test
- **Remove**: complementary-benefit and "balanced trade-off" sentences; NSR −69.7%; recovery-of-contributions wording; secure/guarantee language.
- **Qualify**: all routing percentages (matched baselines), the privacy section, sign-flip robustness (one attack, 20%), "generalization".
- **Need new experiments (optional, not mandatory)**: Gaussian-path comparison with the corrected surrogate cap (NEXT_EXPERIMENT_PLAN); attacker sweep 10/30% and an adaptive attacker; sensitivity to k, χ_rec, C, α; correlated route-quality/label scenario; measured resources. Without them, state them as limitations.
- **Not possible while locked**: any test-set statement.

## 4. Revision steps (in order)
1. Rebuild the results section from Phase 6C/7b tables (`docs/phase8/tables`): audited metrics, validation-only protocol, plus the Phase 7b negative result for the guard.
2. Regenerate figures from the `Phase6C_Final_Handoff/figures` data with units and uncertainty (n=5).
3. Rewrite Methods: network model (including the oracle link-stability ranking), delivery models, surrogate imputation, cap feasibility, empty-round behaviour, threat model, privacy scope.
4. Dataset provenance table (UNSW hashes; CIC file-group counts, prior shift, provenance caveat).
5. Baseline configuration matrix (T6) as a table; drop evaluation claims for "Modular Edge FL-inspired" and "MCHFL-style" unless they are run.
6. Verify every reference and Table 1 entry against original sources; restore declarations (funding, competing interests, contributions).
7. Update the Zenodo archive with the Phase 6C/7/7b/8 code, manifests and tables (needs the user's approval; Phase 8 uploads nothing).
