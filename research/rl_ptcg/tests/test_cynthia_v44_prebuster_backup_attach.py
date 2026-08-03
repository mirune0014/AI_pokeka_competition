"""Focused public-state checks for Cynthia Garchomp v44."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v44_prebuster_backup_attach"
BASELINE_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve"
TWO_PRIZE_TARGET = 9001
ONE_PRIZE_TARGET = 9002


CARD_METADATA = [
    types.SimpleNamespace(cardId=TWO_PRIZE_TARGET, name="Test ex", ex=True, megaEx=False, hp=320),
    types.SimpleNamespace(cardId=ONE_PRIZE_TARGET, name="Test Pokemon", ex=False, megaEx=False, hp=200),
]


def load_agent_module(name, directory):
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
    api.all_card_data = lambda: list(CARD_METADATA)
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location(name, directory / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrebusterBackupAttachTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module("cynthia_v44_main", AGENT_DIR)
        cls.baseline = load_agent_module("cynthia_v23_main_for_v44", BASELINE_DIR)

    @staticmethod
    def card(card_id):
        return types.SimpleNamespace(id=card_id)

    @staticmethod
    def pokemon(card_id, *, hp=400, energies=(), serial=None):
        return types.SimpleNamespace(
            id=card_id,
            hp=hp,
            maxHp=hp,
            energies=list(energies),
            serial=card_id if serial is None else serial,
            tools=[],
            appearThisTurn=False,
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
    ):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=None,
            inPlayArea=in_play_area,
            inPlayIndex=in_play_index,
            attackId=attack_id,
        )

    def observation(
        self,
        options,
        *,
        hand_ids=(),
        active_id=None,
        active_energies=None,
        bench=(),
        target_id=TWO_PRIZE_TARGET,
        target_hp=200,
        opponent_bench=True,
        prizes=3,
        context=None,
        deck_ids=(),
    ):
        a = self.agent
        if active_id is None:
            active_id = a.GARCHOMP_EX
        if active_energies is None:
            active_energies = (a.BASIC_FIGHTING, a.ROCK_FIGHTING)
        mine = types.SimpleNamespace(
            hand=[self.card(card_id) for card_id in hand_ids],
            active=[self.pokemon(active_id, energies=active_energies)] if active_id else [],
            bench=list(bench),
            discard=[],
            prize=[object() for _ in range(prizes)],
            stadium=[],
            deckCount=30,
        )
        foe = types.SimpleNamespace(
            hand=[],
            active=[] if target_id is None else [self.pokemon(target_id, hp=target_hp)],
            bench=[self.pokemon(9998)] if opponent_bench else [],
            discard=[],
            prize=[],
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, foe],
                looking=[],
                stadium=[],
                energyAttached=False,
            ),
            select=types.SimpleNamespace(
                option=options,
                context=context or a.SelectContext.MAIN,
                minCount=1,
                maxCount=1,
                deck=[self.card(card_id) for card_id in deck_ids],
            ),
        )

    def attach(self, *, hand_index=0, target_area=None, target_index=0):
        a = self.agent
        return self.option(
            a.OptionType.ATTACH,
            area=a.AreaType.HAND,
            index=hand_index,
            in_play_area=target_area or a.AreaType.BENCH,
            in_play_index=target_index,
        )

    def attack(self, attack_id=None):
        a = self.agent
        return self.option(a.OptionType.ATTACK, attack_id=attack_id or a.DRACONIC_BUSTER)

    def scored(self, module, obs):
        return [module.score_option_with_champions_call_order(obs, option) for option in obs.select.option]

    def assert_matches_baseline(self, obs):
        self.assertEqual(self.scored(self.baseline, obs), self.scored(self.agent, obs))
        self.assertEqual(self.baseline.choose_options(obs), self.agent.choose_options(obs))

    def test_nonterminal_buster_ko_chooses_highest_existing_backup_attachment(self):
        a = self.agent
        bench = [
            self.pokemon(a.GIBLE),
            self.pokemon(a.GARCHOMP_EX),
            self.pokemon(a.GABITE),
        ]
        options = [
            self.attach(target_index=0),
            self.attach(target_index=1),
            self.attach(target_index=2),
            self.attack(),
        ]
        obs = self.observation(options, hand_ids=(a.BASIC_FIGHTING,), bench=bench)
        rows = [(a.score_option(obs, option)[0], index, "test") for index, option in enumerate(options)]

        self.assertEqual([3], self.baseline.choose_options(obs))
        self.assertEqual(1, a.prebuster_backup_attach_index(obs, rows))
        self.assertGreater(rows[1][0], rows[0][0])
        self.assertGreater(rows[1][0], rows[2][0])
        self.assertEqual([1], a.choose_options(obs))

    def test_attachment_tie_uses_v23_score_then_earliest_index_comparator(self):
        a = self.agent
        bench = [self.pokemon(a.GIBLE, serial=10), self.pokemon(a.GIBLE, serial=11)]
        options = [self.attach(target_index=0), self.attach(target_index=1), self.attack()]
        obs = self.observation(options, hand_ids=(a.BASIC_FIGHTING,), bench=bench)
        rows = [(a.score_option(obs, option)[0], index, "test") for index, option in enumerate(options)]

        self.assertEqual(rows[0][0], rows[1][0])
        self.assertEqual(0, a.prebuster_backup_attach_index(obs, rows))
        self.assertEqual([0], a.choose_options(obs))

    def test_game_winning_by_prizes_buster_is_unchanged(self):
        a = self.agent
        options = [self.attach(), self.attack()]
        obs = self.observation(
            options,
            hand_ids=(a.BASIC_FIGHTING,),
            bench=(self.pokemon(a.GARCHOMP_EX),),
            prizes=2,
        )
        self.assertIsNone(a.prebuster_backup_attach_index(obs, [(14200, 0, "attach"), (43400, 1, "Buster")]))
        self.assert_matches_baseline(obs)
        self.assertEqual([1], a.choose_options(obs))

    def test_board_clear_buster_is_unchanged(self):
        a = self.agent
        options = [self.attach(), self.attack()]
        obs = self.observation(
            options,
            hand_ids=(a.BASIC_FIGHTING,),
            bench=(self.pokemon(a.GARCHOMP_EX),),
            opponent_bench=False,
        )
        self.assert_matches_baseline(obs)
        self.assertEqual([1], a.choose_options(obs))

    def test_buster_non_ko_is_unchanged(self):
        a = self.agent
        options = [self.attach(), self.attack()]
        obs = self.observation(
            options,
            hand_ids=(a.BASIC_FIGHTING,),
            bench=(self.pokemon(a.GARCHOMP_EX),),
            target_hp=300,
        )
        self.assert_matches_baseline(obs)
        self.assertFalse(a.is_approved_buster_conversion(obs))

    def test_buster_not_ordinary_top_is_unchanged(self):
        a = self.agent
        hand_ids = (a.BASIC_FIGHTING, a.GARCHOMP_EX)
        bench = (self.pokemon(a.GABITE),)
        options = [
            self.attach(target_index=0),
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.BENCH,
                in_play_index=0,
            ),
            self.attack(),
        ]
        obs = self.observation(options, hand_ids=hand_ids, bench=bench)
        low_buster = lambda _obs, _attack_id: (24000, "test lower attack")
        with mock.patch.object(a, "attack_score", low_buster), mock.patch.object(
            self.baseline, "attack_score", low_buster
        ):
            self.assertEqual([1], self.baseline.choose_options(obs))
            self.assertEqual([1], a.choose_options(obs))

    def test_corkscrew_and_other_top_attack_are_unchanged(self):
        a = self.agent
        for attack_id in (a.CORKSCREW_DIVE, a.RAGING_CURSE):
            with self.subTest(attack_id=attack_id):
                options = [self.attach(), self.attack(attack_id)]
                obs = self.observation(
                    options,
                    hand_ids=(a.BASIC_FIGHTING,),
                    bench=(self.pokemon(a.GARCHOMP_EX),),
                    target_hp=500,
                )
                high_attack = lambda _obs, _attack_id: (30000, "test top attack")
                with mock.patch.object(a, "attack_score", high_attack), mock.patch.object(
                    self.baseline, "attack_score", high_attack
                ):
                    self.assertEqual([1], self.baseline.choose_options(obs))
                    self.assertEqual([1], a.choose_options(obs))

    def test_active_attachment_is_ignored(self):
        a = self.agent
        options = [
            self.attach(target_area=a.AreaType.ACTIVE),
            self.attack(),
        ]
        obs = self.observation(options, hand_ids=(a.BASIC_FIGHTING,))
        self.assert_matches_baseline(obs)
        self.assertEqual([1], a.choose_options(obs))

    def test_non_main_attachment_target_is_ignored(self):
        a = self.agent
        options = [self.attach(), self.attack()]
        obs = self.observation(
            options,
            hand_ids=(a.BASIC_FIGHTING,),
            bench=(self.pokemon(a.ROSERADE),),
        )
        self.assert_matches_baseline(obs)
        self.assertEqual([1], a.choose_options(obs))

    def test_no_legal_energy_attachment_is_unchanged(self):
        a = self.agent
        for options, hand_ids, bench in (
            ([self.attack()], (), ()),
            (
                [self.attach(), self.attack()],
                (a.POWER_WEIGHT,),
                (self.pokemon(a.GARCHOMP_EX),),
            ),
        ):
            with self.subTest(hand_ids=hand_ids):
                obs = self.observation(options, hand_ids=hand_ids, bench=bench)
                self.assert_matches_baseline(obs)
                self.assertEqual([len(options) - 1], a.choose_options(obs))

    def test_to_hand_search_and_evolution_match_v23_exactly(self):
        a = self.agent
        search_options = [
            self.option(a.OptionType.CARD, area=a.AreaType.DECK, index=index)
            for index in range(3)
        ]
        search_obs = self.observation(
            search_options,
            active_id=a.GIBLE,
            active_energies=(),
            bench=(self.pokemon(a.GABITE),),
            context=a.SelectContext.TO_HAND,
            deck_ids=(a.GARCHOMP_EX, a.GABITE, a.ROSERADE),
        )
        self.assert_matches_baseline(search_obs)

        evolution_options = [
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=0,
                in_play_area=a.AreaType.BENCH,
                in_play_index=0,
            ),
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.BENCH,
                in_play_index=1,
            ),
        ]
        evolution_obs = self.observation(
            evolution_options,
            hand_ids=(a.GARCHOMP_EX, a.ROSERADE),
            active_id=a.GIBLE,
            active_energies=(),
            bench=(self.pokemon(a.GABITE), self.pokemon(a.ROSELIA)),
        )
        self.assert_matches_baseline(evolution_obs)

    def test_next_observation_without_attachment_chooses_buster_normally(self):
        a = self.agent
        first_options = [self.attach(), self.attack()]
        first_obs = self.observation(
            first_options,
            hand_ids=(a.BASIC_FIGHTING,),
            bench=(self.pokemon(a.GARCHOMP_EX),),
        )
        self.assertEqual([0], a.choose_options(first_obs))

        next_obs = self.observation(
            [self.attack()],
            hand_ids=(),
            bench=(self.pokemon(a.GARCHOMP_EX, energies=(a.BASIC_FIGHTING,)),),
        )
        self.assertEqual([0], a.choose_options(next_obs))
        self.assertEqual(self.baseline.choose_options(next_obs), a.choose_options(next_obs))

    def test_candidate_deck_is_byte_identical_and_exactly_sixty_cards(self):
        candidate = (AGENT_DIR / "deck.csv").read_bytes()
        baseline = (BASELINE_DIR / "deck.csv").read_bytes()
        self.assertEqual(baseline, candidate)
        self.assertEqual(60, len([line for line in candidate.splitlines() if line.strip()]))


if __name__ == "__main__":
    unittest.main()
