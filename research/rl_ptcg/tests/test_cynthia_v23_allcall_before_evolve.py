"""Focused ordering checks for Cynthia Garchomp v23."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_PATH = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve" / "main.py"


def load_agent_module():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench",
        PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium")
    api.OptionType = types.SimpleNamespace(
        ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat",
        ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end",
        NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy")
    api.Pokemon = object
    api.SelectContext = types.SimpleNamespace(
        MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active",
        SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard",
        DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look",
        TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", SWITCH="switch", TO_ACTIVE="to_active",
        ATTACH_TO="attach_to", ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage")
    api.all_attack = lambda: []
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location("cynthia_v23_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChampionsCallBeforeEvolveTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def option(self, option_type, *, area=None, index=None, in_play_area=None, in_play_index=None, attack_id=None):
        return types.SimpleNamespace(
            type=option_type, area=area, index=index, playerIndex=None,
            inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=attack_id)

    def observation(self, options, hand, bench):
        mine = types.SimpleNamespace(hand=hand, bench=bench, active=[], discard=[], prize=[], stadium=[])
        opponent = types.SimpleNamespace(hand=[], bench=[], active=[], discard=[], prize=[])
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[]),
            select=types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=len(options), deck=[]))

    def test_call_caps_every_garchomp_evolution_below_normal_call(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.GARCHOMP_EX), types.SimpleNamespace(id=a.GARCHOMP_EX)]
        bench = [types.SimpleNamespace(id=a.GABITE, energies=[]), types.SimpleNamespace(id=a.GABITE, energies=[])]
        options = [
            self.option(a.OptionType.ABILITY, area="bench", index=0),
            self.option(a.OptionType.EVOLVE, area="hand", index=0, in_play_area="bench", in_play_index=0),
            self.option(a.OptionType.EVOLVE, area="hand", index=1, in_play_area="bench", in_play_index=1),
        ]
        obs = self.observation(options, hand, bench)
        call_score, _ = a.score_option(obs, options[0])
        self.assertEqual(call_score, 9500)
        self.assertTrue(all(a.score_option_with_champions_call_order(obs, option)[0] < call_score for option in options[1:]))
        self.assertEqual(a.choose_options(obs)[0], 0)

    def test_unrelated_evolution_is_unchanged_with_call(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.ROSERADE)]
        bench = [types.SimpleNamespace(id=a.GABITE, energies=[]), types.SimpleNamespace(id=a.ROSELIA, energies=[])]
        call = self.option(a.OptionType.ABILITY, area="bench", index=0)
        roserade = self.option(a.OptionType.EVOLVE, area="hand", index=0, in_play_area="bench", in_play_index=1)
        obs = self.observation([call, roserade], hand, bench)
        self.assertEqual(a.score_option_with_champions_call_order(obs, roserade), a.score_option(obs, roserade))

    def test_garchomp_evolution_is_unchanged_without_call(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.GARCHOMP_EX)]
        bench = [types.SimpleNamespace(id=a.GABITE, energies=[])]
        evolve = self.option(a.OptionType.EVOLVE, area="hand", index=0, in_play_area="bench", in_play_index=0)
        obs = self.observation([evolve], hand, bench)
        self.assertEqual(a.score_option_with_champions_call_order(obs, evolve), a.score_option(obs, evolve))

    def test_higher_scored_unrelated_action_remains_ahead_of_call_and_evolution(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.GARCHOMP_EX)]
        bench = [
            types.SimpleNamespace(id=a.GABITE, serial=10, energies=[]),
            types.SimpleNamespace(id=a.GABITE, serial=11, energies=[]),
        ]
        call = self.option(a.OptionType.ABILITY, area="bench", index=0)
        evolve = self.option(a.OptionType.EVOLVE, area="hand", index=0, in_play_area="bench", in_play_index=1)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.DRACONIC_BUSTER)
        obs = self.observation([call, evolve, attack], hand, bench)
        a.attack_score = lambda _obs, _attack_id: (12000, "test high action")
        self.assertEqual(a.choose_options(obs)[0], 2)
        self.assertGreater(a.score_option_with_champions_call_order(obs, attack)[0], a.score_option_with_champions_call_order(obs, call)[0])

    def test_existing_same_gabite_priority_is_preserved(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.GARCHOMP_EX)]
        bench = [types.SimpleNamespace(id=a.GABITE, serial=10, energies=[])]
        call = self.option(a.OptionType.ABILITY, area="bench", index=0)
        evolve = self.option(a.OptionType.EVOLVE, area="hand", index=0, in_play_area="bench", in_play_index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.DRACONIC_BUSTER)
        obs = self.observation([call, evolve, attack], hand, bench)
        a.attack_score = lambda _obs, _attack_id: (12000, "test high action")
        self.assertEqual(a.choose_options(obs)[0], 0)


if __name__ == "__main__":
    unittest.main()
