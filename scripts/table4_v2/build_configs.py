"""Step 1: derive the four new arm configs from LOCKED Phase 6C parent configs (read-only) and write the machine-readable method matrix.
usage: python scripts/table4_v2/build_configs.py        (refuses to overwrite existing different configs)"""
import copy
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t4_common import (COMPARATORS, CFG_DIR, DATASETS, DOC_DIR, NEW_ARMS, OUT_ROOT, ROOT, VERSION, sha256_text_file)  # noqa: E402


def getpath(d, path):
    for k in path.split("."):
        d = d[k]
    return d


def setpath(d, path, v):
    *ks, last = path.split(".")
    for k in ks:
        d = d[k]
    d[last] = v


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict):
            o.update(flat(v, p + k + "."))
        else:
            o[p + k] = v
    return o


BOOKKEEPING = {"experiment.name", "experiment.method_name", "experiment.variant_name", "experiment.output_dir", "experiment.algorithm_version"}


def main():
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    matrix = []
    for ds in DATASETS:
        for arm, (parent, role, desc, ch) in NEW_ARMS.items():
            base = yaml.safe_load((ROOT / f"configs/phase6c/{ds}_{parent}.yaml").read_text(encoding="utf-8"))
            c = copy.deepcopy(base)
            for p, v in ch.items():
                setpath(c, p, v)
            c["experiment"].update(name=f"{VERSION}_{ds}_{arm}", method_name=arm, variant_name=arm, output_dir=OUT_ROOT,
                                   algorithm_version="reference_v1_historical", validation_only=True)
            c["data"]["test_csv"] = ""
            # each arm differs from its parent ONLY in the declared fields (+ bookkeeping)
            fa, fb = flat(base), flat(c)
            diff = {k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k)} - BOOKKEEPING
            assert diff == set(ch), (arm, ds, diff, set(ch))
            text = (f"# {VERSION} arm '{arm}' ({ds}) [{role}]: {desc}\n# parent (locked Phase 6C): configs/phase6c/{ds}_{parent}.yaml; "
                    f"only changes: {ch}\n# Locked by docs/table4_v2/EXPERIMENT_MANIFEST.json; do not edit.\n" + yaml.safe_dump(c, sort_keys=False))
            out = CFG_DIR / f"{ds}_{arm}.yaml"
            if out.exists() and out.read_text(encoding="utf-8") != text:
                sys.exit(f"refusing to overwrite a different existing config: {out}")
            out.write_text(text, encoding="utf-8")
    # method matrix: new arms + existing comparators, both datasets
    sys.path.insert(0, str(ROOT))
    from src.privacy import calibrate_noise_multiplier

    def row(ds, arm, role, parent, cfg_path, ch):
        c = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        r, a, p, f, fl, at = c["routing"], c["aggregation"], c["privacy"], c["failure"], c["fl"], c["attack"]
        enabled = r["enabled"]
        pp = r.get("path_policy", "default")
        eff_path = (("routed" if enabled else "random_shared_rng_historical") if pp == "default" else pp)
        eff_sel = r.get("selection_policy", "top_k") if enabled else "uniform_random_shared_rng_historical"
        dp = p["mode"] == "central_client"
        sigma = ""
        if dp and p.get("auto_calibrate_noise") and p.get("target_epsilon"):
            sigma = round(calibrate_noise_multiplier(float(p["target_epsilon"]), int(fl["rounds"]), float(p["delta"]),
                                                     float(fl["clients_per_round"]) / float(fl["num_clients"])), 6)
        return {
            "dataset": ds, "arm": arm, "role": role, "parent_locked_arm": parent, "config": cfg_path.relative_to(ROOT).as_posix(),
            "config_sha256": sha256_text_file(cfg_path), "declared_changes_vs_parent": str(ch) if ch else "none (existing locked arm, not re-run)",
            "client_selection": eff_sel, "path_assignment": eff_path, "routing_enabled_flag": enabled,
            "aggregation": a["method"], "mad_filter_on_received_updates": a["method"] == "distance_filter", "distance_k": a["distance_k"],
            "surrogate_recovery": f["recovery_enabled"], "surrogate_handling": a.get("surrogate_handling", "reference"),
            "surrogate_total_weight_cap": f.get("surrogate_total_weight_cap"), "client_weighting": fl.get("weighting", "sample_proportional"),
            "central_gaussian_dp": dp, "clip_norm": p["clip_norm"] if dp else "n/a (no DP)", "client_weight_cap": p["max_client_weight_share"] if dp else "n/a (no DP)",
            "target_epsilon_diagnostic": p["target_epsilon"] if dp else "n/a", "calibrated_noise_multiplier": sigma if dp else "n/a",
            "accountant_sample_rate_assumed": fl["clients_per_round"] / fl["num_clients"] if dp else "n/a",
            "server_learning_rate": fl["server_learning_rate"], "server_momentum": fl["server_momentum"],
            "attack": f'{at["attack_type"]} x{at["attack_scale"]}, fraction {at["malicious_fraction"]}, assignment {at["assignment"]}',
            "failure": f'enabled={f["enabled"]}, explicit p={f["client_failure_probability"]}',
            "delivery_model": r.get("delivery_model", "independent_draws"), "trace_mode": r.get("trace_mode", "sequential"), "clients_selected_per_round": fl["clients_per_round"],
            "num_clients": fl["num_clients"], "rounds": fl["rounds"], "local_epochs": fl["local_epochs"], "dirichlet_alpha": fl["dirichlet_alpha"],
            "evaluation_partition": "report partition of locked three-way validation split; test never loaded",
        }
    for ds in DATASETS:
        for arm in COMPARATORS:
            matrix.append(row(ds, arm, "existing locked comparator", arm, ROOT / f"configs/phase6c/{ds}_{arm}.yaml", None))
        for arm, (parent, role, desc, ch) in NEW_ARMS.items():
            matrix.append(row(ds, arm, role, parent, CFG_DIR / f"{ds}_{arm}.yaml", ch))
    with open(DOC_DIR / "TABLE4_V2_METHOD_MATRIX.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(matrix[0]))
        w.writeheader()
        w.writerows(matrix)
    print(f"{len(NEW_ARMS) * len(DATASETS)} configs, {len(matrix)} matrix rows")


if __name__ == "__main__":
    main()
