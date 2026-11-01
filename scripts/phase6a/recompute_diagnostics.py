"""Recompute phase6a_diagnostics.json from saved run logs (no training)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_validation_only import diagnostics  # noqa: E402
from src.config import Config  # noqa: E402

for run in sys.argv[1:]:
    run = Path(run)
    cfg = Config.from_yaml(run / "resolved_config.yaml")
    diag = diagnostics(run, cfg)
    diag["resources"] = json.loads((run / "resource_usage.json").read_text())
    (run / "phase6a_diagnostics.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    u = diag["updates"]
    print(run.parent.parent.name, "effective malicious kept/rejected:", u["effective_malicious_updates_kept"], u["effective_malicious_updates_rejected"], "| benign real rejected:", u["benign_real_rows_rejected"])
