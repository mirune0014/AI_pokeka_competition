"""Evaluation-only loader for one staged Alakazam version.

The staged versions use sibling absolute imports such as ``planner_final_policy``.
This adapter clears only that agent-local module namespace before loading the
selected version, so two staged versions can coexist in one battle process
without reusing the first-loaded policy modules.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


_VERSION = Path(__file__).resolve().parent.name
_TARGET = Path(__file__).resolve().parents[2] / "versions" / _VERSION
_SOURCE = _TARGET / "main.py"
_LOCAL_NAMES = {"_cumulative_parent"}
_LOCAL_PREFIXES = ("planner_",)

for _name in tuple(sys.modules):
    if _name in _LOCAL_NAMES or _name.startswith(_LOCAL_PREFIXES):
        sys.modules.pop(_name, None)

_target_path = str(_TARGET)
sys.path[:] = [_target_path] + [
    entry for entry in sys.path if entry != _target_path
]

_previous = Path.cwd()
try:
    os.chdir(_TARGET)
    _spec = importlib.util.spec_from_file_location(
        f"_staged_alakazam_{_VERSION}_source",
        _SOURCE,
    )
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Could not load {_SOURCE}")
    _module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_module)
finally:
    os.chdir(_previous)

def agent(obs):
    """Call the loaded policy with its own source directory first on sys.path."""

    previous_path = list(sys.path)
    previous_cwd = Path.cwd()
    try:
        sys.path[:] = [_target_path] + [
            entry for entry in sys.path if entry != _target_path
        ]
        os.chdir(_TARGET)
        return _module.agent(obs)
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path


EVAL_TARGET = str(_TARGET)
__all__ = ["agent", "EVAL_TARGET"]
