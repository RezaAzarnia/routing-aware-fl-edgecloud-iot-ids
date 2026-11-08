"""Read-only: reports, for any manuscript .tex, whether each correction's anchor text is present (patch applicable) and whether its 'already applied' marker is present.
usage: python scripts/supp_final/check_anchors.py path/to/main.tex [more.tex ...]"""
import hashlib, re, sys
from pathlib import Path
CHECKS = [  # id, anchor (text to be replaced / located), applied-marker (present only after the patch)
 ("C1", "This lowers, but does not by itself bound, their influence", "has no effect on the applied weights there"),
 ("C2", "the corresponding raw weight is reduced", "sec:aggregation-weights"),
 ("C3", "The weight cap therefore does not prevent surrogate updates", "independently of \(n_i\) and of \(\chi_{\mathrm{rec}}\)"),
 ("C4", "Clipping + cap (selected)", "combined; selected"),
 ("C5", "The non-noise stages therefore represent", "combined non-noise change"),
 ("C6", "Accordingly, privacy-related utility changes must be", "were not separated"),
 ("C7", "Clipping, capped weighting, central Gaussian noise, and server", "evaluated as a bundle"),
 ("C8", "capped weighting", "uniform when at most ten"),
 ("C9", "Adversarial Robustness under Sign-flip Poisoning", "filter-aware attackers were not evaluated"),
 ("C10", "Routing and Network Performance Results on UNSW-NB15", "seeds 12--16 are reported in Section"),
 ("C11a", "can reach $p<0.05$", "exact sign-flip test cannot return"),
 ("C11b", "a two-sided exact\nsign-flip test has a minimum attainable", "unadjusted"),
 ("Z", "A versioned snapshot (release", "not included in this archive"),
]
def norm(s): return re.sub(r"\s+", " ", s)
for f in sys.argv[1:]:
    t = Path(f).read_bytes(); s = norm(t.decode("utf-8", "replace"))
    print(f"\n{f}  sha256={hashlib.sha256(t).hexdigest()[:16]}  bytes={len(t)}")
    z = re.findall(r"zenodo\.(\d+)", s); print("  Zenodo DOIs cited:", sorted(set(z)) or "none")
    for cid, a, m in CHECKS:
        n = s.count(norm(a)); ap = norm(m) in s
        print(f"  {cid:5} anchor x{n:<2} {'ALREADY APPLIED' if ap else ('apply' if n else 'ANCHOR MISSING - locate manually')}")
