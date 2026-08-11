from collections import Counter

import pytest

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.hidden_sampler import (
    DeterminizationError,
    sample_hidden_zones,
)


class FakeApi:
    @staticmethod
    def all_card_data():
        return [{"cardId": card_id, "basic": card_id >= 100} for card_id in range(1, 161)]


def _card(card_id, serial):
    return {"id": card_id, "serial": serial, "playerIndex": 0}


def _observation():
    return {
        "select": {"deck": None},
        "current": {
            "yourIndex": 0,
            "looking": [],
            "stadium": [],
            "players": [
                {
                    "active": [{"id": 1, "serial": 1, "preEvolution": [], "energyCards": [], "tools": []}],
                    "bench": [],
                    "discard": [],
                    "hand": [_card(card_id, card_id) for card_id in range(2, 7)],
                    "handCount": 5,
                    "deckCount": 48,
                    "prize": [None] * 6,
                },
                {
                    "active": [{"id": 101, "serial": 101, "preEvolution": [], "energyCards": [], "tools": []}],
                    "bench": [],
                    "discard": [_card(102, 102)],
                    "hand": None,
                    "handCount": 4,
                    "deckCount": 48,
                    "prize": [None] * 6,
                },
            ],
        },
    }


def test_counter_counts_and_determinism():
    observation = _observation()
    your_deck = list(range(1, 61))
    opponent_deck = list(range(101, 161))
    first = sample_hidden_zones(
        observation,
        branch_group_id="a" * 64,
        rollout_index=0,
        your_deck=your_deck,
        opponent_deck=opponent_deck,
        api_module=FakeApi,
    )
    same = sample_hidden_zones(
        observation,
        branch_group_id="a" * 64,
        rollout_index=0,
        your_deck=your_deck,
        opponent_deck=opponent_deck,
        api_module=FakeApi,
    )
    different = sample_hidden_zones(
        observation,
        branch_group_id="a" * 64,
        rollout_index=1,
        your_deck=your_deck,
        opponent_deck=opponent_deck,
        api_module=FakeApi,
    )
    assert first.fingerprint == same.fingerprint
    assert first.fingerprint != different.fingerprint
    assert len(first.your_deck) == 48
    assert len(first.your_prize) == 6
    assert len(first.opponent_deck) == 48
    assert len(first.opponent_prize) == 6
    assert len(first.opponent_hand) == 4
    assert not set(first.your_deck) & set(range(2, 7))
    assert Counter([1, *range(2, 7), *first.your_deck, *first.your_prize]) == Counter(your_deck)
    assert Counter([101, 102, *first.opponent_deck, *first.opponent_prize, *first.opponent_hand]) == Counter(opponent_deck)


def test_inconsistent_counter_stops():
    with pytest.raises(DeterminizationError):
        sample_hidden_zones(
            _observation(),
            branch_group_id="b" * 64,
            rollout_index=0,
            your_deck=[999, *range(2, 61)],
            opponent_deck=list(range(101, 161)),
            api_module=FakeApi,
        )
