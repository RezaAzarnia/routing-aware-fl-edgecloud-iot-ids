"""SUPP_V2 validation tests (run BEFORE any V2 experiment). Never opens a reserved test file; writes only under results_supplementary_v2/_tests/.

  python scripts/supp_v2/test_v2.py --part unit      overlay import, V1 fingerprint, synthetic holdout tests, fail-closed tests
  python scripts/supp_v2/test_v2.py --part cic       CICIoT2023 leakage checks on the real prepared training/validation data (validation-only load)
  python scripts/supp_v2/test_v2.py --part micro     end-to-end micro run that FORCES zero-weight rounds (abstention, accounting, no apply_update)
  python scripts/supp_v2/test_v2.py --part all
Writes results_supplementary_v2/_tests/test_report_<part>.json; exit code 1 if any check fails."""
import argparse
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v2_overlay  # noqa: E402

v2_overlay.install()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

OUT = ROOT / "results_supplementary_v2" / "_tests"
OUT.mkdir(parents=True, exist_ok=True)
RESULTS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f" [{detail}]" if detail else ""), flush=True)


def raises(fn, exc=Exception) -> bool:
    try:
        fn()
    except exc:
        return True
    return False


# ---------------------------------------------------------------------------------------------------------------------------------------------
def part_unit() -> None:
    from supp_common import V1_MANIFEST, v1_fingerprint
    import src.data as D
    import src.experiment as E

    prov = v2_overlay.import_provenance()
    check("overlay: src.data and src.experiment are served from src_v2", set(prov["overlay_modules"]) == {"src.data", "src.experiment"}, str(prov["overlay_modules"]))
    check("overlay: every other imported src module is the unchanged V1 file", all(not v["from_v2_overlay"] for k, v in prov["modules"].items() if k not in ("src.data", "src.experiment")))
    v1 = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    check("SUPP_V1 code fingerprint still equals its locked manifest", v1_fingerprint() == v1["code_fingerprint"], v1_fingerprint()[:16])
    check("src/data.py and src/experiment.py (V1) are untouched: V2 copies live only in src_v2", (ROOT / "src" / "data.py").read_bytes() != (ROOT / "src_v2" / "data.py").read_bytes())

    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler

    def make_pre():
        return ColumnTransformer([("num", StandardScaler(), ["a", "b", "c"])], remainder="drop")

    rng = np.random.default_rng(0)
    base = pd.DataFrame(rng.normal(size=(300, 3)) * [1, 100, 1e4], columns=["a", "b", "c"])
    dup = base.iloc[:100].copy()                       # 100 exact duplicates of the first 100 rows
    near = base.iloc[100:130].copy()
    near["c"] = near["c"] * (1 + 1e-9)                 # equal at 6 significant digits -> must share a group with the original
    X = pd.concat([base, dup, near], ignore_index=True)
    y = np.concatenate([(rng.random(300) < 0.5).astype(int), (rng.random(100) < 0.5).astype(int), (rng.random(30) < 0.5).astype(int)])
    pre = make_pre()
    Xe, mask, groups, audit = D.fit_preprocessor_with_client_holdout(pre, X, y, 0.2, seed=5)
    grp_h, grp_t = set(groups[mask]), set(groups[~mask])
    check("synthetic: no predictor group straddles train and holdout", not (grp_h & grp_t) and audit["predictor_groups_straddling_train_holdout"] == 0)
    enc = pd.util.hash_pandas_object(pd.DataFrame(Xe), index=False).to_numpy()
    check("synthetic: no encoded vector straddles train and holdout", not (set(enc[mask]) & set(enc[~mask])) and audit["encoded_vectors_straddling_train_holdout"] == 0)
    check("synthetic: exact duplicates and 6-digit near-duplicates are held out together", all(mask[i] == mask[300 + i] for i in range(100)) and all(mask[100 + i] == mask[400 + i] for i in range(30)))
    sc = pre.named_transformers_["num"]
    check("synthetic: preprocessor fitted on non-holdout rows only (n_samples_seen and mean)", int(sc.n_samples_seen_) == int((~mask).sum())
          and np.allclose(sc.mean_, X.loc[~mask, ["a", "b", "c"]].to_numpy().mean(0)))
    check("synthetic: holdout fraction near the request", 0.12 <= audit["realized_fraction"] <= 0.45, f"{audit['realized_fraction']:.3f}")
    _, mask2, _, audit2 = D.fit_preprocessor_with_client_holdout(make_pre(), X, y, 0.2, seed=5)
    _, mask3, _, _ = D.fit_preprocessor_with_client_holdout(make_pre(), X, y, 0.2, seed=6)
    check("synthetic: deterministic for a seed (identical mask hash)", audit["holdout_mask_sha256"] == audit2["holdout_mask_sha256"] and bool((mask == mask2).all()))
    check("synthetic: a different seed gives a different holdout", not bool((mask == mask3).all()))
    check("fail closed: single-class labels", raises(lambda: D.fit_preprocessor_with_client_holdout(make_pre(), X, np.zeros(len(X), dtype=int), 0.2, 5), RuntimeError))
    tiny = pd.DataFrame({"a": np.repeat([1.0, 2.0, 3.0], 40), "b": np.repeat([4.0, 5.0, 6.0], 40), "c": np.repeat([7.0, 8.0, 9.0], 40)})
    check("fail closed: holdout cannot be built without inflating beyond 3x the request or losing a class",
          raises(lambda: D.fit_preprocessor_with_client_holdout(make_pre(), tiny, np.tile([0, 1], 60), 0.05, 5), RuntimeError))

    # the V1 loader must refuse CICIoT2023 holdout, V2 must accept the argument
    spec = importlib.util.spec_from_file_location("src._v1_data_reference", ROOT / "src" / "data.py")
    v1data = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = v1data
    spec.loader.exec_module(v1data)
    from src.config import DataConfig
    cfgd = DataConfig(dataset_name="ciciot2023")
    check("V1 loader refuses CICIoT2023 holdout (documents the V1 failure)", raises(lambda: v1data.load_dataset(cfgd, 1, None, False, 0.2), NotImplementedError))
    import inspect
    check("V2 CICIoT2023 loader accepts holdout_fraction", "holdout_fraction" in inspect.signature(D.load_and_preprocess_ciciot2023).parameters)
    check("V2 experiment exposes the new accounting symbols", "no_valid_contribution" in inspect.getsource(E.run_experiment) and "privacy_attempts" in inspect.getsource(E.run_experiment))


# ---------------------------------------------------------------------------------------------------------------------------------------------
def part_cic() -> None:
    import joblib
    import src.data as D
    from src.config import Config
    from src.data_integrity import predictor_fingerprint
    from src.partitioning import make_partitions, split_client_holdout_by_mask

    cfg = Config.from_yaml(ROOT / "configs" / "supp_v2" / "ciciot_part_topk_indep.yaml")
    check("cic config: validation-only, blank test path, holdout 0.2", cfg.experiment.validation_only and cfg.data.test_csv == "" and cfg.fl.client_holdout_fraction == 0.2)
    audits = {}
    for seed in (12, 13, 12):
        t0 = time.time()
        pre_path = OUT / f"cic_pre_{seed}.joblib"
        b = D.load_dataset(cfg.data, seed=seed, preprocessor_output=pre_path, load_test=False, holdout_fraction=cfg.fl.client_holdout_fraction)
        a = b.client_holdout_audit
        key = "rerun12" if seed in audits else seed
        audits[key] = a
        print(f"  [load seed {seed}: {time.time() - t0:.0f}s, train rows {len(b.y_train)}, holdout rows {a['holdout_rows']}]", flush=True)
        if key == 12 or key == 13:
            check(f"cic seed {seed}: test partition never opened (empty test arrays, blank path)", len(b.y_test) == 0 and b.X_test.shape[0] == 0 and cfg.data.test_csv == "")
            check(f"cic seed {seed}: holdout mask covers training rows and has both classes", len(b.holdout_mask) == len(b.y_train) and a["holdout_attack_rows"] > 0 and a["holdout_benign_rows"] > 0,
                  f"holdout {a['holdout_rows']} ({a['realized_fraction']:.3f}); attack {a['holdout_attack_rows']} benign {a['holdout_benign_rows']}")
            enc = predictor_fingerprint(pd.DataFrame(b.X_train), list(range(b.X_train.shape[1])))
            check(f"cic seed {seed}: independent recomputation - no encoded vector straddles train/holdout", len(np.intersect1d(enc[b.holdout_mask], enc[~b.holdout_mask])) == 0)
            check(f"cic seed {seed}: no predictor group straddles train/holdout", len(np.intersect1d(b.holdout_groups[b.holdout_mask], b.holdout_groups[~b.holdout_mask])) == 0)
            scaler_n = [s.n_samples_seen_ for _, s in joblib.load(pre_path).named_transformers_["numeric"].steps if hasattr(s, "n_samples_seen_")]
            check(f"cic seed {seed}: preprocessor fitted on non-holdout rows only", int(np.ravel(scaler_n)[0]) == int((~b.holdout_mask).sum()), f"{np.ravel(scaler_n)[0]} vs {(~b.holdout_mask).sum()}")
            check(f"cic seed {seed}: reported realized fraction within [0.15, 0.30]", 0.15 <= a["realized_fraction"] <= 0.30, f"{a['realized_fraction']:.3f}")
            check(f"cic seed {seed}: separate calibration/selection/report partitions are intact (three-way split present, disjoint sizes recorded)",
                  b.X_thr is not None and b.X_rep is not None and len(b.y_val) > 0 and len(b.y_thr) > 0 and len(b.y_rep) > 0,
                  f"selection {len(b.y_val)}, calibration {len(b.y_thr)}, report {len(b.y_rep)}")
            parts = make_partitions(b.y_train, num_clients=cfg.fl.num_clients, strategy=cfg.fl.partition, seed=seed, dirichlet_alpha=cfg.fl.dirichlet_alpha, min_client_samples=cfg.fl.min_client_samples)
            tr, ho = split_client_holdout_by_mask(parts, b.holdout_mask)
            elig = [int((b.y_train[h] == 1).sum()) >= 10 for h in ho]
            check(f"cic seed {seed}: every client keeps training rows; eligibility computed", all(len(t) > 0 for t in tr), f"eligible clients for recall: {sum(elig)} of {len(elig)}")
            check(f"cic seed {seed}: client training partitions are disjoint from held-out rows", len(np.intersect1d(np.concatenate(tr), np.concatenate(ho))) == 0)
        del b
    check("cic: holdout is deterministic (seed 12 twice -> identical mask hash)", audits[12]["holdout_mask_sha256"] == audits["rerun12"]["holdout_mask_sha256"])
    check("cic: different seeds give different holdouts", audits[12]["holdout_mask_sha256"] != audits[13]["holdout_mask_sha256"])
    # holdout = 0 must be byte-identical to the V1 loader (the unaffected CIC path)
    spec = importlib.util.spec_from_file_location("src._v1_data_reference", ROOT / "src" / "data.py")
    v1data = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = v1data
    spec.loader.exec_module(v1data)
    b1 = v1data.load_dataset(cfg.data, seed=12, load_test=False)
    b2 = D.load_dataset(cfg.data, seed=12, load_test=False, holdout_fraction=0.0)
    same = all(np.array_equal(getattr(b1, f), getattr(b2, f)) for f in ("X_train", "y_train", "X_val", "y_val", "X_thr", "y_thr", "X_rep", "y_rep"))
    check("cic: holdout=0 reproduces the V1 loader exactly (X/y of train, selection, calibration, report)", same and b2.client_holdout_audit == {"enabled": False})


# ---------------------------------------------------------------------------------------------------------------------------------------------
def part_micro() -> None:
    """End-to-end micro run on UNSW-NB15 (validation-only) that FORCES zero-weight rounds: recovery_weight_factor=0 and the aggregation filter is patched to retain
    only the (zero-weight) surrogate updates whenever surrogates exist in a round."""
    import src.experiment as E
    import src.server as S
    from src.aggregation import AggregationResult
    from src.config import Config

    raw = yaml.safe_load((ROOT / "configs" / "supp_v2" / "unsw_sens_chi0_dp.yaml").read_text(encoding="utf-8"))
    out = OUT / "micro_zero_weight"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    raw["experiment"]["seed"] = 7
    raw["experiment"]["exact_output_dir"] = str(out)
    raw["fl"]["rounds"] = 12
    cfgp = OUT / "_micro_cfg.yaml"
    cfgp.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    cfg = Config.from_yaml(cfgp)
    check("micro: central-DP pipeline, chi_rec=0, validation-only", cfg.privacy.mode == "central_client" and cfg.failure.recovery_weight_factor == 0.0 and cfg.experiment.validation_only)

    orig_safe = E._safe_aggregate
    orig_apply = S.Server.apply_update
    calls = {"apply": 0, "agg": 0}

    def forced(updates, weights, cfg_):
        res, label = orig_safe(updates, weights, cfg_)
        zero = [i for i, w in enumerate(weights) if w == 0.0]
        calls["agg"] += 1
        if zero and calls["agg"] % 2 == 1:      # force abstention on every other aggregation that has surrogates; the rest follow the normal path
            return AggregationResult(update=res.update, kept_indices=zero, rejected_indices=[i for i in range(len(updates)) if i not in zero], distances=res.distances), label
        return res, label

    def counted(self, *a, **k):
        calls["apply"] += 1
        return orig_apply(self, *a, **k)

    E._safe_aggregate = forced
    S.Server.apply_update = counted
    try:
        E.run_experiment(cfg)
    finally:
        E._safe_aggregate, S.Server.apply_update = orig_safe, orig_apply
    rm = pd.read_csv(out / "round_metrics.csv")
    rm = rm[rm["round"] > 0].reset_index(drop=True)
    ab = rm[rm["no_valid_contribution"] == 1]
    ok_rows = rm[rm["no_valid_contribution"] == 0]
    check("micro: run completed without the V1 crash and forced at least one abstention round", len(rm) == 12 and len(ab) >= 1 and len(ok_rows) >= 1, f"{len(ab)} abstention round(s) of {len(rm)}")
    check("micro: abstention rounds add no Gaussian noise and report zero weights", bool((ab["privacy_noise_std"] == 0).all() and (ab["privacy_noise_l2_norm"] == 0).all() and (ab["surrogate_weight_share"] == 0).all() and (ab["real_weight_share"] == 0).all()))
    check("micro: abstention rounds record noisy_release = 0 and are flagged in actual_aggregation_method", bool((ab["noisy_release"] == 0).all() and ab["actual_aggregation_method"].str.contains("no_valid_contribution_abstain").all()))
    check("micro: Server.apply_update (hence momentum) was called exactly once per noisy release and never in abstention rounds", calls["apply"] == int((rm["noisy_release"] == 1).sum()) and calls["apply"] > 0,
          f"apply calls {calls['apply']}, noisy releases {int((rm['noisy_release'] == 1).sum())}, abstentions {len(ab)}")
    check("micro: non-abstaining rounds release with Gaussian noise (positive-weight path unchanged)", bool((ok_rows["noisy_release"] == 1).all() and (ok_rows["privacy_noise_std"] > 0).all()))
    prev = rm["val_f1"].shift(1)
    mdl_same = [abs(rm.loc[i, "val_f1"] - rm.loc[i - 1, "val_f1"]) < 1e-12 and abs(rm.loc[i, "val_roc_auc"] - rm.loc[i - 1, "val_roc_auc"]) < 1e-12 for i in ab.index if i > 0]
    check("micro: global model unchanged in an abstention round (validation metrics identical to the previous round)", bool(mdl_same) and all(mdl_same), f"{len(mdl_same)} comparable round(s)")
    last = rm.iloc[-1]
    check("micro: attempted-round counter = noisy releases + abstentions", int(last["attempted_privacy_rounds_cum"]) == int(last["noise_release_rounds_cum"]) + int(rm["no_valid_contribution"].sum()),
          f"attempted {int(last['attempted_privacy_rounds_cum'])}, releases {int(last['noise_release_rounds_cum'])}, abstentions {int(rm['no_valid_contribution'].sum())}")
    check("micro: conservative attempted-round epsilon >= release-based epsilon, and strictly greater when abstentions occurred",
          last["privacy_epsilon_attempted_rounds_conservative"] >= last["privacy_epsilon_estimate"] and (len(ab) == 0 or last["privacy_epsilon_attempted_rounds_conservative"] > last["privacy_epsilon_estimate"]),
          f"release {last['privacy_epsilon_estimate']:.4f}, attempted {last['privacy_epsilon_attempted_rounds_conservative']:.4f}")
    meta = json.loads((out / "run_metadata.json").read_text(encoding="utf-8"))["privacy"]["supp_v2_accounting"]
    check("micro: run_metadata records both accountings and labels them diagnostic, not certified", meta["both_are_diagnostic_estimates_not_certified_guarantees"] is True
          and meta["no_valid_contribution_rounds"] == len(ab) and meta["noisy_release_rounds"] == int(last["noise_release_rounds_cum"]))
    agg = pd.read_csv(out / "aggregation_diagnostics.csv")
    abr = set(ab["round"])
    sub = agg[agg["round"].isin(abr)]
    check("micro: aggregation diagnostics list zero applied weight for every update in abstention rounds (no surrogate silently weighted)", bool((sub["applied_weight_share"] == 0).all()) and bool((sub["raw_weight"][sub["is_recovered_update"]] == 0).all()))
    check("micro: no client-holdout audit content when holdout is disabled", json.loads((out / "client_holdout_audit.json").read_text(encoding="utf-8")) == {"enabled": False})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["unit", "cic", "micro", "all"], required=True)
    a = ap.parse_args()
    for name, fn in (("unit", part_unit), ("cic", part_cic), ("micro", part_micro)):
        if a.part in (name, "all"):
            RESULTS.clear()
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                import traceback
                traceback.print_exc()
                check(f"{name}: test part completed without an exception", False, repr(exc))
            (OUT / f"test_report_{name}.json").write_text(json.dumps({"part": name, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": RESULTS,
                                                                      "all_pass": all(r["pass"] for r in RESULTS)}, indent=1), encoding="utf-8")
            print(f"== {name}: {sum(r['pass'] for r in RESULTS)}/{len(RESULTS)} passed", flush=True)
    return 0 if all(json.loads(p.read_text())["all_pass"] for p in OUT.glob("test_report_*.json")) else 1


if __name__ == "__main__":
    sys.exit(main())
