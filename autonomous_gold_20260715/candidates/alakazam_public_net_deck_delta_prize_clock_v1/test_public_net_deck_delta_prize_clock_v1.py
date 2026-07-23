from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import sys
import unittest
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path


CANDIDATE = Path(__file__).resolve().parent
ROOT = CANDIDATE.parents[2]
PARENT = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3"
)
ENGINE = (
    ROOT
    / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
REPLAY = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "54802782"
    / "refresh_20260719_0838"
    / "replays"
    / "86778139.json"
)
DECISION = (
    ROOT
    / "autonomous_gold_20260715"
    / "decisions"
    / "20260719_0910_fez_exposure_reject_and_public_net_deck_delta_select.md"
)
ERRATUM = (
    ROOT
    / "autonomous_gold_20260715"
    / "decisions"
    / "20260719_0926_public_net_deck_delta_step128_erratum.md"
)

sys.path.insert(0, str(ENGINE))
from cg.api import search_begin, search_end, search_step, to_observation_class


PARENT_HASHES = {
    "main.py": "49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95",
    "runtime/main.py": "9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A",
    "deck.csv": "7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141",
}
REPLAY_SHA256 = "E81761637DE5281CFB03345F3E1C5576400ED5353334E7AB907C905A98B5271F"
DECISION_SHA256 = "8A8ED810E23BCF4970C12AB936B8249B5A027EDA12B30ECE696442229ECA250A"
ERRATUM_SHA256 = "A7DE4D77F2B7235CAE40D72F84C5B585724541E1E8F6F9546727A48E1232A244"

with REPLAY.open("r", encoding="utf-8") as handle:
    REPLAY_DATA = json.load(handle)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


@contextmanager
def cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


_module_counter = 0


def load_module(path: Path, *, runtime: bool = False):
    global _module_counter
    _module_counter += 1
    source = path / "runtime" / "main.py" if runtime else path / "main.py"
    name = f"net_clock_test_{_module_counter}_{'runtime' if runtime else 'source'}"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(source)
    module = importlib.util.module_from_spec(spec)
    with cwd(source.parent if not runtime else path):
        spec.loader.exec_module(module)
    return module


def raw_step(step: int) -> dict:
    row = next(
        item for item in REPLAY_DATA["steps"][step] if item.get("status") == "ACTIVE"
    )
    return copy.deepcopy(row["observation"])


def act(module, observation: dict) -> list[int]:
    return module.agent(copy.deepcopy(observation))


def selected_type(observation: dict, action: list[int]) -> int:
    return observation["select"]["option"][action[0]]["type"]


def selected_ability_serial(observation: dict, action: list[int]) -> int:
    option = observation["select"]["option"][action[0]]
    assert option["type"] == 10
    mine = observation["current"]["players"][observation["current"]["yourIndex"]]
    area = mine["active"] if option["area"] == 4 else mine["bench"]
    return area[option["index"]]["serial"]


def selected_attach_target(observation: dict, action: list[int]) -> tuple[int, int, int]:
    option = observation["select"]["option"][action[0]]
    assert option["type"] == 8
    mine = observation["current"]["players"][observation["current"]["yourIndex"]]
    card = mine["hand"][option["index"]]
    area = mine["active"] if option["inPlayArea"] == 4 else mine["bench"]
    target = area[option["inPlayIndex"]]
    return card["serial"], option["inPlayArea"], target["serial"]


class CandidateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = load_module(CANDIDATE)
        self.parent = load_module(PARENT)

    def assert_parent_fallback(self, observation: dict) -> None:
        self.assertEqual(act(self.candidate, observation), act(self.parent, observation))


class IdentityAndAnchorTests(CandidateTestCase):
    def test_governing_files_parent_and_deck_are_pinned(self) -> None:
        self.assertEqual(DECISION.stat().st_size, 6823)
        self.assertEqual(ERRATUM.stat().st_size, 2253)
        self.assertEqual(sha256(DECISION), DECISION_SHA256)
        self.assertEqual(sha256(ERRATUM), ERRATUM_SHA256)
        self.assertEqual(sha256(REPLAY), REPLAY_SHA256)
        for relative, expected in PARENT_HASHES.items():
            self.assertEqual(sha256(PARENT / relative), expected)
        self.assertEqual((CANDIDATE / "deck.csv").read_bytes(), (PARENT / "deck.csv").read_bytes())
        cards = [
            int(row)
            for row in (CANDIDATE / "deck.csv").read_text(encoding="utf-8").splitlines()
            if row
        ]
        self.assertEqual(len(cards), 60)

    def test_replay_psychic_draw_108_110_no_and_128_erratum_yes(self) -> None:
        for step, expected_type in ((108, 2), (110, 2), (128, 1)):
            observation = raw_step(step)
            parent_action = act(load_module(PARENT), observation)
            candidate_action = act(load_module(CANDIDATE), observation)
            self.assertEqual(selected_type(observation, parent_action), 1)
            self.assertEqual(selected_type(observation, candidate_action), expected_type)

    def test_replay_step131_suppresses_active_helmet(self) -> None:
        observation = raw_step(131)
        parent_target = selected_attach_target(observation, act(self.parent, observation))
        candidate_target = selected_attach_target(observation, act(self.candidate, observation))
        self.assertEqual(parent_target[1:], (4, 11))
        self.assertEqual(candidate_target[1:], (5, 17))

    def test_replay_steps141_143_choose_serial17_r4(self) -> None:
        for step in (141, 143):
            observation = raw_step(step)
            action = act(load_module(CANDIDATE), observation)
            self.assertEqual(selected_ability_serial(observation, action), 17)
            mine = observation["current"]["players"][0]
            dudunsparce = next(card for card in mine["bench"] if card["serial"] == 17)
            returned = (
                1
                + len(dudunsparce["preEvolution"])
                + len(dudunsparce["energyCards"])
                + len(dudunsparce["tools"])
            )
            self.assertEqual(returned, 4)
            self.assertEqual(mine["deckCount"] + returned, 7)
            self.assertEqual(mine["deckCount"] + returned - 3, 4)
            self.assertGreater(4, len(mine["prize"]))


class PsychicNegativeTests(CandidateTestCase):
    def test_plus_60_needed_preserves_yes(self) -> None:
        observation = raw_step(108)
        target = observation["current"]["players"][1]["active"][0]
        target["hp"] = target["maxHp"] = 300
        self.assert_parent_fallback(observation)
        self.assertEqual(selected_type(observation, act(load_module(CANDIDATE), observation)), 1)

    def test_no_separate_backup_preserves_yes(self) -> None:
        observation = raw_step(110)
        mine = observation["current"]["players"][0]
        mine["bench"] = [card for card in mine["bench"] if card["serial"] != 11]
        self.assert_parent_fallback(observation)

    def test_final_prize_attack_preserves_yes(self) -> None:
        observation = raw_step(108)
        observation["current"]["players"][0]["prize"] = [None]
        self.assert_parent_fallback(observation)

    def test_missing_identity_effect_and_mandatory_prompt_fail_closed(self) -> None:
        missing = raw_step(108)
        missing["select"]["contextCard"]["serial"] = None
        self.assert_parent_fallback(missing)

        effect = raw_step(108)
        effect["select"]["effect"] = {"id": 1225, "serial": 48, "playerIndex": 0}
        self.assert_parent_fallback(effect)

        mandatory = raw_step(108)
        mandatory["select"]["option"] = [{"type": 1}]
        self.assert_parent_fallback(mandatory)

    def test_step128_public_inventory_cannot_force_psychic(self) -> None:
        observation = raw_step(128)
        mine = observation["current"]["players"][0]
        public = list(mine["hand"]) + list(mine["discard"])
        for pokemon in list(mine["active"]) + list(mine["bench"]):
            public.extend(pokemon["energyCards"])
        exposed = [card for card in public if card["id"] in (5, 19)]
        self.assertEqual([(card["id"], card["serial"]) for card in exposed], [(5, 56), (19, 60), (19, 61)])
        remaining = 6 - len(exposed)
        self.assertEqual(remaining, 3)
        self.assertLessEqual(remaining, len(mine["prize"]))
        self.assert_parent_fallback(observation)


class HelmetAndRunAwayNegativeTests(CandidateTestCase):
    def test_helmet_outside_tight_clock_is_parent_exact(self) -> None:
        observation = raw_step(131)
        observation["current"]["players"][0]["deckCount"] = 15
        self.assert_parent_fallback(observation)

    def test_run_away_only_pokemon_fails_closed(self) -> None:
        observation = raw_step(141)
        mine = observation["current"]["players"][0]
        source = copy.deepcopy(next(card for card in mine["bench"] if card["serial"] == 17))
        mine["active"] = [source]
        mine["bench"] = []
        observation["select"]["option"] = [
            {"type": 10, "area": 4, "index": 0},
            {"type": 14},
        ]
        self.assert_parent_fallback(observation)

    def test_run_away_r_le_3_fails_closed(self) -> None:
        observation = raw_step(141)
        source = next(
            card for card in observation["current"]["players"][0]["bench"] if card["serial"] == 17
        )
        source["tools"] = []
        self.assert_parent_fallback(observation)

    def test_run_away_projected_floor_fails_closed(self) -> None:
        observation = raw_step(141)
        observation["current"]["players"][0]["prize"].append(None)
        self.assert_parent_fallback(observation)

    def test_run_away_board_continuity_break_fails_closed(self) -> None:
        observation = raw_step(141)
        mine = observation["current"]["players"][0]
        mine["bench"] = [card for card in mine["bench"] if card["serial"] != 12]
        self.assert_parent_fallback(observation)

    def test_run_away_missing_component_serial_fails_closed(self) -> None:
        observation = raw_step(141)
        source = next(
            card for card in observation["current"]["players"][0]["bench"] if card["serial"] == 17
        )
        source["tools"][0]["serial"] = None
        self.assert_parent_fallback(observation)

    def test_run_away_duplicate_source_option_is_ambiguous(self) -> None:
        observation = raw_step(141)
        duplicate = copy.deepcopy(observation["select"]["option"][13])
        observation["select"]["option"].append(duplicate)
        self.assert_parent_fallback(observation)

    def test_final_prize_attack_does_not_run_away(self) -> None:
        observation = raw_step(141)
        observation["current"]["players"][0]["prize"] = [None]
        self.assert_parent_fallback(observation)


class DeterminismAndParityTests(CandidateTestCase):
    def test_option_order_invariance_by_semantic_target(self) -> None:
        psychic = raw_step(108)
        psychic["select"]["option"].reverse()
        action = act(load_module(CANDIDATE), psychic)
        self.assertEqual(selected_type(psychic, action), 2)

        helmet = raw_step(131)
        helmet["select"]["option"].reverse()
        action = act(load_module(CANDIDATE), helmet)
        self.assertNotEqual(selected_attach_target(helmet, action)[1], 4)

        run_away = raw_step(141)
        run_away["select"]["option"].reverse()
        action = act(load_module(CANDIDATE), run_away)
        self.assertEqual(selected_ability_serial(run_away, action), 17)

    def test_repeated_and_stale_callbacks(self) -> None:
        observation = raw_step(108)
        first = act(self.candidate, observation)
        self.assertEqual(act(self.candidate, observation), first)
        stale = copy.deepcopy(observation)
        stale["select"]["contextCard"]["serial"] = 999999
        self.assertEqual(selected_type(stale, act(self.candidate, stale)), 1)

    def test_unrelated_action_families_are_exact_parent(self) -> None:
        for step in (104, 107, 112, 126, 137, 144):
            observation = raw_step(step)
            self.assertEqual(
                act(load_module(CANDIDATE), observation),
                act(load_module(PARENT), observation),
            )

    def test_source_runtime_parity(self) -> None:
        source = load_module(CANDIDATE)
        runtime = load_module(CANDIDATE, runtime=True)
        expected_types = {108: 2, 110: 2, 128: 1}
        for step in (108, 110, 128, 131, 141, 143):
            observation = raw_step(step)
            left = act(source, observation)
            right = act(runtime, observation)
            self.assertEqual(left, right)
            if step in expected_types:
                self.assertEqual(selected_type(observation, left), expected_types[step])

    def test_checked_engine_run_away_transaction_3_to_7_to_4(self) -> None:
        observation = raw_step(141)
        full = REPLAY_DATA["steps"][0][0]["visualize"][140]["current"]
        mine = full["players"][0]
        theirs = full["players"][1]
        ids = lambda cards: [card["id"] for card in cards]
        state = search_begin(
            to_observation_class(copy.deepcopy(observation)),
            ids(mine["deck"]),
            ids(mine["prize"]),
            ids(theirs["deck"]),
            ids(theirs["prize"]),
            ids(theirs["hand"]),
            [],
            manual_coin=False,
        )
        try:
            checked_observation = asdict(state.observation)
            action = act(load_module(CANDIDATE), checked_observation)
            self.assertEqual(selected_ability_serial(checked_observation, action), 17)
            next_state = search_step(state.searchId, action)
            next_mine = next_state.observation.current.players[0]
            self.assertEqual(next_mine.deckCount, 4)
            self.assertEqual(next_mine.handCount, 21)
            self.assertEqual(len(next_mine.prize), 3)
            self.assertNotIn(17, [pokemon.serial for pokemon in next_mine.bench])
        finally:
            search_end()

    def test_checked_engine_psychic_no_and_helmet_transactions(self) -> None:
        for step, visualize_index in ((108, 107), (131, 130)):
            observation = raw_step(step)
            full = REPLAY_DATA["steps"][0][0]["visualize"][visualize_index]["current"]
            mine = full["players"][0]
            theirs = full["players"][1]
            ids = lambda cards: [card["id"] for card in cards]
            state = search_begin(
                to_observation_class(copy.deepcopy(observation)),
                ids(mine["deck"]),
                ids(mine["prize"]),
                ids(theirs["deck"]),
                ids(theirs["prize"]),
                ids(theirs["hand"]),
                [],
                manual_coin=False,
            )
            try:
                checked_observation = asdict(state.observation)
                action = act(load_module(CANDIDATE), checked_observation)
                next_state = search_step(state.searchId, action)
                next_mine = next_state.observation.current.players[0]
                self.assertEqual(int(next_state.observation.select.context), 0)
                if step == 108:
                    self.assertEqual(selected_type(checked_observation, action), 2)
                    self.assertEqual(next_mine.deckCount, 17)
                    self.assertEqual(next_mine.handCount, 13)
                else:
                    self.assertEqual(
                        selected_attach_target(checked_observation, action)[1:],
                        (5, 17),
                    )
                    dudunsparce = next(
                        pokemon for pokemon in next_mine.bench if pokemon.serial == 17
                    )
                    self.assertEqual([tool.serial for tool in dudunsparce.tools], [37])
                    self.assertEqual(next_mine.deckCount, 7)
            finally:
                search_end()


if __name__ == "__main__":
    unittest.main(verbosity=2)
