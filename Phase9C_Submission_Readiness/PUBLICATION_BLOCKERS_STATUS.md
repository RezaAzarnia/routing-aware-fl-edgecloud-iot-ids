# Publication blockers M1-M6: status after Phase 9C

| ID | Blocker | Status | What was done | What remains (and who) |
|---|---|---|---|---|
| **M1** | Full-text verification of the 21 sources not read in full | **NOT RESOLVED** (partly advanced) | three reviewers retried every legal route; **no full text of any of the 21 was obtainable** by automated legal means (publisher sites refuse scripted access). Abstract-level evidence improved (verbatim abstracts for 14 of them); sentences corrected; 7 weak/unneeded entries dropped; scope note and gap statement restated (11 full/partial, 17 abstract-level among 28 cited) | authors read the 17 abstract-level sources in a browser/institutional access (priority list in `LITERATURE_VERIFICATION_FINAL.md`) and confirm or soften each sentence |
| **M2** | Author declarations | **PREPARED, NOT RESOLVED** | `AUTHOR_DECLARATIONS_TEMPLATE.md` (funding, competing interests, CRediT, ethics, AI-tool disclosure, availability), every unverifiable field marked `[AUTHOR TO CONFIRM]`; nothing invented | authors complete and confirm |
| **M3** | Updated Zenodo/repository deposit | **PREPARED, NOT RESOLVED** | `ZENODO_RELEASE_CHECKLIST.md`; `ZENODO_RELEASE_MANIFEST.json` (tracked files + SHA-256; no datasets/raw runs/credentials); **nothing uploaded or published** | owner: licence, `CITATION.cff`, final tag, deposit, replace the DOI in the paper |
| **M4** | Journal template, length limits, English edit | **NOT RESOLVED** | none (target journal unconfirmed) | authors choose the journal; apply template; language edit |
| **M5** | Final-test decision | **TECHNICALLY PREPARED; DECISION OPEN** | versioned pathway `scripts/final_test/` (frozen manifest of 280 runs, saved-preprocessor path, repaired metrics, overlap control for both datasets, frozen analysis, safe execution plan); readiness R1-R5 and R8-preflight pass (see `FINAL_TEST_READINESS_REPORT.md`); evaluation **not run** | owner decides: run the frozen protocol (R6, R7) **or** state explicitly that the study is validation-only |
| **M6** | Protection of the locked test files | **RESOLVED (software level)** | session-wide guard blocks `open`/`io.open`/`os.open` on the three protected files in every pytest run; the three tests that read them were split into default train/validation-only tests and `authorized_integrity` tests (deselected by `pytest.ini`, skipped without `IOTFL_AUTHORIZED_FINAL_TEST_INTEGRITY=1`, reading only inside `authorized(...)`); regression tests for the guard; the forensic record (`Phase9B_Review/LASTACCESSTIME_FORENSICS.md`) and the truthful manuscript disclosure are preserved; the manuscript states that the files were opened earlier by audits/tests | recommended (not required for the software claim): Windows object-access auditing or an access-controlled location for the three files, performed by the owner/administrator |

## Additional items found in Phase 9C
| Item | Status |
|---|---|
| Bibliography count discrepancy (52 / 43 / 8) | **RESOLVED**: ninth uncited entry was `cho2020clientselection`; final 44 entries = 44 cited = 44 printed (`BIBLIOGRAPHY_AUDIT.md`) |
| Saved `preprocessor.joblib` was not covered by the `COMPLETE.json` hashes | **MITIGATED**: hash frozen in the final-test manifest; equality with a training-only refit shown for 12/12 (dataset, seed) pairs |
| Phase 6C final-test script incompatible with repaired metrics (fingerprint gate) | **RESOLVED** by the two-fingerprint design in the new pathway (old script untouched) |
| No `LICENSE` / `CITATION.cff` in the repository | OPEN (owner) |
| Gaussian group-cap variant still unrun | OPTIONAL (≈22 min CPU, not required for the current claims) |
