from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[4]
CANDIDATE = ROOT / (
    "autonomous_gold_20260715/candidates/"
    "archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2"
)
sys.path.insert(0, str(CANDIDATE))
spec = importlib.util.spec_from_file_location(
    "rule3_repair_v2_diagnostic_impl", CANDIDATE / "main.py"
)
impl = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(impl)


def agent(obs_dict):
    action = impl.agent(obs_dict)
    current = obs_dict.get("current") or {}
    telemetry = impl._last_telemetry
    owner_after = telemetry.get("owner_after") or {}
    if telemetry.get("rule_id") == impl._RULE3_ID and (
        owner_after.get("stage") == "ULTRA_EMITTED"
        or telemetry.get("rule3_completed")
        or telemetry.get("irreversible_abort_fault")
        or (telemetry.get("proof_gates") or {}).get("provisional_release")
    ):
        print(
            "RULE3_DIAGNOSTIC "
            + json.dumps(
                {
                    "turn_action_count": current.get("turnActionCount"),
                    "context": (obs_dict.get("select") or {}).get("context"),
                    "action": action,
                    "logs": obs_dict.get("logs"),
                    "active": (current.get("players") or [])[current["yourIndex"]].get("active"),
                    "telemetry": impl._last_telemetry,
                },
                ensure_ascii=False,
                default=repr,
            )
        )
    return action
