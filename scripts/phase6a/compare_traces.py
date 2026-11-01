"""Check that the exogenous traces (client selection, network draws, failure draws, malicious
set) are identical between two runs, so only the privacy setting differs."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

a, b = Path(sys.argv[1]), Path(sys.argv[2])
na, nb = pd.read_csv(a / "network_metrics.csv"), pd.read_csv(b / "network_metrics.csv")
keys = ["round", "client_id", "edge_id", "pdr", "update_delivered", "end_to_end_delay_ms", "path_stability",
        "expected_pdr", "delivery_draw", "explicit_failure_draw", "explicit_client_failure", "failure_reason"]
same_rows = len(na) == len(nb)
col_equal = {}
for k in keys:
    if same_rows:
        x, y = na[k], nb[k]
        col_equal[k] = bool(((x == y) | (x.isna() & y.isna())).all())
    else:
        col_equal[k] = False
mal = json.loads((a / "malicious_clients.json").read_text()) == json.loads((b / "malicious_clients.json").read_text())
out = {"rows_equal_length": same_rows, "network_rows": [len(na), len(nb)], "columns_identical": col_equal,
       "malicious_set_identical": mal,
       "all_exogenous_traces_identical": bool(same_rows and all(col_equal.values()) and mal)}
print(json.dumps(out, indent=1))
