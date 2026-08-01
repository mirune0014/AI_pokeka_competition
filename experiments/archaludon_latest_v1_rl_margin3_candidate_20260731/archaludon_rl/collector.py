"""Engine-agnostic collection coordinator for checked external runners.

This module intentionally contains no simulator imports or search calls.  The
checked deterministic engine/tooling owns episode execution and feeds callback
observations/results into this coordinator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .policy import ResidualPolicy
from .trajectory import (
    EpisodeBuilder,
    compare_duplicate_traces,
    publish_clean_episode,
    record_failure,
)


CHECKED_PAIRED_RUNNER = "tools/run_seeded_paired_suite.py"


class EpisodeCollector:
    def __init__(
        self,
        *,
        policy: ResidualPolicy,
        builder: EpisodeBuilder,
        output_path: Path,
        failures_ledger: Path,
    ) -> None:
        self.policy = policy
        self.builder = builder
        self.output_path = output_path
        self.failures_ledger = failures_ledger

    def callback(self, observation: Any) -> list[int]:
        decision = self.policy.decide(observation)
        self.builder.append(observation, decision)
        return list(decision.action)

    def terminal(
        self,
        result: int,
        *,
        action_errors: int = 0,
        exception: str | None = None,
        max_step_hit: bool = False,
        terminal_observation: Any | None = None,
    ) -> Mapping[str, Any]:
        episode = self.builder.finish(
            terminal_result=result,
            clean_terminal=True,
            action_errors=action_errors,
            exception=exception,
            max_step_hit=max_step_hit,
            terminal_observation=terminal_observation,
        )
        if episode["clean_terminal"]:
            publish_clean_episode(self.output_path, episode)
        else:
            record_failure(
                self.failures_ledger,
                episode_id=episode["episode_id"],
                reason="unclean_terminal",
                details={
                    "result": result,
                    "action_errors": action_errors,
                    "exception": exception,
                    "max_step_hit": max_step_hit,
                },
            )
        return episode


def validate_duplicate_pair(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> Mapping[str, Any]:
    result = compare_duplicate_traces(first, second)
    if not result["equal"]:
        raise ValueError(
            f"A/B duplicate canonical decision traces differ at "
            f"{result['mismatch_indices']}"
        )
    return result
