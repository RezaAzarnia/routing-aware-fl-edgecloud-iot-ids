"""Installs the SUPP_V2 source overlay: prepends src_v2/ to the search path of the existing `src` package, so that `src.data` and `src.experiment` resolve to
src_v2/data.py and src_v2/experiment.py while every other `src.*` module (and everything importing them, e.g. the audited diagnostics helpers) is the
unchanged SUPP_V1 implementation. Must run BEFORE any `src.<module>` import. Also reports which file every loaded `src.*` module came from."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = ROOT / "src_v2"
OVERLAY_MODULES = ("data", "experiment")


def install() -> None:
    sys.path.insert(0, str(ROOT))
    already = [m for m in sys.modules if m.startswith("src.")]
    if already:
        raise RuntimeError(f"src modules were imported before the V2 overlay was installed: {already}")
    import src

    overlay = str(OVERLAY)
    if overlay not in src.__path__:
        src.__path__.insert(0, overlay)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def import_provenance() -> dict:
    """Every loaded src.* module: file, sha256 (line-ending-normalised), and whether it is served from the V2 overlay. Fails if data/experiment are not V2."""
    mods = {}
    for name, mod in sorted(sys.modules.items()):
        if name == "src" or name.startswith("src."):
            f = getattr(mod, "__file__", None)
            if f:
                mods[name] = {"file": str(Path(f).resolve().relative_to(ROOT).as_posix()), "sha256": sha256(Path(f)), "from_v2_overlay": Path(f).resolve().parent == OVERLAY.resolve()}
    for m in OVERLAY_MODULES:
        key = f"src.{m}"
        if key not in mods or not mods[key]["from_v2_overlay"]:
            raise RuntimeError(f"{key} is not served from src_v2 (overlay inactive): {mods.get(key)}")
    return {"overlay_dir": "src_v2", "modules": mods, "overlay_modules": sorted(k for k, v in mods.items() if v["from_v2_overlay"]),
            "v1_modules_reused_unchanged": sorted(k for k, v in mods.items() if not v["from_v2_overlay"])}
