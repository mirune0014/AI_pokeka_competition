"""Focused contract checks for Cynthia Garchomp v53 pre-Buster progression."""
import ast
import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V52_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v52_prebuster_backup_attach"
V53_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v53_prebuster_inplay_progress"
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


class PrebusterInplayProgressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v52 = load_agent_module("cynthia_v52_for_v53_test", V52_DIR / "main.py")
        cls.v53 = load_agent_module("cynthia_v53_main", V53_DIR / "main.py")

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

    def buster(self):
        return self.option(self.v53.OptionType.ATTACK, attack_id=self.v53.DRACONIC_BUSTER)

    def call(self, bench_index, *, area=None, player_index=None):
        return self.option(
            self.v53.OptionType.ABILITY,
            area=self.v53.AreaType.BENCH if area is None else area,
            index=bench_index,
            player_index=player_index,
        )

    def evolve(self, hand_index, target_index, *, target_area=None, player_index=None):
        return self.option(
            self.v53.OptionType.EVOLVE,
            area=self.v53.AreaType.HAND,
            index=hand_index,
            in_play_area=self.v53.AreaType.BENCH if target_area is None else target_area,
            in_play_index=target_index,
            player_index=player_index,
        )

    def attach(self, hand_index, target_area, target_index):
        return self.option(
            self.v53.OptionType.ATTACH,
            area=self.v53.AreaType.HAND,
            index=hand_index,
            in_play_area=target_area,
            in_play_index=target_index,
        )

    def play(self, hand_index):
        return self.option(self.v53.OptionType.PLAY, index=hand_index)

    def card_option(self, deck_index):
        return self.option(self.v53.OptionType.CARD, area=self.v53.AreaType.DECK, index=deck_index)

    def observation(
        self,
        options,
        *,
        context=None,
        hand=None,
        active=None,
        bench=None,
        opponent_hp=200,
        opponent_bench=None,
        visible_deck=None,
        effect=None,
        min_count=1,
        max_count=1,
        prize_count=6,
        energy_attached=False,
    ):
        a = self.v53
        context = a.SelectContext.MAIN if context is None else context
        active = [self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING, a.ROCK_FIGHTING), serial=1)] if active is None else active
        bench = [
            self.pokemon(a.ROSERADE, serial=10),
            self.pokemon(a.GABITE, serial=20),
        ] if bench is None else bench
        hand = [] if hand is None else hand
        opponent_bench = [] if opponent_bench is None else opponent_bench
        visible_deck = [] if visible_deck is None else visible_deck
        mine = types.SimpleNamespace(
            hand=hand,
            handCount=len(hand),
            active=active,
            bench=bench,
            benchMax=5,
            discard=[],
            prize=[self.pokemon(9900 + index) for index in range(prize_count)],
            deckCount=30,
        )
        other = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=[self.pokemon(9000, hp=opponent_hp)],
            bench=opponent_bench,
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
                energyAttached=energy_attached,
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

    def assert_exact_v52(self, obs):
        self.assertIsNone(self.v53.prebuster_inplay_progress_index(obs))
        self.assertEqual(self.v53.choose_options(obs), self.v52.choose_options(obs))

    def test_scoped_eligible_bench_gabite_calls_before_top_approved_buster(self):
        a = self.v53
        obs = self.observation([self.buster(), self.call(1)])
        self.assertTrue(a.is_approved_buster_conversion(obs))
        self.assertEqual(self.v52.choose_options(obs), [0])
        self.assertEqual(a.prebuster_inplay_progress_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_call_uses_only_eligible_bench_source_with_stable_existing_order(self):
        a = self.v53
        bench = [
            self.pokemon(a.ROSERADE, serial=10),
            self.pokemon(a.GABITE, serial=20, appeared=True),
            self.pokemon(a.GABITE, serial=21),
            self.pokemon(a.GABITE, serial=22),
        ]
        obs = self.observation(
            [self.buster(), self.call(1), self.call(2), self.call(3)],
            bench=bench,
        )
        self.assertEqual(a.prebuster_inplay_progress_index(obs), 2)
        self.assertEqual(a.choose_options(obs), [2])

        all_new = self.observation(
            [self.buster(), self.call(1)],
            bench=[bench[0], self.pokemon(a.GABITE, serial=23, appeared=True)],
        )
        self.assert_exact_v52(all_new)

    def test_scoped_call_to_hand_selects_garchomp_and_stable_duplicate(self):
        a = self.v53
        bench = [
            self.pokemon(a.ROSERADE, serial=10),
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GIBLE, serial=30),
        ]
        visible = [
            self.pokemon(a.GABITE, serial=100),
            self.pokemon(a.GARCHOMP_EX, serial=101),
            self.pokemon(a.GARCHOMP_EX, serial=102),
        ]
        obs = self.observation(
            [self.card_option(0), self.card_option(1), self.card_option(2)],
            context=a.SelectContext.TO_HAND,
            bench=bench,
            visible_deck=visible,
            effect=self.pokemon(a.GABITE, serial=20),
        )
        self.assertEqual(self.v52.choose_options(obs), [0])
        self.assertEqual(a.prebuster_inplay_progress_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_to_hand_override_requires_exact_call_effect_and_public_scope(self):
        a = self.v53
        rose = self.pokemon(a.ROSERADE, serial=10)
        gabite = self.pokemon(a.GABITE, serial=20)
        gible = self.pokemon(a.GIBLE, serial=30)
        visible = [self.pokemon(a.GABITE), self.pokemon(a.GARCHOMP_EX)]

        def make(**overrides):
            values = {
                "context": a.SelectContext.TO_HAND,
                "bench": [rose, gabite, gible],
                "visible_deck": visible,
                "effect": self.pokemon(a.GABITE, serial=20),
            }
            values.update(overrides)
            return self.observation([self.card_option(0), self.card_option(1)], **values)

        cases = {
            "wrong_effect": make(effect=self.pokemon(a.GIBLE, serial=20)),
            "wrong_source_serial": make(effect=self.pokemon(a.GABITE, serial=99)),
            "new_source": make(
                bench=[rose, self.pokemon(a.GABITE, serial=20, appeared=True), gible],
            ),
            "missing_roserade": make(bench=[gabite, gible]),
            "unready_active": make(
                active=[self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING,), serial=1)],
            ),
            "unapproved": make(opponent_hp=400, opponent_bench=[self.pokemon(9001)]),
            "multiple_count": make(max_count=2),
            "no_garchomp_legal": self.observation(
                [self.card_option(0)],
                context=a.SelectContext.TO_HAND,
                bench=[rose, gabite, gible],
                visible_deck=[self.pokemon(a.GABITE)],
                effect=self.pokemon(a.GABITE, serial=20),
            ),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assert_exact_v52(obs)

    def test_gabite_to_garchomp_evolution_precedes_buster_after_call(self):
        a = self.v53
        hand = [self.pokemon(a.GARCHOMP_EX, serial=101)]
        obs = self.observation(
            [self.buster(), self.evolve(0, 1)],
            hand=hand,
        )
        self.assertEqual(self.v52.choose_options(obs), [0])
        self.assertEqual(a.prebuster_inplay_progress_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_gible_to_gabite_evolution_precedes_buster(self):
        a = self.v53
        hand = [self.pokemon(a.GABITE, serial=101)]
        bench = [self.pokemon(a.ROSERADE, serial=10), self.pokemon(a.GIBLE, serial=30)]
        obs = self.observation(
            [self.buster(), self.evolve(0, 1)],
            hand=hand,
            bench=bench,
        )
        self.assertEqual(a.prebuster_inplay_progress_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_evolution_uses_existing_score_and_lowest_index_tie(self):
        a = self.v53
        hand = [self.pokemon(a.GABITE), self.pokemon(a.GARCHOMP_EX)]
        bench = [
            self.pokemon(a.ROSERADE),
            self.pokemon(a.GIBLE),
            self.pokemon(a.GABITE),
        ]
        farther = self.observation(
            [self.buster(), self.evolve(0, 1), self.evolve(1, 2)],
            hand=hand,
            bench=bench,
        )
        self.assertEqual(a.prebuster_inplay_progress_index(farther), 2)

        tied = self.observation(
            [self.buster(), self.evolve(0, 1), self.evolve(1, 2)],
            hand=[self.pokemon(a.GABITE), self.pokemon(a.GABITE)],
            bench=[self.pokemon(a.ROSERADE), self.pokemon(a.GIBLE), self.pokemon(a.GIBLE)],
        )
        self.assertEqual(a.prebuster_inplay_progress_index(tied), 1)
        self.assertEqual(a.choose_options(tied), [1])

    def test_benched_garchomp_stops_call_and_evolution_recursion(self):
        a = self.v53
        bench = [
            self.pokemon(a.ROSERADE, serial=10),
            self.pokemon(a.GABITE, serial=20),
            self.pokemon(a.GARCHOMP_EX, serial=40),
        ]
        obs = self.observation(
            [self.buster(), self.call(1), self.evolve(0, 1)],
            hand=[self.pokemon(a.GARCHOMP_EX)],
            bench=bench,
        )
        self.assert_exact_v52(obs)

    def test_exact_v52_backup_attachment_remains_next_and_stops_progression(self):
        a = self.v53
        attach_state = self.observation(
            [self.attach(0, a.AreaType.BENCH, 1), self.buster()],
            hand=[self.pokemon(a.BASIC_FIGHTING)],
            bench=[self.pokemon(a.ROSERADE), self.pokemon(a.GIBLE)],
        )
        self.assertIsNone(a.prebuster_inplay_progress_index(attach_state))
        self.assertEqual(a.prebuster_backup_attach_index(attach_state), 0)
        self.assertEqual(self.v52.prebuster_backup_attach_index(attach_state), 0)
        self.assertEqual(a.choose_options(attach_state), [0])

        after_attach = self.observation(
            [self.buster(), self.call(1), self.evolve(0, 1)],
            hand=[self.pokemon(a.GARCHOMP_EX)],
            bench=[
                self.pokemon(a.ROSERADE, serial=10),
                self.pokemon(a.GABITE, (a.BASIC_FIGHTING,), serial=20),
            ],
            energy_attached=True,
        )
        self.assert_exact_v52(after_attach)

    def test_prior_turn_energy_does_not_block_inplay_progression(self):
        a = self.v53
        obs = self.observation(
            [self.buster(), self.call(1)],
            bench=[
                self.pokemon(a.ROSERADE, serial=10),
                self.pokemon(a.GABITE, (a.BASIC_FIGHTING,), serial=20),
            ],
            energy_attached=False,
        )
        self.assertEqual(a.prebuster_inplay_progress_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

    def test_main_guard_failures_delegate_exactly_to_v52(self):
        a = self.v53
        options = [self.buster(), self.call(1)]
        cases = {
            "non_garchomp_active": self.observation(
                options,
                active=[self.pokemon(a.GABITE, (a.BASIC_FIGHTING, a.ROCK_FIGHTING))],
            ),
            "unready_active": self.observation(
                options,
                active=[self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING,))],
            ),
            "missing_roserade": self.observation(
                options,
                bench=[self.pokemon(a.GABITE, serial=20)],
            ),
            "unapproved_buster": self.observation(
                options,
                opponent_hp=400,
                opponent_bench=[self.pokemon(9001)],
            ),
            "missing_buster": self.observation(
                [self.option(a.OptionType.END), self.call(1)],
            ),
        }
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assert_exact_v52(obs)

    def test_normal_v52_non_buster_top_blocks_override(self):
        a = self.v53
        obs = self.observation([self.buster(), self.call(1)])
        originals = (
            self.v52.score_option_with_champions_call_order,
            a.score_option_with_champions_call_order,
        )

        def raised_call(original):
            def score(scored_obs, option):
                if option.type == a.OptionType.ABILITY:
                    return 50000, "test higher normal v52 action"
                return original(scored_obs, option)
            return score

        try:
            self.v52.score_option_with_champions_call_order = raised_call(originals[0])
            a.score_option_with_champions_call_order = raised_call(originals[1])
            self.assertIsNone(a.prebuster_inplay_progress_index(obs))
            self.assertEqual(self.v52.choose_options(obs), [1])
            self.assertEqual(a.choose_options(obs), [1])
        finally:
            self.v52.score_option_with_champions_call_order = originals[0]
            a.score_option_with_champions_call_order = originals[1]

    def test_excluded_actions_are_never_selected_by_v53(self):
        a = self.v53
        cases = {}
        excluded_plays = (
            a.GIBLE, a.BUDDY_POFFIN, a.FIGHTING_GONG, a.POKE_PAD, a.HILDA, a.LILLIE,
            a.BOSS, a.XEROSIC, a.SURFER, a.UNFAIR_STAMP, a.NIGHT_STRETCHER,
            a.SACRED_ASH, a.FOREST,
        )
        for card_id in excluded_plays:
            cases[f"play_{card_id}"] = self.observation(
                [self.play(0), self.buster()],
                hand=[self.pokemon(card_id)],
            )
        cases["support_evolution"] = self.observation(
            [self.evolve(0, 1), self.buster()],
            hand=[self.pokemon(a.ROSERADE)],
            bench=[
                self.pokemon(a.ROSERADE),
                self.pokemon(a.ROSELIA),
                self.pokemon(a.GABITE),
            ],
        )
        cases["power_weight"] = self.observation(
            [self.attach(0, a.AreaType.BENCH, 1), self.buster()],
            hand=[self.pokemon(a.POWER_WEIGHT)],
        )
        cases["retreat"] = self.observation(
            [self.option(a.OptionType.RETREAT), self.buster()],
        )
        cases["active_energy"] = self.observation(
            [self.attach(0, a.AreaType.ACTIVE, 0), self.buster()],
            hand=[self.pokemon(a.BASIC_FIGHTING)],
        )
        cases["support_energy"] = self.observation(
            [self.attach(0, a.AreaType.BENCH, 0), self.buster()],
            hand=[self.pokemon(a.BASIC_FIGHTING)],
        )
        for name, obs in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(a.prebuster_inplay_progress_index(obs))
                self.assertEqual(a.choose_options(obs), [1])
                self.assertEqual(a.choose_options(obs), self.v52.choose_options(obs))

    def test_non_main_and_out_of_scope_sources_delegate_exactly_to_v52(self):
        a = self.v53
        visible = [self.pokemon(a.GABITE), self.pokemon(a.GARCHOMP_EX)]
        for context in (a.SelectContext.LOOK, a.SelectContext.ATTACH_TO, a.SelectContext.SETUP_ACTIVE_POKEMON):
            with self.subTest(context=context):
                obs = self.observation(
                    [self.card_option(0), self.card_option(1)],
                    context=context,
                    visible_deck=visible,
                    effect=self.pokemon(a.GABITE, serial=20),
                )
                self.assert_exact_v52(obs)

        wrong_area_call = self.observation(
            [self.buster(), self.call(0, area=a.AreaType.ACTIVE)],
        )
        opponent_call = self.observation(
            [self.buster(), self.call(0, player_index=1)],
        )
        for obs in (wrong_area_call, opponent_call):
            self.assert_exact_v52(obs)

    def test_exact_deck_and_only_scoped_helper_plus_hook_differ_from_v52(self):
        baseline_files = {
            path.relative_to(V52_DIR)
            for path in V52_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V53_DIR)
            for path in V53_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V52_DIR / "main.py").read_bytes()
        baseline_deck = (V52_DIR / "deck.csv").read_bytes()
        candidate_deck = (V53_DIR / "deck.csv").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V52_MAIN_SHA256)
        self.assertEqual(hashlib.sha256(baseline_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(60, len([line for line in candidate_deck.splitlines() if line.strip()]))

        baseline_tree = ast.parse(baseline_main)
        candidate_tree = ast.parse((V53_DIR / "main.py").read_bytes())
        baseline_unchanged = [
            node for node in baseline_tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "choose_options"
        ]
        candidate_unchanged = [
            node for node in candidate_tree.body
            if not isinstance(node, ast.FunctionDef)
            or node.name not in {"prebuster_inplay_progress_index", "choose_options"}
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
            "    progress_index = prebuster_inplay_progress_index(obs)\n"
            "    if progress_index is not None:\n"
            "        return [progress_index]\n"
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
