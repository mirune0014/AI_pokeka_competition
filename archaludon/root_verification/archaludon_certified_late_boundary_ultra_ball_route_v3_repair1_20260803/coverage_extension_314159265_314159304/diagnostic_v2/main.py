"""Local-only telemetry wrapper for the exact Rule 3 v2 comparison parent."""

import importlib.util
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
TARGET_DIR = ROOT / (
    "archaludon/candidates/"
    "archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2"
)
sys.path.insert(0, str(TARGET_DIR))
SPEC = importlib.util.spec_from_file_location(
    "rule3_v2_diagnostic_target", TARGET_DIR / "main.py"
)
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)
LOG = Path(os.environ.get("RULE3_V2_TELEMETRY", str(HERE / "telemetry.jsonl")))


def agent(obs):
    action = TARGET.agent(obs)
    current = obs.get("current") or {}
    select = obs.get("select") or {}
    row = {
        "turn": current.get("turn"),
        "turnActionCount": current.get("turnActionCount"),
        "seat": current.get("yourIndex"),
        "context": select.get("context"),
        "action": action,
        "telemetry": TARGET._last_telemetry,
    }
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return action
