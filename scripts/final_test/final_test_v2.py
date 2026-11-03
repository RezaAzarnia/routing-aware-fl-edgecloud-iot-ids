"""Final-test evaluation pathway v2 (plan ``final-test-eval-v2``). SEPARATE from, and never called by, any training runner.

Sub-commands
  build           write docs/final_test/FINAL_TEST_MANIFEST.json from verified historical runs (reads run folders only; NEVER touches test files)
  readiness       training/validation-only checks R1-R8 (checkpoint+preprocessor+threshold integrity, model/preprocessor compatibility)
  preproc-equiv   proves the saved training-fitted preprocessors equal a training-only refit (reads train/validation data, never test)
  authorization-template
  evaluate        THE one-time final-test evaluation: needs a signed authorization; --dry-run reads no test data

Design rules (see Phase9C_Submission_Readiness/FINAL_TEST_SCRIPT_CHANGELOG.md)
  * frozen checkpoints, thresholds and preprocessors come from the manifest; nothing is selected, tuned, re-fitted or optimised on test data;
  * the saved training-fitted preprocessor is LOADED (never refitted); feature names/order are verified before transforming;
  * the metric code is the repaired single-decision-rule implementation of src/metrics.py (evaluation code is fingerprinted separately from the
    historical training code, whose lineage is recorded and re-verified from the frozen git tags);
  * results go to results_final_test/ (new, outside every historical results tree) and are created exclusively (never overwritten);
  * protected_access_guard blocks any accidental open() of the locked files; the evaluation opens them only inside authorized(...).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "scripts" / "phase6c", ROOT / "scripts" / "final_test"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from p6c_common import (atomic_write_json, code_fingerprint, load_manifest, manifest_hash, now_utc,  # noqa: E402
                        sha256_file, verify_run_dir)
import protected_access_guard as guard  # noqa: E402

SCHEMA = "final_test_manifest_v2"
RESULT_SCHEMA = "final_test_result_v2"
PLAN = "final-test-eval-v2"
EVAL_GLOBS = ["src/*.py", "scripts/final_test/*.py", "scripts/phase6c/p6c_common.py"]
SOURCES = {"phase6c": ("docs/phase6c/EXPERIMENT_MANIFEST.json", "phase6c-final-results"),
           "phase7b": ("docs/phase7b/EXPERIMENT_MANIFEST.json", "phase7b-final-results")}
AUTH_STATEMENT = "I authorize one-time final-test evaluation of the frozen configurations under plan final-test-eval-v2"
MANIFEST_PATH = ROOT / "docs" / "final_test" / "FINAL_TEST_MANIFEST.json"
OUT_ROOT = ROOT / "results_final_test"
PRIMARY_CONTRASTS = [["reference", "clean_fedavg"], ["reference", "scenario_fedavg_topk"], ["corrected", "reference"], ["reference_gaussian", "reference"]]
HISTORICAL_RESULT_DIRS = ("results_phase6c", "results_phase7", "results_phase7b", "results_phase8", "results_phase5", "results_phase6a", "results_phase6b")


# ------------------------------------------------------------------ helpers
def _tag_tree_fingerprint(tag: str, globs) -> tuple[str | None, str | None]:
    """Fingerprint of the code exactly as frozen at a git tag (so the historical training code lineage is verified without the working tree)."""
    ok = subprocess.run(["git", "rev-parse", "--verify", "--quiet", tag], capture_output=True, cwd=ROOT)
    if ok.returncode != 0:
        return None, None
    commit = subprocess.run(["git", "rev-parse", tag + "^{commit}"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        tar = Path(tmp) / "t.tar"
        subprocess.run(["git", "archive", "--format=tar", "-o", str(tar), tag], check=True, cwd=ROOT)
        shutil.unpack_archive(str(tar), str(Path(tmp) / "tree"))
        return code_fingerprint(Path(tmp) / "tree", globs), commit


def _historical_runs(src: str):
    mpath, _ = SOURCES[src]
    M = load_manifest(ROOT / mpath)
    runs = [r for r in sorted(M["runs"], key=lambda r: r["order"]) if src != "phase7b" or r.get("tier") == "mandatory"]
    return M, runs


# ------------------------------------------------------------------ build
def build_manifest(out: Path = MANIFEST_PATH) -> dict:
    sources, runs_out = {}, []
    p6c_manifest = load_manifest(ROOT / SOURCES["phase6c"][0])
    for src, (mpath, tag) in SOURCES.items():
        M, runs = _historical_runs(src)
        globs = M.get("code_fingerprint_globs")
        tag_fp, tag_commit = _tag_tree_fingerprint(tag, globs)
        sources[src] = {"manifest": mpath, "manifest_sha256": M["manifest_sha256"], "code_fingerprint": M["code_fingerprint"], "git_tag": tag,
                        "tag_commit": tag_commit, "tag_tree_fingerprint": tag_fp, "tag_matches_manifest": tag_fp == M["code_fingerprint"]}
        for r in runs:
            d = ROOT / r["out_dir"]
            if not (d / "COMPLETE.json").exists():
                continue                                             # e.g. the optional, never-run CIC tier of Phase 7b
            problems = verify_run_dir(d, r, M)
            if problems:
                raise SystemExit(f"run {r['run_id']} fails verification: {problems}")
            comp = json.loads((d / "COMPLETE.json").read_text(encoding="utf-8"))
            fin = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
            sel = fin["selected_operating_point"]
            runs_out.append({
                "run_id": r["run_id"], "source": src, "dataset": r["dataset"], "arm": r["arm"], "seed": r["seed"], "run_dir": r["out_dir"],
                "config_sha256": r["config_sha256"], "resolved_config_sha256": comp["artifact_sha256"]["resolved_config.yaml"],
                "best_checkpoint_sha256": comp["artifact_sha256"]["best_model_state.pt"], "last_checkpoint_sha256": comp["artifact_sha256"]["last_model_state.pt"],
                "preprocessor_sha256": sha256_file(d / "preprocessor.joblib"),       # NOT part of COMPLETE.json; frozen here and proven by preproc-equiv
                "best_round": fin["best_round"],
                "thresholds": {"best_primary": sel["threshold"], "last_primary": fin["last_round_selection_partition"]["threshold"],
                               "targets": {k: v["calibration_partition"]["threshold"] for k, v in fin["threshold_diagnostics"].items()}},
                "calibration_reference": {"fpr": sel.get("calibration_fpr"), "recall": sel.get("calibration_recall_adr"), "constraint_feasible": sel.get("constraint_feasible")},
            })
    manifest = {
        "schema": SCHEMA, "plan": PLAN, "created_utc": now_utc(),
        "git_commit_at_build": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
        "purpose": "Frozen, one-time final-test evaluation of saved checkpoints. No retraining, no re-selection, no threshold optimisation.",
        "sources": sources,
        "evaluation_code": {"globs": EVAL_GLOBS, "fingerprint": code_fingerprint(ROOT, EVAL_GLOBS),
                            "note": "Evaluation code is fingerprinted separately; historical TRAINING code lineage is the git tags in `sources`."},
        "locked_test": p6c_manifest["locked_test"],           # descriptors copied from the Phase 6C manifest; the files themselves are NOT touched here
        "protected_reference_files": {"unsw": {"train": "data/UNSW_NB15_training-set.csv"},
                                       "ciciot": {"train": p6c_manifest["datasets"]["ciciot"]["prepared_dir"] + "/train.csv.gz",
                                                  "validation": p6c_manifest["datasets"]["ciciot"]["prepared_dir"] + "/validation.csv.gz"}},
        "policy": {"checkpoints": "recorded best_model_state.pt (best_round from the selection partition) and last_model_state.pt (round 30)",
                   "thresholds": "recorded calibration-partition thresholds only; never recomputed or optimised on test data",
                   "preprocessing": "saved training-fitted preprocessor.joblib is loaded; never refitted",
                   "decision_rule": "score >= threshold on raw probabilities (repaired src/metrics.py)",
                   "operational_flag": "test FPR at the primary threshold > 0.25 is reported as a threshold-policy failure; no repair",
                   "primary_contrasts": PRIMARY_CONTRASTS,
                   "overlap_controlled_subsets": ["not_in_reference", "unique_within_test", "not_in_reference_and_unique"]},
        "n_runs": len(runs_out), "runs": runs_out,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(out, manifest)
    return manifest


# ------------------------------------------------------------------ readiness (no test data)
def readiness(manifest_path: Path = MANIFEST_PATH, report: Path | None = None) -> dict:
    import joblib
    import torch

    from src.config import Config
    from src.experiment import _model_factory

    guard.install()
    manifest = load_manifest(manifest_path)
    checks, failures = [], []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)})
        if not ok:
            failures.append(name)

    add("manifest hash verifies", manifest["manifest_sha256"] == manifest_hash(manifest))
    for src, info in manifest["sources"].items():
        add(f"{src}: git tag tree fingerprint equals the locked training-code fingerprint", info["tag_matches_manifest"], info["git_tag"])
    n_ok = 0
    for rec in manifest["runs"]:
        d = ROOT / rec["run_dir"]
        try:
            assert sha256_file(d / "best_model_state.pt") == rec["best_checkpoint_sha256"], "best checkpoint hash"
            assert sha256_file(d / "last_model_state.pt") == rec["last_checkpoint_sha256"], "last checkpoint hash"
            assert sha256_file(d / "preprocessor.joblib") == rec["preprocessor_sha256"], "preprocessor hash"
            cfg = Config.from_yaml(d / "resolved_config.yaml")
            assert cfg.data.test_csv == "" and cfg.experiment.validation_only, "training config must be validation-only"
            prep = joblib.load(d / "preprocessor.joblib")
            dim = len(prep.get_feature_names_out())
            summary = json.loads((d / "dataset_summary.json").read_text(encoding="utf-8"))
            assert dim == int(summary["encoded_feature_dimension"]), "preprocessor output dimension != recorded encoded dimension"
            for key in ("best", "last"):
                model = _model_factory(cfg, dim)()
                state = torch.load(d / f"{key}_model_state.pt", map_location="cpu", weights_only=True)
                model.load_state_dict(state, strict=True)
            thr = rec["thresholds"]
            vals = [thr["best_primary"], thr["last_primary"], *thr["targets"].values()]
            assert all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in vals), "threshold outside [0,1]"
            n_ok += 1
        except Exception as exc:                                  # noqa: BLE001
            failures.append(f"{rec['run_id']}: {exc!r}")
    add(f"all {len(manifest['runs'])} runs: checkpoint/preprocessor hashes, strict state_dict load, dimensions, thresholds", n_ok == len(manifest["runs"]), f"{n_ok} ok")
    add("no locked final-test file was opened during readiness checks", not guard.violations, guard.violations)
    result = {"created_utc": now_utc(), "manifest_sha256": manifest["manifest_sha256"], "checks": checks, "failures": failures, "pass": not failures}
    if report:
        atomic_write_json(report, result)
    return result


# ------------------------------------------------------------------ preprocessor equivalence (train/validation only)
def _prep_params(prep) -> dict:
    out = {"features_in": list(prep.feature_names_in_), "features_out": list(prep.get_feature_names_out())}
    for name, pipe, cols in prep.transformers_:
        if name == "remainder":
            continue
        for step_name, step in pipe.steps:
            for attr in ("statistics_", "mean_", "scale_", "var_"):
                if hasattr(step, attr):
                    out[f"{name}.{step_name}.{attr}"] = getattr(step, attr)
            if hasattr(step, "categories_"):
                out[f"{name}.{step_name}.categories_"] = [list(map(str, c)) for c in step.categories_]
    return out


def _same(va, vb) -> bool:
    import numpy as np

    if va is None or vb is None:
        return False
    if isinstance(va, list) or isinstance(vb, list):
        return va == vb
    a, b = np.asarray(va), np.asarray(vb)
    if a.dtype.kind in "fiu" and b.dtype.kind in "fiu":
        return a.shape == b.shape and bool(np.array_equal(a, b, equal_nan=True))
    return a.shape == b.shape and a.astype(str).tolist() == b.astype(str).tolist()


def preproc_equivalence(manifest_path: Path = MANIFEST_PATH, report: Path | None = None, cic_seeds=(12, 16)) -> dict:
    """Refit each (dataset, seed) preprocessor from TRAINING data only (load_dataset(load_test=False)) and compare with the saved one."""
    import joblib
    import numpy as np

    from src.config import Config
    from src.data import load_dataset

    guard.install()
    manifest = load_manifest(manifest_path)
    seen, rows = set(), []
    for rec in manifest["runs"]:
        key = (rec["dataset"], rec["seed"])
        if key in seen or (rec["dataset"] == "ciciot" and rec["seed"] not in cic_seeds):
            continue
        seen.add(key)
        d = ROOT / rec["run_dir"]
        cfg = Config.from_yaml(d / "resolved_config.yaml")
        cfg.data.test_csv = ""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "refit.joblib"
            load_dataset(cfg.data, seed=rec["seed"], preprocessor_output=out, load_test=False)
            a, b = _prep_params(joblib.load(d / "preprocessor.joblib")), _prep_params(joblib.load(out))
        diffs = []
        for k in sorted(set(a) | set(b)):
            va, vb = a.get(k), b.get(k)
            same = _same(va, vb)
            if not same:
                diffs.append(k)
        rows.append({"dataset": rec["dataset"], "seed": rec["seed"], "run_id": rec["run_id"], "n_features_out": len(a["features_out"]), "identical": not diffs, "differing_keys": diffs})
    result = {"created_utc": now_utc(), "pairs_checked": len(rows), "all_identical": all(r["identical"] for r in rows), "rows": rows,
              "locked_test_opened": guard.violations}
    if report:
        atomic_write_json(report, result)
    return result


# ------------------------------------------------------------------ evaluation core (testable with synthetic fixtures)
def prepare_test_matrix(raw_test, data_cfg, preprocessor):
    """Replicates the training-time feature path with the SAVED preprocessor (no refit): drop label/id columns, inf->NaN, verify names, transform."""
    import numpy as np

    y = raw_test[data_cfg.label_col].astype(int).to_numpy(dtype=np.int64)
    feats = raw_test.drop(columns=[data_cfg.label_col, *data_cfg.drop_cols], errors="ignore").replace([np.inf, -np.inf], np.nan)
    cols = list(preprocessor.feature_names_in_)
    missing, extra = sorted(set(cols) - set(feats.columns)), sorted(set(feats.columns) - set(cols))
    if missing or extra:
        raise ValueError(f"test feature schema differs from the training schema: missing={missing[:5]} extra={extra[:5]}")
    return preprocessor.transform(feats[cols]).astype(np.float32, copy=False), y


def overlap_masks(raw_test, reference_frames, data_cfg):
    import numpy as np

    from src.data_integrity import predictor_fingerprint

    feature_cols = [c for c in raw_test.columns if c not in {data_cfg.label_col, *data_cfg.drop_cols}]
    test_fp = predictor_fingerprint(raw_test, feature_cols)
    ref = set()
    for frame in reference_frames:
        ref |= set(predictor_fingerprint(frame, feature_cols).tolist())
    not_in_ref = np.array([h not in ref for h in test_fp.tolist()])
    _, first = np.unique(test_fp, return_index=True)
    unique = np.zeros(len(test_fp), dtype=bool)
    unique[first] = True
    return {"not_in_reference": not_in_ref, "unique_within_test": unique, "not_in_reference_and_unique": not_in_ref & unique}


def metrics_at(y, prob, threshold):
    from src.metrics import binary_classification_metrics

    m = binary_classification_metrics(y, prob, threshold=float(threshold))
    return {k: (float(v) if isinstance(v, float) else v) for k, v in m.items() if not isinstance(v, (list, dict))}


def predict(cfg, state_path: Path, X, input_dim: int):
    import numpy as np
    import torch

    from src.experiment import _model_factory

    model = _model_factory(cfg, input_dim)()
    model.load_state_dict(torch.load(state_path, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), 8192):
            out.append(torch.softmax(model(torch.from_numpy(X[i:i + 8192]).float()), 1)[:, 1].numpy())
    return np.concatenate(out)


def evaluate_one(rec, root: Path, raw_test, masks, out_root: Path, manifest_sha: str, data_cfg_by_run=None, save_probabilities=True) -> Path:
    import joblib
    import numpy as np

    from src.config import Config

    d = root / rec["run_dir"]
    assert sha256_file(d / "best_model_state.pt") == rec["best_checkpoint_sha256"] and sha256_file(d / "last_model_state.pt") == rec["last_checkpoint_sha256"]
    assert sha256_file(d / "preprocessor.joblib") == rec["preprocessor_sha256"]
    cfg = Config.from_yaml(d / "resolved_config.yaml")
    prep = joblib.load(d / "preprocessor.joblib")
    X, y = prepare_test_matrix(raw_test, cfg.data, prep)
    p_best = predict(cfg, d / "best_model_state.pt", X, X.shape[1])
    p_last = predict(cfg, d / "last_model_state.pt", X, X.shape[1])
    thr = rec["thresholds"]
    result = {
        "schema": RESULT_SCHEMA, "run_id": rec["run_id"], "evaluated_utc": now_utc(), "final_test_manifest_sha256": manifest_sha, "dataset": rec["dataset"], "arm": rec["arm"],
        "seed": rec["seed"], "best_round": rec["best_round"], "checkpoint_sha256": {"best": rec["best_checkpoint_sha256"], "last": rec["last_checkpoint_sha256"]},
        "preprocessor_sha256": rec["preprocessor_sha256"], "thresholds_from_calibration_partition": thr, "calibration_reference": rec["calibration_reference"],
        "test_rows": int(len(y)), "test_benign": int((y == 0).sum()),
        "best": {"primary": metrics_at(y, p_best, thr["best_primary"]), "targets": {k: metrics_at(y, p_best, t) for k, t in thr["targets"].items()}},
        "last": {"primary": metrics_at(y, p_last, thr["last_primary"])},
        "overlap_controlled": {name: {"rows": int(m.sum()), "best_primary": metrics_at(y[m], p_best[m], thr["best_primary"]), "last_primary": metrics_at(y[m], p_last[m], thr["last_primary"])}
                               for name, m in masks.items() if m.sum() > 1 and len(set(y[m].tolist())) == 2},
    }
    rdir = out_root / rec["dataset"] / rec["arm"] / f"seed_{rec['seed']}"
    rdir.mkdir(parents=True, exist_ok=True)
    path = rdir / "final_test_result.json"
    if save_probabilities:
        np.savez_compressed(rdir / "test_probabilities.npz", best=p_best.astype(np.float32), last=p_last.astype(np.float32))
        result["probabilities_file"] = "test_probabilities.npz"
    with open(path, "x", encoding="utf-8") as handle:                  # exclusive create: never overwrite
        json.dump(result, handle, indent=2)
    with open(out_root / "ledger.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"run_id": rec["run_id"], "result_sha256": sha256_file(path), "t": now_utc()}) + "\n")
    return path


def check_authorization(auth: dict, manifest: dict) -> list[str]:
    problems = []
    if auth.get("manifest_sha256") != manifest["manifest_sha256"]:
        problems.append("authorization refers to a different manifest")
    if auth.get("plan") != PLAN:
        problems.append("authorization refers to a different plan version")
    if auth.get("authorized") is not True:
        problems.append("authorized is not true")
    if auth.get("statement") != AUTH_STATEMENT:
        problems.append("authorization statement does not match the required text")
    if not str(auth.get("authorized_by", "")).strip():
        problems.append("authorized_by is empty")
    for flag in ("acknowledge_no_retuning_after_test", "acknowledge_prior_integrity_reads_disclosed"):
        if auth.get(flag) is not True:
            problems.append(f"{flag} missing")
    return problems


def write_authorization_template(manifest: dict, path: Path) -> None:
    atomic_write_json(path, {"manifest_sha256": manifest["manifest_sha256"], "plan": PLAN, "authorized": False, "statement": "", "required_statement": AUTH_STATEMENT,
                             "authorized_by": "", "acknowledge_no_retuning_after_test": False, "acknowledge_prior_integrity_reads_disclosed": False,
                             "note": "Fill ONLY after readiness R1-R8 pass and every manuscript/analysis decision is frozen."})


def refusal_reasons(manifest: dict, auth: dict | None, out_root: Path, root: Path, verify_history: bool = True, require_auth: bool = True) -> list[str]:
    reasons = []
    if require_auth:
        if auth is None:
            reasons.append("no authorization file")
        else:
            reasons += check_authorization(auth, manifest)
    if manifest.get("manifest_sha256") != manifest_hash(manifest):
        reasons.append("final-test manifest was modified after freezing")
    if code_fingerprint(root, manifest["evaluation_code"]["globs"]) != manifest["evaluation_code"]["fingerprint"]:
        reasons.append("evaluation-code fingerprint differs from the frozen manifest")
    resolved = Path(out_root).resolve()
    if any(part in HISTORICAL_RESULT_DIRS for part in resolved.parts) or (resolved.exists() and any(resolved.iterdir())):
        reasons.append("output directory is inside a historical results tree or is not empty (results are never overwritten)")
    if verify_history:
        for src, info in manifest["sources"].items():
            M = load_manifest(root / info["manifest"])
            if M["manifest_sha256"] != info["manifest_sha256"]:
                reasons.append(f"{src}: source manifest changed")
            if not info.get("tag_matches_manifest"):
                reasons.append(f"{src}: training-code lineage (git tag) does not match its manifest")
        for rec in manifest["runs"]:
            M = load_manifest(root / manifest["sources"][rec["source"]]["manifest"])
            run = next(r for r in M["runs"] if r["run_id"] == rec["run_id"])
            if verify_run_dir(root / rec["run_dir"], run, M):
                reasons.append(f"{rec['run_id']}: run no longer verifies")
                break
    return reasons


def read_locked(path: Path, kind: str, expected: str):
    """Single authorised read of a locked test file: hash (raw csv bytes or decompressed gzip content) and parse from the same bytes."""
    import gzip
    import hashlib

    import pandas as pd

    with guard.authorized(path):
        raw = Path(path).read_bytes()
    content = gzip.decompress(raw) if kind == "gzip_csv" else raw
    if hashlib.sha256(content).hexdigest() != expected:
        raise SystemExit(f"REFUSED: {path.name} content hash differs from the locked manifest")
    return pd.read_csv(io.BytesIO(content))


def evaluate(manifest_path: Path, authorization: Path | None, out_root: Path, dry_run: bool, root: Path = ROOT, verify_history: bool = True,
             preflight: bool = False) -> int:
    import pandas as pd

    manifest = load_manifest(manifest_path)
    auth = json.loads(Path(authorization).read_text(encoding="utf-8")) if authorization and Path(authorization).exists() else None
    reasons = refusal_reasons(manifest, auth, out_root, root, verify_history, require_auth=not preflight)
    if reasons:
        print("REFUSED: " + "; ".join(reasons))
        return 2
    if preflight:
        auth_problems = ["no authorization file"] if auth is None else check_authorization(auth, manifest)
        print("PREFLIGHT OK: every non-authorization precondition holds (manifest, evaluation-code fingerprint, training-code lineage, run integrity, "
              f"output directory). Authorization: {'VALID' if not auth_problems else 'NOT SIGNED/INVALID (' + '; '.join(auth_problems) + ')'}. No test data was read.")
        return 0
    if dry_run:
        print(f"DRY RUN: every precondition holds; {manifest['n_runs']} runs would be evaluated once. No test data was read.")
        return 0
    guard.install()
    out_root.mkdir(parents=True, exist_ok=True)
    raw_cache, mask_cache = {}, {}
    done = 0
    for rec in manifest["runs"]:
        ds = rec["dataset"]
        if ds not in raw_cache:
            info = manifest["locked_test"][ds]
            raw_cache[ds] = read_locked(root / info["path"], info["kind"], info.get("sha256") or info.get("content_sha256"))
            ref = manifest["protected_reference_files"][ds]
            frames = [pd.read_csv(root / p) for p in ref.values()]
            from src.config import Config
            cfg0 = Config.from_yaml(root / rec["run_dir"] / "resolved_config.yaml")
            mask_cache[ds] = overlap_masks(raw_cache[ds], frames, cfg0.data)
        evaluate_one(rec, root, raw_cache[ds], mask_cache[ds], out_root, manifest["manifest_sha256"])
        done += 1
    print(f"Final-test evaluation finished: {done} runs evaluated once each.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "readiness", "preproc-equiv", "authorization-template", "evaluate"])
    ap.add_argument("--manifest", default=str(MANIFEST_PATH))
    ap.add_argument("--authorization", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preflight", action="store_true", help="check every precondition EXCEPT the owner's signature; reads no test data")
    args = ap.parse_args()
    manifest_path = Path(args.manifest)
    if args.command == "build":
        m = build_manifest(manifest_path)
        print(f"wrote {manifest_path} ({m['n_runs']} runs, sha256 {m['manifest_sha256'][:16]}...)")
        return 0
    if args.command == "readiness":
        r = readiness(manifest_path, Path(args.out) if args.out else None)
        print(json.dumps({"pass": r["pass"], "failures": r["failures"][:10]}, indent=1))
        return 0 if r["pass"] else 1
    if args.command == "preproc-equiv":
        r = preproc_equivalence(manifest_path, Path(args.out) if args.out else None)
        print(json.dumps({"pairs_checked": r["pairs_checked"], "all_identical": r["all_identical"]}))
        return 0 if r["all_identical"] else 1
    if args.command == "authorization-template":
        write_authorization_template(load_manifest(manifest_path), Path(args.out or "final_test_authorization.json"))
        return 0
    return evaluate(manifest_path, Path(args.authorization) if args.authorization else None, Path(args.out) if args.out else OUT_ROOT, args.dry_run,
                    preflight=args.preflight)


if __name__ == "__main__":
    sys.exit(main())
