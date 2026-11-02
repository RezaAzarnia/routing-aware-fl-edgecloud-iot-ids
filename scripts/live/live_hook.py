"""Live per-round logging for every experiment/seed WITHOUT touching the locked training code.

Installed (opt-in) by scripts/live/sitecustomize.py when IOTFL_LIVE=1. It wraps two things in the freshly imported
`src.experiment` module and returns their results unchanged (no RNG use, no change to any computation):
  * `_evaluate_protocol(cfg, bundle, server)`  - called once for round 0 and once at the end of every round;
  * `Client.train_local(...)`                    - only to read the local training loss from its return value.
Each round appends one JSON line to <run_dir>/live_progress.jsonl and prints one human-readable line to stderr
(which the runner stores in results_phase6c/_logs/<run>.log). Any logging error is swallowed: logging can never
break or alter a run.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

_START = time.time()
_STATES: dict = {}
_CURRENT = {"state": None}
_WARNED = {"done": False}


def _run_dir(cfg) -> Path:
    exp = cfg.experiment
    if getattr(exp, "exact_output_dir", None):
        return Path(exp.exact_output_dir)
    return Path(exp.output_dir) / exp.name / exp.method_name / f"seed_{exp.seed}"


def _fmt(seconds) -> str:
    if seconds is None or not math.isfinite(seconds):
        return "--:--"
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _num(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


class _RunState:
    def __init__(self, cfg, device: str) -> None:
        self.cfg = cfg
        self.calls = 0
        self.losses: list = []
        self.t_loop_start = None
        self.t_last = None
        self.finished = False
        self.device = device
        self.run_dir = _run_dir(cfg)
        self.label = f"{cfg.data.dataset_name}/{cfg.experiment.method_name}/seed{cfg.experiment.seed}"


def _log_round(state: _RunState, selected: dict) -> None:
    cfg = state.cfg
    total = int(cfg.fl.rounds)
    round_number = state.calls
    now = time.time()
    if round_number == 0:
        state.t_loop_start = state.t_last = now
        loss = None
    else:
        loss = float(sum(state.losses) / len(state.losses)) if state.losses else None
    round_seconds = None if round_number == 0 else now - state.t_last
    state.t_last = now
    state.losses = []
    loop_elapsed = now - state.t_loop_start
    eta = None
    if round_number > 0:
        eta = loop_elapsed / round_number * (total - round_number)
    record = {
        "t_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "run": state.label, "seed": int(cfg.experiment.seed), "device": state.device,
        "round": round_number, "rounds_total": total, "pct": round(100.0 * round_number / max(total, 1), 1),
        "train_loss": _num(loss), "val_f1": _num(selected.get("f1")), "val_roc_auc": _num(selected.get("roc_auc")),
        "val_pr_auc": _num(selected.get("pr_auc")), "val_fpr": _num(selected.get("fpr")),
        "val_recall": _num(selected.get("recall_adr")), "val_precision": _num(selected.get("precision")),
        "round_seconds": _num(round_seconds), "elapsed_s": round(now - _START, 1), "eta_s": _num(eta),
    }
    try:
        state.run_dir.mkdir(parents=True, exist_ok=True)
        with open(state.run_dir / "live_progress.jsonl", "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001
        pass

    def f(v, spec):
        return format(v, spec) if v is not None else "  n/a"

    line = (f"[LIVE] {state.label} [{state.device}] round {round_number:>2}/{total} ({record['pct']:>5.1f}%) "
            f"loss {f(record['train_loss'], '.4f')} F1 {f(record['val_f1'], '.4f')} AUC {f(record['val_roc_auc'], '.4f')} "
            f"| {f(record['round_seconds'], '5.1f')}s/round | elapsed {_fmt(now - _START)} | ETA {_fmt(eta)}")
    print(line, file=sys.stderr, flush=True)


def install(module) -> None:
    """Patch the imported `src.experiment` module in place."""
    from src.client import Client

    if getattr(module, "_iotfl_live_installed", False):
        return
    original_eval = module._evaluate_protocol
    original_train = Client.train_local

    def eval_wrapper(cfg, bundle, server):
        result = original_eval(cfg, bundle, server)
        try:
            state = _STATES.get(id(cfg))
            if state is None or state.cfg is not cfg or state.finished:
                state = _RunState(cfg, str(getattr(server, "device", "cpu")))
                _STATES[id(cfg)] = state
                _CURRENT["state"] = state
            if state.calls <= int(cfg.fl.rounds):
                _log_round(state, result[1])
            state.calls += 1
            if state.calls > int(cfg.fl.rounds):
                # the remaining calls are the final reporting evaluations; stop logging after them
                if state.calls >= int(cfg.fl.rounds) + 3:
                    state.finished = True
        except Exception as exc:  # noqa: BLE001
            if not _WARNED["done"]:
                _WARNED["done"] = True
                print(f"[LIVE] logging disabled after an internal error: {exc!r}", file=sys.stderr, flush=True)
        return result

    def train_wrapper(self, *args, **kwargs):
        result = original_train(self, *args, **kwargs)
        try:
            state = _CURRENT["state"]
            if state is not None and not state.finished:
                state.losses.append(float(result.mean_loss))
        except Exception:  # noqa: BLE001
            pass
        return result

    module._evaluate_protocol = eval_wrapper
    Client.train_local = train_wrapper
    module._iotfl_live_installed = True
