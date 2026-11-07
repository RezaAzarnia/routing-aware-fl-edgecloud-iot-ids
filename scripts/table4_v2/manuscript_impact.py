"""Read-only dependency analysis: which manuscript statements depend on the OLD (unsourced) Table 4 values.
usage: python scripts/table4_v2/manuscript_impact.py path/to/main.tex [more.tex ...] > impact.json
Nothing is modified. Dependencies are derived from LaTeX labels/references and from the CONTENT (numbers and method names), not from figure numbers."""
import json
import re
import sys
from pathlib import Path

METHOD_PATTERNS = {"FedAvg": r"\bFedAvg\b", "DP+FedAvg": r"DP\+FedAvg", "Robust no-DP": r"Robust no-DP", "Proposed eps~10": r"varepsilon\s*\\?approx\s*10|ε\s*≈\s*10",
                   "Proposed eps~20": r"varepsilon\s*\\?approx\s*20|ε\s*≈\s*20", "Modular Edge FL-inspired": r"Modular Edge FL", "MCHFL-style": r"MCHFL"}
SECTION_RE = re.compile(r"\\(sub)*section\*?\{([^}]*)\}")


def strip_comment(line):
    return re.sub(r"(?<!\\)%.*$", "", line)


def analyse(path: Path):
    lines = [strip_comment(l) for l in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    text = "\n".join(lines)
    out = {"file": str(path), "lines": len(lines)}
    # locate Table 4 (overall-results) and parse its numbers
    start = next((i for i, l in enumerate(lines) if "label{tab:overall-results}" in l), None)
    values = {}
    if start is not None:
        block = "\n".join(lines[start:start + 90])
        parts = re.split(r"\\textit\{(?:CICIoT2023|UNSW-NB15)\}", block)[1:]
        names = ["FedAvg", "DP+FedAvg", "Robust no-DP", "Proposed eps~10", "Proposed eps~20"]
        for ds, part in zip(("CICIoT2023", "UNSW-NB15"), parts):
            nums = re.findall(r"&\s*([0-9]+\.[0-9]+)", part)
            for n, i in zip(names, range(0, 35, 7)):
                values[f"{ds}|{n}"] = [float(x) for x in nums[i:i + 7]]
    out["table4_found_at_line"] = None if start is None else start + 1
    out["table4_values"] = values
    # section map
    sec, sections = "(front matter)", {}
    for i, l in enumerate(lines):
        m = SECTION_RE.search(l)
        if m:
            sec = m.group(2).strip()
        sections.setdefault(sec, []).append(i + 1)
    where = lambda ln: next((s for s, v in sections.items() if v[0] <= ln <= v[-1]), "?")   # noqa: E731
    def section_of(ln):
        best, best_start = "(front matter)", -1
        for s, v in sections.items():
            if v[0] <= ln and v[0] > best_start:
                best, best_start = s, v[0]
        return best
    # (1) every reference to the table
    out["refs_to_table4"] = [{"line": i + 1, "section": section_of(i + 1), "text": l.strip()[:200]} for i, l in enumerate(lines) if "ref{tab:overall-results}" in l]
    # (2) derived percentages and any Table 4 value quoted in running text
    pct = re.compile(r"\\\(\s*([0-9]+\.[0-9])\s*\\%\s*\\\)|([0-9]+\.[0-9])\s*\\%")
    quoted = []
    vals = {v for arr in values.values() for v in arr}
    for i, l in enumerate(lines):
        if start is not None and start <= i < start + 90:
            continue
        for m in pct.finditer(l):
            quoted.append({"line": i + 1, "section": section_of(i + 1), "kind": "percentage", "value": m.group(1) or m.group(2), "text": l.strip()[:220]})
        for m in re.finditer(r"(?<![0-9.])([0-9]\.[0-9]{4})(?![0-9])", l):
            if float(m.group(1)) in vals:
                quoted.append({"line": i + 1, "section": section_of(i + 1), "kind": "table4 value", "value": m.group(1), "text": l.strip()[:220]})
    out["quoted_numbers"] = quoted
    # (3) figures: caption + whether it names Table-4 methods / is referenced next to Table 4 statements
    figs = []
    for m in re.finditer(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", text, re.S):
        blk = m.group(0)
        ln = text[:m.start()].count("\n") + 1
        lab = re.search(r"\\label\{([^}]*)\}", blk)
        gfx = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", blk, re.S)
        cap = re.search(r"\\caption\{(.*?)\}\s*(?:\\label|\\end)", blk, re.S)
        cap_t = re.sub(r"\s+", " ", cap.group(1)) if cap else ""
        figs.append({"line": ln, "label": lab.group(1) if lab else None, "file": gfx.group(1) if gfx else None, "caption": cap_t[:260]})
    for f in figs:
        refs = [i + 1 for i, l in enumerate(lines) if f["label"] and f"ref{{{f['label']}}}" in l]
        ctx = " ".join(" ".join(lines[max(0, r - 4):r + 4]) for r in [x - 1 for x in refs])
        f["referenced_at_lines"] = refs
        f["methods_named_in_caption_or_context"] = [k for k, p in METHOD_PATTERNS.items() if re.search(p, f["caption"] + " " + ctx)]
        f["mentions_table4_in_context"] = "tab:overall-results" in ctx
    out["figures"] = figs
    # (4) method mentions by section
    mm = {}
    for k, p in METHOD_PATTERNS.items():
        mm[k] = sorted({section_of(i + 1) for i, l in enumerate(lines) if re.search(p, l)})
    out["method_mentions_by_section"] = mm
    # (5) Table 3 content that can depend on the Table 4 experiments
    t3 = next((i for i, l in enumerate(lines) if "label{tab:framework-parameters}" in l), None)
    out["table3_found_at_line"] = None if t3 is None else t3 + 1
    out["table3_rows_of_interest"] = [{"line": i + 1, "text": l.strip()[:160]} for i, l in enumerate(lines[t3:t3 + 140], start=t3)
                                       if re.search(r"seed|Target privacy|noise multiplier|Calibrated|Clipping|Failure|Main comparison|Privacy mechanism|Failure recovery", l, re.I)] if t3 is not None else []
    # (6) abstract/conclusion sentences with numbers
    def block_between(a, b):
        ia = next((i for i, l in enumerate(lines) if re.search(a, l)), None)
        ib = next((i for i, l in enumerate(lines) if ia is not None and i > ia and re.search(b, l)), None)
        return (ia, ib)
    for name, (a, b) in {"abstract": (r"\\begin\{abstract\}", r"\\end\{abstract\}"), "conclusion": (r"\\section\{Conclusion\}", r"Code Availability")}.items():
        ia, ib = block_between(a, b)
        seg = " ".join(lines[ia:ib]) if ia is not None and ib is not None else ""
        sents = [s.strip() for s in re.split(r"(?<=[.])\s+", re.sub(r"\s+", " ", seg)) if re.search(r"\d", s)]
        out[f"{name}_sentences_with_numbers"] = sents
    # (7) privacy-cost table, failure figure, seeds statements
    out["privacy_cost_table_line"] = next((i + 1 for i, l in enumerate(lines) if "label{tab:privacy-cost}" in l), None)
    out["seed_statements"] = [{"line": i + 1, "text": l.strip()[:200]} for i, l in enumerate(lines) if re.search(r"independent seeds|at least three|seed", l, re.I) and "includegraphics" not in l][:12]
    out["test_set_statements"] = [{"line": i + 1, "text": l.strip()[:200]} for i, l in enumerate(lines) if re.search(r"test set|test file|applied unchanged|official test|validation-only|held-out", l, re.I)][:15]
    return out


if __name__ == "__main__":
    print(json.dumps([analyse(Path(p)) for p in sys.argv[1:]], indent=1, ensure_ascii=False))
