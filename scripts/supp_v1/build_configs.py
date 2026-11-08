"""Step 1: derive every supplementary arm config from a LOCKED Phase 6C parent (read-only) and write the machine-readable design matrix.
usage: python scripts/supp_v1/build_configs.py     (refuses to overwrite a different existing config)"""
import copy
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import ARMS, CFG_DIR, DATASETS, DOC_DIR, OUT_ROOT, ROOT, VERSION, sha256_text_file  # noqa: E402

BOOKKEEPING = {"experiment.name", "experiment.method_name", "experiment.variant_name", "experiment.output_dir", "experiment.algorithm_version"}


def setpath(d, path, v):
    *ks, last = path.split(".")
    for k in ks:
        d = d[k]
    d[last] = v


def getpath(d, path):
    for k in path.split("."):
        d = d[k]
    return d


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict):
            o.update(flat(v, p + k + "."))
        else:
            o[p + k] = v
    return o


def main():
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for ds in DATASETS:
        for arm, a in ARMS.items():
            base = yaml.safe_load((ROOT / f"configs/phase6c/{ds}_{a['parent']}.yaml").read_text(encoding="utf-8"))
            c = copy.deepcopy(base)
            applied = {}
            for p, v in a["ch"].items():
                if isinstance(v, tuple) and v[0] == "x":          # relative to the dataset-specific parent value
                    v = round(float(getpath(base, p)) * v[1], 10)
                setpath(c, p, v)
                applied[p] = v
            c["experiment"].update(name=f"{VERSION}_{ds}_{arm}", method_name=arm, variant_name=arm, output_dir=OUT_ROOT, validation_only=True)
            c["data"]["test_csv"] = ""
            fa, fb = flat(base), flat(c)
            diff = {k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k)} - BOOKKEEPING
            assert diff == {k for k, v in applied.items() if fa.get(k) != v}, (arm, ds, diff, set(applied))   # a declared value equal to the parent's is allowed (no-op)
            text = (f"# {VERSION} arm '{arm}' ({ds}) [{a['family']}]: {a['desc']}\n# parent (locked Phase 6C): configs/phase6c/{ds}_{a['parent']}.yaml; "
                    f"only changes: {applied}\n# Locked by docs/supp_v1/EXPERIMENT_MANIFEST.json; do not edit.\n" + yaml.safe_dump(c, sort_keys=False))
            out = CFG_DIR / f"{ds}_{arm}.yaml"
            if out.exists() and out.read_text(encoding="utf-8") != text:
                sys.exit(f"refusing to overwrite a different existing config: {out}")
            out.write_text(text, encoding="utf-8")
            rows.append({"dataset": ds, "arm": arm, "family": a["family"], "parent_locked_arm": a["parent"], "description": a["desc"],
                         "declared_changes": str(applied), "config": out.relative_to(ROOT).as_posix(), "config_sha256": sha256_text_file(out),
                         "seeds": " ".join(map(str, a["seeds"][ds])), "timed_run": a["timed"]})
    with open(DOC_DIR / "SUPPLEMENTARY_DESIGN_MATRIX.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} configs")


if __name__ == "__main__":
    main()
