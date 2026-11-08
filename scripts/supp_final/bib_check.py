"""Read-only structural bibliography check: citation keys used in main.tex vs entries in references.bib. Does NOT verify that cited sources support the claims.
usage: python scripts/supp_final/bib_check.py main.tex references.bib [out.md]"""
import re
import sys
from pathlib import Path

tex = Path(sys.argv[1]).read_text(encoding="utf-8")
bib = Path(sys.argv[2]).read_text(encoding="utf-8")
cites = sorted({k.strip() for m in re.findall(r"\\cite[a-z]*\{([^}]*)\}", tex) for k in m.split(",")})
ents = re.findall(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@|\Z)", bib, flags=re.S)
keys = [e[1] for e in ents]
rows = []
for typ, key, body in ents:
    f = lambda n: bool(re.search(n + r"\s*=", body, re.I))  # noqa: E731
    rows.append((key, typ, f("author"), f("title"), f("year"), f("doi"), f("url")))
undefined = sorted(set(cites) - set(keys))
uncited = sorted(set(keys) - set(cites))
dups = sorted({k for k in keys if keys.count(k) > 1})
out = ["# Bibliography structural check (local, offline)", "",
       f"- main.tex file checked: `{sys.argv[1]}`; entries in references.bib: {len(ents)}; distinct keys cited: {len(cites)}",
       f"- undefined citation keys: {undefined or 'none'}", f"- uncited bib entries: {uncited or 'none'}", f"- duplicate bib keys: {dups or 'none'}",
       f"- entries without DOI: {sum(1 for r in rows if not r[5])} of {len(rows)}; without DOI and URL: {[r[0] for r in rows if not r[5] and not r[6]] or 'none'}",
       f"- entries missing author/title/year: {[r[0] for r in rows if not (r[2] and r[3] and r[4])] or 'none'}", "",
       "**Not verified:** that each reference exists as listed, that DOIs resolve, or that the cited work supports the sentence citing it (needs author/human verification; reviewer comments 1 and 16 stay PARTIAL).", "",
       "| key | type | author | title | year | doi | url |", "|---|---|---|---|---|---|---|"]
out += [f"| {r[0]} | {r[1]} | {'y' if r[2] else 'N'} | {'y' if r[3] else 'N'} | {'y' if r[4] else 'N'} | {'y' if r[5] else '-'} | {'y' if r[6] else '-'} |" for r in rows]
text = "\n".join(out) + "\n"
if len(sys.argv) > 3:
    Path(sys.argv[3]).write_text(text, encoding="utf-8")
print("\n".join(out[:9]))
