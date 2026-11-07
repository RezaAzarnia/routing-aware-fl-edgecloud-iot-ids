"""Resumable runner for the controlled-ablation v2 runs (validation-only; never touches test files).
usage: python scripts/ablation_v2/run_ablation.py --arms a,b --datasets unsw,ciciot --seeds 12,13
A run is COMPLETE only if ablation_COMPLETE.json exists and its recorded artifact hashes still verify."""
import argparse, hashlib, json, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase6c"))
from p6c_common import code_fingerprint, git_head, sha256_text_file  # noqa: E402
OUT = ROOT / "results_ablation_controlled_v2"
ART = ["round_metrics.csv", "network_metrics.csv", "aggregation_diagnostics.csv", "final_validation_metrics.json",
       "resolved_config.yaml", "run_record.json", "phase6c_diagnostics.json", "attacker_assignment.csv"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def is_complete(d):
    f = d / "ablation_COMPLETE.json"
    if not f.exists(): return False
    try: rec = json.loads(f.read_text())
    except Exception: return False
    return all((d / k).exists() and sha(d / k) == v for k, v in rec["artifact_sha256"].items())
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True); ap.add_argument("--datasets", default="ciciot,unsw")
    ap.add_argument("--seeds", default="12,13,14,15,16")
    a = ap.parse_args()
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    for ds in a.datasets.split(","):
        for arm in a.arms.split(","):
            for seed in map(int, a.seeds.split(",")):
                d = OUT / "runs" / ds / arm / f"seed_{seed}"
                if is_complete(d): print("SKIP complete", d.relative_to(ROOT)); continue
                if d.exists() and not (d / "ablation_COMPLETE.json").exists():
                    # partial directory from an interrupted attempt: keep it, restart under a new name
                    d.rename(d.with_name(f"seed_{seed}_partial_{int(time.time())}"))
                cfg = ROOT / f"configs/ablation_v2/{ds}_{arm}.yaml"
                t = time.time()
                log = OUT / "logs" / f"{ds}__{arm}__seed{seed}.log"
                r = subprocess.run([sys.executable, str(ROOT / "scripts/phase6c/run_one.py"), "--config", str(cfg),
                                    "--seed", str(seed), "--out", str(d)], cwd=ROOT, capture_output=True, text=True)
                log.write_text(r.stdout + "\n--- STDERR ---\n" + r.stderr, encoding="utf-8")
                if r.returncode != 0 or any(not (d / k).exists() for k in ART):
                    print("FAILED", ds, arm, seed, "see", log); continue
                rec = {"dataset": ds, "arm": arm, "seed": seed, "config": str(cfg.relative_to(ROOT)),
                       "config_sha256": sha256_text_file(cfg), "git_head": git_head(), "code_fingerprint": code_fingerprint(),
                       "wall_seconds": round(time.time() - t, 1), "artifact_sha256": {k: sha(d / k) for k in ART}}
                (d / "ablation_COMPLETE.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
                print("OK", ds, arm, seed, rec["wall_seconds"], "s")
if __name__ == "__main__": main()
