"""Focused contract checks for Cynthia Garchomp v52's pre-Buster backup attach."""
import ast
import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V50_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v50_champions_call_route"
V52_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v52_prebuster_backup_attach"
V50_MAIN_SHA256 = "124838193f07c2a7f31e5f839cad097c02c2d6dc85ac1cb61a38b6f84875d999"
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


class PrebusterBackupAttachTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v50 = load_agent_module("cynthia_v50_for_v52_test", V50_DIR / "main.py")
        cls.v52 = load_agent_module("cynthia_v52_main", V52_DIR / "main.py")

    @staticmethod
    def pokemon(card_id, energy_ids=(), hp=200):
        return types.SimpleNamespace(
            id=card_id,
            energies=[types.SimpleNamespace(id=energy_id) for energy_id in energy_ids],
            hp=hp,
            maxHp=hp,
            tools=[],
            serial=None,
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
    ):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=None,
            inPlayArea=in_play_area,
            inPlayIndex=in_play_index,
            attackId=attack_id,
            number=None,
        )

    def attach(self, hand_index, target_area, target_index):
        return self.option(
            self.v52.OptionType.ATTACH,
            area=self.v52.AreaType.HAND,
            index=hand_index,
            in_play_area=target_area,
            in_play_index=target_index,
        )

    def buster(self):
        return self.option(self.v52.OptionType.ATTACK, attack_id=self.v52.DRACONIC_BUSTER)

    def end(self):
        return self.option(self.v52.OptionType.END)

    def observation(
        self,
        *,
        options=None,
        hand_ids=None,
        active_id=None,
        active_energy_ids=None,
        bench=None,
        opponent_hp=200,
        opponent_bench=None,
        prize_count=6,
        context=None,
    ):
        a = self.v52
        hand_ids = [a.BASIC_FIGHTING] if hand_ids is None else hand_ids
        active_id = a.GARCHOMP_EX if active_id is None else active_id
        active_energy_ids = [a.BASIC_FIGHTING, a.BASIC_FIGHTING] if active_energy_ids is None else active_energy_ids
        bench = [(a.ROSERADE, ()), (a.GIBLE, ())] if bench is None else bench
        opponent_bench = [] if opponent_bench is None else opponent_bench
        context = a.SelectContext.MAIN if context is None else context
        options = [
            self.attach(0, a.AreaType.BENCH, 1),
            self.buster(),
        ] if options is None else options

        hand = [self.pokemon(card_id) for card_id in hand_ids]
        mine = types.SimpleNamespace(
            hand=hand,
            handCount=len(hand),
            active=[self.pokemon(active_id, active_energy_ids)],
            bench=[self.pokemon(card_id, energies) for card_id, energies in bench],
            benchMax=5,
            discard=[],
            prize=[self.pokemon(9900 + index) for index in range(prize_count)],
            deckCount=30,
        )
        other = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=[self.pokemon(9000, hp=opponent_hp)],
            bench=[self.pokemon(card_id) for card_id in opponent_bench],
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
                minCount=1,
                maxCount=1,
                deck=[],
                effect=None,
            ),
        )

    def assert_exact_v50(self, obs):
        self.assertIsNone(self.v52.prebuster_backup_attach_index(obs))
        self.assertEqual(self.v52.choose_options(obs), self.v50.choose_options(obs))

    def test_ready_supported_garchomp_attaches_to_backup_before_approved_buster(self):
        obs = self.observation()
        self.assertEqual(self.v50.choose_options(obs), [1])
        self.assertEqual(self.v52.prebuster_backup_attach_index(obs), 0)
        self.assertEqual(self.v52.choose_options(obs), [0])

    def test_multiple_eligible_targets_use_existing_score_priority_and_stable_ties(self):
        a = self.v52
        cases = {
            "garchomp_over_gabite_and_gible": (
                self.observation(
                    hand_ids=[a.BASIC_FIGHTING] * 3,
                    bench=[(a.ROSERADE, ()), (a.GIBLE, ()), (a.GABITE, ()), (a.GARCHOMP_EX, ())],
                    options=[
                        self.attach(0, a.AreaType.BENCH, 1),
                        self.attach(1, a.AreaType.BENCH, 2),
                        self.attach(2, a.AreaType.BENCH, 3),
                        self.buster(),
                    ],
                ),
                2,
            ),
            "gabite_over_gible": (
                self.observation(
                    hand_ids=[a.BASIC_FIGHTING] * 2,
                    bench=[(a.ROSERADE, ()), (a.GIBLE, ()), (a.GABITE, ())],
                    options=[
                        self.attach(0, a.AreaType.BENCH, 1),
                        self.attach(1, a.AreaType.BENCH, 2),
                        self.buster(),
                    ],
                ),
                1,
            ),
            "gible_when_only_main_target": (
                self.observation(),
                0,
            ),
            "equal_gible_scores_use_lowest_option_index": (
                self.observation(
                    hand_ids=[a.BASIC_FIGHTING] * 2,
                    bench=[(a.ROSERADE, ()), (a.GIBLE, ()), (a.GIBLE, ())],
                    options=[
                        self.buster(),
                        self.attach(0, a.AreaType.BENCH, 1),
                        self.attach(1, a.AreaType.BENCH, 2),
                    ],
                ),
                1,
            ),
        }
        for name, (obs, expected_index) in cases.items():
            with self.subTest(case=name):
                self.assertEqual(a.prebuster_backup_attach_index(obs), expected_index)
                self.assertEqual(a.choose_options(obs), [expected_index])

    def test_energy_bearing_backup_delegates_exactly_to_v50(self):
        a = self.v52
        obs = self.observation(
            hand_ids=[a.BASIC_FIGHTING],
            bench=[(a.ROSERADE, ()), (a.GIBLE, (a.BASIC_FIGHTING,)), (a.GABITE, ())],
            options=[
                self.attach(0, a.AreaType.BENCH, 2),
                self.buster(),
            ],
        )
        self.assert_exact_v50(obs)

    def test_missing_roserade_delegates_exactly_to_v50(self):
        a = self.v52
        obs = self.observation(
            bench=[(a.GIBLE, ())],
            options=[
                self.attach(0, a.AreaType.BENCH, 0),
                self.buster(),
            ],
        )
        self.assert_exact_v50(obs)

    def test_unready_or_non_garchomp_active_delegates_exactly_to_v50(self):
        a = self.v52
        cases = {
            "one_energy_garchomp": self.observation(active_energy_ids=[a.BASIC_FIGHTING]),
            "ready_gabite": self.observation(
                active_id=a.GABITE,
                active_energy_ids=[a.BASIC_FIGHTING, a.BASIC_FIGHTING],
            ),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assert_exact_v50(obs)

    def test_missing_or_unapproved_buster_delegates_exactly_to_v50(self):
        cases = {
            "missing_buster": self.observation(options=[
                self.attach(0, self.v52.AreaType.BENCH, 1),
                self.end(),
            ]),
            "buster_not_a_visible_ko": self.observation(
                opponent_hp=400,
                opponent_bench=[9001],
            ),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assert_exact_v50(obs)

    def test_out_of_scope_attachments_delegate_exactly_to_v50(self):
        a = self.v52
        cases = {
            "active_garchomp": self.observation(options=[
                self.attach(0, a.AreaType.ACTIVE, 0),
                self.buster(),
            ]),
            "bench_roselia": self.observation(
                bench=[(a.ROSERADE, ()), (a.ROSELIA, ()), (a.GIBLE, ())],
                options=[
                    self.attach(0, a.AreaType.BENCH, 1),
                    self.buster(),
                ],
            ),
            "bench_roserade": self.observation(options=[
                self.attach(0, a.AreaType.BENCH, 0),
                self.buster(),
            ]),
            "bench_spiritomb": self.observation(
                bench=[(a.ROSERADE, ()), (a.SPIRITOMB, ()), (a.GIBLE, ())],
                options=[
                    self.attach(0, a.AreaType.BENCH, 1),
                    self.buster(),
                ],
            ),
            "power_weight_on_gible": self.observation(
                hand_ids=[a.POWER_WEIGHT],
                options=[
                    self.attach(0, a.AreaType.BENCH, 1),
                    self.buster(),
                ],
            ),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assert_exact_v50(obs)

    def test_non_main_contexts_delegate_exactly_to_v50(self):
        a = self.v52
        for context in (a.SelectContext.TO_HAND, a.SelectContext.LOOK, a.SelectContext.ATTACH_TO):
            with self.subTest(context=context):
                self.assert_exact_v50(self.observation(context=context))

    def test_visibly_terminal_buster_still_performs_free_backup_attach(self):
        obs = self.observation(
            prize_count=1,
            opponent_bench=[9001],
        )
        self.assertTrue(self.v52.is_approved_buster_conversion(obs))
        self.assertEqual(self.v50.choose_options(obs), [1])
        self.assertEqual(self.v52.choose_options(obs), [0])

    def test_exact_deck_and_only_helper_plus_early_hook_differ_from_v50(self):
        baseline_files = {
            path.relative_to(V50_DIR)
            for path in V50_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V52_DIR)
            for path in V52_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V50_DIR / "main.py").read_bytes()
        baseline_deck = (V50_DIR / "deck.csv").read_bytes()
        candidate_deck = (V52_DIR / "deck.csv").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V50_MAIN_SHA256)
        self.assertEqual(hashlib.sha256(baseline_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(60, len([line for line in candidate_deck.splitlines() if line.strip()]))

        baseline_tree = ast.parse(baseline_main)
        candidate_tree = ast.parse((V52_DIR / "main.py").read_bytes())
        baseline_unchanged = [
            node for node in baseline_tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "choose_options"
        ]
        candidate_unchanged = [
            node for node in candidate_tree.body
            if not isinstance(node, ast.FunctionDef)
            or node.name not in {"prebuster_backup_attach_index", "choose_options"}
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
            "    backup_attach_index = prebuster_backup_attach_index(obs)\n"
            "    if backup_attach_index is not None:\n"
            "        return [backup_attach_index]\n"
        ).body[0].body
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[:2]],
            [ast.dump(node, include_attributes=False) for node in expected_hook],
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[2:]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body],
        )


if __name__ == "__main__":
    unittest.main()
