"""Focused contract checks for Cynthia Garchomp v51's interleaved backup route."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V50_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v50_champions_call_route"
V51_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v51_interleaved_backup"


def install_api_stub():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench",
        PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium",
    )
    api.OptionType = types.SimpleNamespace(
        ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat",
        ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end",
        NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy",
    )
    api.SelectContext = types.SimpleNamespace(
        MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active",
        SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard",
        DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look",
        TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", TO_BENCH="to_bench",
        SWITCH="switch", TO_ACTIVE="to_active", ATTACH_TO="attach_to",
        ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage",
    )
    api.all_attack = lambda: []
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api


def load_agent_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InterleavedBackupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v50 = load_agent_module("cynthia_v50_for_v51_test", V50_DIR / "main.py")
        cls.v51 = load_agent_module("cynthia_v51_main", V51_DIR / "main.py")

    @staticmethod
    def card(card_id):
        return types.SimpleNamespace(id=card_id, energies=[])

    @staticmethod
    def option(index):
        return types.SimpleNamespace(
            type="card", area="deck", index=index, playerIndex=None,
            inPlayArea=None, inPlayIndex=None, attackId=None, number=None,
        )

    def observation(
        self,
        legal_ids,
        *,
        hand_ids=(),
        active_ids=(),
        bench_ids=(),
        opponent_active_ids=(),
        opponent_bench_ids=(),
        bench_max=5,
        context="to_hand",
        max_count=1,
        effect_id=380,
        hand_available=True,
    ):
        visible_deck = [self.card(card_id) for card_id in legal_ids]
        hand = [self.card(card_id) for card_id in hand_ids] if hand_available else None
        mine = types.SimpleNamespace(
            hand=hand,
            handCount=len(hand or []),
            active=[self.card(card_id) for card_id in active_ids],
            bench=[self.card(card_id) for card_id in bench_ids],
            benchMax=bench_max,
            discard=[],
            prize=[],
            deckCount=30,
        )
        opponent = types.SimpleNamespace(
            hand=None,
            handCount=0,
            active=[self.card(card_id) for card_id in opponent_active_ids],
            bench=[self.card(card_id) for card_id in opponent_bench_ids],
            benchMax=5,
            discard=[],
            prize=[],
            deckCount=30,
        )
        effect = self.card(effect_id) if effect_id is not None else None
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0, players=[mine, opponent], looking=[], stadium=[],
            ),
            select=types.SimpleNamespace(
                option=[self.option(index) for index in range(len(visible_deck))],
                context=context,
                minCount=1,
                maxCount=max_count,
                deck=visible_deck,
                effect=effect,
            ),
        )

    def v50_fallback(self, obs):
        route = self.v50.champions_call_route_index
        try:
            self.v50.champions_call_route_index = lambda _obs: None
            return self.v50.choose_options(obs)
        finally:
            self.v50.champions_call_route_index = route

    def assert_exact_v50(self, obs):
        self.assertEqual(
            self.v51.champions_call_route_index(obs),
            self.v50.champions_call_route_index(obs),
        )
        self.assertEqual(self.v51.choose_options(obs), self.v50.choose_options(obs))

    def test_one_known_garchomp_delegates_to_exact_v50_fallback(self):
        a = self.v51
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE, a.ROSELIA],
            opponent_active_ids=[a.GARCHOMP_EX],
        )
        self.assertEqual(self.v50.champions_call_route_index(obs), 1)
        self.assertIsNone(a.champions_call_route_index(obs))
        self.assertEqual(a.choose_options(obs), self.v50_fallback(obs))

    def test_two_garchomp_in_hand_plus_roselia_selects_roserade(self):
        a = self.v51
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            hand_ids=[a.GARCHOMP_EX, a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE, a.ROSELIA],
        )
        self.assertEqual(a.champions_call_route_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_one_garchomp_in_play_and_one_in_hand_selects_roserade(self):
        a = self.v51
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GARCHOMP_EX],
            bench_ids=[a.GIBLE, a.ROSELIA],
        )
        self.assertEqual(a.choose_options(obs), [1])

    def test_two_garchomp_in_play_selects_roserade(self):
        a = self.v51
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            active_ids=[a.GARCHOMP_EX],
            bench_ids=[a.GARCHOMP_EX, a.ROSELIA],
        )
        self.assertEqual(a.choose_options(obs), [1])

    def test_duplicate_known_garchomp_cards_are_not_collapsed_through_a_set(self):
        a = self.v51
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            hand_ids=[a.GARCHOMP_EX, a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE, a.ROSELIA],
        )
        self.assertEqual({card.id for card in obs.current.players[0].hand}, {a.GARCHOMP_EX})
        self.assertEqual(a.champions_call_route_index(obs), 1)

    def test_state_a_and_state_b_match_v50_existing_cases(self):
        a = self.v51
        cases = {
            "state_a_first_garchomp": self.observation(
                [a.GABITE, a.GARCHOMP_EX], active_ids=[a.GIBLE],
            ),
            "state_b_roselia_before_width": self.observation(
                [a.GABITE, a.GARCHOMP_EX, a.ROSELIA],
                hand_ids=[a.GARCHOMP_EX], active_ids=[a.GIBLE], bench_ids=[a.GABITE],
            ),
            "state_b_roselia_with_roserade_in_hand": self.observation(
                [a.GABITE, a.ROSELIA],
                hand_ids=[a.GARCHOMP_EX, a.ROSERADE],
                active_ids=[a.GIBLE], bench_ids=[a.GABITE],
            ),
        }
        expected_routes = {
            "state_a_first_garchomp": 1,
            "state_b_roselia_before_width": 2,
            "state_b_roselia_with_roserade_in_hand": 1,
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assert_exact_v50(obs)
                self.assertEqual(self.v51.champions_call_route_index(obs), expected_routes[name])

    def test_required_fallbacks_remain_exact_v50(self):
        a = self.v51
        eligible = {
            "legal_ids": [a.GABITE, a.ROSERADE],
            "hand_ids": [a.GARCHOMP_EX, a.GARCHOMP_EX],
            "active_ids": [a.GIBLE],
            "bench_ids": [a.GABITE, a.ROSELIA],
        }
        cases = {
            "full_bench_hand_roselia": self.observation(
                [a.GABITE, a.ROSERADE],
                hand_ids=[a.GARCHOMP_EX, a.GARCHOMP_EX, a.ROSELIA],
                active_ids=[a.GIBLE],
                bench_ids=[a.GABITE, a.SPIRITOMB, 9001, 9002, 9003],
                bench_max=5,
            ),
            "missing_attacker": self.observation([a.GABITE], active_ids=[a.GIBLE]),
            "missing_support_base": self.observation(
                [a.GABITE, a.GARCHOMP_EX],
                hand_ids=[a.GARCHOMP_EX], active_ids=[a.GIBLE], bench_ids=[a.GABITE],
            ),
            "missing_support_evolution": self.observation(
                [a.GABITE, a.ROSELIA],
                hand_ids=[a.GARCHOMP_EX, a.GARCHOMP_EX, a.ROSELIA],
                active_ids=[a.GIBLE], bench_ids=[a.GABITE],
            ),
            "non_call": self.observation(**eligible, effect_id=a.GIBLE),
            "non_to_hand": self.observation(**eligible, context=a.SelectContext.LOOK),
            "max_count_two": self.observation(**eligible, max_count=2),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(a.champions_call_route_index(obs))
                self.assert_exact_v50(obs)

    def test_exact_deck_and_only_frozen_state_c_source_difference(self):
        baseline_files = {
            path.relative_to(V50_DIR)
            for path in V50_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V51_DIR)
            for path in V51_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_deck = (V50_DIR / "deck.csv").read_bytes()
        candidate_deck = (V51_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(60, len([line for line in candidate_deck.splitlines() if line.strip()]))

        baseline_main = (V50_DIR / "main.py").read_bytes()
        candidate_main = (V51_DIR / "main.py").read_bytes()
        newline = b"\r\n" if b"\r\n" in baseline_main else b"\n"
        old = newline.join([
            b"    if (",
            b"        not roserade_in_hand",
            b"        and not roserade_in_play",
            b"        and (roselia_in_hand or roselia_in_play)",
            b"        and (roselia_in_play or bench_is_open)",
            b"    ):",
            b"        return legal_indices.get(ROSERADE)",
        ])
        new = newline.join([
            b"    known_garchomp_count = (",
            b"        sum(1 for card in player.hand if card and card.id == GARCHOMP_EX)",
            b"        + sum(1 for pokemon in my_pokemon(obs) if pokemon.id == GARCHOMP_EX)",
            b"    )",
            b"    if (",
            b"        known_garchomp_count >= 2",
            b"        and not roserade_in_hand",
            b"        and not roserade_in_play",
            b"        and (roselia_in_hand or roselia_in_play)",
            b"        and (roselia_in_play or bench_is_open)",
            b"    ):",
            b"        return legal_indices.get(ROSERADE)",
        ])
        self.assertEqual(baseline_main.count(old), 1)
        self.assertEqual(candidate_main, baseline_main.replace(old, new, 1))


if __name__ == "__main__":
    unittest.main()
