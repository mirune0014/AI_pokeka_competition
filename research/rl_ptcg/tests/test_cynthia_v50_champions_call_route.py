"""Focused contract checks for Cynthia Garchomp v50."""
import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V23_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve"
V50_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v50_champions_call_route"


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


class ChampionsCallRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v23 = load_agent_module("cynthia_v23_for_v50_test", V23_DIR / "main.py")
        cls.v50 = load_agent_module("cynthia_v50_main", V50_DIR / "main.py")

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

    def assert_exact_v23(self, obs):
        self.assertEqual(self.v50.choose_options(obs), self.v23.choose_options(obs))

    def test_no_known_garchomp_selects_legal_garchomp_before_gabite(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
        )
        self.assertEqual(self.v23.choose_options(obs), [0])
        self.assertEqual(a.choose_options(obs), [1])

    def test_attacker_plus_two_main_bodies_selects_roselia_before_width(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.GARCHOMP_EX, a.ROSELIA],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE],
        )
        self.assertEqual(self.v23.choose_options(obs), [0])
        self.assertEqual(a.choose_options(obs), [2])

    def test_attacker_and_roselia_select_roserade(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            active_ids=[a.GARCHOMP_EX],
            bench_ids=[a.GIBLE, a.ROSELIA],
        )
        self.assertEqual(self.v23.choose_options(obs), [0])
        self.assertEqual(a.choose_options(obs), [1])

    def test_roserade_in_hand_without_roselia_still_selects_roselia(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.ROSELIA],
            hand_ids=[a.GARCHOMP_EX, a.ROSERADE],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE],
        )
        self.assertEqual(a.choose_options(obs), [1])

    def test_roserade_in_play_delegates_to_exact_v23(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.ROSELIA],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE, a.ROSERADE],
        )
        self.assert_exact_v23(obs)

    def test_only_one_main_body_delegates_to_exact_v23(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.ROSELIA],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
        )
        self.assert_exact_v23(obs)

    def test_full_bench_with_missing_roselia_delegates_to_exact_v23(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.ROSELIA],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE, a.SPIRITOMB, 9001, 9002, 9003],
            bench_max=5,
        )
        self.assert_exact_v23(obs)

    def test_roselia_only_in_hand_with_full_bench_does_not_force_roserade(self):
        a = self.v50
        obs = self.observation(
            [a.GABITE, a.ROSERADE],
            hand_ids=[a.GARCHOMP_EX, a.ROSELIA],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE, a.SPIRITOMB, 9001, 9002, 9003],
            bench_max=5,
        )
        self.assert_exact_v23(obs)

    def test_missing_required_legal_role_delegates_to_exact_v23(self):
        a = self.v50
        cases = {
            "attacker": self.observation(
                [a.GABITE], active_ids=[a.GIBLE],
            ),
            "support_base": self.observation(
                [a.GABITE, a.GARCHOMP_EX],
                hand_ids=[a.GARCHOMP_EX], active_ids=[a.GIBLE], bench_ids=[a.GABITE],
            ),
            "support_evolution": self.observation(
                [a.GABITE, a.ROSELIA],
                hand_ids=[a.GARCHOMP_EX, a.ROSELIA], active_ids=[a.GIBLE], bench_ids=[a.GABITE],
            ),
        }
        for name, obs in cases.items():
            with self.subTest(role=name):
                self.assert_exact_v23(obs)

    def test_out_of_scope_selections_preserve_exact_v23(self):
        a = self.v50
        common = {
            "legal_ids": [a.GABITE, a.GARCHOMP_EX],
            "active_ids": [a.GIBLE],
        }
        cases = {
            "non_call_to_hand": self.observation(**common, effect_id=a.GIBLE),
            "non_to_hand": self.observation(**common, context=a.SelectContext.LOOK),
            "multiple_count": self.observation(**common, max_count=2),
            "null_effect": self.observation(**common, effect_id=None),
            "unavailable_hand": self.observation(**common, hand_available=False),
        }
        for name, obs in cases.items():
            with self.subTest(scope=name):
                self.assert_exact_v23(obs)

    def test_only_own_hand_and_play_determine_route_state(self):
        a = self.v50
        attacker_obs = self.observation(
            [a.GABITE, a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            opponent_active_ids=[a.GARCHOMP_EX],
        )
        self.assertEqual(a.choose_options(attacker_obs), [1])

        support_obs = self.observation(
            [a.GABITE, a.ROSELIA],
            hand_ids=[a.GARCHOMP_EX],
            active_ids=[a.GIBLE],
            bench_ids=[a.GABITE],
            opponent_active_ids=[a.ROSELIA],
            opponent_bench_ids=[a.ROSERADE],
        )
        self.assertEqual(a.choose_options(support_obs), [1])

    def test_duplicate_legal_role_cards_use_lowest_original_index(self):
        a = self.v50
        cases = {
            "attacker": (
                self.observation(
                    [a.GABITE, a.GARCHOMP_EX, a.GARCHOMP_EX],
                    active_ids=[a.GIBLE],
                ),
                1,
            ),
            "support_base": (
                self.observation(
                    [a.GABITE, a.ROSELIA, a.ROSELIA],
                    hand_ids=[a.GARCHOMP_EX], active_ids=[a.GIBLE], bench_ids=[a.GABITE],
                ),
                1,
            ),
            "support_evolution": (
                self.observation(
                    [a.GABITE, a.ROSERADE, a.ROSERADE],
                    hand_ids=[a.GARCHOMP_EX], active_ids=[a.GIBLE],
                    bench_ids=[a.GABITE, a.ROSELIA],
                ),
                1,
            ),
        }
        for name, (obs, expected) in cases.items():
            with self.subTest(role=name):
                self.assertEqual(a.choose_options(obs), [expected])

    def test_exact_deck_and_no_unrelated_source_member_changes(self):
        baseline_files = {
            path.relative_to(V23_DIR): path
            for path in V23_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V50_DIR): path
            for path in V50_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(set(candidate_files), set(baseline_files))
        self.assertEqual(
            (V50_DIR / "deck.csv").read_bytes(),
            (V23_DIR / "deck.csv").read_bytes(),
        )
        deck_lines = [line for line in (V50_DIR / "deck.csv").read_text().splitlines() if line.strip()]
        self.assertEqual(len(deck_lines), 60)

        baseline_tree = ast.parse((V23_DIR / "main.py").read_text())
        candidate_tree = ast.parse((V50_DIR / "main.py").read_text())
        baseline_other = [
            node for node in baseline_tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "choose_options"
        ]
        candidate_other = [
            node for node in candidate_tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or node.name not in {"choose_options", "champions_call_route_index"}
        ]
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_other],
            [ast.dump(node, include_attributes=False) for node in baseline_other],
        )

        baseline_choose = next(
            node for node in baseline_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        candidate_choose = next(
            node for node in candidate_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        self.assertEqual(
            ast.dump(candidate_choose.args, include_attributes=False),
            ast.dump(baseline_choose.args, include_attributes=False),
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[2:]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body],
        )


if __name__ == "__main__":
    unittest.main()
