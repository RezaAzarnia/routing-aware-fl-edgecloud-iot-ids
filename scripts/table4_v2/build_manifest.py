"""Step 2: write the locked run manifest BEFORE any training. Refuses to overwrite an existing manifest.
The reserved test files are never opened or hashed here; their locked identity stays in docs/phase6c/EXPERIMENT_MANIFEST.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t4_common import (CFG_DIR, DATASETS, DOC_DIR, FG, MANIFEST, NEW_ARMS, OUT_ROOT, PHASE6C_MANIFEST, ROOT, ROUNDS, SEEDS, VERSION,  # noqa: E402
                       DEFAULT_REQUIRED_ARTIFACTS, fingerprint, git_head, manifest_hash, now_utc, sha256_file, sha256_gzip_content, sha256_text_file)


def main():
    if MANIFEST.exists():
        sys.exit(f"{MANIFEST} already exists; refusing to overwrite a locked manifest")
    p6c = json.loads(PHASE6C_MANIFEST.read_text(encoding="utf-8"))
    # dataset identity re-verified NOW against the Phase 6C record (train/validation only)
    unsw = ROOT / p6c["datasets"]["unsw"]["training_csv"]
    assert sha256_file(unsw) == p6c["datasets"]["unsw"]["training_sha256"], "UNSW training CSV hash differs from the Phase 6C record"
    for split, digest in p6c["datasets"]["ciciot"]["content_sha256"].items():
        assert sha256_gzip_content(ROOT / FG / f"{split}.csv.gz") == digest, f"CICIoT2023 {split} content hash differs"
    assert sha256_file(ROOT / FG / "preparation_metadata.json") == p6c["datasets"]["ciciot"]["metadata_sha256"]
    runs, order = [], 0
    for ds in DATASETS:
        for seed in SEEDS:
            for arm in NEW_ARMS:
                order += 1
                cfg = CFG_DIR / f"{ds}_{arm}.yaml"
                runs.append({"run_id": f"{ds}__{arm}__seed{seed}", "order": order, "dataset": ds, "arm": arm, "seed": seed,
                             "config": cfg.relative_to(ROOT).as_posix(), "config_sha256": sha256_text_file(cfg),
                             "out_dir": f"{OUT_ROOT}/{ds}/{arm}/seed_{seed}"})
    manifest = {
        "schema": 1, "created_utc": now_utc(), "version": VERSION,
        "purpose": "Table 4 controlled replacement arms E1-E4 (validation-only; reserved test data never loaded)",
        "git_commit_at_build": git_head(), "git_branch": "table4-controlled-v2", "code_fingerprint": fingerprint(),
        "seeds": SEEDS, "rounds": ROUNDS,
        "protocol_reference": {"manifest": "docs/phase6c/EXPERIMENT_MANIFEST.json", "manifest_sha256": p6c["manifest_sha256"],
                               "phase6c_code_fingerprint": p6c["code_fingerprint"],
                               "note": "same datasets, splits, seeds, model, training budget, matched traces, exposure-controlled attackers and audited metric rule as Phase 6C"},
        "datasets": {"unsw": {"training_csv": p6c["datasets"]["unsw"]["training_csv"], "training_sha256": p6c["datasets"]["unsw"]["training_sha256"],
                              "verified_at_build": True, "validation_protocol": p6c["datasets"]["unsw"]["validation_protocol"]},
                     "ciciot": {**p6c["datasets"]["ciciot"], "verified_at_build": True}},
        "locked_test": {},   # intentionally empty: this study never references, stats or hashes the reserved test files
        "locked_test_reference": "see docs/phase6c/EXPERIMENT_MANIFEST.json (not re-verified here: files not opened)",
        "arms": [{"arm": a, "role": v[1], "parent_locked_arm": v[0], "description": v[2], "declared_changes": v[3]} for a, v in NEW_ARMS.items()],
        "n_runs": len(runs), "runs": runs, "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS,
        "command": ["{python}", "scripts/phase6c/run_one.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "verify_training_semantics": True,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (DOC_DIR / "EXPERIMENT_MANIFEST.sha256").write_text(manifest["manifest_sha256"] + "\n", encoding="utf-8")
    print(f"runs: {len(runs)} | manifest sha256 {manifest['manifest_sha256']} | code fingerprint {manifest['code_fingerprint'][:16]} | commit {manifest['git_commit_at_build'][:8]}")


if __name__ == "__main__":
    main()
