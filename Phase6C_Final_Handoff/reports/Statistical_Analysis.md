# Statistical methods (what `scripts/statistical_analysis.py` computes)

- Unit: one run per (dataset, arm, seed); seeds 12-16 give 5 paired observations. Pairing is by seed (same data partition and training seed); attacker schedules, selection and network draws can differ by arm, so pairing controls only data partition/initialization.
- Per arm: mean, sample SD (ddof=1), min, max and every per-seed value (`tables/aggregate_metrics.csv`).
- Paired contrasts (`tables/paired_comparisons.csv`, 682 rows): mean difference, SD, 95% t-interval (df=4), Cohen's d_z, win counts, **exact** two-sided Wilcoxon signed-rank p, exact sign-flip permutation p. Contrast set = manifest `compare_with` pairs plus declared extras (`contrast_type` column).
- At n=5 the smallest attainable exact two-sided p is 0.0625 (all five differences of the same sign). No contrast can reach p<0.05; no multiplicity correction is applied; intervals are wide and low power. Do not read p>0.05 as equivalence, nor 0.0625 as a significant result.
- Effect sizes are descriptive; d_z with n=5 is unstable.
- Best-checkpoint metrics are on the report partition at the checkpoint selected on a different partition; last-round metrics are on the same report partition at round 30. Threshold from a separate calibration partition. Per-round `val_*` columns in `round_metrics.csv` refer to the selection partition and `val_rep_*` to the report partition; use `val_rep_*` for evaluation.
- Reproduce: `python scripts/statistical_analysis.py --handoff .` (uses only `tables/`).
