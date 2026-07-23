from __future__ import annotations

import importlib.util
import os
from pathlib import Path


_PARENT = Path(__file__).resolve().parent.parent
_SOURCE = _PARENT / "main.py"
_MODULE_NAME = "_alakazam_xerosic_certified_retained_triple_v1_runtime_source"
_previous_cwd = Path.cwd()
try:
    os.chdir(_PARENT)
    _spec = importlib.util.spec_from_file_location(_MODULE_NAME, _SOURCE)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Could not load {_SOURCE}")
    _source_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_source_module)
finally:
    os.chdir(_previous_cwd)

agent = _source_module.agent
__all__ = ["agent"]
