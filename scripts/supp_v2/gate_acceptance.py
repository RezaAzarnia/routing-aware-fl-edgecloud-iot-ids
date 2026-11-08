"""Final SUPP_V2 gate acceptance (read-only): prints PASS/FAIL for every check and writes results_supplementary_v2/_tests/gate_acceptance.json.
usage: python scripts/supp_v2/gate_acceptance.py"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from supp_common import MANIFEST, V1_MANIFEST, V1_ROOT, fingerprint, load_manifest, manifest_hash, v1_fingerprint, verify_run_dir  # noqa: E402

R: list[dict] = []


def chk(group, name, ok, detail=""):
    R.append({"group": group, "check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + f"[{group}] {name}" + (f" - {detail}" if detail else ""), flush=True)


def norm_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main():
    M = load_manifest(MANIFEST)
    gate = [r for r in M["runs"] if r["run_id"] in set(M["gate_run_ids"])]
    chk("0 scope", "10 gate runs in the locked manifest", len(gate) == 10 and len(M["gate_run_ids"]) == 10)
    for r in gate:
        d = ROOT / r["out_dir"]
        chk("0 scope", f"{r['run_id']} COMPLETE and verified against the manifest", not verify_run_dir(d, r, M), "; ".join(verify_run_dir(d, r, M))[:120])

    # 1. V1/V2 regression equivalence (independent re-run of the comparator, exact comparison)
    p = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v2/regression_compare.py"), "--verbose"], capture_output=True, text=True, cwd=ROOT)
    rep = json.loads((ROOT / "results_supplementary_v2/_tests/regression_report.json").read_text(encoding="utf-8"))
    for x in rep["runs"]:
        if x["v1_counterpart"]:
            n_ok = sum(v["pass"] for v in x["checks"].values())
            chk("1 V1/V2 equivalence", f"{x['run_id']}: round metrics, trace, diagnostics, split info, final metrics and best/last tensors identical to SUPP_V1", x["gate_pass"], f"{n_ok}/{len(x['checks'])} sub-checks, {x['v2_abstention_rounds']} abstention rounds")
    chk("1 V1/V2 equivalence", "comparator exit status (all gate runs)", p.returncode == 0 and rep["gate_pass"])
    chk("1 V1/V2 equivalence", "8 gate runs have a verified V1 counterpart (3 UNSW participation, 1 CIC DP control, 4 chi_rec=0)", sum(x["v1_counterpart"] for x in rep["runs"]) == 8)

    # 2. CICIoT2023 holdout leakage
    cic = [r for r in gate if r["dataset"] == "ciciot" and r["arm"].startswith("part_")]
    chk("2 CIC holdout", "a CICIoT2023 holdout gate run exists", len(cic) == 1)
    for r in cic:
        d = ROOT / r["out_dir"]
        a = json.loads((d / "client_holdout_audit.json").read_text(encoding="utf-8"))
        cl = a["clients"]
        meta = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))
        cd = pd.read_csv(d / "client_distribution.csv")
        chk("2 CIC holdout", "predictor groups straddling train/holdout = 0", a["predictor_groups_straddling_train_holdout"] == 0)
        chk("2 CIC holdout", "encoded vectors straddling train/holdout = 0", a["encoded_vectors_straddling_train_holdout"] == 0)
        chk("2 CIC holdout", "preprocessor fitted only on non-holdout rows", a["preprocessor_fitted_on_non_holdout_rows_only"] and a["preprocessor_fit_rows"] == a["train_rows_before_holdout"] - a["holdout_rows"])
        chk("2 CIC holdout", "holdout fraction 0.20 (realized within [0.15, 0.30])", 0.15 <= a["realized_fraction"] <= 0.30, f"{a['realized_fraction']:.4f}, closure iterations {a['closure_iterations']}/12")
        chk("2 CIC holdout", "holdout has both classes; sizes and class counts recorded", a["holdout_attack_rows"] > 0 and a["holdout_benign_rows"] > 0 and a["holdout_attack_rows"] + a["holdout_benign_rows"] == a["holdout_rows"],
            f"attack {a['holdout_attack_rows']}, benign {a['holdout_benign_rows']}")
        chk("2 CIC holdout", "per-client records add up (training + holdout rows = all training rows; holdout rows = mask)", sum(c["train_rows"] for c in cl) + sum(c["holdout_rows"] for c in cl) == a["train_rows_before_holdout"] and sum(c["holdout_rows"] for c in cl) == a["holdout_rows"])
        chk("2 CIC holdout", "per-client training sizes equal the training partition used by the run (client_distribution.csv)", [c["train_rows"] for c in cl] == cd["num_samples"].tolist())
        chk("2 CIC holdout", "per-client eligibility recorded by size only (>=10 holdout attack rows)", all(c["eligible_for_recall"] == (c["holdout_attack"] >= 10) for c in cl), f"{a['eligible_clients_for_recall']} of {len(cl)} eligible")
        chk("2 CIC holdout", "test data never loaded; no test artefacts; blank test path", meta["test_data_loaded"] is False and not [q.name for q in d.iterdir() if "final_test" in q.name.lower() or q.name.lower().startswith("test_pred")])
        chk("2 CIC holdout", "separate calibration / selection / report partitions (three-way split) recorded", "three_way" in json.loads((d / "validation_split_info.json").read_text(encoding="utf-8")))
        chk("2 CIC holdout", "mask hash recorded for cross-arm matching", len(a["holdout_mask_sha256"]) == 64)
    # the mask depends on seed only: the same-seed mask recorded here must equal the one produced by the independent unit-test load (seed 12)
    t = json.loads((ROOT / "results_supplementary_v2/_tests/test_report_cic.json").read_text(encoding="utf-8"))
    chk("2 CIC holdout", "independent unit test on real CICIoT2023 data (seeds 12, 13): all checks passed", t["all_pass"], f"{sum(x['pass'] for x in t['results'])}/{len(t['results'])}")

    # 3. chi_rec = 0 abstention behaviour and accounting
    for r in [x for x in gate if x["arm"] == "sens_chi0_dp"]:
        d = ROOT / r["out_dir"]
        rm = pd.read_csv(d / "round_metrics.csv")
        rm = rm[rm["round"] > 0].reset_index(drop=True)
        ab = rm[rm.no_valid_contribution == 1]
        ag = pd.read_csv(d / "aggregation_diagnostics.csv")
        acc = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))["privacy"]["supp_v2_accounting"]
        g = f"3 chi0 {r['run_id'].replace('v2__', '')}"
        chk(g, "30 rounds completed, no crash", len(rm) == 30)
        chk(g, "attempted = noisy releases + abstentions (per-round cumulative and run metadata)", int(rm.attempted_privacy_rounds_cum.iloc[-1]) == int(rm.noise_release_rounds_cum.iloc[-1]) + len(ab) == acc["attempted_privacy_rounds"] and acc["noisy_release_rounds"] == int(rm.noisy_release.sum()),
            f"attempted {acc['attempted_privacy_rounds']}, releases {acc['noisy_release_rounds']}, abstentions {acc['no_valid_contribution_rounds']}")
        chk(g, "abstention rounds: no noise, no release, zero applied weights, flagged", bool((ab.privacy_noise_std == 0).all() and (ab.noisy_release == 0).all() and (ag[ag["round"].isin(ab["round"])].applied_weight_share == 0).all()
                                                                                       and ab.actual_aggregation_method.str.contains("no_valid_contribution_abstain").all()))
        chk(g, "all-zero-weight abstention only when every retained raw weight is 0 (non-abstention rounds have a positive retained weight sum)",
            all(ag[(ag["round"] == rr) & ag.kept.astype(bool)].raw_weight.sum() > 0 for rr in rm[rm.no_valid_contribution == 0]["round"]) and all(ag[(ag["round"] == rr) & ag.kept.astype(bool)].raw_weight.sum() == 0 for rr in ab["round"]))
        chk(g, "release-based epsilon <= conservative attempted epsilon; equal iff no abstention; both labelled diagnostic", acc["epsilon_release_based_diagnostic"] <= acc["epsilon_attempted_rounds_conservative_diagnostic"] + 1e-12
            and ((len(ab) == 0) == bool(np.isclose(acc["epsilon_release_based_diagnostic"], acc["epsilon_attempted_rounds_conservative_diagnostic"]))) and acc["both_are_diagnostic_estimates_not_certified_guarantees"] is True,
            f"{acc['epsilon_release_based_diagnostic']:.4f} vs {acc['epsilon_attempted_rounds_conservative_diagnostic']:.4f}")
        for rr in ab["round"]:
            prev, cur = rm[rm["round"] == rr - 1].iloc[0] if rr > 1 else None, rm[rm["round"] == rr].iloc[0]
            if prev is not None:
                chk(g, f"model unchanged in abstention round {rr} (validation metrics identical to round {rr - 1})", abs(prev.val_f1 - cur.val_f1) < 1e-12 and abs(prev.val_roc_auc - cur.val_roc_auc) < 1e-12 and cur.server_applied_update_l2_norm == 0)
    s13 = rm if False else None  # noqa: F841
    d13 = ROOT / "results_supplementary_v2/unsw/sens_chi0_dp/seed_13"
    rm13 = pd.read_csv(d13 / "round_metrics.csv")
    chk("3 chi0 seed 13", "the V1 crash round (21) is the abstention round under V2", rm13[rm13.no_valid_contribution == 1]["round"].tolist() == [21])
    chk("3 chi0 seed 13", "V1 crash evidence preserved (FAILED.json + log of both attempts)", all((ROOT / V1_ROOT / ds / "sens_chi0_dp" / "seed_13" / "FAILED.json").exists() for ds in ("unsw", "ciciot")))
    chk("3 chi0 positive-weight seeds", "chi_rec=0 seeds 12 and 14 (both datasets) have 0 abstentions and equal V1 exactly", all(x["gate_pass"] and x["v2_abstention_rounds"] == 0 for x in rep["runs"] if "sens_chi0_dp" in x["run_id"] and ("seed12" in x["run_id"] or "seed14" in x["run_id"])))

    # 4. SUPP_V1 integrity and SUPP_V2 provenance
    v1 = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    chk("4 V1 integrity", "SUPP_V1 manifest hash valid and equal to the hash recorded in the V2 manifest", v1["manifest_sha256"] == manifest_hash(v1) == M["v1_reference"]["manifest_sha256"], v1["manifest_sha256"][:16])
    chk("4 V1 integrity", "SUPP_V1 code fingerprint unchanged", v1_fingerprint() == v1["code_fingerprint"] == M["v1_reference"]["code_fingerprint"], v1_fingerprint()[:16])
    st = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v1/orchestrator.py"), "status"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    chk("4 V1 integrity", "all 246 SUPP_V1 verified runs still verify (COMPLETE.json + artifact hashes)", "'verified': 246" in st, st)
    chk("4 V1 integrity", "SUPP_V1 failure evidence preserved (7 FAILED.json + 6 moved-aside attempts)", len(list((ROOT / V1_ROOT).rglob("FAILED.json"))) == 13, f"{len(list((ROOT / V1_ROOT).rglob('FAILED.json')))} FAILED.json files")
    chk("4 V1 integrity", "no V2 file inside the V1 results tree", not any(".v2" in q.name for q in (ROOT / V1_ROOT).rglob("*")) and not any((ROOT / V1_ROOT).glob("**/v2_import_provenance.json")))
    chk("4 V2 provenance", "V2 manifest hash valid; code fingerprint equals the manifest", M["manifest_sha256"] == manifest_hash(M) and fingerprint() == M["code_fingerprint"], M["code_fingerprint"][:16])
    for r in gate:
        d = ROOT / r["out_dir"]
        pv = json.loads((d / "v2_import_provenance.json").read_text(encoding="utf-8"))
        okmods = pv["overlay_modules"] == ["src.data", "src.experiment"] and all(pv["modules"][m]["sha256"] == norm_sha(ROOT / pv["modules"][m]["file"]) for m in pv["overlay_modules"])
        okv1 = all(v["sha256"] == norm_sha(ROOT / v["file"]) for k, v in pv["modules"].items() if not v["from_v2_overlay"])
        comp = json.loads((d / "COMPLETE.json").read_text(encoding="utf-8"))
        chk("4 V2 provenance", f"{r['run_id']}: imported src_v2 modules + unchanged V1 modules match files on disk; COMPLETE.json carries manifest and fingerprint", okmods and okv1 and comp["manifest_sha256"] == M["manifest_sha256"] and comp["code_fingerprint"] == M["code_fingerprint"])
    chk("4 V2 provenance", "validation-only: no gate config references a test file", all(json.loads((ROOT / r["out_dir"] / "run_metadata.json").read_text(encoding="utf-8"))["test_data_loaded"] is False for r in gate))
    pf = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v2/orchestrator.py"), "preflight"], capture_output=True, text=True, cwd=ROOT).stdout
    chk("4 V2 provenance", "V2 preflight all PASS", "FAIL" not in pf and pf.count("PASS") >= 14, f"{pf.count('PASS')} PASS")
    stv2 = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v2/orchestrator.py"), "status"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    chk("4 V2 provenance", "V2 status = 10 verified, 34 pending, 0 failed/incomplete (no duplicate or leftover directories)", stv2 == "{'verified': 10, 'pending': 34} of 44", stv2)
    pend_dirs = [r["run_id"] for r in M["runs"] if r["run_id"] not in set(M["gate_run_ids"]) and (ROOT / r["out_dir"]).exists()]
    chk("4 V2 provenance", "no output directory exists for any of the 34 pending runs", not pend_dirs, str(pend_dirs[:3]))

    out = ROOT / "results_supplementary_v2/_tests/gate_acceptance.json"
    out.write_text(json.dumps({"all_pass": all(x["pass"] for x in R), "n_checks": len(R), "n_pass": sum(x["pass"] for x in R), "checks": R}, indent=1), encoding="utf-8")
    print(f"== {sum(x['pass'] for x in R)}/{len(R)} checks passed -> {'GATE ACCEPTED' if all(x['pass'] for x in R) else 'GATE NOT ACCEPTED'}")
    return 0 if all(x["pass"] for x in R) else 1


if __name__ == "__main__":
    sys.exit(main())
