"""Generate golden fixtures from the CURRENT (pre-path_policy) implementation. Run once before touching src/."""
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import table4_helpers as h
out = {"network": h.network_golden(), "e2e": {}}
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    for name, routing in h.E2E_CASES.items():
        cfg = h.make_config(td, routing=routing)
        df = h.run_tiny(cfg, td / name)
        out["e2e"][name] = h.e2e_signature(df)
(ROOT / "tests/fixtures/path_policy_golden.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("golden written;", {k: len(v) for k, v in out["e2e"].items()})
