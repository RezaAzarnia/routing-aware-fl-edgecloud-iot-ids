"""Assembles FINAL_MANUSCRIPT_MANUAL_EDIT_PACKAGE (+ .zip, SHA-256 inventory) from existing verified files. Copies only; modifies no source file, result or manuscript.
usage: python scripts/supp_final/build_edit_package.py"""
import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S = ROOT / "Supplementary_Experiments_Package"
NAME = "FINAL_MANUSCRIPT_MANUAL_EDIT_PACKAGE"
OUT = ROOT / "_package_build" / NAME
ZIP = ROOT / f"{NAME}.zip"
if OUT.parent.exists():
    shutil.rmtree(OUT.parent)
OUT.mkdir(parents=True)

# fix evidence path labels in the justification file (copy only)
just = (S / "CORRECTIONS_JUSTIFICATION_AND_PRIORITY.md").read_text(encoding="utf-8")
just = just.replace("`04_findings/chi0_abstention` (T6)", "`02_supplementary_evidence/TABLE_T6_chi0_abstention.csv`").replace("`figures/FIG1_*`", "`04_figures/FIG1_*`")
just = just.replace("`TABLE_T1_attack.csv`", "`02_supplementary_evidence/TABLE_T1_attack.csv`").replace("`TABLE_T3_interaction.csv`", "`02_supplementary_evidence/TABLE_T3_interaction.csv`")
just = just.replace("`STATISTICAL_INFERENCE_NOTE.md` (UNSW", "`03_statistics/STATISTICAL_INFERENCE_NOTE.md` (UNSW").replace("`FINAL_SCIENTIFIC_QA_REPORT.md` check 6", "`06_provenance_and_verification/FINAL_SCIENTIFIC_QA_REPORT.md` check 6")


def put(src, dst_dir, name=None, text=None):
    d = OUT / dst_dir
    d.mkdir(parents=True, exist_ok=True)
    if text is not None:
        (d / name).write_text(text, encoding="utf-8")
    else:
        shutil.copy2(src, d / (name or Path(src).name))


for f in ("START_HERE.md", "EDITING_ORDER.md"):
    put(S / f, ".")
M = "01_manuscript_corrections"
for f in ("MANUSCRIPT_PATCHES_C1_C11_ANCHORED.tex", "MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex", "MANUSCRIPT_READINESS_MAP.md", "MANUSCRIPT_INTEGRATION_CHECKLIST.md", "MAIN_VS_SUPPLEMENTARY.md", "FIGURES_3_6_SEED_PROVENANCE.md"):
    put(S / f, M)
put(None, M, "CORRECTIONS_JUSTIFICATION_AND_PRIORITY.md", text=just)
E_ = "02_supplementary_evidence"
for f in ("SUPPLEMENTARY_EXPERIMENTS_FINAL_REPORT.md", "SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv", "SUPPLEMENTARY_EXPERIMENTS_SUMMARY.csv", "SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv", "SUPPLEMENTARY_HOLDOUT_CLIENT_METRICS.csv",
          "SUPPLEMENTARY_HOLDOUT_PER_CLIENT.csv", "SUPPLEMENTARY_WEIGHT_AUDIT_FINAL.csv", "V2_ABSTENTION_AND_ACCOUNTING_PER_RUN.csv", "GENERATED_TABLES.md",
          "TABLE_T1_attack.csv", "TABLE_T2_sensitivity.csv", "TABLE_T3_interaction.csv", "TABLE_T4_participation.csv", "TABLE_T5_scalability.csv", "TABLE_T6_chi0_abstention.csv"):
    put(S / f, E_)
put(S / "STATISTICAL_INFERENCE_NOTE.md", "03_statistics")
for p in sorted((S / "figures").iterdir()):
    put(p, "04_figures")
put(S / "FIGURE_CAPTIONS_PUBLICATION_READY.md", "04_figures")
for p in sorted((S / "audits").iterdir()):
    if p.suffix in (".csv", ".log") and p.name != "":
        put(p, "05_audits")
P_ = "06_provenance_and_verification"
for f in ("FINAL_SCIENTIFIC_QA_REPORT.md", "FINAL_QA_RESULTS.json", "SUPPLEMENTARY_EXPERIMENTS_PROVENANCE.json", "ZENODO_VERIFICATION.md", "BIBLIOGRAPHY_VERIFICATION.md"):
    put(S / f, P_)
for v in ("supp_v1", "supp_v2"):
    for p in sorted((ROOT / "docs" / v).iterdir()):
        put(p, f"{P_}/manifests/{v}")
for f in ("EXPERIMENT_MANIFEST.json", "EXPERIMENT_MANIFEST.sha256", "TABLE4_V2_FINAL_TABLE.tex", "TABLE4_V2_PER_SEED.csv", "TABLE4_V2_SUMMARY.csv", "TABLE4_V2_PAIRED_EFFECTS.csv", "TABLE4_V2_METHOD_MATRIX.csv", "TABLE4_V2_PROVENANCE.json"):
    src = ROOT / "Table4_V2_Package" / f
    if f.startswith("EXPERIMENT_MANIFEST"):
        src = ROOT / "docs" / "table4_v2" / f
    put(src, f"{P_}/table4_v2_reference")
put(ROOT / "Table4_Audit_Package" / "TABLE4_EVIDENCE_AUDIT.md", f"{P_}/figure_provenance_evidence")
put(ROOT / "Table4_V2_Package" / "TABLE4_V2_MANUSCRIPT_IMPACT.md", f"{P_}/figure_provenance_evidence")
L = "07_publication_ready_latex"
for f in ("SUPPLEMENTARY_RESULTS_LATEX.tex", "SUPPLEMENTARY_TABLES_GENERATED.tex"):
    put(S / f, L)
put(S / "FIGURE_CAPTIONS_PUBLICATION_READY.md", L)
R_ = "08_reviewer_materials"
put(S / "SUPPLEMENTARY_EXPERIMENTS_REVIEWER_MAPPING.md", R_)
put(ROOT / "FINAL_REVIEWER_AUDIT.md", R_)
put(S / "UNRESOLVED_LIMITATIONS.md", R_)
C_ = "09_code_for_traceability"
for p in sorted((ROOT / "scripts" / "supp_final").glob("*.py")):
    put(p, f"{C_}/scripts/supp_final")
for p in sorted((ROOT / "src_v2").glob("*.py")):
    put(p, f"{C_}/src_v2")
put(ROOT / "docs" / "SIMULATION_SPEC.md", C_)
put(None, ".", "NOT_INCLUDED.md", text="""# Not included (by design or unavailable)
- Any manuscript source or PDF (you supply your latest `main.tex` / `references.bib`).
- Large artifacts: `results_supplementary_v1/`, `results_supplementary_v2/`, `results_phase6c/`, `results_table4_controlled_v2/` (model checkpoints, validation predictions, preprocessors), datasets under `data/`, the 76 per-run config YAMLs (hashes are in the manifests), raw logs.
- Unavailable evidence: the generating script/seed list of the manuscript's existing Figs 3-6; claim-level bibliography verification; official CICIoT2023 provenance; any author declarations.
- No experiment was run, no result changed, no Zenodo release created for this package.
""")
# inventory
lines = []
for root, _, fs in os.walk(OUT):
    for f in fs:
        if f == "SHA256_INVENTORY.txt":
            continue
        p = Path(root) / f
        lines.append((p.relative_to(OUT).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest()))
(OUT / "SHA256_INVENTORY.txt").write_text("".join(f"{h}  {n}\n" for n, h in sorted(lines)), encoding="utf-8")
if ZIP.exists():
    ZIP.unlink()
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            z.write(p, f"{NAME}/{p.relative_to(OUT).as_posix()}")
shutil.rmtree(OUT.parent)
# verification: reopen and check every file against the inventory, plus required items
zz = zipfile.ZipFile(ZIP)
assert zz.testzip() is None
inv = [l.split("  ", 1) for l in zz.read(f"{NAME}/SHA256_INVENTORY.txt").decode().splitlines()]
bad = [n for h, n in inv if hashlib.sha256(zz.read(f"{NAME}/{n}")).hexdigest() != h]
names = {n.split("/", 1)[1] for n in zz.namelist() if n != f"{NAME}/"}
extra = sorted(n for n in names if n != "SHA256_INVENTORY.txt" and n not in {x[1] for x in inv})
required = ["START_HERE.md", "EDITING_ORDER.md", f"{M}/MANUSCRIPT_PATCHES_C1_C11_ANCHORED.tex", f"{M}/MANUSCRIPT_CORRECTIONS_BEFORE_AFTER.tex", f"{M}/MANUSCRIPT_READINESS_MAP.md", f"{M}/MANUSCRIPT_INTEGRATION_CHECKLIST.md",
            f"{M}/CORRECTIONS_JUSTIFICATION_AND_PRIORITY.md", f"{E_}/SUPPLEMENTARY_EXPERIMENTS_FINAL_REPORT.md", f"{E_}/SUPPLEMENTARY_EXPERIMENTS_PER_SEED.csv", f"{E_}/SUPPLEMENTARY_EXPERIMENTS_SUMMARY.csv",
            f"{E_}/SUPPLEMENTARY_EXPERIMENTS_PAIRED_EFFECTS.csv", "03_statistics/STATISTICAL_INFERENCE_NOTE.md", f"{P_}/FINAL_SCIENTIFIC_QA_REPORT.md", f"{P_}/FINAL_QA_RESULTS.json",
            f"{P_}/SUPPLEMENTARY_EXPERIMENTS_PROVENANCE.json", f"{P_}/ZENODO_VERIFICATION.md", f"{P_}/BIBLIOGRAPHY_VERIFICATION.md", f"{P_}/manifests/supp_v1/EXPERIMENT_MANIFEST.json", f"{P_}/manifests/supp_v2/EXPERIMENT_MANIFEST.json",
            "05_audits/AUDIT_capnormalize_unit_test.csv", "05_audits/AUDIT_recorded_weights_summary.csv", "05_audits/AUDIT_ablation_weights_summary.csv", f"{E_}/V2_ABSTENTION_AND_ACCOUNTING_PER_RUN.csv",
            f"{L}/SUPPLEMENTARY_RESULTS_LATEX.tex", f"{L}/SUPPLEMENTARY_TABLES_GENERATED.tex", f"{R_}/SUPPLEMENTARY_EXPERIMENTS_REVIEWER_MAPPING.md", f"{R_}/FINAL_REVIEWER_AUDIT.md", f"{R_}/UNRESOLVED_LIMITATIONS.md"]
required += [f"04_figures/FIG{i}_{n}.{e}" for i, n in zip(range(1, 8), ("attack_robustness", "sensitivity_forest", "routing_x_surrogate", "participation_fairness", "scalability", "chi0_abstention", "checkpoint_vs_last")) for e in ("png", "pdf")]
required += [f"04_figures/FIG{i}_{n}_data.csv" for i, n in zip(range(1, 8), ("attack_robustness", "sensitivity_forest", "routing_x_surrogate", "participation_fairness", "scalability", "chi0_abstention", "checkpoint_vs_last"))]
missing = [r for r in required if r not in names]
print("files", len(inv) + 1, "size", ZIP.stat().st_size, "sha256", hashlib.sha256(ZIP.read_bytes()).hexdigest())
print("inventory mismatches:", bad, "| files not in inventory:", extra, "| required missing:", missing)
sys.exit(1 if (bad or missing or extra) else 0)
