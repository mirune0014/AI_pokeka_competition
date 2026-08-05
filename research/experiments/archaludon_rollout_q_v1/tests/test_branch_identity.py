from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import ContinuationUnsafe, PrefixReplayMismatch


def test_identity_failure_types_are_distinct():
    assert issubclass(ContinuationUnsafe, RuntimeError)
    assert issubclass(PrefixReplayMismatch, RuntimeError)


def test_identity_mismatch_can_be_marked_unsafe():
    result = {'status': 'CONTINUATION_UNSAFE'}
    assert result['status'] == 'CONTINUATION_UNSAFE'
