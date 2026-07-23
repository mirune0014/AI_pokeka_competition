from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path


CANDIDATE = Path(__file__).resolve().parent
REPOSITORY = CANDIDATE.parents[2]
AUTONOMOUS = REPOSITORY / "autonomous_gold_20260715"
PARENT = (
    AUTONOMOUS
    / "candidates"
    / "alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3"
)
ENGINE = (
    REPOSITORY
    / "analysis_outputs"
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
REPLAY_SHA256 = (
    "E7802FA07A96F924D6F18F36C013BA25FA29CCC158B3FD3626488939B7562A8D"
)
EXPECTED_PARENT = {
    "source": "49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95",
    "runtime": "9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A",
    "deck": "7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141",
}
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0, str(REPOSITORY))

from cg.api import (  # noqa: E402
    AreaType,
    CardType,
    EnergyType,
    OptionType,
    SelectContext,
    all_card_data,
    search_begin,
    search_end,
    search_step,
    to_observation_class,
)
from rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


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


REPLAY_DATA = json.loads(REPLAY.read_text(encoding="utf-8"))
STEP135 = copy.deepcopy(REPLAY_DATA["steps"][135][1]["observation"])
STEP150 = copy.deepcopy(REPLAY_DATA["steps"][150][1]["observation"])
STEP87 = copy.deepcopy(REPLAY_DATA["steps"][87][1]["observation"])


def reset_and_act(module, observation: dict) -> list[int]:
    module._clear_emergency_state(clear_cache=True)
    return module.agent(copy.deepcopy(observation))


def selected_card(observation: dict, action: list[int]) -> tuple[int, int] | None:
    if len(action) != 1:
        return None
    option = observation["select"]["option"][action[0]]
    if option["type"] not in (7, 8, 9):
        return None
    mine = observation["current"]["players"][
        observation["current"]["yourIndex"]
    ]
    card = mine["hand"][option["index"]]
    return card["id"], card["serial"]


def make_search_observation(
    *, effect_id: int, deck_count: int, cards: list[dict], context: int, max_count: int
) -> dict:
    observation = copy.deepcopy(STEP135)
    mine = observation["current"]["players"][1]
    mine["deckCount"] = deck_count
    observation["select"].update(
        {
            "context": context,
            "contextCard": None,
            "deck": copy.deepcopy(cards),
            "effect": {"id": effect_id, "serial": 990, "playerIndex": 1},
            "minCount": 0,
            "maxCount": max_count,
            "option": [
                {"type": 3, "area": 1, "index": index, "playerIndex": 1}
                for index in range(len(cards))
            ],
            "type": 1,
        }
    )
    return observation


def make_psychic_draw_observation(card_id: int, deck_count: int) -> dict:
    observation = copy.deepcopy(STEP135)
    observation["current"]["players"][1]["deckCount"] = deck_count
    evolved = observation["current"]["players"][1]["active"][0]
    evolved.update(
        {
            "id": card_id,
            "serial": 991,
            "hp": 80 if card_id == 742 else 140,
            "maxHp": 80 if card_id == 742 else 140,
        }
    )
    observation["select"].update(
        {
            "context": 43,
            "contextCard": {"id": card_id, "serial": 991, "playerIndex": 1},
            "deck": None,
            "effect": None,
            "minCount": 1,
            "maxCount": 1,
            "option": [{"type": 1}, {"type": 2}],
            "type": 9,
        }
    )
    return observation


def typed(observation: dict):
    return to_observation_class(copy.deepcopy(observation))


class CandidateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = load_module(
            f"mandatory_candidate_{self.id().replace('.', '_')}", CANDIDATE
        )
        self.parent = load_module(
            f"mandatory_parent_{self.id().replace('.', '_')}", PARENT
        )


class ExactAnchorTests(CandidateTestCase):
    def test_checked_engine_step135_transaction_and_repeats(self) -> None:
        self.assertEqual(sha256(REPLAY), REPLAY_SHA256)
        self.assertEqual(len(STEP135["current"]["players"][1]["prize"]), 2)
        self.assertEqual(len(STEP135["current"]["players"][0]["prize"]), 3)
        full = copy.deepcopy(REPLAY_DATA["steps"][0][0]["visualize"][134]["current"])

        def ids(cards):
            return [card["id"] for card in cards]

        mine = full["players"][1]
        theirs = full["players"][0]
        state = search_begin(
            to_observation_class(copy.deepcopy(STEP135)),
            ids(mine["deck"]),
            ids(mine["prize"]),
            ids(theirs["deck"]),
            ids(theirs["prize"]),
            ids(theirs["hand"]),
            [],
            manual_coin=False,
        )
        rows = []
        try:
            self.candidate._clear_emergency_state(clear_cache=True)
            for expected_context, expected_type in (
                (0, 7),
                (30, 6),
                (0, 8),
                (0, 7),
            ):
                observation = asdict(state.observation)
                action = self.candidate.agent(copy.deepcopy(observation))
                self.assertEqual(
                    self.candidate.agent(copy.deepcopy(observation)), action
                )
                self.assertEqual(observation["select"]["context"], expected_context)
                self.assertEqual(len(action), 1)
                option = observation["select"]["option"][action[0]]
                self.assertEqual(option["type"], expected_type)
                row = {
                    "context": expected_context,
                    "action": action,
                    "type": expected_type,
                }
                if expected_context == 0 and expected_type in (7, 8):
                    card = observation["current"]["players"][1]["hand"][
                        option["index"]
                    ]
                    row["card"] = (card["id"], card["serial"])
                if expected_context == 30:
                    pokemon = observation["current"]["players"][0]["active"][0]
                    energy = pokemon["energyCards"][option["energyIndex"]]
                    row["target"] = (
                        option["playerIndex"],
                        option["area"],
                        pokemon["serial"],
                        option["energyIndex"],
                        energy["id"],
                        energy["serial"],
                    )
                rows.append(row)
                state = search_step(state.searchId, action)
        finally:
            search_end()
        self.assertEqual(rows[0]["card"], (1081, 100))
        self.assertEqual(rows[1]["target"], (0, 4, 26, 0, 19, 7))
        self.assertEqual(rows[2]["card"], (5, 117))
        self.assertEqual(rows[3]["card"], (140, 79))
        self.assertFalse(self.candidate._kadabra_resource_first_latch)

    def test_step150_suppresses_enriching_and_keeps_neutral_parent_order(self) -> None:
        parent_action = reset_and_act(self.parent, STEP150)
        candidate_action = reset_and_act(self.candidate, STEP150)
        self.assertEqual(selected_card(STEP150, parent_action), (13, 122))
        self.assertEqual(selected_card(STEP150, candidate_action), (1081, 100))
        self.assertNotEqual(candidate_action, parent_action)
        self.assertTrue(self.candidate._kadabra_resource_first_latch)

    def test_night_stretcher_step87_is_exact_parent(self) -> None:
        self.assertEqual(
            reset_and_act(self.candidate, STEP87), reset_and_act(self.parent, STEP87)
        )


class FixedDrawBoundaryTests(CandidateTestCase):
    def test_fez_and_enriching_above_below_reserve(self) -> None:
        fez = copy.deepcopy(STEP135)
        mine = fez["current"]["players"][1]
        mine["bench"][0] = {
            "id": 140,
            "serial": 900,
            "hp": 210,
            "maxHp": 210,
            "appearThisTurn": False,
            "energies": [],
            "energyCards": [],
            "tools": [],
            "preEvolution": [],
            "playerIndex": 1,
        }
        fez["select"]["option"] = [
            {"type": 10, "area": 5, "index": 0},
            {"type": 14},
        ]
        for deck_count, expected in ((3, [1]), (4, [0])):
            with self.subTest(effect="fez", deck=deck_count):
                fez["current"]["players"][1]["deckCount"] = deck_count
                result = self.candidate._apply_mandatory_draw_reserve(
                    typed(fez), [0], [0, 1]
                )
                self.assertEqual(result, expected)

        enriching_index = reset_and_act(self.parent, STEP150)[0]
        end_index = next(
            index
            for index, option in enumerate(STEP150["select"]["option"])
            if option["type"] == 14
        )
        for deck_count, expected in ((4, [end_index]), (5, [enriching_index])):
            with self.subTest(effect="enriching", deck=deck_count):
                observation = copy.deepcopy(STEP150)
                observation["current"]["players"][1]["deckCount"] = deck_count
                result = self.candidate._apply_mandatory_draw_reserve(
                    typed(observation),
                    [enriching_index],
                    [enriching_index, end_index],
                )
                self.assertEqual(result, expected)

    def test_psychic_draw_boundaries_choose_no_only_when_unsafe(self) -> None:
        for card_id, draw_count in ((742, 2), (743, 3)):
            for deck_count, expected in (
                (draw_count, [1]),
                (draw_count + 1, [0]),
            ):
                with self.subTest(card=card_id, deck=deck_count):
                    observation = make_psychic_draw_observation(
                        card_id, deck_count
                    )
                    result = self.candidate._apply_mandatory_draw_reserve(
                        typed(observation), [0]
                    )
                    self.assertEqual(result, expected)

    def test_run_away_exact_component_accounting_and_malformed_fail_close(self) -> None:
        variants = (
            ([], [], 2),
            (
                [{"id": 5, "serial": 902, "playerIndex": 1}],
                [],
                3,
            ),
            (
                [{"id": 5, "serial": 902, "playerIndex": 1}],
                [{"id": 1156, "serial": 903, "playerIndex": 1}],
                4,
            ),
        )
        for energies, tools, expected_post in variants:
            with self.subTest(energies=len(energies), tools=len(tools)):
                observation = copy.deepcopy(STEP135)
                source = {
                    "id": 66,
                    "serial": 901,
                    "hp": 140,
                    "maxHp": 140,
                    "appearThisTurn": False,
                    "energies": [5 for _ in energies],
                    "energyCards": energies,
                    "tools": tools,
                    "preEvolution": [
                        {"id": 305, "serial": 904, "playerIndex": 1}
                    ],
                    "playerIndex": 1,
                }
                observation["current"]["players"][1]["bench"][0] = source
                observation["current"]["players"][1]["deckCount"] = 1
                observation["select"]["option"] = [
                    {"type": 10, "area": 5, "index": 0},
                    {"type": 14},
                ]
                post = self.candidate._reserve_main_post_deck_count(
                    typed(observation), 0
                )
                self.assertEqual(post, expected_post)
                self.assertEqual(
                    self.candidate._apply_mandatory_draw_reserve(
                        typed(observation), [0], [0, 1]
                    ),
                    [0],
                )

        malformed = copy.deepcopy(observation)
        malformed_source = malformed["current"]["players"][1]["bench"][0]
        malformed_source["energyCards"] = [
            {"id": 1264, "serial": 905, "playerIndex": 1}
        ]
        malformed_source["energies"] = [5]
        self.assertEqual(
            self.candidate._apply_mandatory_draw_reserve(
                typed(malformed), [0], [0, 1]
            ),
            [1],
        )


class SearchBoundaryTests(CandidateTestCase):
    def assert_cap(
        self,
        effect_id: int,
        cards: list[dict],
        context: int,
        max_count: int,
    ) -> None:
        for deck_count, expected_count in ((1, 0), (2, 1), (4, max_count)):
            with self.subTest(effect=effect_id, deck=deck_count):
                observation = make_search_observation(
                    effect_id=effect_id,
                    deck_count=deck_count,
                    cards=cards,
                    context=context,
                    max_count=max_count,
                )
                parent_action = list(range(max_count))
                result = self.candidate._apply_mandatory_draw_reserve(
                    typed(observation), parent_action
                )
                self.assertEqual(len(result), min(expected_count, len(cards)))

    def test_telepath_poffin_and_pad_zero_and_caps(self) -> None:
        psychic_basics = [
            {"id": 741, "serial": 910, "playerIndex": 1},
            {"id": 741, "serial": 911, "playerIndex": 1},
        ]
        poffin_basics = [
            {"id": 741, "serial": 912, "playerIndex": 1},
            {"id": 305, "serial": 913, "playerIndex": 1},
        ]
        pad = [{"id": 742, "serial": 914, "playerIndex": 1}]
        self.assert_cap(19, psychic_basics, 5, 2)
        self.assert_cap(1086, poffin_basics, 5, 2)
        self.assert_cap(1152, pad, 7, 1)

    def test_hilda_and_dawn_each_phase_above_below_reserve(self) -> None:
        phases = (
            (1225, [{"id": 742, "serial": 920, "playerIndex": 1}]),
            (1225, [{"id": 5, "serial": 921, "playerIndex": 1}]),
            (1231, [{"id": 741, "serial": 922, "playerIndex": 1}]),
            (1231, [{"id": 742, "serial": 923, "playerIndex": 1}]),
            (1231, [{"id": 743, "serial": 924, "playerIndex": 1}]),
        )
        for effect_id, cards in phases:
            self.assert_cap(effect_id, cards, 7, 1)

    def test_unknown_and_malformed_search_delegate_parent(self) -> None:
        cards = [
            {"id": 741, "serial": 930, "playerIndex": 1},
            {"id": 5, "serial": 931, "playerIndex": 1},
        ]
        malformed = make_search_observation(
            effect_id=1225,
            deck_count=1,
            cards=cards,
            context=7,
            max_count=1,
        )
        self.assertEqual(
            self.candidate._apply_mandatory_draw_reserve(
                typed(malformed), [0]
            ),
            [0],
        )
        unknown = make_search_observation(
            effect_id=999,
            deck_count=1,
            cards=[cards[0]],
            context=7,
            max_count=1,
        )
        self.assertEqual(
            self.candidate._apply_mandatory_draw_reserve(typed(unknown), [0]),
            [0],
        )

    def test_option_order_preserves_parent_ranking_when_capped(self) -> None:
        cards = [
            {"id": 741, "serial": 940, "playerIndex": 1},
            {"id": 305, "serial": 941, "playerIndex": 1},
            {"id": 741, "serial": 942, "playerIndex": 1},
        ]
        observation = make_search_observation(
            effect_id=1086,
            deck_count=2,
            cards=cards,
            context=5,
            max_count=2,
        )
        self.assertEqual(
            self.candidate._apply_mandatory_draw_reserve(
                typed(observation), [2, 0]
            ),
            [2],
        )


class ResourceBoundaryTests(CandidateTestCase):
    def assert_start_fails(self, observation: dict) -> None:
        self.candidate._clear_emergency_state(clear_cache=True)
        self.assertIsNone(
            self.candidate._start_kadabra_resource_first(
                typed(observation), [0]
            )
        )
        self.assertFalse(self.candidate._kadabra_resource_first_latch)

    def test_all_frozen_negative_boundaries_fail_closed(self) -> None:
        mutations = []
        remaining_alakazam = copy.deepcopy(STEP135)
        next(
            card
            for card in remaining_alakazam["current"]["players"][1]["discard"]
            if card["id"] == 743
        )["id"] = 1264
        mutations.append(remaining_alakazam)

        recovery_remaining = copy.deepcopy(STEP135)
        next(
            card
            for card in recovery_remaining["current"]["players"][1]["discard"]
            if card["id"] == 1097
        )["id"] = 1264
        mutations.append(recovery_remaining)

        ready_bench = copy.deepcopy(STEP135)
        ready_bench["current"]["players"][1]["bench"][0]["energies"] = [5]
        ready_bench["current"]["players"][1]["bench"][0]["energyCards"] = [
            {"id": 5, "serial": 950, "playerIndex": 1}
        ]
        mutations.append(ready_bench)

        status = copy.deepcopy(STEP135)
        status["current"]["players"][1]["asleep"] = True
        mutations.append(status)

        active_energy = copy.deepcopy(STEP135)
        active_energy["current"]["players"][1]["active"][0]["energies"] = [5]
        active_energy["current"]["players"][1]["active"][0]["energyCards"] = [
            {"id": 5, "serial": 951, "playerIndex": 1}
        ]
        mutations.append(active_energy)

        missing_hammer = copy.deepcopy(STEP135)
        missing_hammer["select"]["option"] = [
            option
            for index, option in enumerate(missing_hammer["select"]["option"])
            if index != 9
        ]
        mutations.append(missing_hammer)

        ambiguous_basic = copy.deepcopy(STEP135)
        ambiguous_basic["select"]["option"].append(
            copy.deepcopy(ambiguous_basic["select"]["option"][5])
        )
        mutations.append(ambiguous_basic)

        missing_target = copy.deepcopy(STEP135)
        missing_target["current"]["players"][0]["active"][0]["energies"] = []
        missing_target["current"]["players"][0]["active"][0]["energyCards"] = []
        mutations.append(missing_target)

        ambiguous_target = copy.deepcopy(STEP135)
        ambiguous_target["current"]["players"][0]["active"][0][
            "energies"
        ].append(5)
        ambiguous_target["current"]["players"][0]["active"][0][
            "energyCards"
        ].append({"id": 19, "serial": 952, "playerIndex": 0})
        mutations.append(ambiguous_target)

        new_active = copy.deepcopy(STEP135)
        new_active["current"]["players"][1]["active"][0][
            "appearThisTurn"
        ] = True
        mutations.append(new_active)

        for index, observation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_start_fails(observation)

    def test_stale_turn_cache_and_malformed_target_clear_latch(self) -> None:
        self.candidate._clear_emergency_state(clear_cache=True)
        action = self.candidate._start_kadabra_resource_first(
            typed(STEP135), [0]
        )
        self.assertEqual(selected_card(STEP135, action), (1081, 100))
        stale = copy.deepcopy(STEP135)
        stale["current"]["turn"] += 1
        self.assertIsNone(self.candidate._kadabra_resource_first_overlay(typed(stale)))
        self.assertFalse(self.candidate._kadabra_resource_first_latch)

        self.candidate._start_kadabra_resource_first(typed(STEP135), [0])
        malformed = copy.deepcopy(STEP135)
        malformed["current"]["turnActionCount"] += 1
        hammer_index = 5
        del malformed["current"]["players"][1]["hand"][hammer_index]
        malformed["current"]["players"][1]["handCount"] -= 1
        malformed["select"].update(
            {
                "context": 30,
                "effect": {"id": 1081, "serial": 100, "playerIndex": 1},
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {
                        "type": 6,
                        "area": 4,
                        "index": 0,
                        "playerIndex": 0,
                        "energyIndex": 9,
                        "count": 1,
                    }
                ],
            }
        )
        self.assertIsNone(
            self.candidate._kadabra_resource_first_overlay(typed(malformed))
        )
        self.assertFalse(self.candidate._kadabra_resource_first_latch)

    def test_option_order_invariance_binds_hammer_serial(self) -> None:
        observation = copy.deepcopy(STEP135)
        observation["select"]["option"] = list(
            reversed(observation["select"]["option"])
        )
        parent_action = reset_and_act(self.parent, observation)
        candidate_action = reset_and_act(self.candidate, observation)
        self.assertEqual(selected_card(observation, parent_action), (140, 79))
        self.assertEqual(selected_card(observation, candidate_action), (1081, 100))


class TerminalAndParityTests(CandidateTestCase):
    def test_terminal_looking_near_ko_and_hidden_enabler_are_non_exempt(self) -> None:
        for label, observation in (
            ("terminal-looking", STEP135),
            ("near-ko", STEP150),
            ("hidden-enabler", make_psychic_draw_observation(743, 3)),
        ):
            with self.subTest(label=label):
                self.assertIsNone(
                    self.candidate._reserve_terminal_win_certificate(
                        typed(observation), 0
                    )
                )
                self.assertFalse(self.candidate._reserve_terminal_win_latch)

    def test_xerosic_callbacks_and_unrelated_replays_are_exact_parent(self) -> None:
        cases = (
            (
                AUTONOMOUS
                / "live/54802782/refresh_20260719_0048/increment_replays/replays"
                / "episode_86676249_replay.json",
                1,
                39,
            ),
            (
                AUTONOMOUS
                / "live/54802782/refresh_20260719_0048/increment_replays/replays"
                / "episode_86674048_replay.json",
                0,
                24,
            ),
            (
                AUTONOMOUS
                / "live/54802782/refresh_20260719_0048/increment_replays/replays"
                / "episode_86665439_replay.json",
                1,
                137,
            ),
        )
        for path, seat, replay_step in cases:
            with self.subTest(episode=path.name, step=replay_step):
                replay = json.loads(path.read_text(encoding="utf-8"))
                matches = [
                    copy.deepcopy(observation)
                    for step, observation, _ in replay_decisions(replay, seat)
                    if step == replay_step
                ]
                self.assertEqual(len(matches), 1)
                self.assertEqual(
                    reset_and_act(self.candidate, matches[0]),
                    reset_and_act(self.parent, matches[0]),
                )

    def test_compile_ast_import_runtime_parent_and_legal_deck(self) -> None:
        source = CANDIDATE / "main.py"
        runtime = CANDIDATE / "runtime/main.py"
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        compile(runtime.read_text(encoding="utf-8"), str(runtime), "exec")
        ast.parse(source.read_text(encoding="utf-8"), str(source))
        self.assertEqual(sha256(PARENT / "main.py"), EXPECTED_PARENT["source"])
        self.assertEqual(
            sha256(PARENT / "runtime/main.py"), EXPECTED_PARENT["runtime"]
        )
        self.assertEqual(sha256(PARENT / "deck.csv"), EXPECTED_PARENT["deck"])
        self.assertEqual(
            (CANDIDATE / "deck.csv").read_bytes(),
            (PARENT / "deck.csv").read_bytes(),
        )

        deck = [
            int(row)
            for row in (CANDIDATE / "deck.csv")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(len(deck), 60)
        card_table = {card.cardId: card for card in all_card_data()}
        self.assertTrue(all(card_id in card_table for card_id in deck))
        counts = Counter(deck)
        self.assertTrue(
            all(
                count <= 4
                or card_table[card_id].cardType == CardType.BASIC_ENERGY
                for card_id, count in counts.items()
            )
        )
        self.assertLessEqual(
            sum(counts[cid] for cid in counts if card_table[cid].aceSpec), 1
        )
        self.assertNotIn("86746844", source.read_text(encoding="utf-8"))

        runtime_module = load_module(
            "mandatory_runtime_parity", CANDIDATE / "runtime"
        )
        source_module = load_module("mandatory_source_parity", CANDIDATE)
        self.assertEqual(
            runtime_module.agent(copy.deepcopy(STEP135)),
            source_module.agent(copy.deepcopy(STEP135)),
        )
        deck_request = {"select": None, "logs": [], "current": None}
        self.assertEqual(runtime_module.agent(deck_request), deck)
        self.assertEqual(source_module.agent(deck_request), deck)


if __name__ == "__main__":
    unittest.main(verbosity=2)
