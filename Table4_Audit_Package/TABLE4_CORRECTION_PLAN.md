# Table 4 correction plan (proposal only; nothing in it has been executed)

Principle: Table 4 has no traceable source, so it cannot be "corrected" number by number. It must be **replaced** by a table built from executed, hash-verified runs under one protocol. The items below are ordered by dependency; each is tagged **[DECISION]**, **[CODE]**, **[EXPERIMENT]**, **[ANALYSIS]** or **[TEXT]**.

## Step 0 — Decisions (blocking everything else)
0.1 **[DECISION]** Which evaluation protocol is the paper's primary one? The Abstract already describes the locked validation-only study (240 runs, seeds 12–16). Recommended: keep it as the single authority and drop all test-set numbers (they cannot be re-derived: the official test files are locked and no run records exist). If a test-set result is wanted, it must come from the frozen final-test pathway (Phase 9C) after the evidence is final, not from the old runs.
0.2 **[DECISION]** Table 4 rows. Recommended rows (all must exist as executed arms): FedAvg (routing disabled), FedAvg with uniform-random selection over routed paths (**exists**: `scenario_fedavg_random`), Robust no-DP (routing disabled), Robust no-DP with uniform-random selection (**exists**: `robust_random_no_imputation`), DP+FedAvg (new), Proposed ε≈10 (**exists**: `reference_gaussian`), Proposed ε≈20 (new). The routed-random pair is required to separate client selection from path assignment (§R4 in the discrepancy report).
0.3 **[DECISION]** Modular Edge FL-inspired and MCHFL-style: either (a) delete all statements that they were compared (manuscript l. 1283–1290, 1308, 1960, related figure legends/bars), or (b) implement and run simplified, clearly documented baselines. Recommended (a): faithful implementations would require the original papers' architectures; "-inspired" labels are not evidence of comparison.

## Step 1 — Code (small, default-off, with unit tests; new commit, no change to locked configs)
1.1 **[CODE]** Make the path-assignment policy explicit and independent of client selection (e.g. `routing.path_policy: routed | random`), so "routing disabled" is expressed as two separate switches rather than the single `routing.enabled=False`. Default must reproduce current behaviour bit-for-bit.
1.2 **[CODE]** Add a DP-FedAvg baseline definition (FedAvg aggregation + the same clipping, weight cap and calibrated Gaussian noise) and an ε≈20 configuration for both datasets with `privacy_plan.json` recording `subsampling_amplification_valid=false`.
1.3 **[CODE]** Report per-run communication accounting with the definitions already tabulated (attempted payload, delivered payload, on-wire bytes) and the received-update count, so Table 4's network columns and the privacy-cost table use one definition.

## Step 2 — Missing experiments (locked, versioned, resumable; new output directory; seeds 12–16 to pair with existing arms; validation-only)
| ID | Arm | Runs | Needed for |
|---|---|---|---|
| E1 | FedAvg, routing disabled (random paths), attack + failures on, recovery off | 10 | Table 4 FedAvg |
| E2 | Robust no-DP, routing disabled, recovery off | 10 | Table 4 Robust no-DP |
| E3 | DP+FedAvg (ε≈10), routing disabled | 10 | Table 4 DP+FedAvg |
| E4 | Proposed ε≈20 (reference pipeline + Gaussian, target ε 20) | 10 | Table 4 ε≈20 |
| E5 (optional) | uniform-random selection with random paths vs with routed paths | 10 | attribution of the network gains to path routing |
Estimated cost from observed durations: about 80 s per UNSW-NB15 run and 200–300 s per CICIoT2023 run (CPU) ⇒ ≈ 1.5–2 h for E1–E4, ≈ 2.5 h with E5. Requires a new manifest (config hashes, code fingerprint, seeds, required artifacts) written **before** the runs; the existing 240 + 40 + 40 + 40 runs and all frozen configs are not touched.

## Step 3 — Analysis (after Step 2)
3.1 **[ANALYSIS]** One per-seed ledger for all Table 4 arms (selected-checkpoint **and** last-round F1, ROC-AUC, FPR, AP; delay, first-transmission PDR, update-delivery rate, received updates, path stability, transfer efficiency, bytes), using the audited metric rule.
3.2 **[ANALYSIS]** Paired differences (same seed, same partitions, matched traces): proposed vs each baseline, with mean, SD, 95 % t-interval and exact sign-flip p (minimum attainable p = 0.0625 with five seeds). Report the selection-only effect (routed-random vs top-k) and the routing-disabled effect separately.
3.3 **[ANALYSIS]** Rebuild every figure that shows these methods (figs 3–8 and the relative-improvement figures) from the ledger, with source CSVs and a generating script kept in the repository.

## Step 4 — Manuscript-only edits (after Steps 0–3; do not edit before numbers exist)
4.1 **[TEXT]** Replace Table 4 and all dependent text. Recompute every percentage in the Abstract, Results (CICIoT2023 and UNSW-NB15 relative-improvement subsections) and Conclusion from the new table; state which baseline each percentage is against. Under the already-executed matched arms the selection-only effect on CICIoT2023 is about −7.5 % delay, +8.9 % PDR, +8.0 % path stability, +16.5 % transfer efficiency; larger claims need E1/E5.
4.2 **[TEXT]** Make Methods consistent with the protocol actually used: remove "applied unchanged to the test set"; describe the file-group CICIoT2023 split and the three-way partition; state seeds 12–16 for the main study; align Table 3 with the locked configs (add attacker assignment, delivery model, trace mode, partitions).
4.3 **[TEXT]** Report PDR as a first-transmission packet metric and add the update-delivery rate; remove sentences that equate PDR with update-delivery success.
4.4 **[TEXT]** Privacy: present ε as a diagnostic RDP estimate (Poisson-sampling assumption not met: deterministic top-k, data-dependent filtering); replace the privacy-cost table by values from the new runs; do not attribute accuracy loss of the private pipeline to noise alone (the controlled study shows clipping + weight cap account for roughly 53–63 % of the measured selected-checkpoint loss in the executed runs).
4.5 **[TEXT]** Remove or rewrite the old ablation text (η_s = 1.0 variant, "complementary contributions" wording) and use the controlled Component-wise Experimental Analysis; remove or replace the failure-resilience figure and its interpretation (see the Figure 9 audit): PDR and delay do not respond to injected failures by construction, and baseline failures exist at "0 %".
4.6 **[TEXT]** Delete the Modular Edge FL-inspired / MCHFL-style comparison statements unless Step 0.3(b) is chosen. Fix the Data/Code availability statements: the Zenodo archive (DOI 10.5281/zenodo.21131047) contains the 2026-07-02 code only, not results or configs of the locked studies; publish a new archive version with manifests, ledgers and figure data, or reword.

## Dependency graph (short)
0.1 → 0.2 → 1.1–1.3 → E1–E5 → 3.1 → 3.2 → 3.3 → 4.1–4.6. Items 0.3, 4.2 (partially), 4.5 (text part) and 4.6 (deletions) do not depend on new experiments and can be done first once the decisions are made.

## What not to do
* Do not substitute locked-arm values for Table 4 entries under the old names (e.g. `reference_gaussian` for "Proposed ε≈10") without relabelling the protocol and the baselines; the arms are not equivalent (discrepancy report §A, evidence audit §5).
* Do not re-evaluate on the official test files to "check" the old numbers; they are locked.
