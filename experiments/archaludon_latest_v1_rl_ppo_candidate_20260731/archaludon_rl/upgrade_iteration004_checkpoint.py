"""Create a byte-distinct iteration-004 checkpoint without running games/PPO."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

import torch

from .encoders import ACTION_DIM, ENCODER_SCHEMA_VERSION, STATE_DIM
from .frozen_sources import checkpoint_source_hashes
from .model import (
    MODEL_SCHEMA_VERSION,
    ModelConfig,
    ResidualActorCritic,
    load_checkpoint,
    save_checkpoint,
    sha256_checkpoint,
)
from .reference_policy import (
    behavior_policy_sha256,
    canonical_behavior_policy_receipt,
    validate_reference_prior_identity,
)


LEGACY_MODEL_SCHEMA_VERSION = "residual-actor-critic-v2"


def _validate_legacy_metadata(
    metadata: Mapping[str, Any],
    *,
    expected_sources: Mapping[str, str],
) -> None:
    if metadata.get("model_schema_version") != LEGACY_MODEL_SCHEMA_VERSION:
        raise ValueError("input is not the exact legacy v2 checkpoint schema")
    encoder = metadata.get("encoder") or {}
    if (
        encoder.get("schema_version") != ENCODER_SCHEMA_VERSION
        or encoder.get("state_dim") != STATE_DIM
        or encoder.get("action_dim") != ACTION_DIM
    ):
        raise ValueError("legacy checkpoint encoder schema/dimension mismatch")
    prior_receipt = metadata.get("reference_prior_receipt")
    if not isinstance(prior_receipt, Mapping):
        raise ValueError("legacy checkpoint reference-prior receipt missing")
    validate_reference_prior_identity(
        prior_receipt,
        metadata.get("reference_prior_schema_sha256"),
    )
    if dict(metadata.get("source_hashes") or {}) != dict(expected_sources):
        raise ValueError("legacy checkpoint frozen-source hashes mismatch")
    if (
        "behavior_policy_receipt" in metadata
        or "behavior_policy_schema_sha256" in metadata
    ):
        raise ValueError("legacy checkpoint unexpectedly has behavior provenance")


def upgrade_checkpoint(input_path: Path, output_path: Path) -> dict[str, Any]:
    source = input_path.resolve(strict=True)
    destination = output_path.resolve(strict=False)
    if source == destination:
        raise ValueError("output checkpoint must differ from input checkpoint")
    if destination.exists():
        raise FileExistsError(f"output checkpoint already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = torch.load(source, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or not isinstance(payload.get("metadata"), dict):
        raise ValueError("legacy checkpoint payload/metadata is invalid")
    expected_sources = checkpoint_source_hashes()
    metadata = dict(payload["metadata"])
    _validate_legacy_metadata(metadata, expected_sources=expected_sources)
    if payload.get("optimizer_state") is not None:
        raise ValueError("iteration-004 upgrade accepts an untrained zero checkpoint only")
    config = ModelConfig(**payload.get("model_config", {}))
    if config.state_dim != STATE_DIM or config.action_dim != ACTION_DIM:
        raise ValueError("legacy checkpoint model dimensions mismatch")
    model = ResidualActorCritic(config)
    model.load_state_dict(payload.get("model_state") or {}, strict=True)
    final = model.residual_head[-1]
    if (
        torch.count_nonzero(final.weight).item() != 0
        or torch.count_nonzero(final.bias).item() != 0
    ):
        raise ValueError("input residual output head is not exactly zero")

    input_hash = sha256_checkpoint(source)
    behavior_receipt = canonical_behavior_policy_receipt()
    upgraded_metadata = dict(metadata)
    upgraded_metadata.update(
        {
            "model_schema_version": MODEL_SCHEMA_VERSION,
            "behavior_policy_receipt": behavior_receipt,
            "behavior_policy_schema_sha256": behavior_policy_sha256(
                behavior_receipt
            ),
            "training": {
                **dict(metadata.get("training") or {}),
                "iteration004_behavior_contract_upgrade": {
                    "input_checkpoint_sha256": input_hash,
                    "games_run": 0,
                    "ppo_steps": 0,
                },
            },
        }
    )
    output_hash = save_checkpoint(destination, model, upgraded_metadata)
    loaded, loaded_metadata, optimizer_state = load_checkpoint(
        destination,
        expected_source_hashes=expected_sources,
        device="cpu",
    )
    if optimizer_state is not None:
        raise AssertionError("upgraded zero checkpoint gained optimizer state")
    for name, value in model.state_dict().items():
        if not torch.equal(value, loaded.state_dict()[name]):
            raise AssertionError(f"model weight changed during upgrade: {name}")
    if loaded_metadata != upgraded_metadata:
        raise AssertionError("upgraded checkpoint metadata roundtrip mismatch")
    if output_hash == input_hash:
        raise AssertionError("upgraded checkpoint is not byte-distinct")
    return {
        "input_checkpoint": str(source),
        "input_checkpoint_sha256": input_hash,
        "output_checkpoint": str(destination),
        "output_checkpoint_sha256": output_hash,
        "model_weights_unchanged": True,
        "source_receipts_unchanged": True,
        "zero_residual_output_head": True,
        "games_run": 0,
        "ppo_steps": 0,
        "behavior_policy_schema_sha256": behavior_policy_sha256(
            behavior_receipt
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-checkpoint", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(
        json.dumps(
            upgrade_checkpoint(args.input_checkpoint, args.output_checkpoint),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
