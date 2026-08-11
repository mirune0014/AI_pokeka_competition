from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock


AUTONOMOUS_ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = (
    AUTONOMOUS_ROOT
    / "candidates"
    / "archaludon_historical_silver_replay_repair_alakazam_lillie_v1"
)
sys.path.insert(0, str(CANDIDATE))

import main
from cg.api import AreaType, OptionType, SelectContext, SelectType, to_observation_class


def card(card_id: int, serial: int, seat: int) -> dict:
    return {"id": card_id, "serial": serial, "playerIndex": seat}


def pokemon(
    card_id: int,
    serial: int,
    seat: int,
    *,
    hp: int | None = None,
    max_hp: int | None = None,
    energy_ids: tuple[int, ...] = (),
    status: dict | None = None,
    tools: tuple[int, ...] = (),
) -> dict:
    data = main._parent.CARD_DB[card_id]
    actual_max_hp = data.hp if max_hp is None else max_hp
    actual_hp = actual_max_hp if hp is None else hp
    status = {} if status is None else status
    return {
        "id": card_id,
        "serial": serial,
        "hp": actual_hp,
        "maxHp": actual_max_hp,
        "appearThisTurn": False,
        "energies": [
            int(main._parent.CARD_DB[eid].energyType) for eid in energy_ids
        ],
        "energyCards": [card(eid, serial + 100 + i, seat) for i, eid in enumerate(energy_ids)],
        "tools": [card(tid, serial + 200 + i, seat) for i, tid in enumerate(tools)],
        "preEvolution": [],
        "asleep": bool(status.get("asleep", False)),
        "paralyzed": bool(status.get("paralyzed", False)),
        "confused": bool(status.get("confused", False)),
        "poisoned": bool(status.get("poisoned", False)),
        "burned": bool(status.get("burned", False)),
    }


def player(
    seat: int,
    hand: list[dict] | None,
    active: dict,
    bench: list[dict] | None = None,
    *,
    deck_count: int,
    prizes: int,
    hand_count: int | None = None,
    discard: list[dict] | None = None,
) -> dict:
    hand_count = len(hand or []) if hand_count is None else hand_count
    return {
        "active": [active],
        "bench": [] if bench is None else bench,
        "benchMax": 5,
        "deckCount": deck_count,
        "discard": [] if discard is None else discard,
        "prize": [None] * prizes,
        "handCount": hand_count,
        "hand": hand,
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def play(index: int, seat: int = 0) -> dict:
    return {
        "type": int(OptionType.PLAY),
        "index": index,
        "playerIndex": seat,
    }


def attach(index: int, seat: int = 0) -> dict:
    return {
        "type": int(OptionType.ATTACH),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": seat,
        "inPlayArea": int(AreaType.ACTIVE),
        "inPlayIndex": 0,
    }


def evolve(index: int, seat: int = 0) -> dict:
    return {
        "type": int(OptionType.EVOLVE),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": seat,
        "inPlayArea": int(AreaType.ACTIVE),
        "inPlayIndex": 0,
    }


def attack(attack_id: int) -> dict:
    return {"type": int(OptionType.ATTACK), "attackId": attack_id}


def end() -> dict:
    return {"type": int(OptionType.END)}


def base_raw(*, options: list[dict] | None = None) -> dict:
    hand = [
        card(main._LILLIE, 1, 0),
        card(main._LILLIE, 2, 0),
        card(main._parent.NIGHT_STRETCHER, 3, 0),
        card(main._METAL_ENERGY, 4, 0),
        card(main._BOSS, 5, 0),
        card(main._METAL_ENERGY, 6, 0),
        card(main._LILLIE, 7, 0),
    ]
    own_active = pokemon(
        main._DURALUDON,
        63,
        0,
        hp=230,
        max_hp=230,
        energy_ids=(main._METAL_ENERGY,) * 3,
        tools=(main._parent.HERO_CAPE,),
    )
    opponent_active = pokemon(
        main._parent.ALAKAZAM,
        26,
        1,
        hp=140,
        max_hp=140,
        energy_ids=(19,),
    )
    opponent_bench = [pokemon(742, 27, 1, hp=80, max_hp=80)]
    ours = player(0, hand, own_active, deck_count=33, prizes=5)
    theirs = player(
        1,
        None,
        opponent_active,
        opponent_bench,
        deck_count=24,
        prizes=5,
        hand_count=15,
    )
    if options is None:
        options = [
            play(0),
            play(1),
            play(2),
            attach(3),
            play(4),
            attach(5),
            play(6),
            attack(223),
            attack(main._parent.RAGING_HAMMER),
            end(),
        ]
    return {
        "select": {
            "type": int(SelectType.MAIN),
            "context": int(SelectContext.MAIN),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": options,
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": 4,
            "turnActionCount": 4,
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


class AlakazamLillieSurvivalTests(unittest.TestCase):
    def setUp(self) -> None:
        main._setup_ledger = None
        main._materialization_owner = None
        main._last_proposal = None
        main._parent._opp_last_attack_id = None
        main._parent._cur_turn_logs.clear()

    def call(self, raw: dict) -> tuple[list[int], object]:
        obs = to_observation_class(copy.deepcopy(raw))
        with mock.patch.object(main._parent, "agent", wraps=main._parent.agent) as parent_agent:
            action = main.agent(raw)
            self.assertEqual(parent_agent.call_count, 1)
        return action, obs

    def helper(self, raw: dict) -> bool:
        return main._parent.should_prioritize_lillie_against_alakazam(
            to_observation_class(copy.deepcopy(raw))
        )

    def test_episode_91850626_after_cape_prefers_lillie(self):
        raw = base_raw()
        action, _ = self.call(raw)
        self.assertEqual(action, [0])
        self.assertTrue(self.helper(raw))
        self.assertEqual(20 * (15 + 1), 320)

    def test_episode_91850626_before_cape_keeps_cape_first(self):
        raw = base_raw()
        raw["current"]["players"][0]["active"][0]["tools"] = []
        raw["current"]["players"][0]["hand"].append(card(main._parent.HERO_CAPE, 8, 0))
        raw["current"]["players"][0]["handCount"] += 1
        raw["select"]["option"].insert(7, play(7))
        action, _ = self.call(raw)
        self.assertEqual(action, [7])
        self.assertTrue(self.helper(raw))

    def test_episode_91850626_keeps_pokegear_first(self):
        raw = base_raw()
        raw["current"]["players"][0]["hand"].append(card(main._parent.POKEGEAR, 8, 0))
        raw["current"]["players"][0]["handCount"] += 1
        raw["select"]["option"].insert(7, play(7))
        action, _ = self.call(raw)
        self.assertEqual(action, [7])

    def test_backup_duraludon_play_is_not_preempted(self):
        raw = base_raw()
        raw["current"]["players"][0]["hand"].append(card(main._DURALUDON, 8, 0))
        raw["current"]["players"][0]["handCount"] += 1
        raw["select"]["option"].insert(7, play(7))
        action, _ = self.call(raw)
        self.assertEqual(action, [7])

    def test_archaludon_ex_evolution_is_not_preempted(self):
        raw = base_raw()
        raw["current"]["players"][0]["hand"].append(card(main._ARCHALUDON_EX, 8, 0))
        raw["current"]["players"][0]["handCount"] += 1
        raw["select"]["option"].insert(7, evolve(7))
        action, _ = self.call(raw)
        self.assertEqual(action, [7])
        self.assertFalse(self.helper(raw))

    def test_non_ko_attack_loses_to_survival_lillie(self):
        raw = base_raw()
        raw["current"]["players"][0]["hand"].pop(4)
        raw["current"]["players"][0]["handCount"] -= 1
        raw["select"]["option"][4] = end()
        action, _ = self.call(raw)
        self.assertEqual(action, [0])

    def test_end_turn_loses_to_survival_lillie(self):
        raw = base_raw()
        raw["select"]["option"] = [play(0), play(1), play(2), attach(3), play(6), end()]
        action, _ = self.call(raw)
        self.assertEqual(action, [0])

    def test_current_alakazam_ko_disables_survival_priority(self):
        raw = base_raw()
        raw["current"]["players"][1]["active"][0]["hp"] = 80
        action, _ = self.call(raw)
        self.assertEqual(action, [8])
        self.assertFalse(self.helper(raw))

    def test_existing_backup_bench_disables_survival_priority(self):
        raw = base_raw()
        raw["current"]["players"][0]["bench"] = [pokemon(main._DURALUDON, 88, 0)]
        action, _ = self.call(raw)
        self.assertNotEqual(action, [0])
        self.assertFalse(self.helper(raw))

    def test_powerful_hand_floor_below_hp_disables_priority(self):
        raw = base_raw()
        raw["current"]["players"][1]["handCount"] = 5
        action, _ = self.call(raw)
        self.assertNotEqual(action, [0])
        self.assertFalse(self.helper(raw))

    def test_benched_alakazam_does_not_trigger(self):
        raw = base_raw()
        raw["current"]["players"][1]["active"] = [pokemon(742, 26, 1, hp=80, max_hp=80)]
        raw["current"]["players"][1]["bench"] = [pokemon(main._parent.ALAKAZAM, 27, 1)]
        action, _ = self.call(raw)
        self.assertNotEqual(action, [0])
        self.assertFalse(self.helper(raw))

    def test_unpayable_powerful_hand_does_not_trigger(self):
        raw = base_raw()
        raw["current"]["players"][1]["active"][0]["energyCards"] = []
        raw["current"]["players"][1]["active"][0]["energies"] = []
        action, _ = self.call(raw)
        self.assertNotEqual(action, [0])
        self.assertFalse(self.helper(raw))

    def test_attack_preventing_status_disables_priority(self):
        for status in ("asleep", "paralyzed", "confused"):
            with self.subTest(status=status):
                raw = base_raw()
                raw["current"]["players"][1][status] = True
                action, _ = self.call(raw)
                self.assertNotEqual(action, [0])
                self.assertFalse(self.helper(raw))

    def test_three_or_fewer_prizes_disables_priority(self):
        for prizes in (3, 2, 1):
            with self.subTest(prizes=prizes):
                raw = base_raw()
                raw["current"]["players"][0]["prize"] = [None] * prizes
                action, _ = self.call(raw)
                self.assertNotEqual(action, [0])
                self.assertFalse(self.helper(raw))

    def test_unusable_lillie_disables_priority(self):
        raw = base_raw()
        raw["current"]["supporterPlayed"] = True
        raw["current"]["players"][0]["hand"] = [
            card(main._parent.NIGHT_STRETCHER, 2, 0),
            card(main._BOSS, 3, 0),
        ]
        raw["current"]["players"][0]["handCount"] = 2
        raw["current"]["players"][0]["deckCount"] = 0
        raw["current"]["players"][1]["deckCount"] = 0
        raw["current"]["players"][1]["bench"] = []
        raw["select"]["option"] = [play(0), play(1), attack(main._parent.RAGING_HAMMER), end()]
        action, _ = self.call(raw)
        self.assertIn(action, ([0], [2], [3]))
        self.assertFalse(self.helper(raw))


if __name__ == "__main__":
    unittest.main()
