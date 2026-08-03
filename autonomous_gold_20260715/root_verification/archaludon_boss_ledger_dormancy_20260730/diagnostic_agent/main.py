"""Read-only diagnostic adapter for the frozen Boss-ledger candidate.

The adapter does not alter the returned action.  It records the candidate's
own post-decision resolver telemetry so that a trace-identical evaluation can
be separated into absent opportunities and fail-closed rejections.
"""

from __future__ import annotations

import importlib.util
import json
import os
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
INNER_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_persistent_public_boss_access_ledger_last_copy_guard_v1"
)
INNER_PATH = INNER_DIR / "main.py"

_spec = importlib.util.spec_from_file_location(
    f"boss_ledger_diagnostic_inner_{id(object())}",
    INNER_PATH,
)
if _spec is None or _spec.loader is None:
    raise ImportError(INNER_PATH)
_inner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inner)


@contextmanager
def _inner_cwd():
    previous = Path.cwd()
    os.chdir(INNER_DIR)
    try:
        yield
    finally:
        os.chdir(previous)


def _card_ids(cards):
    result = []
    for card in cards or ():
        if isinstance(card, dict) and card.get("id") is not None:
            result.append(int(card["id"]))
    return result


def agent(obs):
    with _inner_cwd():
        action = _inner.agent(obs)

    telemetry_path = os.environ.get("PTCG_BOSS_DIAGNOSTIC_TELEMETRY")
    if telemetry_path:
        current = obs.get("current") or {}
        players = current.get("players") or []
        player_index = current.get("yourIndex")
        mine = (
            players[int(player_index)]
            if isinstance(player_index, int)
            and 0 <= int(player_index) < len(players)
            else {}
        )
        select = obs.get("select") or {}
        effect = select.get("effect") or {}
        state = _inner._boss_guard_debug_state()
        row = {
            "pid": os.getpid(),
            "turn": current.get("turn"),
            "turn_action_count": current.get("turnActionCount"),
            "your_index": player_index,
            "context": select.get("context"),
            "effect_card_id": effect.get("id"),
            "min_count": select.get("minCount"),
            "max_count": select.get("maxCount"),
            "hand_ids": _card_ids(mine.get("hand") or []),
            "action": list(action),
            "resolution": state.get("last_resolution"),
            "ledger_card_rows": state.get("cards"),
            "last_reset_reason": state.get("last_reset_reason"),
        }
        path = Path(telemetry_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    return action
