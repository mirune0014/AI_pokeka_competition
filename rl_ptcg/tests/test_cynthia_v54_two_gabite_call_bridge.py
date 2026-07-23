"""Focused contract checks for Cynthia Garchomp v54's two-Gabite Call bridge."""
import ast
import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V52_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v52_prebuster_backup_attach"
V54_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v54_two_gabite_call_bridge"
V52_MAIN_SHA256 = "2ef986b5e59559e591268358ce11aa9bb6633f9d2d49b80fa54676d5d5e930c7"
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


class TwoGabiteCallBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v52 = load_agent_module("cynthia_v52_for_v54_test", V52_DIR / "main.py")
        cls.v54 = load_agent_module("cynthia_v54_main", V54_DIR / "main.py")

    @staticmethod
    def pokemon(card_id, energy_ids=(), *, serial=None, appeared=False, hp=200):
        return types.SimpleNamespace(
            id=card_id,
            serial=serial,
            appearThisTurn=appeared,
            energies=[types.SimpleNamespace(id=energy_id) for energy_id in energy_ids],
            hp=hp,
            maxHp=hp,
            tools=[],
        )

    @staticmethod
    def option(
        option_type,
        *,
        area=None,
        index=None,
        in_play_area=None,
        in_play_index=None,
        attack_id=None,
        player_index=None,
    ):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=player_index,
            inPlayArea=in_play_area,
            inPlayIndex=in_play_index,
            attackId=attack_id,
            number=None,
        )

    def card_option(self, deck_index):
        return self.option(self.v54.OptionType.CARD, area=self.v54.AreaType.DECK, index=deck_index)

    def call(self, bench_index):
        return self.option(
            self.v54.OptionType.ABILITY,
            area=self.v54.AreaType.BENCH,
            index=bench_index,
        )

    def evolve(self, hand_index, target_index, *, target_area=None, player_index=None):
        return self.option(
            self.v54.OptionType.EVOLVE,
            area=self.v54.AreaType.HAND,
            index=hand_index,
            in_play_area=self.v54.AreaType.BENCH if target_area is None else target_area,
            in_play_index=target_index,
            player_index=player_index,
        )

    def play(self, hand_index):
        return self.option(self.v54.OptionType.PLAY, index=hand_index)

    def attach(self, hand_index, target_index):
        return self.option(
            self.v54.OptionType.ATTACH,
            area=self.v54.AreaType.HAND,
            index=hand_index,
            in_play_area=self.v54.AreaType.BENCH,
            in_play_index=target_index,
        )

    def observation(
        self,
        options,
        *,
        context=None,
        hand=None,
        active=None,
        bench=None,
        visible_deck=None,
        effect=None,
        min_count=1,
        max_count=1,
    ):
        a = self.v54
        context = a.SelectContext.MAIN if context is None else context
        active = [self.pokemon(a.ROSELIA, serial=1)] if active is None else active
        bench = [
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GIBLE, serial=30),
        ] if bench is None else bench
        hand = [] if hand is None else hand
        visible_deck = [] if visible_deck is None else visible_deck
        mine = types.SimpleNamespace(
            hand=hand,
            handCount=len(hand),
            active=active,
            bench=bench,
            benchMax=5,
            discard=[],
            prize=[self.pokemon(9900 + index) for index in range(6)],
            deckCount=30,
        )
        other = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=[self.pokemon(9000)],
            bench=[],
            benchMax=5,
            discard=[],
            prize=[self.pokemon(9800 + index) for index in range(6)],
            deckCount=30,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, other],
                looking=[],
                stadium=[],
            ),
            select=types.SimpleNamespace(
                option=options,
                context=context,
                minCount=min_count,
                maxCount=max_count,
                deck=visible_deck,
                effect=effect,
            ),
        )

    def call_observation(
        self,
        *,
        hand=None,
        active=None,
        bench=None,
        visible_deck=None,
        effect=None,
        max_count=1,
    ):
        a = self.v54
        visible_deck = [
            self.pokemon(a.GARCHOMP_EX, serial=100),
            self.pokemon(a.GABITE, serial=101),
        ] if visible_deck is None else visible_deck
        return self.observation(
            [self.card_option(index) for index in range(len(visible_deck))],
            context=a.SelectContext.TO_HAND,
            hand=hand,
            active=active,
            bench=bench,
            visible_deck=visible_deck,
            effect=self.pokemon(a.GABITE, serial=20) if effect is None else effect,
            max_count=max_count,
        )

    def assert_exact_v52(self, obs):
        self.assertEqual(self.v54.choose_options(obs), self.v52.choose_options(obs))

    def test_eligible_first_call_chooses_lowest_legal_gabite_index(self):
        a = self.v54
        visible = [
            self.pokemon(a.GARCHOMP_EX),
            self.pokemon(a.GABITE),
            self.pokemon(a.GABITE),
        ]
        obs = self.call_observation(visible_deck=visible)
        self.assertEqual(self.v52.choose_options(obs), [0])
        self.assertEqual(a.two_gabite_call_target_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_garchomp_in_play_delegates_exactly_to_v52(self):
        a = self.v54
        obs = self.call_observation(
            active=[self.pokemon(a.GARCHOMP_EX, serial=1)],
        )
        self.assertIsNone(a.two_gabite_call_target_index(obs))
        self.assert_exact_v52(obs)

    def test_zero_or_two_in_play_gabites_delegate_exactly_to_v52(self):
        a = self.v54
        cases = {
            "zero": [self.pokemon(a.GIBLE, serial=30)],
            "two": [
                self.pokemon(a.GABITE, serial=20),
                self.pokemon(a.GABITE, serial=21),
                self.pokemon(a.GIBLE, serial=30),
            ],
        }
        for name, bench in cases.items():
            with self.subTest(case=name):
                obs = self.call_observation(bench=bench)
                self.assertIsNone(a.two_gabite_call_target_index(obs))
                self.assert_exact_v52(obs)

    def test_missing_old_benched_gible_delegates_exactly_to_v52(self):
        a = self.v54
        cases = {
            "no_gible": [self.pokemon(a.GABITE, serial=20)],
            "new_gible": [
                self.pokemon(a.GABITE, serial=20),
                self.pokemon(a.GIBLE, serial=30, appeared=True),
            ],
            "old_active_gible": [self.pokemon(a.GABITE, serial=20)],
        }
        for name, bench in cases.items():
            with self.subTest(case=name):
                active = [self.pokemon(a.GIBLE, serial=1)] if name == "old_active_gible" else None
                obs = self.call_observation(bench=bench, active=active)
                self.assertIsNone(a.two_gabite_call_target_index(obs))
                self.assert_exact_v52(obs)

    def test_no_legal_gabite_call_target_delegates_exactly_to_v52(self):
        a = self.v54
        visible = [self.pokemon(a.GARCHOMP_EX), self.pokemon(a.ROSERADE)]
        obs = self.call_observation(visible_deck=visible)
        self.assertIsNone(a.two_gabite_call_target_index(obs))
        self.assert_exact_v52(obs)

    def test_bridge_evolves_highest_v52_score_old_benched_gible(self):
        a = self.v54
        hand = [self.pokemon(a.GARCHOMP_EX), self.pokemon(a.GABITE), self.pokemon(a.GABITE)]
        bench = [
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GIBLE, serial=30),
            self.pokemon(a.GIBLE, (a.BASIC_FIGHTING,), serial=31),
        ]
        obs = self.observation(
            [self.evolve(0, 0), self.evolve(1, 1), self.evolve(2, 2)],
            hand=hand,
            bench=bench,
        )
        self.assertEqual(self.v52.choose_options(obs), [0])
        self.assertEqual(a.old_gible_to_gabite_bridge_index(obs), 2)
        self.assertEqual(a.choose_options(obs), [2])

    def test_bridge_exact_score_ties_use_lowest_option_index(self):
        a = self.v54
        hand = [self.pokemon(a.GARCHOMP_EX), self.pokemon(a.GABITE), self.pokemon(a.GABITE)]
        bench = [
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GIBLE, serial=30),
            self.pokemon(a.GIBLE, serial=31),
        ]
        obs = self.observation(
            [self.evolve(0, 0), self.evolve(1, 2), self.evolve(2, 1)],
            hand=hand,
            bench=bench,
        )
        self.assertEqual(a.old_gible_to_gabite_bridge_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_newly_appeared_gible_is_never_forced_to_evolve(self):
        a = self.v54
        all_new = self.observation(
            [self.evolve(0, 0), self.evolve(1, 1)],
            hand=[self.pokemon(a.GARCHOMP_EX), self.pokemon(a.GABITE)],
            bench=[
                self.pokemon(a.GABITE, serial=20),
                self.pokemon(a.GIBLE, (a.BASIC_FIGHTING,), serial=30, appeared=True),
            ],
        )
        self.assertIsNone(a.old_gible_to_gabite_bridge_index(all_new))
        self.assert_exact_v52(all_new)

        mixed = self.observation(
            [self.evolve(0, 1), self.evolve(1, 2)],
            hand=[self.pokemon(a.GABITE), self.pokemon(a.GABITE)],
            bench=[
                self.pokemon(a.GABITE, serial=20),
                self.pokemon(a.GIBLE, serial=30),
                self.pokemon(
                    a.GIBLE,
                    (a.BASIC_FIGHTING, a.ROCK_FIGHTING),
                    serial=31,
                    appeared=True,
                ),
            ],
        )
        self.assertEqual(a.old_gible_to_gabite_bridge_index(mixed), 0)
        self.assertEqual(a.choose_options(mixed), [0])

    def test_after_two_gabites_second_call_activation_and_target_match_v52(self):
        a = self.v54
        bench = [
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GABITE, serial=21),
            self.pokemon(a.GIBLE, serial=30),
        ]
        main_obs = self.observation(
            [self.call(0), self.evolve(0, 0), self.evolve(1, 2)],
            hand=[self.pokemon(a.GARCHOMP_EX), self.pokemon(a.GABITE)],
            bench=bench,
        )
        self.assertIsNone(a.old_gible_to_gabite_bridge_index(main_obs))
        self.assertEqual(self.v52.choose_options(main_obs), [0])
        self.assert_exact_v52(main_obs)

        visible = [self.pokemon(a.GABITE), self.pokemon(a.GARCHOMP_EX)]
        target_obs = self.call_observation(bench=bench, visible_deck=visible)
        self.assertIsNone(a.two_gabite_call_target_index(target_obs))
        self.assertEqual(self.v52.choose_options(target_obs), [1])
        self.assert_exact_v52(target_obs)

    def test_no_third_gabite_or_excluded_action_is_forced(self):
        a = self.v54
        two_gabites = [
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GABITE, serial=21),
            self.pokemon(a.GIBLE, serial=30),
        ]
        third_visible = [self.pokemon(a.GABITE), self.pokemon(a.ROSERADE)]
        third_obs = self.call_observation(
            bench=two_gabites,
            visible_deck=third_visible,
            hand=[self.pokemon(a.GARCHOMP_EX)],
        )
        self.assertIsNone(a.two_gabite_call_target_index(third_obs))
        self.assert_exact_v52(third_obs)

        base_bench = [
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GIBLE, serial=30),
            self.pokemon(a.ROSELIA, serial=40),
        ]
        cases = {
            "attack": self.observation(
                [self.option(a.OptionType.ATTACK, attack_id=a.LEAF_STEP)],
                bench=base_bench,
            ),
            "supporter": self.observation(
                [self.play(0)], hand=[self.pokemon(a.BOSS)], bench=base_bench,
            ),
            "item": self.observation(
                [self.play(0)], hand=[self.pokemon(a.POKE_PAD)], bench=base_bench,
            ),
            "attachment": self.observation(
                [self.attach(0, 1)], hand=[self.pokemon(a.BASIC_FIGHTING)], bench=base_bench,
            ),
            "retreat": self.observation(
                [self.option(a.OptionType.RETREAT)], bench=base_bench,
            ),
            "roserade_evolution": self.observation(
                [self.evolve(0, 2)], hand=[self.pokemon(a.ROSERADE)], bench=base_bench,
            ),
            "garchomp_evolution": self.observation(
                [self.evolve(0, 0)], hand=[self.pokemon(a.GARCHOMP_EX)], bench=base_bench,
            ),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(a.old_gible_to_gabite_bridge_index(obs))
                self.assert_exact_v52(obs)

    def test_non_main_and_non_call_selections_match_v52(self):
        a = self.v54
        visible = [self.pokemon(a.GABITE), self.pokemon(a.GARCHOMP_EX)]
        for context in (a.SelectContext.LOOK, a.SelectContext.ATTACH_TO, a.SelectContext.TO_DECK):
            with self.subTest(context=context):
                obs = self.observation(
                    [self.card_option(0), self.card_option(1)],
                    context=context,
                    visible_deck=visible,
                    effect=self.pokemon(a.GABITE),
                )
                self.assertIsNone(a.two_gabite_call_target_index(obs))
                self.assertIsNone(a.old_gible_to_gabite_bridge_index(obs))
                self.assert_exact_v52(obs)

        non_call = self.call_observation(effect=self.pokemon(a.GIBLE))
        self.assertIsNone(a.two_gabite_call_target_index(non_call))
        self.assert_exact_v52(non_call)

    def test_exact_deck_and_only_two_helpers_plus_hooks_differ_from_v52(self):
        baseline_files = {
            path.relative_to(V52_DIR)
            for path in V52_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V54_DIR)
            for path in V54_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V52_DIR / "main.py").read_bytes()
        baseline_deck = (V52_DIR / "deck.csv").read_bytes()
        candidate_main = (V54_DIR / "main.py").read_bytes()
        candidate_deck = (V54_DIR / "deck.csv").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V52_MAIN_SHA256)
        self.assertEqual(hashlib.sha256(baseline_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(60, len([line for line in candidate_deck.splitlines() if line.strip()]))
        candidate_main.decode("ascii")

        baseline_tree = ast.parse(baseline_main)
        candidate_tree = ast.parse(candidate_main)
        baseline_unchanged = [
            node for node in baseline_tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "choose_options"
        ]
        candidate_unchanged = [
            node for node in candidate_tree.body
            if not isinstance(node, ast.FunctionDef)
            or node.name not in {
                "two_gabite_call_target_index",
                "old_gible_to_gabite_bridge_index",
                "choose_options",
            }
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
        expected_hooks = ast.parse(
            "def choose_options(obs):\n"
            "    call_target_index = two_gabite_call_target_index(obs)\n"
            "    if call_target_index is not None:\n"
            "        return [call_target_index]\n"
            "    bridge_evolve_index = old_gible_to_gabite_bridge_index(obs)\n"
            "    if bridge_evolve_index is not None:\n"
            "        return [bridge_evolve_index]\n"
        ).body[0].body
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[:4]],
            [ast.dump(node, include_attributes=False) for node in expected_hooks],
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[4:]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body],
        )


if __name__ == "__main__":
    unittest.main()
