"""Focused public-state checks for Cynthia Garchomp v43's Roserade breakpoint."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v43_roserade_buster_breakpoint"
BASELINE_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve"
TWO_PRIZE_TARGET = 9001
ONE_PRIZE_TARGET = 9002


CARD_METADATA = [
    types.SimpleNamespace(
        cardId=TWO_PRIZE_TARGET,
        name="Test ex target",
        ex=True,
        megaEx=False,
        hp=320,
    ),
    types.SimpleNamespace(
        cardId=ONE_PRIZE_TARGET,
        name="Test one-prize target",
        ex=False,
        megaEx=False,
        hp=320,
    ),
]


def load_agent_module(name, directory):
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench", PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium")
    api.OptionType = types.SimpleNamespace(ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat", ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end", NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy")
    api.SelectContext = types.SimpleNamespace(MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active", SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard", DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look", TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", SWITCH="switch", TO_ACTIVE="to_active", ATTACH_TO="attach_to", ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage")
    api.all_attack = lambda: []
    api.all_card_data = lambda: list(CARD_METADATA)
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location(name, directory / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoseradeBusterBreakpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module("cynthia_v43_main", AGENT_DIR)
        cls.baseline = load_agent_module("cynthia_v23_main", BASELINE_DIR)

    @staticmethod
    def card(card_id):
        return types.SimpleNamespace(id=card_id)

    @staticmethod
    def pokemon(card_id, *, hp=200, energies=(), appear_this_turn=False):
        return types.SimpleNamespace(id=card_id, hp=hp, energies=list(energies), appearThisTurn=appear_this_turn)

    def option(self, index):
        a = self.agent
        return types.SimpleNamespace(type=a.OptionType.CARD, area=a.AreaType.DECK, index=index, playerIndex=None, inPlayArea=None, inPlayIndex=None, attackId=None)

    def observation(
        self,
        *,
        active_id=None,
        active_energies=(6,),
        hand_ids=(6,),
        roselia_appeared=False,
        include_roselia=True,
        existing_roserades=0,
        extra_bench_ids=(),
        target_id=TWO_PRIZE_TARGET,
        target_hp=280,
        remaining_prizes=6,
        energy_attached=False,
        context=None,
        option_ids=None,
    ):
        a = self.agent
        option_ids = list(option_ids or (a.ROSERADE, a.GARCHOMP_EX))
        options = [self.option(index) for index in range(len(option_ids))]
        bench = []
        if include_roselia:
            bench.append(self.pokemon(a.ROSELIA, appear_this_turn=roselia_appeared))
        bench.extend(self.pokemon(a.ROSERADE) for _ in range(existing_roserades))
        bench.extend(self.pokemon(card_id) for card_id in extra_bench_ids)
        mine = types.SimpleNamespace(
            hand=[self.card(card_id) for card_id in hand_ids],
            active=[self.pokemon(active_id or a.GARCHOMP_EX, energies=active_energies)],
            bench=bench,
            discard=[], prize=[object()] * remaining_prizes, stadium=[], deckCount=30,
        )
        foe = types.SimpleNamespace(
            hand=[],
            active=[] if target_id is None else [self.pokemon(target_id, hp=target_hp)],
            bench=[],
            discard=[],
            prize=[],
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], energyAttached=energy_attached),
            select=types.SimpleNamespace(
                option=options,
                context=context or a.SelectContext.TO_HAND,
                minCount=1,
                maxCount=1,
                deck=[self.card(card_id) for card_id in option_ids],
            ),
        )

    def score(self, obs, index=0):
        return self.agent.score_option(obs, obs.select.option[index])

    def test_positive_one_energy_breakpoint_roserade_outranks_garchomp(self):
        a = self.agent
        obs = self.observation(
            active_id=a.GARCHOMP_EX,
            active_energies=(a.BASIC_FIGHTING,),
            hand_ids=(a.BASIC_FIGHTING,),
            roselia_appeared=False,
            existing_roserades=0,
            target_id=TWO_PRIZE_TARGET,
            target_hp=280,
            energy_attached=False,
        )
        roserade = self.score(obs, 0)
        garchomp = self.score(obs, 1)
        self.assertEqual(2, self.agent.prize_value(obs.current.players[1].active[0]))
        self.assertEqual(0, self.agent.count_in_play(obs, a.ROSERADE))
        self.assertEqual((17000, "take Roserade for immediate Draconic Buster breakpoint"), roserade)
        self.assertGreater(roserade[0], garchomp[0])
        self.assertEqual([0], self.agent.choose_options(obs))

    def test_breakpoint_score_outranks_existing_to_hand_maximum(self):
        a = self.agent
        obs = self.observation(
            extra_bench_ids=(a.GIBLE, a.GABITE),
            option_ids=(a.ROSERADE, a.GABITE, a.GARCHOMP_EX),
        )
        self.assertEqual([17000, 16000, 15000], [self.score(obs, i)[0] for i in range(3)])
        self.assertEqual([0], a.choose_options(obs))

    def test_no_boost_when_current_buster_already_kos(self):
        self.assertEqual((9000, "take Roserade"), self.score(self.observation(target_hp=260)))

    def test_no_boost_when_one_roserade_still_misses_ko(self):
        self.assertEqual((9000, "take Roserade"), self.score(self.observation(target_hp=291)))

    def test_no_boost_when_roselia_appeared_this_turn(self):
        self.assertEqual((9000, "take Roserade"), self.score(self.observation(roselia_appeared=True)))

    def test_no_boost_after_manual_attachment_with_one_energy(self):
        self.assertEqual((9000, "take Roserade"), self.score(self.observation(energy_attached=True)))

    def test_two_energy_active_works_without_energy_in_hand(self):
        self.assertEqual(17000, self.score(self.observation(active_energies=(6, 20), hand_ids=()))[0])

    def test_one_prize_nonterminal_target_is_not_boosted(self):
        obs = self.observation(target_id=ONE_PRIZE_TARGET, remaining_prizes=2)
        self.assertEqual(1, self.agent.prize_value(obs.current.players[1].active[0]))
        self.assertEqual((9000, "take Roserade"), self.score(obs))

    def test_game_winning_one_prize_target_is_boosted(self):
        obs = self.observation(target_id=ONE_PRIZE_TARGET, remaining_prizes=1)
        self.assertEqual((17000, "take Roserade for immediate Draconic Buster breakpoint"), self.score(obs))

    def test_existing_roserade_count_is_included_in_damage(self):
        obs = self.observation(existing_roserades=1, target_hp=310)
        self.assertEqual(17000, self.score(obs)[0])

    def test_only_to_hand_roserade_can_receive_breakpoint_score(self):
        a = self.agent
        look_obs = self.observation(context=a.SelectContext.LOOK)
        self.assertEqual((9000, "take Roserade"), self.score(look_obs))

        roselia_obs = self.observation(option_ids=(a.ROSELIA, a.GARCHOMP_EX))
        self.assertEqual(
            self.baseline.score_option(roselia_obs, roselia_obs.select.option[0]),
            self.score(roselia_obs),
        )

    def test_other_required_public_state_gates(self):
        a = self.agent
        cases = [
            ("active is not Garchomp ex", self.observation(active_id=a.GABITE)),
            ("no Roselia in play", self.observation(include_roselia=False)),
            ("no opposing active", self.observation(target_id=None)),
            ("active has no Energy", self.observation(active_energies=(), hand_ids=(a.BASIC_FIGHTING,))),
            ("hand has no Fighting Energy", self.observation(active_energies=(a.BASIC_FIGHTING,), hand_ids=(9999,))),
        ]
        for name, obs in cases:
            with self.subTest(name=name):
                candidate_score = self.score(obs)
                baseline_score = self.baseline.score_option(obs, obs.select.option[0])
                self.assertEqual(baseline_score, candidate_score)
                self.assertNotEqual(17000, candidate_score[0])

    def test_one_energy_with_rock_fighting_in_hand_is_feasible(self):
        a = self.agent
        obs = self.observation(
            active_energies=(a.BASIC_FIGHTING,),
            hand_ids=(a.ROCK_FIGHTING,),
        )
        self.assertEqual(17000, self.score(obs)[0])

    def test_nonqualifying_scores_and_selected_action_match_v23_exactly(self):
        obs = self.observation(target_hp=291)
        baseline_obs = self.observation(target_hp=291)
        self.assertEqual(
            [self.baseline.score_option(baseline_obs, option) for option in baseline_obs.select.option],
            [self.agent.score_option(obs, option) for option in obs.select.option],
        )
        self.assertEqual(self.baseline.choose_options(baseline_obs), self.agent.choose_options(obs))

    def test_candidate_deck_is_byte_identical_and_exactly_60_cards(self):
        candidate = (AGENT_DIR / "deck.csv").read_bytes()
        baseline = (BASELINE_DIR / "deck.csv").read_bytes()
        self.assertEqual(baseline, candidate)
        self.assertEqual(60, len([line for line in candidate.splitlines() if line.strip()]))


if __name__ == "__main__":
    unittest.main()
