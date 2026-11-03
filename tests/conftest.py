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
