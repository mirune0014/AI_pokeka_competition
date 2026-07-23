"""Focused opening-width ordering checks for Cynthia Garchomp v24."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v24_width_before_first_resource" / "main.py"


def load_agent_module():
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
        TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", SWITCH="switch", TO_ACTIVE="to_active",
        ATTACH_TO="attach_to", ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage")
    api.all_attack = lambda: []
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location("cynthia_v24_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WidthBeforeFirstResourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def option(self, option_type, *, area=None, index=None, in_play_area=None, in_play_index=None, attack_id=None):
        return types.SimpleNamespace(type=option_type, area=area, index=index, playerIndex=None,
                                     inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=attack_id)

    def observation(self, options, hand, bench, active=None, turn=1):
        mine = types.SimpleNamespace(hand=hand, bench=bench, active=active or [], discard=[], prize=[], stadium=[], deckCount=30)
        opponent = types.SimpleNamespace(hand=[], bench=[], active=[], discard=[], prize=[])
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[], turn=turn),
            select=types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=len(options), deck=[]))

    def scored(self, obs):
        a = self.agent
        base = [(a.score_option_with_champions_call_order(obs, opt)[0], i, "base") for i, opt in enumerate(obs.select.option)]
        return a.cap_opening_first_resource_after_width(obs, base)

    def opening_options(self, include_poffin=True):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.BUDDY_POFFIN), types.SimpleNamespace(id=a.ROCK_FIGHTING),
                types.SimpleNamespace(id=a.POWER_WEIGHT), types.SimpleNamespace(id=a.BASIC_FIGHTING)]
        options = []
        if include_poffin:
            options.append(self.option(a.OptionType.PLAY, area="hand", index=0))
        options.extend([
            self.option(a.OptionType.ATTACH, area="hand", index=1, in_play_area="bench", in_play_index=0),
            self.option(a.OptionType.ATTACH, area="hand", index=2, in_play_area="bench", in_play_index=0),
            self.option(a.OptionType.ATTACH, area="hand", index=3, in_play_area="bench", in_play_index=0),
        ])
        return options, hand

    def test_positive_caps_rock_and_weight_below_best_legal_width_action(self):
        a = self.agent
        options, hand = self.opening_options()
        obs = self.observation(options, hand, [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[])])
        scores = [row[0] for row in self.scored(obs)]
        self.assertEqual([8600, 8599, 8599], scores[:3])

    def test_two_main_line_bodies_leave_attachment_scores_unchanged(self):
        a = self.agent
        options, hand = self.opening_options()
        obs = self.observation(options, hand, [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[]), types.SimpleNamespace(id=a.GIBLE, energies=[])])
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))
        self.assertEqual(self.scored(obs)[1][0], a.score_option(obs, options[1])[0])
        self.assertEqual(self.scored(obs)[2][0], a.score_option(obs, options[2])[0])

    def test_energized_main_line_leaves_attachment_scores_unchanged(self):
        a = self.agent
        options, hand = self.opening_options()
        energy = types.SimpleNamespace(id=a.BASIC_FIGHTING)
        obs = self.observation(options, hand, [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[energy])])
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))
        self.assertEqual(self.scored(obs)[1][0], a.score_option(obs, options[1])[0])
        self.assertEqual(self.scored(obs)[2][0], a.score_option(obs, options[2])[0])

    def test_basic_energy_attachment_is_unchanged(self):
        a = self.agent
        options, hand = self.opening_options()
        obs = self.observation(options, hand, [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[])])
        scores = [row[0] for row in self.scored(obs)]
        self.assertEqual(scores[3], a.score_option(obs, options[3])[0])

    def test_unrelated_higher_action_is_unchanged(self):
        a = self.agent
        options, hand = self.opening_options()
        options.append(self.option(a.OptionType.ATTACK, attack_id=a.DRACONIC_BUSTER))
        obs = self.observation(options, hand, [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[])])
        a.attack_score = lambda _obs, _attack_id: (20000, "high unrelated action")
        scores = [row[0] for row in self.scored(obs)]
        self.assertEqual(scores[4], 20000)
        self.assertEqual(a.choose_options(obs)[0], 4)

    def test_no_eligible_setup_action_leaves_scores_unchanged(self):
        a = self.agent
        options, hand = self.opening_options(include_poffin=False)
        obs = self.observation(options, hand, [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[])])
        base = [(a.score_option_with_champions_call_order(obs, opt)[0], i, "base") for i, opt in enumerate(options)]
        self.assertEqual(self.scored(obs), base)

    def test_late_board_collapse_does_not_reactivate_opening_gate(self):
        a = self.agent
        options, hand = self.opening_options()
        obs = self.observation(
            options,
            hand,
            [types.SimpleNamespace(id=a.GARCHOMP_EX, energies=[])],
            turn=13,
        )
        self.assertFalse(a.opening_width_before_first_resource_applies(obs))
        self.assertEqual(self.scored(obs)[1][0], a.score_option(obs, options[1])[0])
        self.assertEqual(self.scored(obs)[2][0], a.score_option(obs, options[2])[0])


if __name__ == "__main__":
    unittest.main()
