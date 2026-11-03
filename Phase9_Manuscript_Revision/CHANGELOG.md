# Phase 9 change log: old manuscript (`main paper.zip`, 14 Oct 2026) → `latex/main.tex`

The old manuscript source is untouched (it lives outside the repository). The new text is a reconstruction on the Phase 6C / 7b / 8 evidence, not an edit of the old numbers.

| Area | Old manuscript | Revised manuscript | Reason / evidence |
|---|---|---|---|
| Title | "…Secure and Resilient Edge–Cloud IoT Intrusion Detection" | "…under Client Failures and Sign-Flip Attackers: A Reproducible Simulation Study of Delivery Reliability, Participation Fairness and Stability" | "Secure" overreached (one attack, trusted server); issue #20 |
| Framing | A proposed framework with a "practical balance" | A controlled measurement study with explicit RQ1-RQ3; no new estimator, no privacy claim | Phase 8 evidence audit; novelty not established |
| Protocol | Official test sets; row-level CIC split; "Proposed ε≈20" | Validation-only, three-way group-disjoint (calibration/selection/report); CIC capture-group split; final test locked | Phase 6C manifest; `docs/phase6c/EXPERIMENT_MANIFEST.json` |
| Results | Old pre-6C numbers (abstract percentages, Tables 4-6) | Phase 6C 240 runs + Phase 7b 40 runs, audited values, per-seed, paired contrasts | `ledger/*.csv` |
| Abstract percentages (delay −26.6%, PDR +13.4%, stability +62.8%, transfer +46.0%, F1 +8.3%, AUC +6.6%, NSR −69.7%) | headline claims | removed; replaced by reproducible values (top-k vs uniform: PDR +8.9%, delay −6.0% UNSW) and explicit "not retained" note | not reproducible with the present simulator; different ε regimes |
| Privacy | "estimated central-DP budget", "privacy-aware" | ε is diagnostic; assumptions violated listed; server sees unperturbed updates; defect in the Gaussian path disclosed | issue #3; `privacy_plan.json` |
| "Failure recovery" (73 mentions) | recovery of failed clients' contributions | "median-based surrogate imputation"; shares and null effect reported | issue #5; ablation |
| Network model | parameters only | full description incl. oracle delivery probability, delivery models, communication accounting units | issue #4, #13; `src/network.py` |
| Routing results | reliability gains only | reliability **and** participation fairness (Gini, never-selected, per-client recall) together | issue #7 |
| Filter | claimed robustness | behaviour by number of genuine updates (0%/39%/…, 14% retained at ≥6) | `T5b` |
| Corrected pipeline | the "proposed" method | demoted: not better than Reference; stability problems; delay artefact of delivery model | Phase 6C/7b |
| Guard | n/a | pre-registered negative result reported with disclosure of seen seeds | Phase 7b |
| Threshold / FPR | FPR transfer issues discussed on test sets | calibration-partition rule documented; FPR ≈0.15 by construction, uninformative; transfer untested | issue #9 |
| Metric audit | n/a | clipping/threshold-1.0 defect and its effect described; audited values everywhere | Phase 7b |
| Statistics | means only | mean±SD, per-seed, paired CI, wins, exact sign-flip p, n=5 caveat | issue #11 |
| Ablation | "complementary benefits" | single-factor controls; no attribution; wording removed | issue #14 |
| Related work | citations, Table 1 | rewritten with verified references and an explicit, hedged gap statement; three contribution types separated | bibliography verification |
| Datasets | partial provenance | counts, hashes, partition sizes, prior shift, provenance caveats | issue #8 |
| Figures | 10 images from the old study | 7 regenerated figures (PDF+SVG) with per-seed dots and source CSVs | `figures/`, `figures/data/` |
| Reproducibility | Zenodo DOI (pre-6C) | repository, manifests, tests, commands, explicit "deposit must be updated" | `REPRODUCIBILITY.md` |
| Declarations | missing | flagged as to-do | `UNRESOLVED_ISSUES.md` |
