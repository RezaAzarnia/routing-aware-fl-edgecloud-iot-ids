import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


import shutil
import subprocess

import pytest


@pytest.fixture(scope="session")
def phase6c_tree(tmp_path_factory):
    """Directory holding the Phase 6C code exactly as locked (git tag phase6c-final-results).

    Phase 7 deliberately changes src/, so the Phase 6C code fingerprint must be verified against the locked
    commit, not against the Phase 7 working tree. Falls back to the working tree when the tag is absent
    (e.g. a clone without tags)."""
    ok = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "phase6c-final-results"], capture_output=True, cwd=ROOT).returncode == 0
    if not ok:
        return ROOT
    dest = tmp_path_factory.mktemp("p6c_locked")
    archive = dest / "tree.tar"
    subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), "phase6c-final-results"], check=True, cwd=ROOT)
    shutil.unpack_archive(str(archive), str(dest / "tree"))
    return dest / "tree"


# ---------------------------------------------------------------------------------------------------------------------
# Final-test protection (Phase 9C): ordinary test runs can NEVER open the locked final-test files. Tests that must read them
# are marked `authorized_integrity`, are deselected by default (pytest.ini) and, when selected, additionally require
# IOTFL_AUTHORIZED_FINAL_TEST_INTEGRITY=1 and an explicit `authorized(...)` block around the read.
import os

sys.path.insert(0, str(ROOT / "scripts" / "final_test"))
import protected_access_guard as _guard  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _protect_locked_final_test_files():
    _guard.install()
    yield
    assert not _guard.violations, f"locked final-test file access attempted: {_guard.violations}"
    _guard.uninstall()


def pytest_collection_modifyitems(config, items):
    if os.environ.get("IOTFL_AUTHORIZED_FINAL_TEST_INTEGRITY") == "1":
        return
    skip = pytest.mark.skip(reason="authorised integrity workflow only (set IOTFL_AUTHORIZED_FINAL_TEST_INTEGRITY=1 and run -m authorized_integrity)")
    for item in items:
        if "authorized_integrity" in item.keywords:
            item.add_marker(skip)
