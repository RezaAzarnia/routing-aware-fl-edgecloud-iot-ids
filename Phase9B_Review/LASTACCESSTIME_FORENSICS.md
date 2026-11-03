# LastAccessTime of the locked test files: unresolved forensic observation (read-only metadata only)

Method: `Get-Item` / `Get-ChildItem` metadata queries and `fsutil behavior query disablelastaccess`; no file content was opened. Queries of attributes do not update NTFS access times. Nothing here is treated as proof of, or evidence against, leakage.

## Observations (UTC; Tehran local = UTC+3:30)
`DisableLastAccess = 2` (system-managed, last-access updates **enabled**). Test and training files all have a last-access time inside a 35-second window on 2026-11-03:

| File | Created | Last written | Last accessed |
|---|---|---|---|
| `data/UNSW_NB15_training-set.csv` | 11-01 12:24:21 | 02-27 07:51 | 11-03 **08:45:16** |
| `data/UNSW_NB15_testing-set.csv` (locked) | 11-01 12:24:21 | 02-27 07:48 | 11-03 **08:45:48** |
| `CICIoT2023/prepared_verified_v2_filegroup/train.csv.gz` | 11-01 13:23:39 | 11-01 13:24:28 | 11-03 08:45:50 |
| `.../validation.csv.gz` | 11-01 13:24:29 | 11-01 13:24:35 | 11-03 08:45:50 |
| `.../test.csv.gz` (locked) | 11-01 13:24:37 | 11-01 13:24:49 | 11-03 **08:45:51** |

Other contextual facts: of the 352 files under `data/` the maximum last-access time is 08:45:51Z (the locked CIC test file itself). The Windows Search service is running. A full `pytest` run was started by this project at about 08:44:40Z (12:14:40 local, process list taken at 12:20:40 local showed `pytest` aged 6 min).

## Candidate explanations (not mutually exclusive)
1. **Repository unit tests that read the data files.** `tests/test_phase5_validation.py::test_real_unsw_group_disjoint_split_and_official_test_untouched` (reads `UNSW_NB15_testing-set.csv` completely for SHA-256 and loads the dataset with the test path set), `tests/test_data_integrity_ciciot.py::test_official_unsw_files_are_unmodified_and_test_partition_preserved` (SHA-256 of both UNSW files, `load_dataset` with the test path, `pd.read_csv(test_csv)` and a label-array equality check) and `tests/test_phase5_validation.py::test_filegroup_dataset_protocol_invariants` (`sha256_gzip_content` of the CIC train/validation/**test** files and reading the provenance files). The timing (full suite started at ≈08:44:40Z; all five data files touched between 08:45:16 and 08:45:51Z) matches this explanation best. These tests only hash files, count rows, and compare label arrays; none trains, predicts or computes performance on the test data. They are pre-existing Phase 5 tests; the same suite was presumably run in earlier phases, which would also explain the earlier Phase 6C observation.
2. Earlier **data-integrity audits** (Phase 4, `scripts/data_audit/*`, outputs in `docs/data_integrity/`) read the UNSW and CIC test files to count duplicates, predictor-vector overlap and conflicting-label groups (`unsw_overlap_audit.json`, `audit_prepared_verified_v2_filegroup.json`); they were descriptive audits and not used for model selection, but they are *label-aware reads of the test files*.
3. Background software (antivirus, backup, search indexer) is not excluded; NTFS access time can also be updated by other tools. Not testable post hoc.

## Consequences
* The sentence "final-test data were not accessed" is **inaccurate as a literal statement** and has been replaced in the manuscript by a precise one (never used to fit/select/tune/evaluate any model; opened by data-integrity audits and unit tests for hashing, row counts, duplicate/overlap and label-consistency counts).
* Practical impact on scientific validity: the descriptive audits and tests influenced **no** training, threshold, checkpoint, arm or claim. They do mean the test files are not "never-read"; the protocol's guarantee must be stated as *no use for modelling or evaluation*, not *no access*.
* The cause of every individual timestamp is **not established**. Process-level logging (e.g., Sysmon or Windows auditing) was not enabled, so a definitive reconstruction is impossible.
* Recommendation: (a) mark the data-reading tests with `@pytest.mark.skipif(locked_test)` or point them at hash-only helpers so routine test runs do not open the locked files; (b) enable file auditing (or move the locked files to an access-controlled location) before the one-time evaluation; (c) disclose the above in the paper's data/protocol statement.
