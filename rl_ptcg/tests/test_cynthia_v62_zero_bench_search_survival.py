"""Focused contract checks for Cynthia Garchomp v62's zero-Bench search route."""

import ast
import hashlib
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V58_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v58_core_bridge_before_chip"
V62_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v62_zero_bench_search_survival"
REPLAY_DIR = ROOT / "analysis_outputs" / "kaggle_live" / "submission_54666167_cynthia_v58"
V58_MAIN_SHA256 = "8375c5e73d7ad9c1b4e863993a6cbe8bcc96668008bb3ae709b3dc62d6f8d25a"
DECK_SHA256 = "606b44f7d6181c57c6ccdd7ee493c72baf39e684b264886bc01631dbee8d349c"
REPLAY_CASES = {
    85835485: {
        "sha256": "216e7ee64db6870c454c40f7b1d2ba897244a9b4ae4f59768a59076e6f2d0a99",
        "step": 21,
        "player": 1,
        "effect": 1152,
        "v58_index": 6,
        "v62_index": 0,
    },
    85842301: {
        "sha256": "9d5e267e807edef2a9dca85a6d4930309645ab611f29d92976340e3de484d8cb",
        "step": 17,
        "player": 0,
        "effect": 380,
        "v58_index": 4,
        "v62_index": 5,
    },
    85852617: {
        "sha256": "58b1f6e8c77ce6a07954ba168e96205ced13a2f2e94e9baf45e97e97f01f4ee6",
        "step": 43,
        "player": 1,
        "effect": 380,
        "v58_index": 3,
        "v62_index": 2,
    },
}


def install_api_stub():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        DECK=1, HAND=2, DISCARD=3, ACTIVE=4, BENCH=5, PRIZE=6, STADIUM=7,
        LOOKING=12,
    )
    api.OptionType = types.SimpleNamespace(
        NUMBER=0, YES=1, NO=2, CARD=3, TOOL_CARD=4, ENERGY_CARD=5, ENERGY=6,
        PLAY=7, ATTACH=8, EVOLVE=9, ABILITY=10, DISCARD=11, RETREAT=12,
        ATTACK=13, END=14,
    )
    api.SelectContext = types.SimpleNamespace(
        MAIN=0, SETUP_ACTIVE_POKEMON=1, SETUP_BENCH_POKEMON=2, SWITCH=3,
        TO_ACTIVE=4, TO_BENCH=5, TO_HAND=7, DISCARD=8, TO_DECK=9,
        TO_DECK_BOTTOM=10, DAMAGE=15, HEAL=17, ATTACH_FROM=21, ATTACH_TO=22,
        LOOK=24, DISCARD_CARD_OR_ATTACHED_CARD=29, IS_FIRST=41,
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


def to_object(value):
    if isinstance(value, dict):
        return types.SimpleNamespace(**{key: to_object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [to_object(item) for item in value]
    return value


class ZeroBenchSearchSurvivalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v58 = load_agent_module("cynthia_v58_for_v62_test", V58_DIR / "main.py")
        cls.v62 = load_agent_module("cynthia_v62_main", V62_DIR / "main.py")

    @staticmethod
    def card(card_id, *, serial=None):
        return types.SimpleNamespace(
            id=card_id,
            serial=serial,
            energies=[],
            energyCards=[],
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

    def cards(self, card_ids):
        return [None if card_id is None else self.card(card_id) for card_id in card_ids]

    def search_observation(
        self,
        legal_ids,
        *,
        hand_ids=(),
        active_ids=None,
        bench_ids=(),
        bench_max=5,
        effect_id=None,
        context=None,
        max_count=1,
        hand_observable=True,
    ):
        a = self.v62
        active_ids = (a.GIBLE,) if active_ids is None else active_ids
        effect_id = a.POKE_PAD if effect_id is None else effect_id
        visible_deck = [self.card(card_id, serial=100 + index) for index, card_id in enumerate(legal_ids)]
        hand = self.cards(hand_ids) if hand_observable else None
        mine = types.SimpleNamespace(
            hand=hand,
            handCount=len(hand_ids),
            active=self.cards(active_ids),
            bench=self.cards(bench_ids),
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
                maxCount=max_count,
                deck=visible_deck,
                effect=None if effect_id is False else self.card(effect_id),
            ),
        )

    def main_observation(self, basic_id, *, active_id):
        a = self.v62
        mine = types.SimpleNamespace(
            hand=[self.card(basic_id)],
            handCount=1,
            active=[self.card(active_id)],
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

    @staticmethod
    def replay_observation(episode_id, case):
        replay_path = REPLAY_DIR / f"episode_{episode_id}_replay.json"
        replay_bytes = replay_path.read_bytes()
        if hashlib.sha256(replay_bytes).hexdigest() != case["sha256"]:
            raise AssertionError(f"unexpected replay hash for {episode_id}")
        replay = json.loads(replay_bytes)
        raw = replay["steps"][case["step"]][case["player"]]["observation"]
        return to_object(raw)

    def assert_preserves_v58(self, obs):
        self.assertIsNone(self.v62.zero_bench_search_survival_index(obs))
        self.assertEqual(self.v62.choose_options(obs), self.v58.choose_options(obs))

    def test_three_live_replay_states_choose_lowest_index_gible_and_it_is_benchable(self):
        a = self.v62
        for episode_id, case in REPLAY_CASES.items():
            with self.subTest(episode_id=episode_id):
                obs = self.replay_observation(episode_id, case)
                player = a.me(obs)
                hand = {card.id for card in player.hand if card}
                in_play = {pokemon.id for pokemon in a.my_pokemon(obs)}

                self.assertEqual(obs.select.context, a.SelectContext.TO_HAND)
                self.assertEqual(obs.select.maxCount, 1)
                self.assertEqual(obs.select.effect.id, case["effect"])
                self.assertEqual(len([pokemon for pokemon in player.active if pokemon]), 1)
                self.assertEqual(len([pokemon for pokemon in player.bench if pokemon]), 0)
                self.assertLess(0, player.benchMax)
                self.assertTrue(hand.isdisjoint(a.CYNTHIA_BASICS))
                if case["effect"] == a.GABITE:
                    self.assertIn(a.GARCHOMP_EX, hand | in_play)

                self.assertEqual(self.v58.choose_options(obs), [case["v58_index"]])
                self.assertEqual(a.zero_bench_search_survival_index(obs), case["v62_index"])
                self.assertEqual(a.choose_options(obs), [case["v62_index"]])
                selected = a.option_card(obs, obs.select.option[case["v62_index"]])
                self.assertEqual(selected.id, a.GIBLE)

                next_main = self.main_observation(selected.id, active_id=player.active[0].id)
                play = next_main.select.option[0]
                self.assertEqual(a.score_play(next_main, play), self.v58.score_play(next_main, play))
                self.assertEqual(self.v58.choose_options(next_main), [0])
                self.assertEqual(a.choose_options(next_main), [0])

    def test_basic_priority_and_lowest_option_index_for_both_searches(self):
        a = self.v62
        search_hands = {
            a.POKE_PAD: (),
            a.GABITE: (a.GARCHOMP_EX,),
        }
        cases = (
            ([a.SPIRITOMB, a.ROSELIA, a.GIBLE, a.GIBLE], 2),
            ([a.SPIRITOMB, a.ROSELIA, a.ROSELIA], 1),
            ([a.SPIRITOMB, a.SPIRITOMB], 0),
        )
        for effect_id, hand_ids in search_hands.items():
            for legal_ids, expected in cases:
                with self.subTest(effect_id=effect_id, legal_ids=legal_ids):
                    obs = self.search_observation(
                        legal_ids,
                        hand_ids=hand_ids,
                        effect_id=effect_id,
                    )
                    self.assertEqual(a.zero_bench_search_survival_index(obs), expected)
                    self.assertEqual(a.choose_options(obs), [expected])

    def test_champions_call_accepts_garchomp_in_play(self):
        a = self.v62
        obs = self.search_observation(
            [a.ROSERADE, a.ROSELIA],
            active_ids=(a.GARCHOMP_EX,),
            effect_id=a.GABITE,
        )
        self.assertEqual(a.zero_bench_search_survival_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_nonempty_and_full_bench_preserve_v58(self):
        a = self.v62
        cases = (
            ((a.ROSELIA,), 5),
            ((a.GIBLE, a.ROSELIA, a.SPIRITOMB, 9001, 9002), 5),
        )
        for bench_ids, bench_max in cases:
            with self.subTest(bench_ids=bench_ids):
                obs = self.search_observation(
                    [a.GABITE, a.GIBLE],
                    bench_ids=bench_ids,
                    bench_max=bench_max,
                )
                self.assert_preserves_v58(obs)

    def test_empty_placeholder_slots_use_occupied_counts(self):
        a = self.v62
        obs = self.search_observation(
            [a.GABITE, a.GIBLE],
            active_ids=(None, a.GIBLE),
            bench_ids=(None, None, None, None, None),
            bench_max=5,
        )
        self.assertEqual(a.zero_bench_search_survival_index(obs), 1)

    def test_basic_already_in_hand_preserves_v58(self):
        a = self.v62
        for basic_id in (a.GIBLE, a.ROSELIA, a.SPIRITOMB):
            with self.subTest(basic_id=basic_id):
                obs = self.search_observation(
                    [a.GABITE, a.GIBLE],
                    hand_ids=(basic_id,),
                )
                self.assert_preserves_v58(obs)

    def test_wrong_context_effect_and_count_preserve_v58(self):
        a = self.v62
        cases = (
            {"context": a.SelectContext.LOOK},
            {"effect_id": a.HILDA},
            {"effect_id": False},
            {"max_count": 2},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                obs = self.search_observation([a.GABITE, a.GIBLE], **kwargs)
                self.assert_preserves_v58(obs)

    def test_unobservable_hand_and_invalid_active_count_preserve_v58(self):
        a = self.v62
        cases = (
            {"hand_observable": False},
            {"active_ids": ()},
            {"active_ids": (a.GIBLE, a.ROSELIA)},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                obs = self.search_observation([a.GABITE, a.GIBLE], **kwargs)
                self.assert_preserves_v58(obs)

    def test_no_legal_basic_preserves_v58(self):
        a = self.v62
        obs = self.search_observation([a.GABITE, a.GARCHOMP_EX, a.ROSERADE])
        self.assert_preserves_v58(obs)

    def test_champions_call_without_garchomp_preserves_v58(self):
        a = self.v62
        obs = self.search_observation(
            [a.GIBLE, a.GARCHOMP_EX],
            effect_id=a.GABITE,
        )
        self.assertIsNone(a.zero_bench_search_survival_index(obs))
        self.assertEqual(self.v58.choose_options(obs), [1])
        self.assertEqual(a.choose_options(obs), [1])

    def test_exact_v58_copy_except_helper_and_pre_route_hook(self):
        baseline_files = {
            path.relative_to(V58_DIR)
            for path in V58_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V62_DIR)
            for path in V62_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V58_DIR / "main.py").read_bytes()
        candidate_main = (V62_DIR / "main.py").read_bytes()
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
            or node.name not in {"zero_bench_search_survival_index", "choose_options"}
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
            "    survival_index = zero_bench_search_survival_index(obs)\n"
            "    if survival_index is not None:\n"
            "        return [survival_index]\n"
        ).body[0].body
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[:2]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body[:2]],
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[2:4]],
            [ast.dump(node, include_attributes=False) for node in expected_hook],
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[4:]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body[2:]],
        )

        baseline_deck = (V58_DIR / "deck.csv").read_bytes()
        candidate_deck = (V62_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(len([line for line in candidate_deck.splitlines() if line.strip()]), 60)


if __name__ == "__main__":
    unittest.main()
