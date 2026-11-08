"""Step 2: write the locked run manifest BEFORE any training. Refuses to overwrite. The reserved test files are never opened or hashed here."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import (ARMS, CFG_DIR, DATASETS, DOC_DIR, FG, MANIFEST, OUT_ROOT, PHASE6C_MANIFEST, ROOT, ROUNDS, VERSION,  # noqa: E402
                         DEFAULT_REQUIRED_ARTIFACTS, fingerprint, git_head, manifest_hash, now_utc, sha256_file, sha256_gzip_content, sha256_text_file)


def main():
    if MANIFEST.exists():
        sys.exit(f"{MANIFEST} already exists; refusing to overwrite a locked manifest")
    p6c = json.loads(PHASE6C_MANIFEST.read_text(encoding="utf-8"))
    assert sha256_file(ROOT / p6c["datasets"]["unsw"]["training_csv"]) == p6c["datasets"]["unsw"]["training_sha256"], "UNSW training CSV hash differs"
    for split, digest in p6c["datasets"]["ciciot"]["content_sha256"].items():
        assert sha256_gzip_content(ROOT / FG / f"{split}.csv.gz") == digest, f"CICIoT2023 {split} content hash differs"
    assert sha256_file(ROOT / FG / "preparation_metadata.json") == p6c["datasets"]["ciciot"]["metadata_sha256"]
    runs = []
    for arm, a in sorted(ARMS.items(), key=lambda kv: (kv[1]["order"], kv[0])):
        for ds in DATASETS:
            for seed in a["seeds"][ds]:
                cfg = CFG_DIR / f"{ds}_{arm}.yaml"
                runs.append({"run_id": f"{ds}__{arm}__seed{seed}", "family": a["family"], "dataset": ds, "arm": arm, "seed": seed, "timed": a["timed"],
                             "config": cfg.relative_to(ROOT).as_posix(), "config_sha256": sha256_text_file(cfg),
                             "out_dir": f"{OUT_ROOT}/{ds}/{arm}/seed_{seed}"})
    for i, r in enumerate(runs, 1):
        r["order"] = i
    manifest = {
        "schema": 1, "created_utc": now_utc(), "version": VERSION,
        "purpose": "Supplementary reviewer-response experiments (attack robustness, sensitivity, scalability, routing x surrogate interaction, participation bias); validation-only",
        "git_commit_at_build": git_head(), "git_branch": "main", "code_fingerprint": fingerprint(), "seeds": [12, 13, 14, 15, 16], "rounds": ROUNDS,
        "protocol_reference": {"manifest": "docs/phase6c/EXPERIMENT_MANIFEST.json", "manifest_sha256": p6c["manifest_sha256"],
                               "phase6c_code_fingerprint": p6c["code_fingerprint"],
                               "note": "same datasets, splits, model, training budget, matched traces and audited metric rule as Phase 6C / Table 4 v2"},
        "datasets": {"unsw": {"training_csv": p6c["datasets"]["unsw"]["training_csv"], "training_sha256": p6c["datasets"]["unsw"]["training_sha256"],
                              "verified_at_build": True, "validation_protocol": p6c["datasets"]["unsw"]["validation_protocol"]},
                     "ciciot": {**p6c["datasets"]["ciciot"], "verified_at_build": True}},
        "locked_test": {}, "locked_test_reference": "see docs/phase6c/EXPERIMENT_MANIFEST.json (not re-verified here: files not opened)",
        "arms": [{"arm": k, "family": v["family"], "parent_locked_arm": v["parent"], "description": v["desc"], "timed": v["timed"]} for k, v in ARMS.items()],
        "n_runs": len(runs), "runs": runs, "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS,
        "command": ["{python}", "scripts/phase6c/run_one.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "command_timed": ["{python}", "scripts/supp_v1/timed_run.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "verify_training_semantics": True,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (DOC_DIR / "EXPERIMENT_MANIFEST.sha256").write_text(manifest["manifest_sha256"] + "\n", encoding="utf-8")
    from collections import Counter
    print("runs:", len(runs), dict(Counter(r["family"] for r in runs)), "| manifest sha256", manifest["manifest_sha256"][:16])


if __name__ == "__main__":
    main()
