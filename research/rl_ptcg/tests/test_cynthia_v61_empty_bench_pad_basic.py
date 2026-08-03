"""Focused contract checks for Cynthia Garchomp v61's empty-Bench Pad route."""

import ast
import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V58_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v58_core_bridge_before_chip"
V61_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v61_empty_bench_pad_basic"
V58_MAIN_SHA256 = "8375c5e73d7ad9c1b4e863993a6cbe8bcc96668008bb3ae709b3dc62d6f8d25a"
DECK_SHA256 = "606b44f7d6181c57c6ccdd7ee493c72baf39e684b264886bc01631dbee8d349c"


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


class EmptyBenchPokePadBasicTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v58 = load_agent_module("cynthia_v58_for_v61_test", V58_DIR / "main.py")
        cls.v61 = load_agent_module("cynthia_v61_main", V61_DIR / "main.py")

    @staticmethod
    def card(card_id, *, serial=None):
        return types.SimpleNamespace(
            id=card_id,
            serial=serial,
            energies=[],
            hp=200,
            maxHp=200,
            tools=[],
        )

    @staticmethod
    def option(option_type, *, area=None, index=None):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=None,
            inPlayArea=None,
            inPlayIndex=None,
            attackId=None,
            number=None,
        )

    def pad_observation(
        self,
        legal_ids,
        *,
        hand_ids=(),
        active_ids=None,
        bench_ids=(),
        bench_max=5,
        effect_id=None,
        context=None,
    ):
        a = self.v61
        active_ids = (a.GIBLE,) if active_ids is None else active_ids
        effect_id = a.POKE_PAD if effect_id is None else effect_id
        visible_deck = [self.card(card_id, serial=100 + index) for index, card_id in enumerate(legal_ids)]
        mine = types.SimpleNamespace(
            hand=[self.card(card_id) for card_id in hand_ids],
            handCount=len(hand_ids),
            active=[self.card(card_id) for card_id in active_ids],
            bench=[self.card(card_id) for card_id in bench_ids],
            benchMax=bench_max,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        opponent = types.SimpleNamespace(
            hand=None,
            handCount=0,
            active=[self.card(9000)],
            bench=[],
            benchMax=5,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, opponent],
                looking=[],
                stadium=[],
            ),
            select=types.SimpleNamespace(
                option=[
                    self.option(a.OptionType.CARD, area=a.AreaType.DECK, index=index)
                    for index in range(len(visible_deck))
                ],
                context=a.SelectContext.TO_HAND if context is None else context,
                minCount=1,
                maxCount=1,
                deck=visible_deck,
                effect=self.card(effect_id) if effect_id is not False else None,
            ),
        )

    def main_observation(self, basic_id):
        a = self.v61
        mine = types.SimpleNamespace(
            hand=[self.card(basic_id)],
            handCount=1,
            active=[self.card(a.GIBLE)],
            bench=[],
            benchMax=5,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        opponent = types.SimpleNamespace(
            hand=None,
            handCount=0,
            active=[self.card(9000)],
            bench=[],
            benchMax=5,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, opponent],
                looking=[],
                stadium=[],
            ),
            select=types.SimpleNamespace(
                option=[
                    self.option(a.OptionType.PLAY, index=0),
                    self.option(a.OptionType.END),
                ],
                context=a.SelectContext.MAIN,
                minCount=1,
                maxCount=1,
                deck=[],
                effect=None,
            ),
        )

    def test_live_turn2_reconstruction_selects_gible_over_gabite(self):
        a = self.v61
        obs = self.pad_observation(
            [a.GABITE, a.GIBLE, a.ROSELIA],
            hand_ids=(a.BASIC_FIGHTING,),
        )
        self.assertEqual(self.v58.choose_options(obs), [0])
        self.assertEqual(a.empty_bench_poke_pad_basic_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_without_gible_selects_lowest_roselia_then_spiritomb(self):
        a = self.v61
        cases = {
            "Roselia": ([a.GABITE, a.SPIRITOMB, a.ROSELIA, a.ROSELIA], 2),
            "Spiritomb": ([a.GABITE, a.SPIRITOMB, a.SPIRITOMB], 1),
        }
        for route, (legal_ids, expected) in cases.items():
            with self.subTest(route=route):
                obs = self.pad_observation(legal_ids)
                self.assertEqual(a.empty_bench_poke_pad_basic_index(obs), expected)
                self.assertEqual(a.choose_options(obs), [expected])

    def test_nonempty_bench_vetoes_route(self):
        a = self.v61
        obs = self.pad_observation(
            [a.GABITE, a.GIBLE],
            bench_ids=(a.ROSELIA,),
        )
        self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))
        self.assertEqual(a.choose_options(obs), self.v58.choose_options(obs))

    def test_benchable_basic_already_in_hand_vetoes_route(self):
        a = self.v61
        for basic_id in (a.GIBLE, a.ROSELIA, a.SPIRITOMB):
            with self.subTest(basic_id=basic_id):
                obs = self.pad_observation(
                    [a.GABITE, a.GIBLE],
                    hand_ids=(basic_id,),
                )
                self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))
                self.assertEqual(a.choose_options(obs), self.v58.choose_options(obs))

    def test_non_pad_effect_vetoes_route(self):
        a = self.v61
        for effect_id in (a.GABITE, False):
            with self.subTest(effect_id=effect_id):
                obs = self.pad_observation(
                    [a.GABITE, a.GIBLE],
                    effect_id=effect_id,
                )
                self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))

    def test_non_to_hand_context_vetoes_route(self):
        a = self.v61
        for context in (a.SelectContext.MAIN, a.SelectContext.LOOK):
            with self.subTest(context=context):
                obs = self.pad_observation(
                    [a.GABITE, a.GIBLE],
                    context=context,
                )
                self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))

    def test_full_bench_vetoes_route(self):
        a = self.v61
        obs = self.pad_observation(
            [a.GABITE, a.GIBLE],
            bench_ids=(a.GIBLE, a.ROSELIA, a.SPIRITOMB, 9001, 9002),
            bench_max=5,
        )
        self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))

    def test_active_must_contain_exactly_one_pokemon(self):
        a = self.v61
        for active_ids in ((), (a.GIBLE, a.ROSELIA)):
            with self.subTest(active_count=len(active_ids)):
                obs = self.pad_observation(
                    [a.GABITE, a.GIBLE],
                    active_ids=active_ids,
                )
                self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))

    def test_no_legal_basic_option_returns_none(self):
        a = self.v61
        obs = self.pad_observation([a.GABITE, a.GARCHOMP_EX, a.ROSERADE])
        self.assertIsNone(a.empty_bench_poke_pad_basic_index(obs))
        self.assertEqual(a.choose_options(obs), self.v58.choose_options(obs))

    def test_next_main_uses_unchanged_v58_scores_to_bench_selected_basic(self):
        a = self.v61
        for basic_id in (a.GIBLE, a.ROSELIA, a.SPIRITOMB):
            with self.subTest(basic_id=basic_id):
                obs = self.main_observation(basic_id)
                play = obs.select.option[0]
                self.assertEqual(a.score_play(obs, play), self.v58.score_play(obs, play))
                self.assertEqual(self.v58.choose_options(obs), [0])
                self.assertEqual(a.choose_options(obs), [0])

    def test_exact_v58_copy_except_helper_and_first_choose_hook(self):
        baseline_files = {
            path.relative_to(V58_DIR)
            for path in V58_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V61_DIR)
            for path in V61_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V58_DIR / "main.py").read_bytes()
        candidate_main = (V61_DIR / "main.py").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V58_MAIN_SHA256)
        baseline_tree = ast.parse(baseline_main)
        candidate_tree = ast.parse(candidate_main)
        baseline_unchanged = [
            node for node in baseline_tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "choose_options"
        ]
        candidate_unchanged = [
            node for node in candidate_tree.body
            if not isinstance(node, ast.FunctionDef)
            or node.name not in {"empty_bench_poke_pad_basic_index", "choose_options"}
        ]
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_unchanged],
            [ast.dump(node, include_attributes=False) for node in baseline_unchanged],
        )

        baseline_choose = next(
            node for node in baseline_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        candidate_choose = next(
            node for node in candidate_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        expected_hook = ast.parse(
            "def choose_options(obs):\n"
            "    pad_basic_index = empty_bench_poke_pad_basic_index(obs)\n"
            "    if pad_basic_index is not None:\n"
            "        return [pad_basic_index]\n"
        ).body[0].body
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[:2]],
            [ast.dump(node, include_attributes=False) for node in expected_hook],
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[2:]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body],
        )

        baseline_deck = (V58_DIR / "deck.csv").read_bytes()
        candidate_deck = (V61_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(len([line for line in candidate_deck.splitlines() if line.strip()]), 60)


if __name__ == "__main__":
    unittest.main()
