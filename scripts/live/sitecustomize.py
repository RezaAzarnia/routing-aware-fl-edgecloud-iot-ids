"""Opt-in activation of live logging: only when the environment variable IOTFL_LIVE=1 is set.

Python imports `sitecustomize` automatically at interpreter start-up if this directory is on PYTHONPATH.
When active, a meta-path finder patches `src.experiment` right after it is imported (see live_hook.py).
Everything is wrapped in try/except: this file can never prevent Python or a run from starting.
"""
import os
import sys

if os.environ.get("IOTFL_LIVE") == "1":
    try:
        import importlib.abc

        class _LiveFinder(importlib.abc.MetaPathFinder):
            _busy = False

            def find_spec(self, name, path, target=None):
                if name != "src.experiment" or _LiveFinder._busy:
                    return None
                _LiveFinder._busy = True
                try:
                    spec = None
                    for finder in sys.meta_path:
                        if finder is self or not hasattr(finder, "find_spec"):
                            continue
                        spec = finder.find_spec(name, path, target)
                        if spec is not None:
                            break
                finally:
                    _LiveFinder._busy = False
                if spec is None or spec.loader is None:
                    return None
                original = spec.loader

                class _Loader(importlib.abc.Loader):
                    def create_module(self, s):
                        return original.create_module(s)

                    def exec_module(self, module):
                        original.exec_module(module)
                        try:
                            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                            import live_hook

                            live_hook.install(module)
                        except Exception as exc:  # noqa: BLE001
                            print(f"[LIVE] could not install live logging: {exc!r}", file=sys.stderr)

                spec.loader = _Loader()
                return spec

        sys.meta_path.insert(0, _LiveFinder())
    except Exception:  # noqa: BLE001
        pass
