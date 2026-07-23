"""Focused energized-active pressure checks for Cynthia Garchomp v26."""
import csv
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v26_width_with_energized_active_guard" / "main.py"
V24_DECK_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v24_width_before_first_resource" / "deck.csv"
V26_DECK_PATH = AGENT_PATH.parent / "deck.csv"


def load_agent_module():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench", PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium")
    api.OptionType = types.SimpleNamespace(ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat", ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end", NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy")
    api.SelectContext = types.SimpleNamespace(MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active", SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard", DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look", TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", SWITCH="switch", TO_ACTIVE="to_active", ATTACH_TO="attach_to", ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage")
    api.all_attack = lambda: []
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location("cynthia_v26_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WidthWithEnergizedActiveGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def option(self, option_type, *, area=None, index=None, in_play_area=None, in_play_index=None):
        return types.SimpleNamespace(type=option_type, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=None)

    def observation(self, *, opponent_active=None, turn=1, main_line=None):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.BUDDY_POFFIN), types.SimpleNamespace(id=a.ROCK_FIGHTING), types.SimpleNamespace(id=a.POWER_WEIGHT)]
        options = [self.option(a.OptionType.PLAY, area="hand", index=0), self.option(a.OptionType.ATTACH, area="hand", index=1, in_play_area="bench", in_play_index=0), self.option(a.OptionType.ATTACH, area="hand", index=2, in_play_area="bench", in_play_index=0)]
        mine = types.SimpleNamespace(hand=hand, bench=main_line or [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[])], active=[], discard=[], prize=[], stadium=[], deckCount=30)
        opponent = types.SimpleNamespace(hand=[], bench=[], active=[opponent_active] if opponent_active else [], discard=[], prize=[])
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[], turn=turn), select=types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=len(options), deck=[]))

    def scored(self, obs):
        a = self.agent
        base = [(a.score_option_with_champions_call_order(obs, option)[0], index, "base") for index, option in enumerate(obs.select.option)]
        return a.cap_opening_first_resource_after_width(obs, base), base

    def test_energized_basic_active_disables_width_deferral(self):
        a = self.agent
        obs = self.observation(opponent_active=types.SimpleNamespace(id=999, preEvolution="", energies=[types.SimpleNamespace(id=a.BASIC_FIGHTING)]))
        scored, base = self.scored(obs)
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))
        self.assertEqual(scored, base)

    def test_energized_evolved_active_disables_width_deferral(self):
        a = self.agent
        obs = self.observation(opponent_active=types.SimpleNamespace(id=999, preEvolution=998, energies=[types.SimpleNamespace(id=a.BASIC_FIGHTING)]))
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))

    def test_unenergized_active_retains_width_deferral(self):
        obs = self.observation(opponent_active=types.SimpleNamespace(id=999, preEvolution="", energies=[]))
        self.assertTrue(self.agent.opening_width_before_first_resource_applies(obs))

    def test_no_pressure_state_still_caps_rock_and_weight(self):
        scores = [score for score, _index, _reason in self.scored(self.observation())[0]]
        self.assertEqual(scores, [8600, 8599, 8599])

    def test_late_turn_and_own_width_conditions_remain_unchanged(self):
        a = self.agent
        self.assertFalse(a.opening_width_before_first_resource_applies(self.observation(turn=3)))
        wide_line = [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[]), types.SimpleNamespace(id=a.GIBLE, energies=[])]
        self.assertFalse(a.opening_width_before_first_resource_applies(self.observation(main_line=wide_line)))

    def test_deck_is_unchanged_and_has_sixty_cards(self):
        with V24_DECK_PATH.open(newline="") as v24_file, V26_DECK_PATH.open(newline="") as v26_file:
            v24_cards = [row[0] for row in csv.reader(v24_file) if row]
            v26_cards = [row[0] for row in csv.reader(v26_file) if row]
        self.assertEqual(len(v26_cards), 60)
        self.assertEqual(v26_cards, v24_cards)


if __name__ == "__main__":
    unittest.main()
