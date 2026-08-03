from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


CANDIDATE = Path(__file__).resolve().parent
REPOSITORY = CANDIDATE.parents[2]
AUTONOMOUS = REPOSITORY / "archaludon"
PARENT = (
    AUTONOMOUS
    / "candidates"
    / "alakazam_mandatory_draw_reserve_kadabra_resource_first_v1"
)
ENGINE = (
    REPOSITORY
     / "_local_generated" / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
REPLAY = (
    AUTONOMOUS
    / "live"
    / "54802782"
    / "refresh_20260719_0524"
    / "episode_86746844_replay.json"
)
EXPECTED_PARENT = {
    "source": "3EFFE5520F6B1C2F8283B25ED4A76564BCB3305E213FFA87612BA4A7A2CF606B",
    "runtime": "1E41868984188606AA879305CD5F66F59C8FE5235E94BC1B7CFB3B2013A1D04E",
    "deck": "7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141",
}

if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from cg.api import (  # noqa: E402
    AreaType,
    EnergyType,
    OptionType,
    SelectContext,
    to_observation_class,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


@contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def load_module(name: str, directory: Path, filename: str = "main.py"):
    with pushd(directory):
        spec = importlib.util.spec_from_file_location(name, directory / filename)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module


BASE = copy.deepcopy(
    json.loads(REPLAY.read_text(encoding="utf-8"))["steps"][135][1][
        "observation"
    ]
)


def _card(card_id: int, serial: int, owner: int) -> dict:
    return {"id": card_id, "serial": serial, "playerIndex": owner}


def _pokemon(
    card_id: int,
    serial: int,
    owner: int,
    *,
    hp: int,
    energy_ids: tuple[int, ...] = tuple(),
    tool_ids: tuple[int, ...] = tuple(),
) -> dict:
    return {
        "id": card_id,
        "serial": serial,
        "hp": hp,
        "maxHp": hp,
        "appearThisTurn": False,
        "energies": [
            {
                5: int(EnergyType.PSYCHIC),
                8: int(EnergyType.METAL),
                9: int(EnergyType.COLORLESS),
                19: int(EnergyType.PSYCHIC),
            }[energy_id]
            for energy_id in energy_ids
        ],
        "energyCards": [
            _card(energy_id, serial + 10 + index, owner)
            for index, energy_id in enumerate(energy_ids)
        ],
        "tools": [
            _card(tool_id, serial + 20 + index, owner)
            for index, tool_id in enumerate(tool_ids)
        ],
        "preEvolution": [],
    }


def guard_observation(
    *, seat: int = 1, context: str = "search", fez_only: bool = False
) -> dict:
    observation = copy.deepcopy(BASE)
    mine = copy.deepcopy(observation["current"]["players"][1])
    theirs = copy.deepcopy(observation["current"]["players"][0])
    players = [None, None]
    players[seat] = mine
    players[1 - seat] = theirs
    observation["current"]["players"] = players
    observation["current"]["yourIndex"] = seat
    observation["current"].update(
        {
            "turn": 9 + seat,
            "turnActionCount": 3,
            "result": -1,
            "stadium": [],
        }
    )

    mine = players[seat]
    theirs = players[1 - seat]
    mine.update(
        {
            "active": [_pokemon(305, 90000, seat, hp=70)],
            "bench": [],
            "benchMax": 5,
            "deckCount": 12,
            "hand": [],
            "handCount": 0,
            "prize": [None, None],
            "poisoned": False,
            "burned": False,
            "asleep": False,
            "paralyzed": False,
            "confused": False,
        }
    )
    theirs.update(
        {
            "active": [
                _pokemon(
                    190,
                    91000,
                    1 - seat,
                    hp=300,
                    energy_ids=(8, 8, 8),
                )
            ],
            "bench": [],
            "benchMax": 5,
            "hand": None,
            "handCount": 5,
            "prize": [None, None],
            "poisoned": False,
            "burned": False,
            "asleep": False,
            "paralyzed": False,
            "confused": False,
        }
    )
    observation["logs"] = []

    if context == "search":
        cards = [_card(140, 92000, seat)]
        if not fez_only:
            cards.append(_card(142, 92001, seat))
        observation["select"].update(
            {
                "context": int(SelectContext.TO_HAND),
                "contextCard": None,
                "deck": cards,
                "effect": _card(1231, 92010, seat),
                "minCount": 0,
                "maxCount": 1,
                "option": [
                    {
                        "type": int(OptionType.CARD),
                        "area": int(AreaType.DECK),
                        "index": index,
                        "playerIndex": seat,
                    }
                    for index in range(len(cards))
                ],
                "type": 1,
            }
        )
    else:
        mine["hand"] = [
            _card(140, 92000, seat),
            _card(142, 92001, seat),
        ]
        mine["handCount"] = 2
        observation["select"].update(
            {
                "context": int(SelectContext.MAIN),
                "contextCard": None,
                "deck": None,
                "effect": None,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": int(OptionType.PLAY), "index": 0},
                    {"type": int(OptionType.PLAY), "index": 1},
                    {"type": int(OptionType.END)},
                ],
                "type": 0,
            }
        )
    return observation


def selected_card_id(observation: dict, action: list[int]) -> int | None:
    if len(action) != 1:
        return None
    option = observation["select"]["option"][action[0]]
    if option["type"] == int(OptionType.CARD):
        return observation["select"]["deck"][option["index"]]["id"]
    if option["type"] == int(OptionType.PLAY):
        seat = observation["current"]["yourIndex"]
        return observation["current"]["players"][seat]["hand"][
            option["index"]
        ]["id"]
    return None


def fake_parent_prefers_fez(observation: dict) -> list[int]:
    select = observation["select"]
    seat = observation["current"]["yourIndex"]
    for index, option in enumerate(select["option"]):
        if option["type"] == int(OptionType.CARD):
            card = select["deck"][option["index"]]
        elif option["type"] == int(OptionType.PLAY):
            card = observation["current"]["players"][seat]["hand"][
                option["index"]
            ]
        else:
            continue
        if card["id"] == 140:
            return [index]
    return [0] if select["option"] else []


class GuardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        suffix = self.id().replace(".", "_")
        self.candidate = load_module(f"fez_guard_{suffix}", CANDIDATE)
        self.parent = load_module(f"fez_parent_{suffix}", PARENT)

    def typed(self, observation: dict):
        return to_observation_class(copy.deepcopy(observation))


class PublicThreatCertificateTests(GuardTestCase):
    def test_both_seats_fixed_cost_and_exact_210_boundary(self) -> None:
        attack = self.candidate.attack_table[253]
        original_damage = attack.damage
        try:
            attack.damage = 210
            for seat in (0, 1):
                certificate = self.candidate._fez_exposure_certificate(
                    self.typed(guard_observation(seat=seat))
                )
                self.assertIsNotNone(certificate)
                self.assertEqual(
                    certificate["threats"][0][2]["certified_damage"],
                    210,
                )
            attack.damage = 209
            self.assertIsNone(
                self.candidate._fez_exposure_certificate(
                    self.typed(guard_observation())
                )
            )
        finally:
            attack.damage = original_damage

    def test_energy_payment_status_and_variable_attack_fail_closed(self) -> None:
        observation = guard_observation()
        self.assertIsNotNone(
            self.candidate._fez_exposure_certificate(self.typed(observation))
        )
        unpaid = copy.deepcopy(observation)
        attacker = unpaid["current"]["players"][0]["active"][0]
        attacker["energies"].pop()
        attacker["energyCards"].pop()
        self.assertIsNone(
            self.candidate._fez_exposure_certificate(self.typed(unpaid))
        )
        for status in ("asleep", "paralyzed", "confused"):
            disabled = copy.deepcopy(observation)
            disabled["current"]["players"][0][status] = True
            self.assertIsNone(
                self.candidate._fez_exposure_certificate(
                    self.typed(disabled)
                )
            )

        attack = self.candidate.attack_table[253]
        original_text = attack.text
        try:
            attack.text = "Flip a coin. If heads, this attack does more damage."
            self.assertIsNone(
                self.candidate._fez_exposure_certificate(
                    self.typed(observation)
                )
            )
        finally:
            attack.text = original_text

    def test_weakness_resistance_and_recognized_maximum_belt(self) -> None:
        observation = guard_observation()
        typed = self.typed(observation)
        attacker = typed.current.players[0].active[0]
        attack = self.candidate.attack_table[253]
        target = copy.copy(self.candidate.card_table[140])

        target.weakness = EnergyType.METAL
        target.resistance = None
        weak = self.candidate._fez_fixed_attack_damage(
            typed,
            attacker=attacker,
            attacker_owner=0,
            attack=attack,
            target_data=target,
        )
        self.assertEqual(weak["certified_damage"], 440)

        target.weakness = None
        target.resistance = EnergyType.METAL
        resisted = self.candidate._fez_fixed_attack_damage(
            typed,
            attacker=attacker,
            attacker_owner=0,
            attack=attack,
            target_data=target,
        )
        self.assertEqual(resisted["certified_damage"], 190)

        belted = guard_observation()
        belted["current"]["players"][0]["active"][0]["tools"] = [
            _card(1158, 91100, 0)
        ]
        original_damage = attack.damage
        try:
            attack.damage = 160
            certificate = self.candidate._fez_exposure_certificate(
                self.typed(belted)
            )
            self.assertIsNotNone(certificate)
            profile = certificate["threats"][0][2]
            self.assertEqual(profile["recognized_before_wr_bonus"], 50)
            self.assertEqual(profile["certified_damage"], 210)
        finally:
            attack.damage = original_damage

    def test_incomplete_duplicate_and_existing_multi_prize_delegate(self) -> None:
        incomplete = guard_observation()
        incomplete["current"]["players"][0]["active"][0][
            "energyCards"
        ].pop()
        self.assertIsNone(
            self.candidate._fez_exposure_certificate(self.typed(incomplete))
        )

        duplicate = guard_observation()
        duplicate["current"]["players"][0]["active"][0]["serial"] = 90000
        self.assertIsNone(
            self.candidate._fez_exposure_certificate(self.typed(duplicate))
        )

        exposed = guard_observation()
        exposed["current"]["players"][1]["active"][0].update(
            {"id": 140, "hp": 210, "maxHp": 210}
        )
        self.assertIsNone(
            self.candidate._fez_exposure_certificate(self.typed(exposed))
        )


class SearchAndMainPolicyTests(GuardTestCase):
    def test_optional_mixed_and_fez_only_search(self) -> None:
        mixed = guard_observation()
        self.candidate._clear_emergency_state(clear_cache=True)
        parent_action = self.parent.agent(copy.deepcopy(mixed))
        self.assertEqual(selected_card_id(mixed, parent_action), 140)
        action = self.candidate.agent(copy.deepcopy(mixed))
        self.assertEqual(selected_card_id(mixed, action), 142)
        self.assertEqual(
            self.candidate.agent(copy.deepcopy(mixed)), action
        )

        only = guard_observation(fez_only=True)
        self.candidate._clear_emergency_state(clear_cache=True)
        self.assertEqual(self.candidate.agent(copy.deepcopy(only)), [])
        self.assertEqual(
            self.candidate.agent(copy.deepcopy(only)), []
        )

    def test_mandatory_non_fez_and_option_order(self) -> None:
        mandatory = guard_observation()
        mandatory["select"]["minCount"] = 1
        expected = self.parent.agent(copy.deepcopy(mandatory))
        self.assertEqual(
            self.candidate.agent(copy.deepcopy(mandatory)), expected
        )

        non_fez = guard_observation()
        non_fez["select"]["deck"] = non_fez["select"]["deck"][1:]
        non_fez["select"]["option"] = non_fez["select"]["option"][1:]
        non_fez["select"]["option"][0]["index"] = 0
        expected = self.parent.agent(copy.deepcopy(non_fez))
        self.assertEqual(
            self.candidate.agent(copy.deepcopy(non_fez)), expected
        )

        for reverse in (False, True):
            observation = guard_observation()
            if reverse:
                observation["select"]["deck"].reverse()
            self.candidate._clear_emergency_state(clear_cache=True)
            action = self.candidate.agent(copy.deepcopy(observation))
            self.assertEqual(selected_card_id(observation, action), 142)

    def test_main_masks_only_play_fez_and_uses_parent_next_ranking(self) -> None:
        observation = guard_observation(context="main")
        with patch.object(
            self.candidate,
            "_parent_agent",
            side_effect=fake_parent_prefers_fez,
        ):
            self.candidate._clear_emergency_state(clear_cache=True)
            action = self.candidate.agent(copy.deepcopy(observation))
            self.assertEqual(selected_card_id(observation, action), 142)
            self.assertEqual(
                self.candidate.agent(copy.deepcopy(observation)), action
            )

    def test_malformed_duplicate_options_and_stale_latches_delegate(self) -> None:
        duplicate = guard_observation(context="main")
        duplicate["select"]["option"].insert(
            1, copy.deepcopy(duplicate["select"]["option"][0])
        )
        with patch.object(
            self.candidate,
            "_parent_agent",
            side_effect=fake_parent_prefers_fez,
        ):
            self.candidate._clear_emergency_state(clear_cache=True)
            self.assertEqual(
                self.candidate.agent(copy.deepcopy(duplicate)), [0]
            )

        observation = guard_observation(context="main")
        calls = iter(([0], []))

        def failed_rerank_parent(_):
            action = list(next(calls))
            self.candidate._hilda_source_latch.clear()
            self.candidate._hilda_source_latch.update(
                stage=("original_parent" if action else "masked_failed")
            )
            return action

        with patch.object(
            self.candidate,
            "_parent_agent",
            side_effect=failed_rerank_parent,
        ):
            self.candidate._clear_emergency_state(clear_cache=True)
            self.assertEqual(
                self.candidate.agent(copy.deepcopy(observation)), [0]
            )
            self.assertEqual(
                self.candidate._hilda_source_latch,
                {"stage": "original_parent"},
            )

    def test_successful_masked_rerun_discards_first_parent_state(self) -> None:
        observation = guard_observation(context="main")
        calls = 0

        def stateful_parent(raw):
            nonlocal calls
            calls += 1
            if calls == 1:
                self.candidate._hilda_source_latch.update(
                    stage="first_fez_choice"
                )
                return fake_parent_prefers_fez(raw)
            self.assertFalse(self.candidate._hilda_source_latch)
            self.candidate._enriching_reserve_latch.update(
                stage="masked_parent_choice"
            )
            return fake_parent_prefers_fez(raw)

        with patch.object(
            self.candidate,
            "_parent_agent",
            side_effect=stateful_parent,
        ):
            self.candidate._clear_emergency_state(clear_cache=True)
            action = self.candidate.agent(copy.deepcopy(observation))
        self.assertEqual(selected_card_id(observation, action), 142)
        self.assertFalse(self.candidate._hilda_source_latch)
        self.assertEqual(
            self.candidate._enriching_reserve_latch,
            {"stage": "masked_parent_choice"},
        )

    def test_parent_equivalence_outside_guard(self) -> None:
        observation = guard_observation()
        observation["current"]["players"][0]["prize"].append(None)
        self.candidate._clear_emergency_state(clear_cache=True)
        self.parent._clear_emergency_state(clear_cache=True)
        self.assertEqual(
            self.candidate.agent(copy.deepcopy(observation)),
            self.parent.agent(copy.deepcopy(observation)),
        )


class TerminalAndArtifactTests(GuardTestCase):
    def test_already_legal_fixed_lethal_is_not_a_fez_exemption(self) -> None:
        observation = guard_observation(context="main")
        seat = observation["current"]["yourIndex"]
        mine = observation["current"]["players"][seat]
        target = observation["current"]["players"][1 - seat]["active"][0]
        mine["active"] = [
            _pokemon(742, 90000, seat, hp=80, energy_ids=(19,))
        ]
        mine["prize"] = [None, None]
        target["hp"] = 30
        target["maxHp"] = 300
        observation["select"]["option"].insert(
            2,
            {
                "type": int(OptionType.ATTACK),
                "attackId": 1071,
            },
        )
        typed = self.typed(observation)
        self.assertIsNone(
            self.candidate._fez_enabled_terminal_certificate(typed)
        )
        with patch.object(
            self.candidate,
            "_parent_agent",
            side_effect=fake_parent_prefers_fez,
        ):
            self.candidate._clear_emergency_state(clear_cache=True)
            self.assertEqual(
                selected_card_id(
                    observation,
                    self.candidate.agent(copy.deepcopy(observation)),
                ),
                142,
            )

    def test_uncertified_powerful_hand_terminal_looking_delegates(self) -> None:
        observation = guard_observation(context="main")
        seat = observation["current"]["yourIndex"]
        mine = observation["current"]["players"][seat]
        mine["active"] = [
            _pokemon(743, 90000, seat, hp=140, energy_ids=(19,))
        ]
        mine["hand"] = [
            _card(140, 92000, seat),
            _card(142, 92001, seat),
            _card(1264, 92002, seat),
            _card(1264, 92003, seat),
            _card(1264, 92004, seat),
            _card(1264, 92005, seat),
            _card(1264, 92006, seat),
            _card(1264, 92007, seat),
            _card(1264, 92008, seat),
        ]
        mine["handCount"] = len(mine["hand"])
        observation["current"]["players"][1 - seat]["active"][0]["hp"] = 210
        observation["select"]["option"].insert(
            2,
            {
                "type": int(OptionType.ATTACK),
                "attackId": 1072,
            },
        )
        with patch.object(
            self.candidate,
            "_parent_agent",
            side_effect=fake_parent_prefers_fez,
        ):
            self.candidate._clear_emergency_state(clear_cache=True)
            action = self.candidate.agent(copy.deepcopy(observation))
            self.assertEqual(selected_card_id(observation, action), 140)

    def test_runtime_parity_parent_hashes_and_legal_deck(self) -> None:
        self.assertEqual(sha256(PARENT / "main.py"), EXPECTED_PARENT["source"])
        self.assertEqual(
            sha256(PARENT / "runtime" / "main.py"),
            EXPECTED_PARENT["runtime"],
        )
        self.assertEqual(sha256(PARENT / "deck.csv"), EXPECTED_PARENT["deck"])
        rows = [
            row
            for row in (CANDIDATE / "deck.csv").read_text().splitlines()
            if row
        ]
        self.assertEqual(len(rows), 60)
        self.assertEqual(sha256(CANDIDATE / "deck.csv"), EXPECTED_PARENT["deck"])

        runtime = load_module(
            f"fez_runtime_{self.id().replace('.', '_')}",
            CANDIDATE / "runtime",
        )
        observation = guard_observation()
        self.candidate._clear_emergency_state(clear_cache=True)
        runtime._source_module._clear_emergency_state(clear_cache=True)
        self.assertEqual(
            runtime.agent(copy.deepcopy(observation)),
            self.candidate.agent(copy.deepcopy(observation)),
        )


if __name__ == "__main__":
    unittest.main()
