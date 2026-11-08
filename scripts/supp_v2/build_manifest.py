"""Step 2 (SUPP_V2): write the locked run manifest BEFORE any training. Refuses to overwrite. The reserved test files are never opened or hashed here.
Also records the SUPP_V1 manifest hash / code fingerprint so the V2 preflight can prove that SUPP_V1 was not altered."""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import (CFG_DIR, DESIGN, DOC_DIR, FG, MANIFEST, OUT_ROOT, PHASE6C_MANIFEST, ROOT, ROUNDS, V1_MANIFEST, VERSION,  # noqa: E402
                         DEFAULT_REQUIRED_ARTIFACTS, GATE_IDS, fingerprint, git_head, manifest_hash, now_utc, sha256_file, sha256_gzip_content, sha256_text_file, v1_fingerprint)


def main():
    if MANIFEST.exists():
        sys.exit(f"{MANIFEST} already exists; refusing to overwrite a locked manifest")
    p6c = json.loads(PHASE6C_MANIFEST.read_text(encoding="utf-8"))
    v1 = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    assert v1_fingerprint() == v1["code_fingerprint"], "SUPP_V1 code fingerprint no longer matches its locked manifest"
    assert sha256_file(ROOT / p6c["datasets"]["unsw"]["training_csv"]) == p6c["datasets"]["unsw"]["training_sha256"], "UNSW training CSV hash differs"
    for split, digest in p6c["datasets"]["ciciot"]["content_sha256"].items():
        assert sha256_gzip_content(ROOT / FG / f"{split}.csv.gz") == digest, f"CICIoT2023 {split} content hash differs"
    runs = []
    for d in sorted(DESIGN, key=lambda x: (x["order"], x["dataset"], x["arm"])):
        cfg = CFG_DIR / f"{d['dataset']}_{d['arm']}.yaml"
        for seed in d["seeds"]:
            rid = f"v2__{d['dataset']}__{d['arm']}__seed{seed}"
            runs.append({"run_id": rid, "family": d["family"], "dataset": d["dataset"], "arm": d["arm"], "seed": seed, "timed": False, "role": d["role"],
                         "v1_identity": f"{d['dataset']}__{d['arm']}__seed{seed}", "gate": rid in GATE_IDS,
                         "config": cfg.relative_to(ROOT).as_posix(), "config_sha256": sha256_text_file(cfg), "out_dir": f"{OUT_ROOT}/{d['dataset']}/{d['arm']}/seed_{seed}"})
    assert set(GATE_IDS) <= {r["run_id"] for r in runs}
    for i, r in enumerate(runs, 1):
        r["order"] = i
    manifest = {
        "schema": 1, "created_utc": now_utc(), "version": VERSION,
        "purpose": ("Corrective protocol for the 32 SUPP_V1 identities that could not be executed (30 CICIoT2023 participation runs: client holdout was missing for CICIoT2023; "
                    "2 chi_rec=0 runs: zero-weight-sum crash) plus the V1-to-V2 regression controls; validation-only"),
        "git_commit_at_build": git_head(), "git_branch": "main", "code_fingerprint": fingerprint(), "seeds": [12, 13, 14, 15, 16], "rounds": ROUNDS,
        "supersedes_nothing": "SUPP_V1 results, manifest, fingerprint and failure evidence are preserved unchanged; V2 runs are reported separately and joined by identity with a provenance column",
        "v1_reference": {"manifest": "docs/supp_v1/EXPERIMENT_MANIFEST.json", "manifest_sha256": v1["manifest_sha256"], "code_fingerprint": v1["code_fingerprint"],
                         "results_root": "results_supplementary_v1"},
        "source_overlay": {"dir": "src_v2", "modules_changed": ["data.py", "experiment.py"], "installed_by": "scripts/supp_v2/v2_overlay.py",
                           "changes": ["CICIoT2023 leakage-safe group-aware client holdout (shared fail-closed implementation, UNSW logic extracted verbatim)",
                                       "no-valid-contribution abstention when all retained raw weights are zero",
                                       "attempted-round vs noisy-release accounting columns; client_holdout_audit.json"]},
        "protocol_reference": {"manifest": "docs/phase6c/EXPERIMENT_MANIFEST.json", "manifest_sha256": p6c["manifest_sha256"], "phase6c_code_fingerprint": p6c["code_fingerprint"]},
        "datasets": {"unsw": {"training_csv": p6c["datasets"]["unsw"]["training_csv"], "training_sha256": p6c["datasets"]["unsw"]["training_sha256"], "verified_at_build": True,
                              "validation_protocol": p6c["datasets"]["unsw"]["validation_protocol"]},
                     "ciciot": {**p6c["datasets"]["ciciot"], "verified_at_build": True}},
        "locked_test": {}, "locked_test_reference": "see docs/phase6c/EXPERIMENT_MANIFEST.json (not re-verified here: files not opened)",
        "gate_run_ids": GATE_IDS, "n_runs": len(runs), "runs": runs,
        "required_artifacts": DEFAULT_REQUIRED_ARTIFACTS + ["v2_import_provenance.json", "client_holdout_audit.json"],
        "command": ["{python}", "scripts/supp_v2/run_one.py", "--config", "{config}", "--seed", "{seed}", "--out", "{out_dir}"],
        "verify_training_semantics": True,
    }
    manifest["manifest_sha256"] = manifest_hash(manifest)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    (DOC_DIR / "EXPERIMENT_MANIFEST.sha256").write_text(manifest["manifest_sha256"] + "\n", encoding="utf-8")
    print("runs:", len(runs), dict(Counter(r["family"] for r in runs)), "gate:", len(GATE_IDS), "| manifest sha256", manifest["manifest_sha256"][:16])


if __name__ == "__main__":
    main()
