from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.dataset import complete_action_feature, episode_split


def test_episode_split_is_deterministic_and_exclusive():
    values = [episode_split(f'episode-{index}') for index in range(100)]
    assert set(values) <= {'training', 'validation'}
    assert [episode_split('episode-7')] * 2 == ['training' if episode_split('episode-7') == 'training' else 'validation'] * 2


def test_complete_action_set_pooling_has_fixed_width():
    vectors = [[1.0, 2.0], [3.0, 4.0]]
    feature = complete_action_feature(vectors, (0, 1))
    assert feature == [4.0, 6.0, 2.0, 3.0, 3.0, 4.0, 2 / 6]
