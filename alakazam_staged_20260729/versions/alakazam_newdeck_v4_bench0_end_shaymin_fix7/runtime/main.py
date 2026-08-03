from __future__ import annotations

import importlib.util
import os
import sys


_PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)
_SOURCE = os.path.join(_PARENT, "main.py")
_MODULE_NAME = "_alakazam_integrated_domain_turn_planner_v1_runtime_source"
_previous_cwd = os.getcwd()
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


def get_last_v0_port_trace():
    return _source_module.LAST_V0_PORT_TRACE


def get_last_staged_policy_trace():
    return _source_module.LAST_STAGED_POLICY_TRACE


def __getattr__(name):
    if name == 'LAST_V0_PORT_TRACE':
        return _source_module.LAST_V0_PORT_TRACE
    if name == 'LAST_V1_PACKAGE_TRACE':
        return _source_module.LAST_V1_PACKAGE_TRACE
    if name == 'LAST_STAGED_POLICY_TRACE':
        return _source_module.LAST_STAGED_POLICY_TRACE
    raise AttributeError(name)

__all__ = ["agent"]
