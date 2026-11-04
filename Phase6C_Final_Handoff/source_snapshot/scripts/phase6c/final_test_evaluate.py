"""Locked, one-time final-test evaluation (a SEPARATE operation; never called by the training runner).

Preconditions (all enforced):
  1. the experiment manifest hash verifies (configs, seeds, datasets frozen);
  2. every run in the manifest is COMPLETE and verified, with the manifest's code fingerprint;
  3. an authorization file explicitly authorises THIS manifest hash;
  4. the test files' sha256 equal the hashes recorded in the manifest;
  5. a run has no previous final-test result (each frozen run is evaluated exactly once).
No retraining, no threshold change: thresholds are the ones chosen on the calibration partition.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from p6c_common import (  # noqa: E402
    ROOT, atomic_write_json, code_fingerprint, load_manifest, log, now_utc, sha256_file, sha256_gzip_content,
)

AUTH_STATEMENT = "I authorize one-time final-test evaluation of the frozen configurations"


def write_template(manifest: dict, path: Path) -> None:
    atomic_write_json(path, {
        "manifest_sha256": manifest["manifest_sha256"],
        "authorized": False,
        "statement": "",
        "required_statement": AUTH_STATEMENT,
        "authorized_by": "",
        "acknowledge_no_retuning_after_test": False,
        "note": "Set authorized=true, copy required_statement into statement, fill authorized_by, set acknowledge_no_retuning_after_test=true. "
                "Do this ONLY after all configurations and selection decisions are frozen.",
    })


def check_authorization(auth: dict, manifest: dict) -> list[str]:
    problems = []
    if auth.get("manifest_sha256") != manifest["manifest_sha256"]:
        problems.append("authorization refers to a different manifest")
    if auth.get("authorized") is not True:
        problems.append("authorized is not true")
    if auth.get("statement") != AUTH_STATEMENT:
        problems.append("authorization statement does not match the required text")
    if not str(auth.get("authorized_by", "")).strip():
        problems.append("authorized_by is empty")
    if auth.get("acknowledge_no_retuning_after_test") is not True:
        problems.append("no-retuning acknowledgement missing")
    return problems


def test_file_problems(manifest: dict, root: Path) -> list[str]:
    problems = []
    for name, info in manifest["locked_test"].items():
        path = root / info["path"]
        if not path.exists():
            problems.append(f"{name}: test file missing")
            continue
        actual = sha256_file(path) if info["kind"] == "csv" else sha256_gzip_content(path)
        expected = info.get("sha256") or info.get("content_sha256")
        if actual != expected:
            problems.append(f"{name}: test file hash differs from the locked manifest")
    return problems


def metrics_at(y, prob, threshold):
    from src.metrics import binary_classification_metrics

    m = binary_classification_metrics(y, prob, threshold=float(threshold))
    return {k: (float(v) if isinstance(v, float) else v) for k, v in m.items() if not isinstance(v, (list, dict))}


def predict(cfg, state_path: Path, X) -> "np.ndarray":
    import numpy as np
    import torch

    from src.experiment import _model_factory

    model = _model_factory(cfg, X.shape[1])()
    model.load_state_dict(torch.load(state_path))
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), 8192):
            logits = model(torch.from_numpy(X[i:i + 8192]).float())
            out.append(torch.softmax(logits, 1)[:, 1].numpy())
    return np.concatenate(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "docs" / "phase6c" / "EXPERIMENT_MANIFEST.json"))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--authorization", default=None)
    parser.add_argument("--write-authorization-template", default=None)
    parser.add_argument("--dry-run", action="store_true", help="check every precondition without reading any test data")
    args = parser.parse_args()
    root = Path(args.root)
    manifest = load_manifest(Path(args.manifest))

    if args.write_authorization_template:
        write_template(manifest, Path(args.write_authorization_template))
        print(f"Wrote {args.write_authorization_template} (authorized=false). Edit it only when everything is frozen.")
        return 0

    from orchestrator import run_status

    if not args.authorization or not Path(args.authorization).exists():
        print("REFUSED: no authorization file. Create one with --write-authorization-template and sign it deliberately.")
        return 2
    auth = json.loads(Path(args.authorization).read_text(encoding="utf-8"))
    problems = check_authorization(auth, manifest)
    if problems:
        print("REFUSED: authorization invalid: " + "; ".join(problems))
        return 2
    if code_fingerprint(root) != manifest["code_fingerprint"]:
        print("REFUSED: the code/config fingerprint differs from the locked manifest.")
        return 2
    not_ready = [r["run_id"] for r in manifest["runs"] if run_status(r, manifest, root)[0] != "verified"]
    if not_ready:
        print(f"REFUSED: {len(not_ready)} runs are not complete and verified (e.g. {not_ready[:3]}). Freeze everything first.")
        return 2
    if args.dry_run:
        print("DRY RUN: all preconditions except the test-file hashes are satisfied. No test data was read.")
        print(f"Would evaluate {len(manifest['runs'])} frozen runs once each.")
        return 0
    bad = test_file_problems(manifest, root)
    if bad:
        print("REFUSED: " + "; ".join(bad))
        return 2

    import numpy as np
    import pandas as pd

    from src.config import Config
    from src.data import load_dataset
    from src.data_integrity import predictor_fingerprint

    ft_root = root / "results_phase6c" / "_final_test"
    ft_root.mkdir(parents=True, exist_ok=True)
    ledger = ft_root / "ledger.jsonl"
    bundles: dict = {}
    done = skipped = 0
    for run in sorted(manifest["runs"], key=lambda r: r["order"]):
        result_dir = ft_root / run["dataset"] / run["arm"] / f"seed_{run['seed']}"
        result_path = result_dir / "final_test_result.json"
        if result_path.exists():
            skipped += 1
            continue
        out = root / run["out_dir"]
        cfg = Config.from_yaml(out / "resolved_config.yaml")
        locked = manifest["locked_test"][run["dataset"]]
        cfg.data.test_csv = str(root / locked["path"])
        key = (run["dataset"], run["seed"])
        if key not in bundles:
            bundles.clear()
            log(f"loading {run['dataset']} seed {run['seed']} (train/val + locked test)")
            bundles[key] = load_dataset(cfg.data, seed=run["seed"], load_test=True)
        bundle = bundles[key]
        fin = json.loads((out / "final_validation_metrics.json").read_text(encoding="utf-8"))
        best_thr = fin["selected_operating_point"]["threshold"]
        last_thr = fin["last_round_selection_partition"]["threshold"]
        targets = {k: v["calibration_partition"]["threshold"] for k, v in fin["threshold_diagnostics"].items()}
        p_best = predict(cfg, out / "best_model_state.pt", bundle.X_test)
        p_last = predict(cfg, out / "last_model_state.pt", bundle.X_test)
        y = bundle.y_test
        result = {
            "run_id": run["run_id"], "evaluated_utc": now_utc(), "manifest_sha256": manifest["manifest_sha256"],
            "config_sha256": run["config_sha256"], "code_fingerprint": manifest["code_fingerprint"],
            "test_file": locked["path"], "test_file_hash": locked.get("sha256") or locked.get("content_sha256"),
            "test_rows": int(len(y)), "test_benign": int((y == 0).sum()),
            "checkpoint_sha256": {"best": sha256_file(out / "best_model_state.pt"), "last": sha256_file(out / "last_model_state.pt")},
            "thresholds_from_calibration_partition": {"best_primary": best_thr, "last_primary": last_thr, "targets": targets},
            "best_checkpoint": {"primary_threshold": metrics_at(y, p_best, best_thr),
                                "targets": {k: metrics_at(y, p_best, t) for k, t in targets.items()}},
            "last_checkpoint": {"primary_threshold": metrics_at(y, p_last, last_thr)},
        }
        if run["dataset"] == "unsw":
            seen = np.concatenate([bundle.X_train, bundle.X_val] + [a for a in (bundle.X_thr, bundle.X_rep) if a is not None])
            fp_train = set(predictor_fingerprint(pd.DataFrame(seen), list(range(seen.shape[1]))).tolist())
            fp_test = predictor_fingerprint(pd.DataFrame(bundle.X_test), list(range(bundle.X_test.shape[1])))
            keep = np.array([f not in fp_train for f in fp_test.tolist()])
            result["duplicate_controlled"] = {
                "rule": "test rows whose predictor vector does not occur in the official training file",
                "rows": int(keep.sum()), "excluded_rows": int((~keep).sum()),
                "best_primary": metrics_at(y[keep], p_best[keep], best_thr),
                "best_targets": {k: metrics_at(y[keep], p_best[keep], t) for k, t in targets.items()},
            }
        result_dir.mkdir(parents=True, exist_ok=True)
        with open(result_path, "x", encoding="utf-8") as handle:  # exclusive: never overwrite
            json.dump(result, handle, indent=2)
        with open(ledger, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"run_id": run["run_id"], "result_sha256": sha256_file(result_path), "t": now_utc()}) + "\n")
        done += 1
        log(f"final-test evaluated {run['run_id']}")
    print(f"Final-test evaluation finished: {done} newly evaluated, {skipped} already had a result (never re-evaluated).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
