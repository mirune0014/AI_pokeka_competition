"""Focused contract checks for Cynthia Garchomp v48."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V23_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve"
V48_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v48_all_calls_before_attack"


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


class AllCallsBeforeAttackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v23 = load_agent_module("cynthia_v23_for_v48_test", V23_DIR / "main.py")
        cls.v48 = load_agent_module("cynthia_v48_main", V48_DIR / "main.py")

    def card(self, card_id, *, serial=None, hp=100, max_hp=100, energies=None):
        return types.SimpleNamespace(
            id=card_id,
            serial=serial,
            hp=hp,
            maxHp=max_hp,
            energies=list(energies or []),
            tools=[],
        )

    def option(
        self,
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

    def observation(
        self,
        options,
        *,
        deck_count=7,
        context="main",
        hand=None,
        active=None,
        bench=None,
        prizes=None,
        opponent_active=None,
        visible_deck=None,
        max_count=1,
    ):
        mine = types.SimpleNamespace(
            hand=list(hand or []),
            handCount=len(hand or []),
            active=list(active or []),
            bench=list(bench or []),
            discard=[],
            prize=list(prizes or []),
            deckCount=deck_count,
        )
        other = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=list(opponent_active or []),
            bench=[],
            discard=[],
            prize=[],
            deckCount=60,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, other], looking=[], stadium=[]),
            select=types.SimpleNamespace(
                option=list(options),
                context=context,
                minCount=1,
                maxCount=max_count,
                deck=list(visible_deck or []),
            ),
        )

    def assert_exact_v23(self, obs):
        for option in obs.select.option:
            self.assertEqual(self.v48.score_option(obs, option), self.v23.score_option(obs, option))
            self.assertEqual(
                self.v48.score_option_with_champions_call_order(obs, option),
                self.v23.score_option_with_champions_call_order(obs, option),
            )
        self.assertEqual(self.v48.choose_options(obs), self.v23.choose_options(obs))

    def test_call_precedes_higher_scored_corkscrew_and_buster(self):
        a = self.v48
        for attack_id in (a.CORKSCREW_DIVE, a.DRACONIC_BUSTER):
            with self.subTest(attack_id=attack_id):
                attack = self.option(a.OptionType.ATTACK, attack_id=attack_id)
                call = self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0)
                obs = self.observation(
                    [attack, call],
                    deck_count=7,
                    active=[self.card(a.GARCHOMP_EX, energies=[a.BASIC_FIGHTING, a.ROCK_FIGHTING])],
                    bench=[self.card(a.GABITE, serial=10)],
                )
                self.assertGreater(a.score_option(obs, attack)[0], a.score_option(obs, call)[0])
                self.assertEqual(self.v23.choose_options(obs), [0])
                self.assertEqual(a.choose_options(obs), [1])

    def test_visible_game_winning_attack_still_follows_call(self):
        a = self.v48
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        call = self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0)
        obs = self.observation(
            [attack, call],
            deck_count=7,
            active=[self.card(a.GARCHOMP_EX, energies=[a.BASIC_FIGHTING, a.ROCK_FIGHTING])],
            bench=[self.card(a.GABITE, serial=10)],
            prizes=[object()],
            opponent_active=[self.card(9999, hp=100, max_hp=100)],
        )
        self.assertTrue(a.is_game_winning_corkscrew(obs, attack))
        self.assertEqual(self.v23.choose_options(obs), [0])
        self.assertEqual(a.choose_options(obs), [1])

    def test_two_calls_use_existing_order_and_re_evaluate_after_resolution(self):
        a = self.v48
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        first_call = self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0)
        second_call = self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=1)
        active = [self.card(a.GARCHOMP_EX, energies=[a.BASIC_FIGHTING, a.ROCK_FIGHTING])]
        obs = self.observation(
            [attack, first_call, second_call],
            deck_count=8,
            active=active,
            bench=[self.card(a.GABITE, serial=10), self.card(a.GABITE, serial=11)],
        )
        self.assertEqual(a.choose_options(obs), [1])

        remaining_call = self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0)
        after_first_call = self.observation(
            [attack, remaining_call],
            deck_count=7,
            active=active,
            bench=[self.card(a.GABITE, serial=11)],
        )
        self.assertEqual(a.choose_options(after_first_call), [1])

    def test_deck_six_attack_ordering_is_exact_v23(self):
        a = self.v48
        options = [
            self.option(a.OptionType.ATTACK, attack_id=a.DRACONIC_BUSTER),
            self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0),
            self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE),
        ]
        obs = self.observation(
            options,
            deck_count=6,
            active=[self.card(a.GARCHOMP_EX, energies=[a.BASIC_FIGHTING, a.ROCK_FIGHTING])],
            bench=[self.card(a.GABITE, serial=10)],
            max_count=len(options),
        )
        self.assert_exact_v23(obs)

    def test_without_attack_play_evolve_attach_ordering_is_exact_v23(self):
        a = self.v48
        hand = [self.card(a.ROSERADE), self.card(a.BASIC_FIGHTING), self.card(a.GIBLE)]
        active = [self.card(a.GIBLE)]
        bench = [self.card(a.GABITE, serial=10), self.card(a.ROSELIA)]
        options = [
            self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0),
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=0,
                in_play_area=a.AreaType.BENCH,
                in_play_index=1,
            ),
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.ACTIVE,
                in_play_index=0,
            ),
            self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=2),
        ]
        obs = self.observation(
            options,
            deck_count=30,
            hand=hand,
            active=active,
            bench=bench,
            max_count=len(options),
        )
        self.assert_exact_v23(obs)

    def test_without_call_all_scores_and_selection_are_exact_v23(self):
        a = self.v48
        hand = [self.card(a.ROSERADE), self.card(a.BASIC_FIGHTING)]
        active = [self.card(a.GARCHOMP_EX, energies=[a.BASIC_FIGHTING, a.ROCK_FIGHTING])]
        bench = [self.card(a.ROSELIA)]
        options = [
            self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE),
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=0,
                in_play_area=a.AreaType.BENCH,
                in_play_index=0,
            ),
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.ACTIVE,
                in_play_index=0,
            ),
        ]
        obs = self.observation(
            options,
            deck_count=30,
            hand=hand,
            active=active,
            bench=bench,
            max_count=len(options),
        )
        self.assert_exact_v23(obs)

    def test_existing_call_before_matching_garchomp_evolution_is_intact(self):
        a = self.v48
        hand = [self.card(a.GARCHOMP_EX)]
        bench = [self.card(a.GABITE, serial=10)]
        evolve = self.option(
            a.OptionType.EVOLVE,
            area=a.AreaType.HAND,
            index=0,
            in_play_area=a.AreaType.BENCH,
            in_play_index=0,
        )
        call = self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0)
        obs = self.observation([evolve, call], deck_count=30, hand=hand, bench=bench)
        self.assertEqual(self.v23.choose_options(obs), [1])
        self.assertEqual(a.choose_options(obs), [1])

    def test_search_result_scoring_is_exact_v23(self):
        a = self.v48
        visible_deck = [
            self.card(a.GARCHOMP_EX),
            self.card(a.GABITE),
            self.card(a.ROSERADE),
            self.card(a.ROCK_FIGHTING),
            self.card(a.BOSS),
        ]
        options = [
            self.option(a.OptionType.CARD, area=a.AreaType.DECK, index=index)
            for index in range(len(visible_deck))
        ]
        obs = self.observation(
            options,
            context=a.SelectContext.TO_HAND,
            hand=[self.card(a.BASIC_FIGHTING)],
            bench=[self.card(a.GIBLE), self.card(a.ROSELIA)],
            visible_deck=visible_deck,
            max_count=len(options),
        )
        for option in options:
            self.assertEqual(a.score_to_hand(obs, option), self.v23.score_to_hand(obs, option))
            self.assertEqual(
                a.score_to_hand(obs, option, allow_support_pivot=True),
                self.v23.score_to_hand(obs, option, allow_support_pivot=True),
            )
            self.assertEqual(a.score_option(obs, option), self.v23.score_option(obs, option))

    def test_exact_deck_and_all_non_main_files_match_v23(self):
        baseline_files = {
            path.relative_to(V23_DIR): path
            for path in V23_DIR.rglob("*")
            if path.is_file()
            and path.name != "main.py"
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V48_DIR): path
            for path in V48_DIR.rglob("*")
            if path.is_file()
            and path.name != "main.py"
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        }
        self.assertEqual(set(candidate_files), set(baseline_files))
        for relative_path, baseline_path in baseline_files.items():
            self.assertEqual(candidate_files[relative_path].read_bytes(), baseline_path.read_bytes())
        deck_lines = [line for line in (V48_DIR / "deck.csv").read_text().splitlines() if line.strip()]
        self.assertEqual(len(deck_lines), 60)


if __name__ == "__main__":
    unittest.main()
