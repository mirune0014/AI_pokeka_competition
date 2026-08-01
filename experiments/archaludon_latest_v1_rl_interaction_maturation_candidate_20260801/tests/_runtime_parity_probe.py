"""Emit fixed-input policy outputs for default/single-thread parity tests."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--single-thread", action="store_true")
    args = parser.parse_args()

    required_environment = {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }
    if args.single_thread:
        os.environ.update(required_environment)

    from archaludon_rl.encoders import ACTION_DIM, STATE_DIM
    from archaludon_rl.frozen_sources import checkpoint_source_hashes
    from archaludon_rl.model import load_checkpoint
    from archaludon_rl.reference_policy import ReferencePolicy
    from archaludon_rl.runtime_contract import configure_single_thread_runtime

    if args.single_thread:
        configured = configure_single_thread_runtime()
    else:
        import torch

        configured = {
            "observed_thread_counts": {
                "torch_num_threads": int(torch.get_num_threads()),
                "torch_num_interop_threads": int(
                    torch.get_num_interop_threads()
                ),
            }
        }
    model, _, _ = load_checkpoint(
        args.checkpoint,
        expected_source_hashes=checkpoint_source_hashes(),
        device="cpu",
    )
    reference = ReferencePolicy()
    rows = []
    for option_count in (2, 3, 4, 7, 10, 19):
        state = [
            (((index + 1) * (option_count + 5)) % 29 - 14) / 14.0
            for index in range(STATE_DIM)
        ]
        actions = [
            [
                (
                    (
                        (option_index + 1) * 11
                        + (feature_index + 1) * 5
                        + option_count
                    )
                    % 31
                    - 15
                )
                / 15.0
                for feature_index in range(ACTION_DIM)
            ]
            for option_index in range(option_count)
        ]
        residuals, value = model.predict(state, actions)
        teacher_index = option_count // 2
        distribution = reference.distribution(
            option_count,
            teacher_index,
            residuals,
        )
        argmax = reference.deployment_argmax(distribution).index
        samples = [
            reference.training_sample(distribution, random.Random(seed)).index
            for seed in range(64)
        ]
        rows.append(
            {
                "option_count": option_count,
                "residuals": residuals,
                "value": value,
                "probabilities": distribution.probabilities,
                "argmax": argmax,
                "seeded_samples": samples,
            }
        )
    print(
        json.dumps(
            {
                "single_thread": args.single_thread,
                "observed_thread_counts": configured[
                    "observed_thread_counts"
                ],
                "rows": rows,
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

