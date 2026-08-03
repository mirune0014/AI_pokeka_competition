"""Local deployment wrapper for the independent behavior-cloned actor."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any


RUNTIME_DIR = Path(__file__).resolve().parent
PROJECT_DIR = RUNTIME_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from archaludon_rl.bc_actor import BehaviorCloningPolicy
from archaludon_rl.catalog import catalog_from_cg
from archaludon_rl.deployment_audit import DeploymentAudit
from archaludon_rl.frozen_sources import checkpoint_source_hashes
from archaludon_rl.model import load_checkpoint, sha256_checkpoint
from archaludon_rl.teacher_adapter import LatestV1Teacher


_controller: BehaviorCloningPolicy | None = None
_game_epoch = 0
_callback_ordinal = 0
_deployment_audit = DeploymentAudit.from_environment()


def _new_controller(*, seat: int | None) -> BehaviorCloningPolicy:
    global _game_epoch
    _game_epoch += 1
    checkpoint = os.environ.get("ARCHALUDON_BC_CHECKPOINT", "").strip()
    if not checkpoint:
        raise RuntimeError("ARCHALUDON_BC_CHECKPOINT is required")
    model, metadata, _ = load_checkpoint(
        Path(checkpoint),
        expected_source_hashes=checkpoint_source_hashes(),
        device=os.environ.get("ARCHALUDON_BC_DEVICE", "cpu"),
    )
    training = metadata.get("training") or {}
    if (
        training.get("algorithm") != "teacher_action_behavior_cloning"
        or training.get("actor_logits_only") is not True
        or float(training.get("teacher_fixed_margin", -1.0)) != 0.0
        or training.get("legal_action_mask") is not True
        or training.get("future_ppo_kl_reference") is not True
    ):
        raise ValueError("checkpoint is not an independent BC actor reference")
    teacher = LatestV1Teacher(game_id=f"runtime-bc-{_game_epoch}", seat=seat)
    return BehaviorCloningPolicy(
        teacher,
        model=model,
        checkpoint_sha256=sha256_checkpoint(checkpoint),
        catalog=catalog_from_cg(),
    )


def agent(observation: dict[str, Any]) -> list[int]:
    global _callback_ordinal, _controller
    current = observation.get("current") or {}
    select = observation.get("select")
    seat = current.get("yourIndex")
    if _controller is None or select is None:
        _controller = _new_controller(
            seat=int(seat) if seat in (0, 1) else None
        )
        _callback_ordinal = 0
    decision = _controller.decide(observation)
    _callback_ordinal += 1
    if _deployment_audit is not None:
        _deployment_audit.record(
            decision,
            game_epoch=_game_epoch,
            callback_ordinal=_callback_ordinal,
        )
    return list(decision.action)
