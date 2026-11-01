"""Runner regression tests with a MOCK workload (no model training): dry-run, preflight, sequential
execution, exit-code handling, resume after failure/interruption, immutability, locking, stopping
rules, verification and aggregation statistics."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import (  # noqa: E402
    code_fingerprint, manifest_hash, sha256_file, sha256_text_file,
)

ORCH = ROOT / "scripts" / "phase6c" / "orchestrator.py"
MOCK = ROOT / "tests" / "mock_p6c_run.py"
REQUIRED = ["run_record.json", "resolved_config.yaml", "round_metrics.csv", "network_metrics.csv",
            "aggregation_diagnostics.csv", "final_validation_metrics.json", "threshold_diagnostics.json",
            "run_metadata.json", "metric_accounting.json", "best_model_state.pt", "last_model_state.pt",
            "privacy_plan.json", "validation_split_info.json", "phase6c_diagnostics.json"]
ARMS = [("reference", None), ("corrected", "reference"), ("baseline_x", None)]
SEEDS = [12, 13, 14]
DATASETS = ["unsw", "ciciot"]


def make_project(tmp_path: Path, arms=ARMS, seeds=SEEDS) -> Path:
    cfg_dir = tmp_path / "configs" / "phase6c"
    cfg_dir.mkdir(parents=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "train.csv").write_text("x\n", encoding="utf-8")
    (tmp_path / "data" / "test.csv").write_text("secret test data\n", encoding="utf-8")
    runs, order = [], 0
    hashes = {}
    for d in DATASETS:
        for arm, _ in arms:
            path = cfg_dir / f"{d}_{arm}.yaml"
            path.write_text("experiment:\n  validation_only: true\ndata:\n  test_csv: ''\nfl:\n  rounds: 30\n", encoding="utf-8")
            hashes[(d, arm)] = sha256_text_file(path)
    for d in DATASETS:
        for seed in seeds:
            for arm, _ in arms:
                order += 1
                runs.append({"run_id": f"{d}__{arm}__seed{seed}", "order": order, "dataset": d, "arm": arm, "seed": seed,
                             "config": f"configs/phase6c/{d}_{arm}.yaml", "config_sha256": hashes[(d, arm)],
                             "out_dir": f"results_phase6c/{d}/{arm}/seed_{seed}"})
    manifest = {
        "schema": 1, "code_fingerprint": code_fingerprint(tmp_path), "seeds": seeds, "rounds": 30,
        "datasets": {"unsw": {"training_csv": "data/train.csv", "training_sha256": "x"},
                     "ciciot": {"prepared_dir": "data", "content_sha256": {}, "metadata_sha256": "x"}},
        "locked_test": {"unsw": {"path": "data/test.csv", "kind": "csv", "sha256": sha256_file(tmp_path / "data" / "test.csv"),
                                 "bytes": (tmp_path / "data" / "test.csv").stat().st_size},
                        "ciciot": {"path": "data/test.csv", "kind": "csv", "sha256": sha256_file(tmp_path / "data" / "test.csv"),
                                   "bytes": (tmp_path / "data" / "test.csv").stat().st_size}},
        "arms": [{"arm": a, "group": "main", "description": "", "algorithm_version": "v", "compare_with": c} for a, c in arms],
        "primary_contrasts": [["corrected", "reference"]],
        "n_runs": len(runs), "runs": runs, "required_artifacts": REQUIRED,
        "command": ["{python}", str(MOCK), "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "verify_training_semantics": True,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def orch(tmp_path, manifest, *args, env=None):
    cmd = [sys.executable, str(ORCH), args[0], "--manifest", str(manifest), "--root", str(tmp_path), *args[1:]]
    full_env = dict(os.environ, **(env or {}))
    return subprocess.run(cmd, capture_output=True, text=True, env=full_env, cwd=str(tmp_path))


COMMON = ["--skip-data-hash", "--min-free-gb", "0.0001"]


def runs_dirs(tmp_path):
    return sorted(p for p in (tmp_path / "results_phase6c").glob("*/*/seed_*"))


def test_plan_is_a_dry_run_and_creates_nothing(tmp_path):
    m = make_project(tmp_path)
    r = orch(tmp_path, m, "plan")
    assert r.returncode == 0
    assert "Total runs: 18" in r.stdout and "pending" in r.stdout
    assert not (tmp_path / "results_phase6c").exists()


def test_preflight_passes_and_detects_tampering(tmp_path):
    m = make_project(tmp_path)
    assert orch(tmp_path, m, "preflight", *COMMON).returncode == 0
    # modified config
    cfg = tmp_path / "configs" / "phase6c" / "unsw_reference.yaml"
    cfg.write_text(cfg.read_text() + "extra: 1\n", encoding="utf-8")
    r = orch(tmp_path, m, "preflight", *COMMON)
    assert r.returncode == 2 and "FAIL" in r.stdout


def test_preflight_rejects_config_that_references_a_test_file(tmp_path):
    m = make_project(tmp_path)
    manifest = json.loads(m.read_text())
    cfg = tmp_path / "configs" / "phase6c" / "unsw_reference.yaml"
    cfg.write_text("experiment:\n  validation_only: true\ndata:\n  test_csv: data/test.csv\nfl:\n  rounds: 30\n", encoding="utf-8")
    h = sha256_text_file(cfg)
    for run in manifest["runs"]:
        if run["config"].endswith("unsw_reference.yaml"):
            run["config_sha256"] = h
    manifest["code_fingerprint"] = code_fingerprint(tmp_path)
    manifest["manifest_sha256"] = manifest_hash(manifest)
    m.write_text(json.dumps(manifest), encoding="utf-8")
    r = orch(tmp_path, m, "preflight", *COMMON)
    assert r.returncode == 2 and "blank test path" in r.stdout


def test_modified_manifest_is_rejected(tmp_path):
    m = make_project(tmp_path)
    manifest = json.loads(m.read_text())
    manifest["seeds"] = [1, 2, 3]
    m.write_text(json.dumps(manifest), encoding="utf-8")
    r = orch(tmp_path, m, "plan")
    assert r.returncode == 2 and "modified after it was locked" in r.stdout


def test_full_mock_execution_completes_sequentially_and_validates(tmp_path):
    m = make_project(tmp_path)
    r = orch(tmp_path, m, "run", *COMMON)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ALL 18 RUNS COMPLETE AND VERIFIED" in r.stdout
    assert len(runs_dirs(tmp_path)) == 18
    for d in runs_dirs(tmp_path):
        assert (d / "COMPLETE.json").exists() and not (d / "FAILED.json").exists()
    assert not (tmp_path / "results_phase6c" / "_state" / "runner.lock").exists()   # lock released
    v = orch(tmp_path, m, "validate")
    assert v.returncode == 0 and "VALIDATION: PASS" in v.stdout
    # event log shows strictly sequential start/complete pairs
    events = [json.loads(line) for line in (tmp_path / "results_phase6c" / "_state" / "events.jsonl").read_text().splitlines()]
    active = 0
    for e in events:
        if e["event"] == "run_started":
            active += 1
            assert active == 1
        if e["event"] in ("run_completed", "run_failed"):
            active -= 1


def test_failure_is_recorded_then_resume_reruns_only_the_failed_run_and_preserves_the_attempt(tmp_path):
    m = make_project(tmp_path)
    r1 = orch(tmp_path, m, "run", *COMMON, env={"MOCK_FAIL": "ciciot_corrected__seed13"})
    assert r1.returncode == 1                       # some failure, not a crash
    failed = tmp_path / "results_phase6c" / "ciciot" / "corrected" / "seed_13"
    info = json.loads((failed / "FAILED.json").read_text())
    assert info["exit_code"] == 7
    verified = [d for d in runs_dirs(tmp_path) if (d / "COMPLETE.json").exists()]
    assert len(verified) == 17
    before = {str(d): sha256_file(d / "COMPLETE.json") for d in verified}
    # without -Resume the runner refuses (never touches leftovers silently)
    r_refuse = orch(tmp_path, m, "run", *COMMON)
    assert r_refuse.returncode == 2 and "-Resume" in r_refuse.stdout
    # resume re-runs only the failed run
    r2 = orch(tmp_path, m, "run", *COMMON, "--resume")
    assert r2.returncode == 0, r2.stdout
    assert (failed / "COMPLETE.json").exists()
    preserved = list((tmp_path / "results_phase6c" / "ciciot" / "corrected").glob("seed_13.failed.*"))
    assert len(preserved) == 1 and (preserved[0] / "FAILED.json").exists()
    after = {str(d): sha256_file(d / "COMPLETE.json") for d in verified}
    assert before == after                           # verified runs were not touched
    assert orch(tmp_path, m, "validate").returncode == 0


def test_interrupted_partial_directory_is_preserved_and_rerun_on_resume(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    partial = tmp_path / "results_phase6c" / "unsw" / "reference" / "seed_12"
    partial.mkdir(parents=True)
    (partial / "round_metrics.csv").write_text("half-written", encoding="utf-8")
    (partial / "INTERRUPTED.json").write_text("{}", encoding="utf-8")
    assert orch(tmp_path, m, "run", *COMMON).returncode == 2           # refuses without -Resume
    r = orch(tmp_path, m, "run", *COMMON, "--resume")
    assert r.returncode == 0, r.stdout
    kept = list(partial.parent.glob("seed_12.incomplete.*"))
    assert len(kept) == 1 and (kept[0] / "round_metrics.csv").read_text() == "half-written"
    assert (partial / "COMPLETE.json").exists()


def test_verified_results_are_never_overwritten_and_tampering_stops_the_runner(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    assert orch(tmp_path, m, "run", *COMMON).returncode == 0
    victim = tmp_path / "results_phase6c" / "unsw" / "reference" / "seed_12" / "best_model_state.pt"
    victim.write_bytes(b"tampered")
    r = orch(tmp_path, m, "run", *COMMON, "--resume")
    assert r.returncode == 2 and ("no longer verifies" in r.stdout or "corrupted" in r.stdout)
    assert victim.read_bytes() == b"tampered"       # the runner did not "fix" or overwrite it
    assert orch(tmp_path, m, "validate").returncode == 1


def test_second_concurrent_runner_is_refused(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    state = tmp_path / "results_phase6c" / "_state"
    state.mkdir(parents=True)
    (state / "runner.lock").write_text(json.dumps({"pid": os.getpid(), "started": "now"}), encoding="utf-8")  # a LIVE pid
    r = orch(tmp_path, m, "run", *COMMON)
    assert r.returncode == 2
    assert "[FAIL] no other runner is active" in r.stdout
    assert not (tmp_path / "results_phase6c" / "unsw").exists()      # nothing was started


def test_stale_lock_from_a_dead_process_is_recovered(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    state = tmp_path / "results_phase6c" / "_state"
    state.mkdir(parents=True)
    (state / "runner.lock").write_text(json.dumps({"pid": 2 ** 22 + 12345, "started": "long ago"}), encoding="utf-8")
    r = orch(tmp_path, m, "run", *COMMON)
    assert r.returncode == 0, r.stdout + r.stderr


def test_runner_stops_safely_after_consecutive_failures(tmp_path):
    m = make_project(tmp_path)
    r = orch(tmp_path, m, "run", *COMMON, "--max-consecutive-failures", "3", env={"MOCK_FAIL": "seed"})
    assert r.returncode == 4 and "STOPPING SAFELY" in r.stdout
    assert len(list((tmp_path / "results_phase6c").glob("*/*/seed_*"))) == 3   # stopped after 3, did not burn the queue


def test_artifact_verification_catches_missing_files_after_a_successful_exit(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    manifest = json.loads(m.read_text())
    # a workload that exits 0 but forgets an artifact must NOT be marked complete
    broken = tmp_path / "broken_run.py"
    broken.write_text(
        "import sys, subprocess, pathlib\n"
        f"subprocess.run([sys.executable, r'{MOCK}'] + sys.argv[1:], check=True)\n"
        "out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])\n"
        "(out / 'best_model_state.pt').unlink()\n", encoding="utf-8")
    manifest["command"] = ["{python}", str(broken), "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"]
    manifest["manifest_sha256"] = manifest_hash(manifest)
    m.write_text(json.dumps(manifest), encoding="utf-8")
    r = orch(tmp_path, m, "run", *COMMON, "--max-consecutive-failures", "1")
    assert r.returncode == 4
    d = tmp_path / "results_phase6c" / "unsw" / "reference" / "seed_12"
    assert (d / "FAILED.json").exists() and not (d / "COMPLETE.json").exists()


def test_status_command_is_read_only_and_reports_progress(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    orch(tmp_path, m, "run", *COMMON, env={"MOCK_FAIL": "ciciot_baseline_x"})
    snapshot = sorted(str(p) for p in (tmp_path / "results_phase6c").rglob("*"))
    r = orch(tmp_path, m, "status")
    assert r.returncode == 0 and "Verified complete" in r.stdout and "Failures" in r.stdout
    assert snapshot == sorted(str(p) for p in (tmp_path / "results_phase6c").rglob("*"))


def test_aggregation_produces_tables_and_exact_paired_statistics(tmp_path):
    m = make_project(tmp_path)
    assert orch(tmp_path, m, "run", *COMMON).returncode == 0
    r = orch(tmp_path, m, "aggregate")
    assert r.returncode == 0, r.stdout + r.stderr
    summary = tmp_path / "results_phase6c" / "_summary"
    for name in ("runs_table_validation.csv", "arm_summary_validation.csv", "paired_contrasts_validation.csv", "SUMMARY_validation.md"):
        assert (summary / name).exists()
    import pandas as pd
    contrasts = pd.read_csv(summary / "paired_contrasts_validation.csv")
    row = contrasts[(contrasts.arm == "corrected") & (contrasts.versus == "reference") & (contrasts.metric == "auc_best")
                    & (contrasts.dataset == "unsw")].iloc[0]
    assert row["n_pairs"] == 3 and row["mean_diff"] > 0.0   # mock gives corrected a +0.03 AUC bonus
    assert 0 < row["sign_test_p"] <= 1


def test_exact_tests_and_holm():
    from orchestrator import exact_sign_test, exact_wilcoxon, holm

    assert exact_sign_test([1, 2, 3, 4, 5]) == pytest.approx(0.0625)
    assert exact_wilcoxon([1, 2, 3, 4, 5]) == pytest.approx(0.0625)
    assert exact_wilcoxon([1, -2, 3, -4, 5]) > 0.5
    assert exact_wilcoxon([0, 0]) == 1.0
    adj = holm([0.01, 0.04, 0.03])
    assert adj == pytest.approx([0.03, 0.06, 0.06])


def test_cloud_mode_requires_the_locked_test_files_to_be_absent(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    # test files present -> cloud mode refuses (test data must never be on the remote machine)
    r_present = orch(tmp_path, m, "preflight", *COMMON, "--cloud-mode")
    assert r_present.returncode == 2 and "[FAIL] cloud mode: locked test file ABSENT" in r_present.stdout
    (tmp_path / "data" / "test.csv").unlink()
    r_absent = orch(tmp_path, m, "preflight", *COMMON, "--cloud-mode")
    assert r_absent.returncode == 0, r_absent.stdout
    # ... while normal (local) mode needs them present
    r_local = orch(tmp_path, m, "preflight", *COMMON)
    assert r_local.returncode == 2 and "locked test file present" in r_local.stdout
    # a full mock run works in cloud mode and never needs the test files
    r_run = orch(tmp_path, m, "run", *COMMON, "--cloud-mode")
    assert r_run.returncode == 0, r_run.stdout


def test_migration_marker_stops_the_local_runner_but_not_the_cloud_runner(tmp_path):
    m = make_project(tmp_path, seeds=[12])
    state = tmp_path / "results_phase6c" / "_state"
    state.mkdir(parents=True)
    (state / "MIGRATED_TO_CLOUD.json").write_text("{}", encoding="utf-8")
    r = orch(tmp_path, m, "run", *COMMON)
    assert r.returncode == 2 and "migrated to a cloud machine" in r.stdout
    assert not (tmp_path / "results_phase6c" / "unsw").exists()          # nothing was started locally
    (tmp_path / "data" / "test.csv").unlink()                           # the cloud copy has no test files
    r_cloud = orch(tmp_path, m, "run", *COMMON, "--cloud-mode")
    assert r_cloud.returncode == 0, r_cloud.stdout
