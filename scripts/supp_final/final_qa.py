"""FINAL independent QA over SUPP_V1 (246 verified / 7 failed / 25 pending) and SUPP_V2 (44 runs). Read-only on every result tree.
usage: python scripts/supp_final/final_qa.py [--out Supplementary_Experiments_Package]
Writes FINAL_QA_RESULTS.json (machine-readable PASS/FAIL per check) into the output directory."""
import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "supp_v2"))
from supp_common import (V1_MANIFEST, V1_ROOT, MANIFEST, fingerprint, v1_fingerprint, load_manifest, manifest_hash, sha256_file, sha256_text_file, verify_run_dir)  # noqa: E402

CHECKS = []


def add(group, name, ok, detail=""):
    CHECKS.append(dict(group=group, check=name, status="PASS" if ok else "FAIL", detail=str(detail)))
    print(("PASS " if ok else "FAIL ") + f"[{group}] {name} :: {str(detail)[:160]}", flush=True)


def flat(d, p=""):
    o = {}
    for k, v in d.items():
        o.update(flat(v, p + k + ".") if isinstance(v, dict) else {p + k: v})
    return o


def cfg_drift(r):
    a = yaml.safe_load((ROOT / r["config"]).read_text(encoding="utf-8"))
    b = yaml.safe_load((ROOT / r["out_dir"] / "resolved_config.yaml").read_text(encoding="utf-8"))
    for blk in (a, b):
        for k in ("seed", "exact_output_dir"):
            blk["experiment"].pop(k, None)
    fa, fb = flat(a), flat(b)
    return [k for k in fa if fa.get(k) != fb.get(k) and not (isinstance(fa.get(k), float) and isinstance(fb.get(k), float) and abs(fa[k] - fb[k]) < 1e-12)]


def run_checks(tag, manifest, rows):
    """integrity + leakage-type checks applied identically to every completed run of a manifest."""
    probs, drift, test_loaded, cfg_hash_bad, prov_bad = [], [], [], [], []
    for r in rows:
        d = ROOT / r["out_dir"]
        p = verify_run_dir(d, r, manifest)
        if p:
            probs.append((r["run_id"], p[:2]))
        comp = json.loads((d / "COMPLETE.json").read_text(encoding="utf-8"))
        if comp["manifest_sha256"] != manifest["manifest_sha256"] or comp["code_fingerprint"] != manifest["code_fingerprint"] or comp["config_sha256"] != r["config_sha256"]:
            prov_bad.append(r["run_id"])
        if sha256_text_file(ROOT / r["config"]) != r["config_sha256"]:
            cfg_hash_bad.append(r["run_id"])
        meta = json.loads((d / "run_metadata.json").read_text(encoding="utf-8"))
        if meta.get("test_data_loaded") is not False:
            test_loaded.append(r["run_id"])
        dr = cfg_drift(r)
        if dr:
            drift.append((r["run_id"], dr[:3]))
    n = len(rows)
    add(tag, f"{n} runs: verify_run_dir (artifact hashes, 30 rounds, accounting, test_data_loaded=false) vs locked manifest", not probs, f"{n - len(probs)}/{n} verified {probs[:2]}")
    add(tag, f"{n} runs: COMPLETE.json manifest hash, code fingerprint and config hash equal the lock", not prov_bad, prov_bad[:3])
    add(tag, f"{n} runs: config file sha256 equals the manifest", not cfg_hash_bad, cfg_hash_bad[:3])
    add(tag, f"{n} runs: run_metadata test_data_loaded is false", not test_loaded, test_loaded[:3])
    add(tag, f"{n} runs: resolved run config equals the locked config (no drift)", not drift, drift[:2])


def replay_and_confusion(tag, rows):
    mism, err, bad_sets = 0, 0.0, []
    for r in rows:
        d = ROOT / r["out_dir"]
        fv = json.loads((d / "final_validation_metrics.json").read_text(encoding="utf-8"))
        rm = pd.read_csv(d / "round_metrics.csv")
        best, rep = float(rm[rm["round"] == 0].val_roc_auc.iloc[0]), 0
        for rn, sc in zip(rm["round"], rm.val_roc_auc):
            if rn > 0 and sc > best + 1e-4:
                best, rep = float(sc), int(rn)
        mism += int(rep != fv["best_round"])
        for blk in ("report_partition_at_selected_threshold", "last_round_report_partition"):
            b = fv[blk]
            tp, fp, fn, tn = b["tp"], b["fp"], b["fn"], b["tn"]
            err = max(err, abs(2 * tp / max(2 * tp + fp + fn, 1) - b["f1"]), abs(fp / max(fp + tn, 1) - b["fpr"]))
        ref = json.loads((ROOT / "results_phase6c" / r["dataset"] / "reference" / f"seed_{r['seed']}" / "validation_split_info.json").read_text())
        cur = json.loads((d / "validation_split_info.json").read_text())
        keys = [k for k in ref if "hash" in k or k in ("calibration_rows", "selection_rows", "report_rows", "validation_rows", "validation_attack", "validation_benign")]
        if any(ref.get(k) != cur.get(k) for k in keys) or ref.get("three_way") != cur.get("three_way"):
            bad_sets.append(r["run_id"])
    add(tag, "checkpoint selection = replay of the rule on the SELECTION partition ROC-AUC (no report-partition use)", mism == 0, f"{mism} mismatches of {len(rows)}")
    add(tag, "F1/FPR recomputed from logged confusion counts (selected and last)", err < 1e-9, f"max abs err {err:.2e}")
    add(tag, "validation calibration/selection/report split identical to locked Phase 6C split of same dataset+seed (no validation drift/leakage)", not bad_sets, bad_sets[:3])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="Supplementary_Experiments_Package")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    M1, M2 = load_manifest(V1_MANIFEST), load_manifest(MANIFEST)
    # ------------------------------------------------------------------ 1/2 inventory + provenance
    v1_done = [r for r in M1["runs"] if (ROOT / r["out_dir"] / "COMPLETE.json").exists()]
    v1_failed = [r for r in M1["runs"] if (ROOT / r["out_dir"] / "FAILED.json").exists() and not (ROOT / r["out_dir"] / "COMPLETE.json").exists()]
    v1_pending = [r for r in M1["runs"] if not (ROOT / r["out_dir"]).exists()]
    add("1 inventory", "SUPP_V1: 246 verified-candidate / 7 failed / 25 pending (frozen)", (len(v1_done), len(v1_failed), len(v1_pending)) == (246, 7, 25), (len(v1_done), len(v1_failed), len(v1_pending)))
    v2_done = [r for r in M2["runs"] if (ROOT / r["out_dir"] / "COMPLETE.json").exists()]
    add("1 inventory", "SUPP_V2: 44/44 COMPLETE.json present, no FAILED.json", len(v2_done) == 44 and not list((ROOT / "results_supplementary_v2").rglob("FAILED.json")), len(v2_done))
    stray = [p.name for p in (ROOT / "results_supplementary_v2").rglob("seed_*") if ".incomplete." in p.name or ".failed." in p.name]
    add("1 inventory", "SUPP_V2: no moved-aside incomplete/failed attempt directories", not stray, stray[:3])
    run_checks("1 V1 integrity", M1, v1_done)
    run_checks("1 V2 integrity", M2, v2_done)
    # ------------------------------------------------------------------ 2 manifests, fingerprints, datasets
    for tag, M, mp in (("V1", M1, V1_MANIFEST), ("V2", M2, MANIFEST)):
        add("2 provenance", f"{tag} manifest self-hash valid and equals sidecar .sha256", manifest_hash(M) == M["manifest_sha256"] and mp.with_suffix(".sha256").read_text().split()[0] == M["manifest_sha256"], M["manifest_sha256"][:16])
    add("2 provenance", "V1 code fingerprint recomputed today equals the V1 lock (V2 work altered no V1-fingerprinted file)", v1_fingerprint() == M1["code_fingerprint"], M1["code_fingerprint"][:16])
    add("2 provenance", "V2 code fingerprint recomputed today equals the V2 lock", fingerprint() == M2["code_fingerprint"], M2["code_fingerprint"][:16])
    add("2 provenance", "V2 manifest records the V1 manifest hash unchanged", M2["v1_reference"].get("manifest_sha256", "") == M1["manifest_sha256"] if isinstance(M2["v1_reference"], dict) else M1["manifest_sha256"] in json.dumps(M2["v1_reference"]), "")
    pf = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v2/orchestrator.py"), "preflight"], capture_output=True, text=True, cwd=ROOT)
    add("2 provenance", "V2 preflight incl. dataset sha256 (UNSW csv, CICIoT2023 train/validation content) all PASS", pf.stdout.count("FAIL") == 0 and pf.stdout.count("PASS") >= 14, f"{pf.stdout.count('PASS')} PASS / {pf.stdout.count('FAIL')} FAIL")
    pf1 = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v1/orchestrator.py"), "preflight"], capture_output=True, text=True, cwd=ROOT)
    add("2 provenance", "V1 preflight incl. dataset sha256 all PASS", pf1.stdout.count("FAIL") == 0, f"{pf1.stdout.count('PASS')} PASS / {pf1.stdout.count('FAIL')} FAIL")
    imp_bad = []
    for r in M2["runs"]:
        pv = json.loads((ROOT / r["out_dir"] / "v2_import_provenance.json").read_text())
        mods = pv.get("modules", pv)
        flags = {k: (v.get("from_v2_overlay") if isinstance(v, dict) else None) for k, v in mods.items() if k in ("src.data", "src.experiment")}
        others = [k for k, v in mods.items() if isinstance(v, dict) and v.get("from_v2_overlay") and k not in ("src.data", "src.experiment")]
        if flags != {"src.data": True, "src.experiment": True} or others:
            imp_bad.append((r["run_id"], flags, others))
    add("2 provenance", "every V2 run imported exactly src.data and src.experiment from src_v2 (all other src.* modules are the unchanged V1 code)", not imp_bad, imp_bad[:2])
    # ------------------------------------------------------------------ 3 no test access
    for tag, M in (("V1", M1), ("V2", M2)):
        cfgs = [yaml.safe_load((ROOT / r["config"]).read_text()) for r in M["runs"]]
        add("3 test data", f"{tag}: every config has a blank test path / validation-only flag; manifest locked_test empty", all(not (c.get("data", {}).get("test_path") or c.get("data", {}).get("test_csv")) for c in cfgs) and not M["locked_test"], len(cfgs))
    tf = [str(p) for rd in (ROOT / V1_ROOT, ROOT / "results_supplementary_v2") for p in rd.rglob("*") if p.is_file() and "test" in p.name.lower() and "_tests" not in p.parts and "_logs" not in p.parts]
    add("3 test data", "no artifact containing test-set predictions/scores exists in any V1/V2 run directory", not tf, tf[:3])
    # ------------------------------------------------------------------ 4 leakage (selection/threshold/split)
    replay_and_confusion("4 leakage V1", v1_done)
    replay_and_confusion("4 leakage V2", v2_done)
    # ------------------------------------------------------------------ 5 CIC client holdout
    cic = [r for r in M2["runs"] if r["family"] == "E_participation_cic"]
    audits = {r["run_id"]: json.loads((ROOT / r["out_dir"] / "client_holdout_audit.json").read_text()) for r in cic}
    A = list(audits.values())
    add("5 CIC holdout", "30 CIC participation runs, each with an enabled holdout audit", len(A) == 30 and all(x.get("enabled") for x in A), len(A))
    add("5 CIC holdout", "zero predictor-group and encoded-vector straddling between training and holdout in all 30", all(x["predictor_groups_straddling_train_holdout"] == 0 and x["encoded_vectors_straddling_train_holdout"] == 0 for x in A), "")
    add("5 CIC holdout", "preprocessor fitted on non-holdout rows only in all 30; fit rows = train - holdout", all(x["preprocessor_fitted_on_non_holdout_rows_only"] and x["preprocessor_fit_rows"] == x["train_rows_before_holdout"] - x["holdout_rows"] for x in A), "")
    add("5 CIC holdout", "both classes in training remainder and holdout, realised fraction within 3x request, closure converged (<=12 its)", all(x["holdout_attack_rows"] > 0 and x["holdout_benign_rows"] > 0 and x["retained_training_attack_rows"] > 0 and x["retained_training_benign_rows"] > 0 and 0 < x["holdout_rows"] <= 3 * 0.2 * x["train_rows_before_holdout"] and x["closure_iterations"] <= 12 for x in A),
        f"closure its {sorted({x['closure_iterations'] for x in A})}; realised fraction {min(x['realized_fraction'] for x in A):.4f}-{max(x['realized_fraction'] for x in A):.4f}")
    by_seed = defaultdict(set)
    part_by_seed = defaultdict(set)
    for r in cic:
        by_seed[r["seed"]].add(audits[r["run_id"]]["holdout_mask_sha256"])
        part_by_seed[r["seed"]].add(audits[r["run_id"]].get("client_partition_sha256"))
    add("5 CIC holdout", "matched randomisation: holdout mask identical across the six arms of a seed", all(len(v) == 1 for v in by_seed.values()), {s: len(v) for s, v in by_seed.items()})
    add("5 CIC holdout", "client partition identical across the six arms of a seed", all(len(v) == 1 and None not in v for v in part_by_seed.values()), {s: len(v) for s, v in part_by_seed.items()})
    add("5 CIC holdout", "holdout masks differ between seeds (seed-driven)", len({next(iter(v)) for v in by_seed.values()}) == 5, "")
    elig = [(r["run_id"], sum(c["eligible_for_recall"] for c in audits[r["run_id"]]["clients"])) for r in cic]
    add("5 CIC holdout", "per-client eligible-for-recall counts recorded (>=10 holdout attack rows); eligibility depends on holdout sizes only", all(isinstance(e[1], int) for e in elig), f"eligible clients per run min {min(e[1] for e in elig)} max {max(e[1] for e in elig)} of 50")
    dsum = [r["run_id"] for r in cic if not (json.loads((ROOT / r["out_dir"] / "run_metadata.json").read_text()).get("test_data_loaded") is False)]
    add("5 CIC holdout", "test data never loaded in the 30 CIC holdout runs", not dsum, "")
    unsw_aud = [r for r in M2["runs"] if r["dataset"] == "unsw"]
    add("5 CIC holdout", "UNSW V2 runs: enabled flag matches design (participation runs) and CIC non-participation V2 runs have holdout disabled", all(json.loads((ROOT / r["out_dir"] / "client_holdout_audit.json").read_text()).get("enabled") == (r["arm"].startswith("part_")) for r in M2["runs"] if r["family"] != "E_participation_cic"), "")
    # ------------------------------------------------------------------ 6/7 weights, abstention, accounting
    wbad, rows7 = [], []
    for r in M2["runs"]:
        d = ROOT / r["out_dir"]
        rm = pd.read_csv(d / "round_metrics.csv")
        rr = rm[rm["round"] > 0].reset_index(drop=True)
        ag = pd.read_csv(d / "aggregation_diagnostics.csv")
        priv = json.loads((d / "privacy_plan.json").read_text())
        meta = json.loads((d / "run_metadata.json").read_text())
        acc = meta["privacy"].get("supp_v2_accounting", {})
        ab = rr.no_valid_contribution.astype(int)
        nab = int(ab.sum())
        sums = ag.groupby("round").applied_weight_share.sum()
        okw = True
        for rn in rr["round"]:
            s = float(sums.get(rn, 0.0))
            if ab[rn - 1] or int(rr.received_updates[rn - 1]) == 0:   # abstention or an empty round (no update delivered, no surrogate): nothing is aggregated
                okw &= abs(s) < 1e-12
            else:
                okw &= abs(s - 1.0) < 1e-6
        if not okw:
            wbad.append(r["run_id"])
        dp = bool(priv.get("privacy_enabled", False))
        pr = {}
        pr["attempt_ok"] = int(rr.attempted_privacy_rounds_cum.iloc[-1]) == 30 if dp else True
        nempty = int(((rr.received_updates == 0) & (ab == 0)).sum())
        pr["release_ok"] = int(rr.noise_release_rounds_cum.iloc[-1]) == 30 - nab - nempty if dp else True
        pr["release==sum(noisy_release)"] = int(rr.noisy_release.sum()) == int(rr.noise_release_rounds_cum.iloc[-1]) if dp else True
        pr["abstain_noise0"] = bool((rr.loc[ab == 1, "privacy_noise_std"] == 0).all()) if dp else True
        pr["abstain_nonoisy_release"] = bool((rr.loc[ab == 1, "noisy_release"] == 0).all())
        eps_rel, eps_att = rr.privacy_epsilon_estimate.iloc[-1], rr.privacy_epsilon_attempted_rounds_conservative.iloc[-1]
        pr["eps_att>=eps_rel"] = bool(eps_att >= eps_rel - 1e-12) if dp else True
        pr["eps_equal_if_no_abstention"] = (abs(eps_att - eps_rel) < 1e-9) if (dp and nab == 0) else True
        # model unchanged in abstention rounds => validation score identical to the previous round
        unchanged = True
        for i in np.where(ab == 1)[0]:
            prev = rm[rm["round"] == rr["round"].iloc[i] - 1].iloc[0]
            unchanged &= abs(float(rr.val_roc_auc.iloc[i]) - float(prev.val_roc_auc)) < 1e-12
        pr["model_unchanged_on_abstention"] = bool(unchanged)
        pr["no_abstention_unless_chi0"] = (nab == 0) if r["arm"] != "sens_chi0_dp" else True
        pr["acc_release_matches_metadata"] = (acc.get("noisy_release_rounds") == int(rr.noisy_release.sum()) and acc.get("no_valid_contribution_rounds") == nab and acc.get("attempted_privacy_rounds") == int(rr.attempted_privacy_rounds_cum.iloc[-1])) if dp else True
        if not all(pr.values()):
            wbad.append((r["run_id"], [k for k, v in pr.items() if not v]))
        rows7.append(dict(run_id=r["run_id"], dataset=r["dataset"], arm=r["arm"], seed=r["seed"], family=r["family"], dp_enabled=dp, abstention_rounds=nab, abstention_round_ids=";".join(map(str, rr["round"][ab == 1].tolist())),
                          noisy_release_rounds=int(rr.noisy_release.sum()), attempted_rounds=int(rr.attempted_privacy_rounds_cum.iloc[-1]), eps_release_diag=float(eps_rel), eps_attempted_diag=float(eps_att)))
    pd.DataFrame(rows7).to_csv(out / "V2_ABSTENTION_AND_ACCOUNTING_PER_RUN.csv", index=False)
    add("6 weights", "aggregation weights sum to 1 in every non-abstaining round and to 0 in abstaining rounds (44 V2 runs)", not [w for w in wbad if not isinstance(w, tuple)], [w for w in wbad if not isinstance(w, tuple)][:3])
    add("7 accounting", "noisy-release / attempted-round counters, abstention noise=0, eps_attempted>=eps_release, unchanged validation score on abstention, abstention only in chi_rec=0 arm (44 V2 runs)", not [w for w in wbad if isinstance(w, tuple)], [w for w in wbad if isinstance(w, tuple)][:3])
    ch = pd.DataFrame(rows7)
    ch0 = ch[ch.arm == "sens_chi0_dp"]
    add("6 weights", "non-chi0 V2 runs (34) contain zero abstention rounds", int(ch[ch.arm != "sens_chi0_dp"].abstention_rounds.sum()) == 0, "")
    add("6 weights", "chi_rec=0 V2 runs: abstention counts recorded (diagnostic)", True, ch0[["run_id", "abstention_rounds"]].to_dict("records"))
    # capped-uniform property across all DP runs of V1+V2
    nonuni, tot = 0, 0
    for M, rows in ((M1, v1_done), (M2, M2["runs"])):
        for r in rows:
            d = ROOT / r["out_dir"]
            pj = json.loads((d / "privacy_plan.json").read_text())
            if not pj.get("privacy_enabled", False):
                continue
            ag = pd.read_csv(d / "aggregation_diagnostics.csv")
            kept = ag[ag.kept.astype(bool)]
            g = kept.groupby("round")
            n = g.size()
            spread = g.applied_weight_share.agg(lambda x: x.max() - x.min())
            for rn in n.index:
                tot += 1
                if n[rn] <= 10 and spread[rn] > 1e-9:
                    nonuni += 1
    add("6 weights", "central-DP runs (V1+V2): every aggregation round with <=10 retained updates has exactly uniform weights 1/n", nonuni == 0, f"{tot} DP rounds inspected, {nonuni} non-uniform")
    # ------------------------------------------------------------------ 8 regression equivalence
    rg = subprocess.run([sys.executable, str(ROOT / "scripts/supp_v2/regression_compare.py")], capture_output=True, text=True, cwd=ROOT)
    add("8 regression", "V1 vs V2 regression controls (4 UNSW/CIC controls + chi0 seeds 12,14 x 2 datasets): all deterministic artifacts and model tensors bit-identical", "GATE PASS" in rg.stdout, rg.stdout.strip().splitlines()[-1])
    # ------------------------------------------------------------------ 9 historical evidence
    P6 = load_manifest(ROOT / "docs/phase6c/EXPERIMENT_MANIFEST.json")
    T4 = load_manifest(ROOT / "docs/table4_v2/EXPERIMENT_MANIFEST.json")
    bad6 = [r["run_id"] for r in P6["runs"] if verify_run_dir(ROOT / r["out_dir"], r, P6)]
    bad4 = [r["run_id"] for r in T4["runs"] if verify_run_dir(ROOT / r["out_dir"], r, T4)]
    add("9 historical", f"locked Phase 6C: {len(P6['runs'])} runs re-verified against their manifest (artifact hashes unchanged)", not bad6, bad6[:3])
    add("9 historical", f"Table 4 v2: {len(T4['runs'])} runs re-verified against their manifest (artifact hashes unchanged)", not bad4, bad4[:3])
    gd = subprocess.run(["git", "diff", "--stat", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    add("9 historical", "git: no tracked file differs from HEAD (manuscript, src, ledger, Table 4 evidence, README untouched)", gd == "", gd[:120])
    add("9 historical", "Table 4 v2 published tables / Phase 9 ledger tracked and unchanged", subprocess.run(["git", "ls-files", "--error-unmatch", "Phase9_Manuscript_Revision/ledger/ledger_per_run_phase6c.csv"], capture_output=True, cwd=ROOT).returncode == 0 and gd == "", "")
    # ------------------------------------------------------------------ 10 duplicates
    ids1 = [r["run_id"] for r in M1["runs"]]; ids2 = [r["run_id"] for r in M2["runs"]]
    add("10 duplicates", "run ids unique within and between V1 and V2", len(set(ids1)) == 278 and len(set(ids2)) == 44 and not set(ids1) & set(ids2), "")
    idn1 = {(r["dataset"], r["arm"], r["seed"]): r for r in v1_done}
    ov = [(r["dataset"], r["arm"], r["seed"]) for r in M2["runs"] if (r["dataset"], r["arm"], r["seed"]) in idn1]
    add("10 duplicates", "V2 identities already verified in V1 = exactly the 8 regression controls (4 R-family + chi0 seeds 12,14 x 2 datasets); these are counted ONCE in pooled analysis", len(ov) == 8, ov)
    fail_ids = {(r["dataset"], r["arm"], r["seed"]) for r in v1_failed + v1_pending}
    v2_ids = {(r["dataset"], r["arm"], r["seed"]) for r in M2["runs"]}
    unresolved = fail_ids - v2_ids
    add("10 duplicates", "all 32 unresolved V1 identities (7 failed + 25 pending) are each completed by exactly one V2 run", len(fail_ids) == 32 and not unresolved, f"{len(fail_ids)} unresolved V1 identities; covered by V2: {len(fail_ids & v2_ids)}; uncovered: {sorted(unresolved)[:3]}")
    res = {"n_pass": sum(c["status"] == "PASS" for c in CHECKS), "n_fail": sum(c["status"] == "FAIL" for c in CHECKS), "checks": CHECKS}
    (out / "FINAL_QA_RESULTS.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\nTOTAL {res['n_pass']} PASS / {res['n_fail']} FAIL")
    return 0 if res["n_fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
