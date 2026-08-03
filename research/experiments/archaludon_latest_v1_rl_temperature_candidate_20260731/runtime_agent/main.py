"""Local deployment wrapper for the clean-room latest-v1 residual policy.

No checkpoint means byte-for-byte action parity with exact latest-v1.  This
directory is a local runtime surface, not a Kaggle package.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any


RUNTIME_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RUNTIME_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from archaludon_rl.catalog import catalog_from_cg
from archaludon_rl.effect_features import EffectCatalog
from archaludon_rl.frozen_sources import checkpoint_source_hashes
from archaludon_rl.policy import PolicyConfig, ResidualPolicy
from archaludon_rl.teacher_adapter import LatestV1Teacher


_controller: ResidualPolicy | None = None
_game_epoch = 0


def _source_hashes() -> dict[str, str]:
    return checkpoint_source_hashes()


def _new_controller(*, seat: int | None) -> ResidualPolicy:
    global _game_epoch
    _game_epoch += 1
    teacher = LatestV1Teacher(game_id=f"runtime-{_game_epoch}", seat=seat)
    checkpoint = os.environ.get("ARCHALUDON_RL_CHECKPOINT", "").strip()
    if not checkpoint:
        return ResidualPolicy(
            teacher,
            model=None,
            catalog=EffectCatalog(),
            config=PolicyConfig(mode="deployment"),
        )
    from archaludon_rl.model import load_checkpoint, sha256_checkpoint

    model, _, _ = load_checkpoint(
        Path(checkpoint),
        expected_source_hashes=_source_hashes(),
        device=os.environ.get("ARCHALUDON_RL_DEVICE", "cpu"),
    )
    return ResidualPolicy(
        teacher,
        model=model,
        checkpoint_sha256=sha256_checkpoint(checkpoint),
        catalog=catalog_from_cg(),
        config=PolicyConfig(mode="deployment"),
    )


def agent(observation: dict[str, Any]) -> list[int]:
    global _controller
    current = observation.get("current") or {}
    select = observation.get("select")
    seat = current.get("yourIndex")
    if _controller is None or select is None:
        _controller = _new_controller(
            seat=int(seat) if seat in (0, 1) else None
        )
    return list(_controller.decide(observation).action)
