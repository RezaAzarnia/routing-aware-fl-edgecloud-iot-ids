# Which supplementary results go where

| Result | Table / figure | Placement | Reason |
|---|---|---|---|
| Uniform weights in the DP pipeline; χrec and sample size inert; surrogate share ≈30 %; abstention rule | text (C1–C3) | **Main** | changes the method description |
| Gaussian-only vs combined contrasts | Table 5 relabel (C4–C6) | **Main** | corrects attribution |
| Attack robustness (FedAvg vs MAD+surrogate; SF 10/20/30 %, BSF, LF; static only) | T1 + FIG1 | **Main** (compact) | answers the robustness criticism; the only place the framework shows a gain |
| Routing × surrogate 2×2 | T3 + FIG3 | **Main** (compact) | tests the surrogate/routing claim; no interaction demonstrated |
| Sensitivity (MAD k, α, clip, χrec) | T2 + FIG2 | Supplementary | α = 0.1 and clip 0.5× are the only notable effects; CIC n = 3 |
| Participation, held-out client recall | T4 + FIG4 | Supplementary (one sentence in main) | held-out recall differs in protocol between UNSW (V1) and CIC (V2) |
| Scalability, memory, bytes | T5 + FIG5 | Supplementary | shared-host timings, indicative only |
| χrec = 0 abstention + accounting | T6 + FIG6 | Supplementary (one sentence in main) | detail |
| Selected vs last-round stability | FIG7 | Supplementary | supports the FedAvg collapse already in T1 |
| Per-seed / paired CSVs, audits, manifests | all CSV/JSON | Supplementary / repository | traceability |

Never mix UNSW participation (SUPP_V1 holdout) with CICIoT2023 participation (SUPP_V2 holdout) in a single pooled statistic or compare the latter with earlier CICIoT2023 runs.
