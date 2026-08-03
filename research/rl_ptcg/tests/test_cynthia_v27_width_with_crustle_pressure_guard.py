"""Focused Crustle-pressure checks for Cynthia Garchomp v27."""
import csv
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_PATH = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v27_width_with_crustle_pressure_guard" / "main.py"
V24_DECK_PATH = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v24_width_before_first_resource" / "deck.csv"
V27_DECK_PATH = AGENT_PATH.parent / "deck.csv"


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
    spec = importlib.util.spec_from_file_location("cynthia_v27_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WidthWithCrustlePressureGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def pokemon(self, card_id, *, energies=None):
        return types.SimpleNamespace(id=card_id, energies=energies or [])

    def option(self, option_type, *, area=None, index=None, in_play_area=None, in_play_index=None):
        return types.SimpleNamespace(type=option_type, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=None)

    def observation(self, *, opponent_active=None, opponent_bench=None, turn=1, main_line=None):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.BUDDY_POFFIN), types.SimpleNamespace(id=a.ROCK_FIGHTING), types.SimpleNamespace(id=a.POWER_WEIGHT)]
        options = [self.option(a.OptionType.PLAY, area="hand", index=0), self.option(a.OptionType.ATTACH, area="hand", index=1, in_play_area="bench", in_play_index=0), self.option(a.OptionType.ATTACH, area="hand", index=2, in_play_area="bench", in_play_index=0)]
        mine = types.SimpleNamespace(hand=hand, bench=main_line or [self.pokemon(a.GARCHOMP_EX)], active=[], discard=[], prize=[], stadium=[], deckCount=30)
        opponent = types.SimpleNamespace(hand=[], active=[opponent_active] if opponent_active else [], bench=opponent_bench or [], discard=[], prize=[])
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[], turn=turn), select=types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=len(options), deck=[]))

    def scored(self, obs):
        a = self.agent
        base = [(a.score_option_with_champions_call_order(obs, option)[0], index, "base") for index, option in enumerate(obs.select.option)]
        return a.cap_opening_first_resource_after_width(obs, base), base

    def test_dwebble_visible_with_energy_elsewhere_disables_deferral(self):
        a = self.agent
        obs = self.observation(opponent_active=self.pokemon(344), opponent_bench=[self.pokemon(999, energies=[types.SimpleNamespace(id=a.BASIC_FIGHTING)])])
        scored, base = self.scored(obs)
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))
        self.assertEqual(scored, base)

    def test_energized_crustle_disables_deferral(self):
        a = self.agent
        obs = self.observation(opponent_active=self.pokemon(345, energies=[types.SimpleNamespace(id=a.BASIC_FIGHTING)]))
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))

    def test_dwebble_without_opponent_energy_retains_deferral(self):
        obs = self.observation(opponent_active=self.pokemon(344), opponent_bench=[self.pokemon(999)])
        self.assertTrue(self.agent.opening_width_before_first_resource_applies(obs))

    def test_opponent_energy_without_crustle_line_retains_generic_width(self):
        a = self.agent
        obs = self.observation(opponent_active=self.pokemon(999, energies=[types.SimpleNamespace(id=a.BASIC_FIGHTING)]))
        self.assertTrue(a.opening_width_before_first_resource_applies(obs))

    def test_no_pressure_state_still_caps_rock_and_weight(self):
        scores = [score for score, _index, _reason in self.scored(self.observation())[0]]
        self.assertEqual(scores, [8600, 8599, 8599])

    def test_late_turn_and_own_width_conditions_remain_unchanged(self):
        a = self.agent
        self.assertFalse(a.opening_width_before_first_resource_applies(self.observation(turn=3)))
        wide_line = [self.pokemon(a.GARCHOMP_EX), self.pokemon(a.GIBLE)]
        self.assertFalse(a.opening_width_before_first_resource_applies(self.observation(main_line=wide_line)))

    def test_deck_is_unchanged_and_has_sixty_cards(self):
        with V24_DECK_PATH.open(newline="") as v24_file, V27_DECK_PATH.open(newline="") as v27_file:
            v24_cards = [row[0] for row in csv.reader(v24_file) if row]
            v27_cards = [row[0] for row in csv.reader(v27_file) if row]
        self.assertEqual(len(v27_cards), 60)
        self.assertEqual(v27_cards, v24_cards)


if __name__ == "__main__":
    unittest.main()
