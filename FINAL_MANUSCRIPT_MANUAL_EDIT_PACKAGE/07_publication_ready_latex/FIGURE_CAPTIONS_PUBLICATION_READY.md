# Publication-ready captions for the seven supplementary figures (all exploratory; seeds 12–16 unless stated)

Files: `04_figures/FIGn_*.pdf|png` and `*_data.csv` (every point carries its run ID).

**Fig. S1 — Attack robustness.** Selected-checkpoint (top) and last-round (bottom) ROC–AUC of FedAvg (no filter, no recovery) and the MAD-plus-surrogate pipeline under no attack, sign-flip (SF) at 10, 20 and 30 % exposure-controlled malicious clients, a norm-preserving sign-flip (BSF, 20 %) and label flipping (LF, 20 %), on UNSW-NB15 and CICIoT2023. Dots: individual seeds; bars: means (n = 5). All attacks are static; adaptive attackers were not evaluated. SF 20 % uses the locked reference runs.

**Fig. S2 — Parameter sensitivity.** Paired change in selected-checkpoint ROC–AUC relative to the parent arm (central-DP `reference_gaussian` for MAD k, Dirichlet α, clipping and χrec = 0 under DP; non-private `reference` for χrec in {0, 0.25, 0.75}); mean and 95 % t-interval; n = 5 (UNSW-NB15) or 3 (CICIoT2023, except χrec = 0 under DP, n = 5). With n = 5 the smallest attainable exact sign-flip p is 0.0625; intervals are unadjusted for multiplicity. Under central DP, χrec has no effect on the applied weights.

**Fig. S3 — Routing × surrogate design.** Selected-checkpoint ROC–AUC in the 2 × 2 design (routing on/off × surrogate imputation on/off), five seeds per cell; routing-off cells share identical network traces. The interaction contrast does not demonstrate an interaction (UNSW-NB15 +0.0068 [−0.0024, +0.0159]; CICIoT2023 +0.0005 [−0.0004, +0.0014]).

**Fig. S4 — Participation and held-out client recall.** Worst eligible-client recall on client holdouts never used for training (top) and selection Gini (bottom) for top-k, coverage-aware and uniform selection under independent and coupled networks. UNSW-NB15: SUPP_V1; CICIoT2023: SUPP_V2 leakage-safe holdout (protocols are not pooled). Only clients with at least 10 held-out attack rows contribute to recall.

**Fig. S5 — Scalability.** Selected-checkpoint ROC–AUC, wall-clock seconds per run and simulated bytes on the wire for N ∈ {25, 50, 100} clients and k ∈ {5, 10, 20} selected per round (3 seeds). Timings come from one shared CPU host and are indicative only; bytes are simulated serialized-update accounting.

**Fig. S6 — χrec = 0 under central DP.** Difference in selected-checkpoint and last-round ROC–AUC between the χrec = 0 run (with the no-valid-contribution rule) and `reference_gaussian`, per seed. Abstention (1 round in seed 13; 4 rounds in seed 15) occurs only in rounds where all retained updates are surrogates; seeds with no abstention are bit-identical to the reference.

**Fig. S7 — Selected-checkpoint versus last-round stability.** Selected-checkpoint minus last-round ROC–AUC for representative arms (dots: seeds; bars: means). The checkpoint-selection rule can conceal last-round collapse.
