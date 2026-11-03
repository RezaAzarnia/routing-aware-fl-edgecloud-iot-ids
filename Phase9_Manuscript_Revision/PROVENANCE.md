# Provenance of the Phase 9 revision

- Branch: `research/phase9-manuscript-revision` (created from `research/phase8-evidence-repair`, commit `740a166`, itself on top of `7e71889`).
- Frozen tags (local): `phase6c-final-results`, `phase7-guard-v1`, `phase7b-final-results`.
- Algorithms, configs, manifests, results: unchanged in Phase 9 (verified by `scripts/verify_runs.py`: Phase 6C 240/240, Phase 7b 40/40 mandatory, config hashes 80/80 per manifest).
- No training was run; final-test data were not accessed.
- Evidence ledgers: `ledger/` (per-run original vs audited metrics, network/fairness, paired contrasts, Phase 7b).
- Old manuscript source: `Desktop/New folder/main paper.zip` (14 Oct 2026), InsightAI report 2026-10-01 (`InsightAI_HDQL_GTE_Readiness_Report_2026-10-01.docx`); neither is part of the repository.
- Bibliography: `bibliography/verified_references.bib` and `verification_report.md` (Crossref/arXiv metadata check by a delegated agent; title-level, not full-text).
- Not committed: raw datasets, `data/CICIoT2023/`, `Phase6C_Final_Handoff*`, scratch files, LaTeX build artifacts.
