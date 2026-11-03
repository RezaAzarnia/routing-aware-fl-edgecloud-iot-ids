"""Runtime guard that makes an accidental READ of the locked final-test files impossible during ordinary work.

Protected = the official UNSW-NB15 testing CSV, the CICIoT2023 prepared test split and its provenance file, i.e. any file named
UNSW_NB15_testing-set.csv / test.csv.gz / test_provenance.csv.gz located under <repo>/data. Metadata queries (exists/stat) are NOT blocked;
only OPENING (builtins.open, io.open, os.open, and everything built on them: pandas.read_csv, gzip.open, Path.read_bytes/read_text/open,
hashlib via open) raises ``ProtectedFinalTestAccess``.

Use:
    from protected_access_guard import install, authorized
    install()                                   # block (idempotent)
    with authorized(path): ...                  # ONLY inside the authorised final-test evaluation / authorised integrity workflow
The guard cannot be switched off by an environment variable alone: the authorised workflow must call ``authorized(...)`` explicitly
(see FINAL_TEST_SAFE_EXECUTION_PLAN.md).
"""
from __future__ import annotations

import builtins
import contextlib
import io
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTECTED_NAMES = {"unsw_nb15_testing-set.csv", "test.csv.gz", "test_provenance.csv.gz"}
_installed = False
_orig = {}
_authorized: set[str] = set()
_extra_protected: set[str] = set()
violations: list[str] = []


class ProtectedFinalTestAccess(RuntimeError):
    """Raised when code tries to open a locked final-test file without explicit authorisation."""


def _norm(path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def is_protected(path) -> bool:
    try:
        p = _norm(path)
    except TypeError:                         # file descriptors and other non-path objects
        return False
    if p in _extra_protected:
        return True
    data_root = _norm(ROOT / "data")
    return os.path.basename(p) in PROTECTED_NAMES and (p == data_root or p.startswith(data_root + os.sep))


def _check(file):
    if isinstance(file, int):
        return
    if is_protected(file) and _norm(file) not in _authorized:
        violations.append(_norm(file))
        raise ProtectedFinalTestAccess(f"opening a locked final-test file is blocked: {file}")


def _wrap(fn):
    def wrapped(file, *args, **kwargs):
        _check(file)
        return fn(file, *args, **kwargs)
    wrapped.__wrapped_by_guard__ = True
    return wrapped


def install(extra_protected=()) -> None:
    global _installed
    for p in extra_protected:
        _extra_protected.add(_norm(p))
    if _installed:
        return
    _orig.update(builtins_open=builtins.open, io_open=io.open, os_open=os.open)
    builtins.open = _wrap(builtins.open)
    io.open = _wrap(io.open)
    os.open = _wrap(os.open)
    _installed = True


def uninstall() -> None:
    global _installed
    if not _installed:
        return
    builtins.open, io.open, os.open = _orig["builtins_open"], _orig["io_open"], _orig["os_open"]
    _installed = False
    _extra_protected.clear()


@contextlib.contextmanager
def authorized(*paths):
    keys = {_norm(p) for p in paths}
    _authorized.update(keys)
    try:
        yield
    finally:
        _authorized.difference_update(keys)
