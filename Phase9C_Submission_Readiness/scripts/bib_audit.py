"""Exact bibliography inventory: entries in the .bib, keys cited in the LaTeX sources, uncited entries, undefined citations, and the printed reference list
(.bbl) size. Read-only.  python Phase9C_Submission_Readiness/scripts/bib_audit.py"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P9 = ROOT / "Phase9_Manuscript_Revision"
tex = "".join((P9 / f).read_text(encoding="utf-8") for f in ("latex/main.tex", "sections/related_work.tex"))
bib = (P9 / "bibliography" / "verified_references.bib").read_text(encoding="utf-8")
keys = re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib)
cited = []
for m in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", tex):
    cited += [k.strip() for k in m.group(1).split(",") if k.strip()]
cited_set = set(cited)
bbl = P9 / "latex" / "main.bbl"
printed = len(re.findall(r"\\bibitem", bbl.read_text(encoding="utf-8"))) if bbl.exists() else None
res = {"bib_entries": len(keys), "bib_unique_keys": len(set(keys)), "cite_commands_keys_total": len(cited), "distinct_cited_keys": len(cited_set),
       "cited_and_defined": len(cited_set & set(keys)), "undefined_citations": sorted(cited_set - set(keys)), "uncited_entries": sorted(set(keys) - cited_set),
       "printed_in_bbl": printed}
res["consistent"] = (res["bib_entries"] == res["cited_and_defined"] + len(res["uncited_entries"])) and not res["undefined_citations"] and (printed in (None, res["distinct_cited_keys"]))
print(json.dumps(res, indent=1))
