# Zenodo archive verification (queried live from the Zenodo API on 2026-11-08; read-only)

Concept DOI (all versions): 10.5281/zenodo.21131047. Two published versions exist; the user-quoted "v1.0.5" is real, and the manuscript cites the older one.

| item | v1.0.4 | v.1.0.5 (latest) |
|---|---|---|
| Zenodo record / DOI | 24031823 / 10.5281/zenodo.24031823 | 24032087 / 10.5281/zenodo.24032087 |
| Zenodo version string | `v1.0.4` | `v.1.0.5` (with a dot after v) |
| Published | 2026-11-07 (created 09:01 UTC) | 2026-11-07 (created 09:15 UTC), `is_last = true` |
| Linked GitHub tag | `v1.0.4` → commit `e74e2e1b2ae4d8bbdcf4b4cdb8db2ba44e375e95` ("Merge branch 'table4-controlled-v2'…") | `v.1.0.5` → commit `7d598855fa64bc516b85ff17fd4f075cd459d422` ("Docs: cite Zenodo v1.0.4 … README: file-group split …") |
| Archive file | `…-v1.0.4.zip`, 12,603,060 bytes | `…-v.1.0.5.zip`, 12,603,716 bytes, md5 `55ce7c83…cb735` |
| Differences | — | v1.0.4 → v.1.0.5: 3 files: `README.md`, `manuscript/README.md`, `manuscript/main.tex` (21+/17−) |

- **Manuscript (`main.tex`, lines 2278–2289) cites v1.0.4 / 10.5281/zenodo.24031823.** `README.md` and `FINAL_REVIEWER_AUDIT.md` also say v1.0.4. Nothing in the repository mentions v.1.0.5 or 24032087 — the earlier readiness report was consistent with the manuscript, but the *latest* archived version is v.1.0.5.
- **Current HEAD** is `7d5280d` (exactly one commit after `v.1.0.5`: it adds `docs/SIMULATION_SPEC.md` and the compiled `manuscript/main.pdf` and edits `manuscript/main.tex` and `FINAL_REVIEWER_AUDIT.md`). Neither archived version is the current manuscript snapshot.
- **Supplementary outputs are NOT in either archive.** Both were created before SUPP_V1/V2 ran; `git ls-tree v.1.0.5` contains no `scripts/supp_*`, `configs/supp_*`, `docs/supp_*`, `src_v2` or `Supplementary_Experiments_Package` entries (0 matches), and those directories are untracked in the working tree today. The archived zips contain what the tagged commits contain (not the gitignored `results_*` directories). The statement that the archive contains "the manifest, scripts and per-seed/summary/paired tables" holds only for the Table 4 v2 controlled study.
- **Consequence:** Code/Data Availability must not imply that supplementary results are archived. Options for the authors (not executed; no release was created): cite the concept DOI plus the exact version, or publish a new release containing the supplementary package after approval and then update the DOI. Decide whether to cite v.1.0.5 (latest) or keep v1.0.4; either is valid but they differ in snapshot commit.
