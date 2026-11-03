"""Phase 9E: write FINAL_TEST_REPRODUCIBILITY_RECORD.json (hashes of every frozen input + environment). Read-only; opens no locked file.
Run AFTER the last edit of the listed files:  python Phase9E_PreTest_Signoff/scripts/make_repro_record.py
The commit that carries this record is the one to tag (see PROPOSED_TAG.md); `git rev-parse HEAD` at tagging time identifies it."""
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
import final_test_v2 as ft  # noqa: E402


def sha(p: str) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def git(*a) -> str:
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT).stdout.strip()


m = ft.load_manifest(ft.MANIFEST_PATH)
import numpy, pandas, scipy, sklearn, torch  # noqa: E402

rec = {
    "purpose": "Reproducibility record for the one-time final-test evaluation (plan final-test-eval-v2). Prepared, NOT executed.",
    "base_commit_when_prepared": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
    "note_on_tag": "tag the commit that contains this record: git tag -a final-test-eval-v1 -m '...' <that commit>; the tag is NOT created yet",
    "manifest": {"path": "docs/final_test/FINAL_TEST_MANIFEST.json", "canonical_sha256": m["manifest_sha256"], "file_sha256": sha("docs/final_test/FINAL_TEST_MANIFEST.json"),
                 "n_runs": m["n_runs"], "evaluation_code_fingerprint": m["evaluation_code"]["fingerprint"],
                 "training_code_lineage": {k: {"tag": v["git_tag"], "tag_commit": v["tag_commit"], "fingerprint": v["code_fingerprint"], "matches": v["tag_matches_manifest"]} for k, v in m["sources"].items()}},
    "locked_test_descriptors_from_manifest": m["locked_test"],
    "frozen_files_sha256": {p: sha(p) for p in (
        "scripts/final_test/final_test_v2.py", "scripts/final_test/analyze_final_test.py", "scripts/final_test/protected_access_guard.py", "scripts/phase6c/p6c_common.py",
        "tests/conftest.py", "pytest.ini", "Phase9E_PreTest_Signoff/PRETEST_SIGNOFF.md", "Phase9E_PreTest_Signoff/PRETEST_RUN_TABLE.csv",
        "Phase9E_PreTest_Signoff/FINAL_TEST_AUTHORIZATION_FA.md", "Phase9D_Final_Freeze/evidence/preprocessor_coverage_15_pairs.json")},
    "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "numpy": numpy.__version__, "pandas": pandas.__version__, "scipy": scipy.__version__,
                    "scikit_learn": sklearn.__version__, "torch": torch.__version__, "pip_freeze_file": "Phase9E_PreTest_Signoff/evidence/pip_freeze_venv.txt",
                    "pip_freeze_sha256": sha("Phase9E_PreTest_Signoff/evidence/pip_freeze_venv.txt")},
    "authorization": {"file_exists_in_repository": any((ROOT / n).exists() for n in ("final_test_authorization.json",)), "status": "OPEN (R7): to be created and signed by the owner outside the repository"},
    "results_dir_exists": (ROOT / "results_final_test").exists(),
}
out = ROOT / "Phase9E_PreTest_Signoff" / "FINAL_TEST_REPRODUCIBILITY_RECORD.json"
out.write_text(json.dumps(rec, indent=1), encoding="utf-8")
print("record written:", out.name, "| manifest", m["manifest_sha256"][:16], "| results dir exists:", rec["results_dir_exists"])
