"""Compare the local raw CICIoT2023 manifest with a third-party per-file SHA-256 manifest.

Matching establishes byte-equivalence with that third-party release only; it does not
authenticate official-provider provenance.
"""
import json
import sys
from pathlib import Path

import pandas as pd

local = pd.read_csv(sys.argv[1])
ext = json.load(open(sys.argv[2], encoding="utf-8"))
out = Path(sys.argv[3])
local["rel"] = local["path"].str.replace("\\", "/", regex=False)
ext_df = pd.DataFrame(
    [{"rel": k.split("CSV/", 1)[1], **v} for k, v in ext.items()]
).rename(columns={"sha256": "ext_sha256", "size_bytes": "ext_size", "n_rows": "ext_rows",
                  "n_missing_cells": "ext_nan", "n_inf_cells": "ext_inf", "n_columns": "ext_ncols"})
merged = local.merge(ext_df, on="rel", how="outer", indicator=True)
only_local = merged[merged["_merge"] == "left_only"]
only_ext = merged[merged["_merge"] == "right_only"]
both = merged[merged["_merge"] == "both"].copy()
both["sha_ok"] = both["sha256"] == both["ext_sha256"]
both["size_ok"] = both["size"] == both["ext_size"]
both["rows_ok"] = both["rows"] == both["ext_rows"]
both["nan_ok"] = both["nan"] == both["ext_nan"]
both["inf_ok"] = both["inf"] == both["ext_inf"]
both["cols_ok"] = both["ncols"] == both["ext_ncols"]
summary = {
    "local_files": int(len(local)), "external_files": int(len(ext_df)),
    "paths_in_both": int(len(both)),
    "local_only_paths": only_local["rel"].tolist(), "external_only_paths": only_ext["rel"].tolist(),
    "sha256_matches": int(both["sha_ok"].sum()), "size_matches": int(both["size_ok"].sum()),
    "row_matches": int(both["rows_ok"].sum()), "nan_matches": int(both["nan_ok"].sum()),
    "inf_matches": int(both["inf_ok"].sum()), "ncols_matches": int(both["cols_ok"].sum()),
    "local_total_rows_unique_paths_in_both": int(both["rows"].sum()),
    "external_total_rows": int(ext_df["ext_rows"].sum()),
    "external_total_nan": int(ext_df["ext_nan"].sum()), "external_total_inf": int(ext_df["ext_inf"].sum()),
    "classes_external": sorted({r.split("/")[0] for r in ext_df["rel"]}),
}
summary["verdict"] = (
    "EXACT_MATCH"
    if summary["sha256_matches"] == summary["external_files"] == summary["paths_in_both"]
    else "PARTIAL_MATCH" if summary["sha256_matches"] > 0 else "NOT_VERIFIED"
)
out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
both[~(both.sha_ok & both.size_ok & both.rows_ok)][["rel"]].to_csv(out.with_suffix(".mismatches.csv"), index=False)
print(json.dumps(summary, indent=1)[:2500])
