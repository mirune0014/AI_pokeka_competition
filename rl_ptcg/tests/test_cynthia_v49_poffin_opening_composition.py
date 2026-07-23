"""Focused contract checks for Cynthia Garchomp v49."""
import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V23_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve"
V49_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v49_poffin_opening_composition"


def install_api_stub():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench",
        PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium")
    api.OptionType = types.SimpleNamespace(
        ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat",
        ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end",
        NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy")
    api.SelectContext = types.SimpleNamespace(
        MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active",
        SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard",
        DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look",
        TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", TO_BENCH="to_bench",
        SWITCH="switch", TO_ACTIVE="to_active", ATTACH_TO="attach_to",
        ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage")
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


class PoffinOpeningCompositionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v23 = load_agent_module("cynthia_v23_for_v49_test", V23_DIR / "main.py")
        cls.v49 = load_agent_module("cynthia_v49_main", V49_DIR / "main.py")

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
        visible_ids,
        *,
        active_ids=(),
        bench_ids=(),
        context="to_bench",
        min_count=0,
        max_count=2,
    ):
        visible_deck = [self.card(card_id) for card_id in visible_ids]
        mine = types.SimpleNamespace(
            hand=[],
            active=[self.card(card_id) for card_id in active_ids],
            bench=[self.card(card_id) for card_id in bench_ids],
            discard=[],
            prize=[],
            deckCount=30,
        )
        opponent = types.SimpleNamespace(
            hand=[], active=[], bench=[], discard=[], prize=[], deckCount=30,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0, players=[mine, opponent], looking=[], stadium=[],
            ),
            select=types.SimpleNamespace(
                option=[self.option(index) for index in range(len(visible_deck))],
                context=context,
                minCount=min_count,
                maxCount=max_count,
                deck=visible_deck,
            ),
        )

    def assert_exact_v23(self, obs):
        self.assertEqual(self.v49.choose_options(obs), self.v23.choose_options(obs))

    def test_one_main_selects_one_gible_and_one_roselia(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.GIBLE, a.ROSELIA, a.ROSELIA],
            active_ids=[a.GIBLE],
        )
        self.assertEqual(self.v23.choose_options(obs), [0, 1])
        self.assertEqual(a.choose_options(obs), [0, 2])

    def test_two_mains_select_one_gible_and_one_roselia(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.GIBLE, a.ROSELIA],
            active_ids=[a.GARCHOMP_EX],
            bench_ids=[a.GABITE],
        )
        self.assertEqual(a.choose_options(obs), [0, 2])

    def test_zero_mains_preserves_two_gible_result(self):
        a = self.v49
        obs = self.observation([a.GIBLE, a.GIBLE, a.ROSELIA])
        self.assertEqual(self.v23.choose_options(obs), [0, 1])
        self.assert_exact_v23(obs)

    def test_existing_roselia_preserves_v23(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.GIBLE, a.ROSELIA],
            active_ids=[a.GIBLE],
            bench_ids=[a.ROSELIA],
        )
        self.assert_exact_v23(obs)

    def test_existing_roserade_preserves_v23(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.GIBLE, a.ROSELIA],
            active_ids=[a.GABITE],
            bench_ids=[a.ROSERADE],
        )
        self.assert_exact_v23(obs)

    def test_missing_legal_roselia_preserves_v23(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.GIBLE, a.SPIRITOMB],
            active_ids=[a.GIBLE],
        )
        self.assert_exact_v23(obs)

    def test_missing_legal_gible_preserves_v23(self):
        a = self.v49
        obs = self.observation(
            [a.ROSELIA, a.ROSELIA, a.SPIRITOMB],
            active_ids=[a.GARCHOMP_EX],
        )
        self.assert_exact_v23(obs)

    def test_single_selection_slot_preserves_v23(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.ROSELIA],
            active_ids=[a.GIBLE],
            max_count=1,
        )
        self.assert_exact_v23(obs)

    def test_nonzero_minimum_preserves_v23(self):
        a = self.v49
        obs = self.observation(
            [a.GIBLE, a.GIBLE, a.ROSELIA],
            active_ids=[a.GIBLE],
            min_count=1,
        )
        self.assert_exact_v23(obs)

    def test_non_to_bench_contexts_preserve_v23(self):
        a = self.v49
        for context in (a.SelectContext.MAIN, a.SelectContext.TO_HAND, a.SelectContext.SETUP_BENCH_POKEMON):
            with self.subTest(context=context):
                obs = self.observation(
                    [a.GIBLE, a.GIBLE, a.ROSELIA],
                    active_ids=[a.GIBLE],
                    context=context,
                )
                self.assert_exact_v23(obs)

    def test_duplicated_roles_use_lowest_original_indices_in_stable_order(self):
        a = self.v49
        obs = self.observation(
            [a.SPIRITOMB, a.ROSELIA, a.ROSELIA, a.GIBLE, a.GIBLE],
            active_ids=[a.GABITE],
        )
        self.assertEqual(a.choose_options(obs), [1, 3])

    def test_exact_deck_and_no_unrelated_source_member_changes(self):
        baseline_files = {
            path.relative_to(V23_DIR): path
            for path in V23_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V49_DIR): path
            for path in V49_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(set(candidate_files), set(baseline_files))
        self.assertEqual(
            (V49_DIR / "deck.csv").read_bytes(),
            (V23_DIR / "deck.csv").read_bytes(),
        )
        deck_lines = [line for line in (V49_DIR / "deck.csv").read_text().splitlines() if line.strip()]
        self.assertEqual(len(deck_lines), 60)

        baseline_tree = ast.parse((V23_DIR / "main.py").read_text())
        candidate_tree = ast.parse((V49_DIR / "main.py").read_text())
        baseline_other = [
            node for node in baseline_tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "choose_options"
        ]
        candidate_other = [
            node for node in candidate_tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            or node.name not in {"choose_options", "poffin_opening_composition_indices"}
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
