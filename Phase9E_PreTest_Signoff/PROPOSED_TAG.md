# Proposed final tag (R8): NOT CREATED

Proposed tag: `final-test-eval-v1` (annotated), on the commit that contains `FINAL_TEST_REPRODUCIBILITY_RECORD.json`, `PRETEST_SIGNOFF.md` and the frozen scripts. Creating it is an irreversible-in-spirit freeze marker, so it is left to the owner's decision.

```powershell
cd "C:\Users\R_Azarnia\Desktop\New folder\routing-aware-fl-edgecloud-iot-ids"
git status --short                                     # only unrelated untracked files may remain
$PY = "C:\Users\R_Azarnia\Desktop\IoT-FL-Recovery\venv\Scripts\python.exe"
& $PY Phase9E_PreTest_Signoff\scripts\make_repro_record.py   # refresh hashes if anything frozen changed (then re-commit)
& $PY -m pytest tests\test_phase9c_final_test_v2.py tests\test_phase9e_rehearsal.py -q --basetemp=C:/cs/tag
& $PY scripts\final_test\final_test_v2.py evaluate --preflight
git tag -a final-test-eval-v1 -m "Frozen pre-test state: manifest 737b901f..., plan final-test-eval-v2 (no test executed)"
git rev-parse final-test-eval-v1^{commit}              # record this hash in the authorization notes
```
Conditions before tagging: R7 file exists and is valid; no change to any file listed in `frozen_files_sha256` (the manifest test `test_frozen_manifest_is_consistent_and_evaluation_code_is_unchanged` and the evaluation-code fingerprint enforce this). Do not push without the owner's decision.
