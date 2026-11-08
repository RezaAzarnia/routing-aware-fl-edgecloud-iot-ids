# InsightAI 20-comment mapping (after SUPP_V1 + SUPP_V2)

Status rule: CLOSED = resolved by verified evidence (manuscript integration may still be pending, stated); PARTIAL = resolved in part; OPEN = not resolved. Nothing is "closed" merely because runs completed. T-/FIG- refer to `GENERATED_TABLES.md` and `figures/`.

| # | Comment | Status | Verified evidence | Remaining limitation | Required manuscript action |
|---|---|---|---|---|---|
| 1 | Bibliography | PARTIAL (unchanged) | prior audit: 35 entries, 0 undefined | authors must verify each citation's claim | none from experiments |
| 2 | Figures embedded | CLOSED (unchanged) | prior audit | — | add FIG1–7 only if supplementary is included |
| 3 | Privacy accounting | CLOSED as empirical diagnostic | `privacy_plan.json`, T6: ε≈9.9993 attempted; release-based 9.86/9.43 with abstention | diagnostic RDP under Poisson assumption, not certified DP | keep "diagnostic"; add release-vs-attempted note |
| 4 | Network model | CLOSED (unchanged) | prior audit; network traces matched across arms (QA) | — | none |
| 5 | Surrogate imputation vs recovery | PARTIAL | T3 + paired file: imputation ON vs OFF ΔAUC +0.0016 [−0.0036,+0.0068] UNSW, +0.0001 CIC; cap010 and post-filter ≈ 0 (Phase 6C `ctl_imputation_*`, 5 seeds both datasets); DP-pipeline share 0.30, surrogate-only rounds 2.8 % | evidence is on the Phase 6C protocol, not Table 4 v2; no detection benefit demonstrated; mechanism by which surrogates help unmeasured (direction not logged) | state surrogates carry ~30 % of weight and show no demonstrated detection benefit |
| 6 | Total algorithm and weight cap | CLOSED (algorithm) with **mandatory correction** | `SUPPLEMENTARY_WEIGHT_AUDIT_FINAL.csv`, `audits/AUDIT_capnormalize_unit_test.csv`: uniform 1/n in all DP rounds with ≤10 retained; cap applied only in DP path | — | rewrite eq. (capped-weighting) paragraph and χrec statements (C1–C3) |
| 7 | Participation bias | CLOSED (evidence); manuscript integration pending | T4/FIG4: Gini, never-selected, held-out worst/P10/mean recall, both datasets × 6 policy/network arms × 5 seeds, leakage-safe holdouts (QA 5) | held-out recall only for eligible clients (44–50/50 CIC, ≈44/50 UNSW); UNSW and CIC protocols not pooled; seeds of existing Figs 3–6 still need a statement | replace/annotate Figs 3–6 provenance; report worst-client recall |
| 8 | Preprocessing provenance | PARTIAL (unchanged) | CIC V2 holdout audit adds group-closure/leakage audit | UNSW 194-feature encoding item from prior audit; CIC official provenance unverified | disclose CIC holdout protocol (V2) |
| 9 | Threshold selection / FPR | PARTIAL (unchanged) | rule documented; FPR ≈0.14–0.15 everywhere (cap-driven) | high FPR is a design consequence | none new |
| 10 | Baseline identities | CLOSED (unchanged) | method matrix | — | none |
| 11 | Uncertainty / significance | CLOSED | five paired seeds, t-intervals, exact sign-flip with p-floor 0.0625 (n=3: 0.25), per-seed CSV | exact test floor p=0.0625 (n=5) while t-intervals can exclude 0; ~1,700 unadjusted exploratory comparisons; no significance claim (see STATISTICAL_INFERENCE_NOTE.md) | retain "no significance claim" wording |
| 12 | Attacker model / robustness | **PARTIAL** | T1/FIG1: SF 10/20/30 %, BSF 20 %, LF 20 %, FedAvg vs reference, 2 datasets, 5 seeds | **no adaptive attack implemented**; BSF/LF harmless in this setup; MAD keeps 79–80 % of BSF updates | scope claims to static, non-adaptive attacks; add as limitation |
| 13 | Communication accounting | CLOSED (simulated accounting) | T5/FIG5: serialized update bytes, attempted/delivered/on-wire bytes per configuration | bytes are simulated; wall/CPU from a shared host | report T5 with caveat |
| 14 | Ablation confounding | CLOSED with **mandatory relabelling** | `audits/AUDIT_ablation_*`: Gaussian-only contrast clean; "Clipping + cap" and "Full privacy pipeline" are bundles | — | Table 5 relabel (C4–C5) |
| 15 | Sensitivity and resources | CLOSED (exploratory resolution) | T2/FIG2 (k, χrec, α, clip; UNSW n=5, CIC n=3), T5 scaling N=25/50/100, k=5/10/20, memory/runtime | CIC n=3; p-floor; wall-times not benchmarks | add supplementary section |
| 16 | Integration gap | PARTIAL (unchanged) | — | literature entries need author verification | none |
| 17 | Relative changes / NSR | CLOSED (unchanged) | — | — | none |
| 18 | Reproducibility archive | PARTIAL | new scripts/manifests/results exist locally only | Latest Zenodo version v.1.0.5 (10.5281/zenodo.24032087, snapshot 7d59885) and v1.0.4 (24031823, snapshot e74e2e1) both predate SUPP_V1/V2 and contain no supplementary output (see ZENODO_VERIFICATION.md) | authors decide on a new release (not done) |
| 19 | Author declarations | **OPEN (author input)** | — | funding, competing interests, CRediT, ethics | authors |
| 20 | Title/prose vs evidence | PARTIAL | evidence now shows conditional benefit (attack only), ~30 % surrogate share, inert χrec in DP | prose must be toned to this | apply corrections |

**Count: 11 CLOSED, 8 PARTIAL, 1 OPEN.** Not closed: adaptive-attack robustness (12), formal DP (3 is closed only as a diagnostic).
