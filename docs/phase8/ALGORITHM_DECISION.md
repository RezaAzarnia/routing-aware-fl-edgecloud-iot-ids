# Phase 8 algorithm decision

## Question: is a genuinely new algorithm scientifically necessary?
**No.** The evidence supports (i) one confirmed implementation defect, now fixed as a default-off variant, and (ii) design limitations that should be *reported*, not patched by more hand-tuned mechanisms. A further guard or threshold would be tuning on inspected seeds (12-21 have all been seen).

| Priority | Finding | Class | Action |
|---|---|---|---|
| A | MAD/median filter powerless with ≤2 genuine updates (100% of malicious accepted), unreliable at 3 (39% honest rejected), retains 14-24% malicious even with ≥6 | Design limitation | Report in the paper; keep Reference/Corrected/Guard as they are. The Phase 7 guard failed its pre-registered criterion: no new threshold. |
| A | Weight cap infeasible for <10 retained updates; share up to 1.00 | Design limitation | Rewrite the claim ("bounded by the feasible cap"), report realised shares. |
| B | Surrogates = repeated median vector; enter MAD in the pre-filter mode | Design limitation | Report; `ctl_imputation_*` arms already show ≤0.002 AUC differences. |
| B | Collective surrogate cap discarded in the DP path (share 0.48 instead of ≤0.10), logged as applied | **Confirmed bug** | Fixed as `preserve_surrogate_cap` (default off); new variant `p8_corrected_gaussian_groupcap`; historical arms preserved. |
| C | Top-k starvation (Gini 0.73); coverage-aware reduces it (0.49) with no accuracy cost measured | Design limitation | Report as a reliability-vs-participation trade-off. |
| C | Reference vs Corrected use different effective channels (delivery 0.848 vs 0.626) | Confound (confirmed) | Use `ctl_delivery_coupled` as the matched control in all comparisons. |
| C | Routing ranks with the true delivery probability; security score independent of attackers | Design limitation | State explicitly; no attacker-avoidance claim. |
| D | ε is a diagnostic RDP value; selection deterministic, filtering data-dependent | Design limitation | Keep "diagnostic" wording; remove "secure/privacy guarantee" language. |
| Hypothesis | Corrected instability is caused by real-update starvation | Not supported (Phase 7b: guard failed) | Do not pursue without new evidence. |

## The one new variant: `p8_corrected_gaussian_groupcap`
- Failure mechanism: projection to the infeasible per-client cap collapses to uniform weights and undoes the surrogate scaling.
- Smallest interpretable correction: apply the collective surrogate cap as a group mass first, per-client cap inside groups. No new hyper-parameter (cap 0.10 and client cap 0.10 are the Phase 6C values).
- No performance claim is made. Whether it narrows the Gaussian gap is the single hypothesis in NEXT_EXPERIMENT_PLAN and is optional.
