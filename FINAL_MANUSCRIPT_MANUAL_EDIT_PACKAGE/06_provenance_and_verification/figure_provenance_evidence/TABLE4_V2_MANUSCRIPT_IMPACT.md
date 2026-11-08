# Table 4 v2: manuscript impact (read-only analysis)

> **STATUS: PROVISIONAL.** `main(10).tex`, the authoritative manuscript, was not available on this machine when this report was produced. The dependency scan was run (read-only) on the newest file found, `Downloads/main_Figure_Layout_Refined_Preserved_Text.tex` (6 Nov), purely so the mapping method is exercised and the numeric consequences are known. **It must be re-run on `main(10).tex`** (`python scripts/table4_v2/manuscript_impact.py main(10).tex`); line numbers, figure numbers and the newer Figures 7/8 and Ablation section could differ. No manuscript file was modified. The numeric comparison (old value vs new value) does not depend on the manuscript version beyond the old Table 4 values, which should be re-confirmed.

Dependencies below are derived from the LaTeX label `tab:overall-results` (11 `\ref`s) and from content (method names, numbers, percentages), not from figure numbers.

## 1. Old Table 4 vs controlled evidence

The old Table 4 rows (e.g. CICIoT2023 FedAvg delay 89.34 ms, PDR 0.7364, path stability 0.5601; UNSW FedAvg F1 0.7754) came from runs that differ in selection, path assignment and, for the random-path baseline, were not run under matched traces. They cannot be reproduced as single-factor comparisons. The new controlled table decomposes each headline effect.

| Quantity (percent change vs baseline) | Old text | New: vs E1 (uniform sel., random paths) | New: vs routed uniform FedAvg | Reading |
|---|---|---|---|---|
| CICIoT2023 delay | -26.6% | -24.4% | -8.2% | direction survives; size depends on baseline |
| CICIoT2023 PDR (first transmission) | +13.4% | +22.6% | +8.9% | direction survives, magnitude differs (PDR metric redefined; Deliv. separate) |
| CICIoT2023 path stability | +62.8% | +76.5% | +8.0% | survives with different magnitude |
| CICIoT2023 transfer efficiency | +46.0% | +30.4% | +7.3% | survives, smaller |
| UNSW-NB15 F1 (eps~20) | +8.3% | +27.8% | +25.6% | gain real in size but **mis-attributed** (see below) |
| UNSW-NB15 ROC-AUC (eps~20) | +6.6% | +8.7% | +8.8% | same |
| UNSW-NB15 delay | -24.7% | -21.2% | -6.4% | survives |
| UNSW-NB15 path stability | +63.5% | +76.5% | +8.0% | survives |
| NSR reduction vs DP+FedAvg | up to -69.7% | CICIoT2023 -71.8%, UNSW -71.4% (E3 -> E4) | n/a | approximately survives, but is a multi-factor bundle with eps 10->20 |

## 2. Decomposition (five paired seeds; exact p floor 0.0625)

| Factor | Network metrics | Detection |
|---|---|---|
| Routed vs random **paths** | delay -15.4 ms, PDR +0.087, stability +0.332, TE +2.1 (CIC) / +3.1 (UNSW), 5/5 seeds | none detectable (ΔAUC within ±0.01, CIs include 0) |
| Top-k vs uniform **selection** | delay -5.9/-5.3 ms, PDR +0.069, stability +0.069, 5/5 seeds | none detectable |
| MAD **aggregation** vs FedAvg | none (identical by construction) | UNSW ΔAUC +0.098 (CI 0.017–0.179, 5/5); CIC +0.0025 (5/5) |
| **DP** pipeline on the reference | none | ΔAUC -0.0032 (CIC), -0.0419 (UNSW), 5/5 |
| eps 10 -> 20 | none | +0.0007 (CIC), +0.0103 (UNSW), not distinguishable |

## 3. Claims: supported / replace / remove

**Supported (keep, re-sourced to the new table)**
* Routing-aware path assignment and top-k selection improve delay, PDR, path stability and transfer efficiency (direction in 5/5 seeds on both datasets).
* Detection performance of the proposed pipeline is competitive (CICIoT2023 F1 0.991, AUC 0.994; UNSW F1 0.907, AUC 0.952 at eps~20).
* Central DP costs detection (quantified above) and eps~20 is no worse than eps~10.

**Replace (numbers and attribution change)**
* All percentages in the Abstract and Conclusion (26.6, 13.4, 62.8, 46.0, 8.3, 6.6, 24.7, 63.5, 69.7) must be replaced by values from the controlled table, each with the baseline named (random-path uniform FedAvg vs routed uniform FedAvg) and with the five-seed caveat; no "significant" wording (minimum p = 0.0625).
* Every sentence that explains the UNSW-NB15 F1/AUC gain over FedAvg by routing or coupling: the controlled evidence attributes it to the MAD-filter aggregation, not to routing or selection.
* "Proposed vs DP+FedAvg" comparisons: label as multi-factor, descriptive.
* PDR wording: first-transmission PDR and update-delivery success are different quantities and both are reported.
* Final-round behaviour: add AUC_last, which exposes FedAvg collapse (AUC_last about 0.5) hidden by selected-checkpoint metrics.
* Sections to revise: Results (Intrusion Detection and Routing/Network Performance, CICIoT2023 and UNSW-NB15, lines ≈1835–2112 of the Nov-6 file), Privacy and Communication Cost Analysis (NSR 57.21 -> 17.34), Complementary Benchmark Evaluation, Conclusion (≈2494–2499).

**Remove (not supported by controlled evidence)**
* Any claim that routing, path selection or network-data coupling improves intrusion-detection accuracy (ΔAUC ≈ 0, CIs include 0).
* Any claim of statistical significance or of three-seed generality from the old Table 4 (five seeds, p floor 0.0625; old table has no controlled baselines).
* Unmatched-baseline comparisons presented as isolating the routing effect.
* Any statement that the eps values are certified DP guarantees (diagnostic RDP only).

## 4. Dependency map (Nov-6 scan; re-run on main(10).tex)

* Abstract: 4 sentences with numbers depend on old Table 4 (CICIoT2023 delay/PDR/stability/TE; UNSW F1/AUC/delay/stability; NSR).
* Results: `tab:overall-results` referenced at lines 1835, 1838, 1883, 1890, 1919, 1957, 1962, 2021, 2108, 2112.
* Conclusion: three sentences repeat the Abstract percentages (lines 2494–2499).
* Privacy and Communication Cost Analysis: NSR percentage 69.7% (line 2469).
* Ablation section: contains rows with Table 4 values (lines ≈2286–2345); the user instructed the newer controlled Ablation section and Figures 7/8 must NOT be modified, so these must be checked against `main(10).tex`, where that section is already the controlled version. Do not edit.
* Table 3: rows "Main comparison seeds", "Target privacy budgets", "Calibrated Gaussian noise multiplier", "Privacy mechanism", "Failure recovery" describe the Table 4 setting; the seed row must state five paired seeds (12–16), validation-only, and the noise multipliers (0.9939 for eps 10, 0.6717 for eps 20) are consistent with the new runs.
* Figures: fig3 (routing/fairness/PDR on UNSW) is referenced next to `tab:overall-results`; fig2, fig4, fig5, fig6, fig11 and the ablation figures (fig9/10) do not name Table 4 methods in caption or context and are not directly dependent by this scan. Verify figure captions that quote PDR against the new PDR/Deliv. distinction.

Machine-readable output of the scan: `_impact_provisional_nov6.json`.
