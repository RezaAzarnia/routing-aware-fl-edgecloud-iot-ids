"""Step 1 (SUPP_V2): derive each V2 config from the LOCKED SUPP_V1 config of the same (dataset, arm); only experiment.name / experiment.output_dir may differ (asserted).
The V1 files are only read. Refuses to overwrite a different existing V2 config.   usage: python scripts/supp_v2/build_configs.py"""
import csv
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import BOOKKEEPING, CFG_DIR, DESIGN, DOC_DIR, OUT_ROOT, ROOT, V1_CFG_DIR, VERSION, sha256_text_file  # noqa: E402


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
    done = set()
    for d in DESIGN:
        key = (d["dataset"], d["arm"])
        if key in done:
            continue
        done.add(key)
        src = V1_CFG_DIR / f"{d['dataset']}_{d['arm']}.yaml"
        raw_text = src.read_text(encoding="utf-8")
        base = yaml.safe_load(raw_text)
        c = yaml.safe_load(raw_text)
        c["experiment"]["name"] = f"{VERSION}_{d['dataset']}_{d['arm']}"
        c["experiment"]["output_dir"] = OUT_ROOT
        diff = {k for k in set(flat(base)) | set(flat(c)) if flat(base).get(k) != flat(c).get(k)}
        assert diff <= BOOKKEEPING, (key, diff)
        comment = [ln for ln in raw_text.splitlines() if ln.startswith("#")][:2]
        text = (f"# {VERSION} [{d['family']}] {d['dataset']} / {d['arm']}: {d['role']}\n"
                f"# identical to the locked SUPP_V1 config {src.relative_to(ROOT).as_posix()} (sha256 {sha256_text_file(src)[:16]}) except experiment.name / experiment.output_dir\n"
                + "\n".join(comment) + "\n# Locked by docs/supp_v2/EXPERIMENT_MANIFEST.json; do not edit.\n" + yaml.safe_dump(c, sort_keys=False))
        out = CFG_DIR / f"{d['dataset']}_{d['arm']}.yaml"
        if out.exists() and out.read_text(encoding="utf-8") != text:
            sys.exit(f"refusing to overwrite a different existing config: {out}")
        out.write_text(text, encoding="utf-8")
        rows.append({"dataset": d["dataset"], "arm": d["arm"], "family": d["family"], "role": d["role"], "v1_config": src.relative_to(ROOT).as_posix(),
                     "v1_config_sha256": sha256_text_file(src), "config": out.relative_to(ROOT).as_posix(), "config_sha256": sha256_text_file(out),
                     "seeds": " ".join(map(str, d["seeds"])), "v1_status": d["v1"]})
    with open(DOC_DIR / "SUPP_V2_DESIGN_MATRIX.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} configs")


if __name__ == "__main__":
    main()
