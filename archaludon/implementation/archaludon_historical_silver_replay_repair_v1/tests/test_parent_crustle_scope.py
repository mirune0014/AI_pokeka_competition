from __future__ import annotations

from pathlib import Path
import sys
import unittest


AUTO = Path(__file__).resolve().parents[3]
CANDIDATE = AUTO / "candidates" / "archaludon_historical_silver_replay_repair_v1"
sys.path.insert(0, str(CANDIDATE))

import _historical_silver_parent as parent
from cg.api import AreaType, OptionType, SelectContext, SelectType, to_observation_class


def card(card_id, serial, seat):
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(card_id, serial, seat, *, energy_serials=()):
    data = parent.CARD_DB[card_id]
    return {
        "id": card_id,
        "serial": serial,
        "hp": data.hp,
        "maxHp": data.hp,
        "appearThisTurn": False,
        "energies": [int(data.energyType) for _ in energy_serials],
        "energyCards": [card(parent.METAL_ENERGY, value, seat) for value in energy_serials],
        "tools": [],
        "preEvolution": [],
    }


def player(seat, hand, active, bench=(), *, discard=()):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": 40,
        "discard": list(discard),
        "prize": [None] * 4,
        "handCount": len(hand) if hand is not None else 0,
        "hand": hand,
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def option(option_type, **values):
    raw = {"type": int(option_type)}
    raw.update(values)
    return raw


def observation(*, opponent_active, opponent_bench=(), context=SelectContext.MAIN, opt=None):
    ours = player(
        0,
        [card(parent.ARCHALUDON_EX, 100, 0)],
        pokemon(parent.DURALUDON, 10, 0),
        discard=(card(parent.METAL_ENERGY, 201, 0), card(parent.METAL_ENERGY, 202, 0)),
    )
    theirs = player(
        1,
        None,
        pokemon(opponent_active, 20, 1),
        opponent_bench,
    )
    if opt is None:
        opt = option(
            OptionType.EVOLVE,
            area=int(AreaType.HAND),
            index=0,
            playerIndex=0,
            inPlayArea=int(AreaType.ACTIVE),
            inPlayIndex=0,
        )
    raw = {
        "select": {
            "type": int(SelectType.MAIN if context == SelectContext.MAIN else SelectType.CARD),
            "context": int(context),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [opt],
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": 6,
            "turnActionCount": 2,
            "yourIndex": 0,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": [ours, theirs],
        },
        "search_begin_input": None,
    }
    return to_observation_class(raw)


class ParentCrustleScopeTests(unittest.TestCase):
    def test_benched_crustle_does_not_block_evolution(self):
        obs = observation(opponent_active=723, opponent_bench=[pokemon(345, 30, 1)])
        score, reason = parent.apply_overrides(obs, obs.select.option[0], 1000, "base")
        self.assertGreater(score, -10000)
        self.assertNotIn("don't evolve", reason)

    def test_non_crustle_active_does_not_block_metal_defender(self):
        obs = observation(
            opponent_active=723,
            opponent_bench=[pokemon(345, 30, 1)],
            opt=option(OptionType.ATTACK, attackId=parent.METAL_DEFENDER),
        )
        score, reason = parent.apply_overrides(obs, obs.select.option[0], 220, "attack")
        self.assertEqual(score, 220)
        self.assertNotIn("Metal Defender does 0", reason)

    def test_active_crustle_keeps_evolution_and_metal_defender_denies(self):
        evolve = observation(opponent_active=345)
        score, reason = parent.apply_overrides(evolve, evolve.select.option[0], 1000, "base")
        self.assertEqual(score, -10000)
        self.assertEqual(reason, "Crustle active: don't evolve to ex")

        attack_obs = observation(
            opponent_active=345,
            opt=option(OptionType.ATTACK, attackId=parent.METAL_DEFENDER),
        )
        score, reason = parent.apply_overrides(
            attack_obs, attack_obs.select.option[0], 220, "attack"
        )
        self.assertEqual(score, -5000)
        self.assertEqual(reason, "Crustle active: Metal Defender does 0")

    def test_to_hand_and_discard_suppression_is_active_only(self):
        to_hand_opt = option(
            OptionType.CARD,
            area=int(AreaType.HAND),
            index=0,
            playerIndex=0,
        )
        inactive = observation(opponent_active=723, opponent_bench=[pokemon(345, 30, 1)], context=SelectContext.TO_HAND, opt=to_hand_opt)
        self.assertEqual(parent.apply_overrides(inactive, inactive.select.option[0], 100, "take")[0], 100)

        active = observation(opponent_active=345, context=SelectContext.TO_HAND, opt=to_hand_opt)
        self.assertEqual(parent.apply_overrides(active, active.select.option[0], 100, "take")[0], -3000)

        discard = observation(opponent_active=723, opponent_bench=[pokemon(345, 30, 1)], context=SelectContext.DISCARD, opt=to_hand_opt)
        self.assertEqual(parent.apply_overrides(discard, discard.select.option[0], -1, "discard")[0], -1)
        discard_active = observation(opponent_active=345, context=SelectContext.DISCARD, opt=to_hand_opt)
        self.assertEqual(parent.apply_overrides(discard_active, discard_active.select.option[0], -1, "discard")[0], 9000)

    def test_ogerpon_hard_rule_remains_unchanged(self):
        obs = observation(opponent_active=117)
        score, reason = parent.apply_overrides(obs, obs.select.option[0], 1000, "base")
        self.assertEqual(score, -10000)
        self.assertEqual(reason, "Ogerpon: don't evolve into Ability attacker")


if __name__ == "__main__":
    unittest.main()
