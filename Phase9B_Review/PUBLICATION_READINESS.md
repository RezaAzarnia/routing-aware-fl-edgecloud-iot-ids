# Publication-readiness verdict (Phase 9B)

Legend: **R** ready as written · **Q** ready with the stated qualification (already in the text) · **D** needs further analysis of *existing* data · **E** needs a *new experiment* · **X** remove/forbidden.

## A. Claim-by-claim
| # | Claim (manuscript) | Evidence status | Verdict |
|---|---|---|---|
| 1 | Undefended FedAvg collapses under 20% sign-flip (last-round AUC 0.60-0.65 UNSW; CIC 0.31-0.76) | 20 runs, audited | R (one attack family; stated) |
| 2 | MAD+momentum restores clean-FedAvg performance (0.9838 vs 0.9843) | paired, n=5 | Q: equivalence not tested; exploratory |
| 3 | MAD filter has no power with ≤2 genuine updates (12/12 malicious accepted), poor at 3, keeps 14.1% at ≥6 | pooled 6C observations | Q: pooled across arms, descriptive |
| 4 | Top-k vs uniform: PDR +8.9%, delay −6.0%, stability, transfer; Gini 0.731 vs 0.205; 27.2 never selected | 5 seeds, one simulated trace | Q: oracle delivery probability; trace identical for both datasets |
| 5 | Coverage-aware selection restores part of participation at no measurable AUC cost | paired CI includes 0 | Q |
| 6 | No recall penalty for never-selected clients | per-client recall, 6C | Q: partitions tested only; correlated scenario not simulated (**E** if claimed more broadly) |
| 7 | Security score does not steer selection away from attackers | malicious share 0.195 vs 0.188 | R |
| 8 | Packet-coupled delivery changes the effective channel (delay ×3.5, delivered 0.848→0.681) | `ctl_delivery_coupled` | R |
| 9 | Corrected is not better than Reference (UNSW −0.0082, 0/5) | paired | Q: bundle; cause not isolated (**E**: leave-one-out from Corrected, optional) |
| 10 | No benefit from surrogate imputation | ablation | Q: ≤0.002 differences, n=5 |
| 11 | Guard failed its pre-registered criterion; mean gain carried by an inspected seed | 7b, 40 runs | R |
| 12 | Gaussian costs AUC (−0.042 UNSW) | 6C | Q: **defective surrogate-cap path**; gap not a pure noise cost; corrected variant unrun (**E**, optional, ≈22 min) |
| 13 | ε is diagnostic, not DP | privacy_plan.json | R |
| 14 | Audit: best AUC change ≤0.0037; 17 runs change last-round values | posthoc | Q: re-selection of best round not reproducible |
| 15 | Validation FPR ≈0.15 by construction; FPR transfer untested | protocol | Q: needs final-test to be answered |
| 16 | Gap/novelty statement | 14/35 read in full, rest abstract/metadata | Q: must be re-checked by authors (**D**) |
| 17 | "Final-test data not used for modelling" | tests/audits read the files for hashing/overlap counts | Q (precise wording, forensics unresolved) |
| 18 | Claims about robustness to *other* attacks, other fractions, adaptive attackers, parameter sensitivity, deployment/resources | not tested | **X** as claims; limitations only (**E** if the authors want them) |
| 19 | Generalisation to official test distributions / threshold transfer | not tested | **X** until final-test |
| 20 | Old abstract percentages, NSR −69.7%, "complementary benefits", "Secure", "certified/ guaranteed privacy" | not supported | X (removed) |

## B. Mandatory blockers for journal submission
| ID | Blocker | Type |
|---|---|---|
| M1 | Full-text verification of the 21 sources not read in full; confirm or soften each related-work sentence (priority list in `LITERATURE_REVIEW_SUMMARY.md` §5) | literature (authors' reading) |
| M2 | Author declarations: funding, competing interests, contributions, ethics; confirm author list | editorial |
| M3 | Updated Zenodo/repository deposit of the Phase 6C-9 code, manifests, ledgers (the cited DOI predates them) | reproducibility |
| M4 | Target-journal template, page/length limits, English-language edit | editorial |
| M5 | Decide the final-test question: either run the frozen protocol (conditions R1-R8 of `FINAL_TEST_PLAN_FROZEN_v2.md`) or state explicitly, in the title/abstract framing, that the study is validation-only (the old manuscript reported test results, so reviewers will ask) | scientific |
| M6 | Resolve how the locked test files are protected: stop unit tests from opening them; record the forensic finding; keep the disclosure sentence | integrity |

## C. Optional improvements (not blockers)
* Run the 15-run Gaussian group-cap experiment (seeds 22-26, ≈22 min CPU) *or* keep the Gaussian result explicitly labelled historical/defective.
* Attacker sweep (10/30%), one adaptive attacker, sensitivity to $k,\lambda$, momentum, caps; noisy-router variant; correlated route/label scenario; resource measurements.
* Leave-one-out ablations from Corrected (to attribute its deficit); held-out confirmation seeds 22-26 for the main contrasts.
* Dots instead of bars for the truncated AUC panel of Fig. 4; use the journal figure style; systematic literature search protocol.

## D. Are algorithm changes or more training necessary?
**No.** Every claim now made is supported by existing runs with the stated qualifications; claims that would need new training (items 18, 19, parts of 6, 9, 12) are either already removed or explicitly flagged as limitations. The Phase 8 group-cap variant is optional.

## E. Suitability for independent peer review
* **Independent scientific (internal/pre-submission) review: yes** — numbers re-derived (93/93), equations match code, provenance separated, limitations explicit.
* **Journal submission: not yet** — blockers M1-M6.
