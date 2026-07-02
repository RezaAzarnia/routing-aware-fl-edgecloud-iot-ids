# Recommended reporting protocol for CICIoT2023 external validation

- Task: binary intrusion detection (`BenignTraffic=0`, all attack labels `=1`).
- Raw source: official CICIoT2023 CSV release.
- Split: deterministic CSV-shard-held-out split (70% train, 10% validation, 20% test; seed 2023).
- Training sample: 1,000,000 rows, balanced between benign and malicious traffic; attack rows sampled across attack categories to reduce domination by flooding attacks.
- Validation sample: 200,000 rows sampled according to the natural category distribution of the validation shards.
- Test sample: 300,000 rows sampled according to the natural category distribution of the held-out test shards.
- Preprocessing: numeric median imputation and standardization fitted on training only.
- Model selection and threshold selection: validation only.
- Test set: untouched until final evaluation.
- Main runs: five independent seeds (2–6) for Proposed ε≈10 and Proposed ε≈20.
- Baselines: five seeds under matched data, attack, failure, client-participation, and communication-round settings.
- Sweeps and ablations: at least three seeds.
- Required reporting: exact sample counts, source-shard manifest, actual estimated ε, δ, clip norm, noise multiplier, mean±SD, 95% CI, and fixed-FPR operating points.

## Required limitation statement

The official CICIoT2023 feature CSV release does not expose a stable device identifier in the prepared tabular shards used here. Therefore, the external-validation protocol is shard-held-out rather than device-held-out or temporal-held-out. The prepared dataset is a reproducible sample of the full release, and the exact sample sizes and sampling strategy are reported.
