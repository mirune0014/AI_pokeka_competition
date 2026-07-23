"""Focused public-state regression checks for Cynthia Garchomp v36."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v36_starmie_direct_gible_before_attach"
BASELINE_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v35_reliable_development_before_attack"


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
    spec = importlib.util.spec_from_file_location("cynthia_v36_main", AGENT_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StarmieDirectGibleBeforeAttachTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def pokemon(self, card_id, energies=()):
        return types.SimpleNamespace(id=card_id, hp=200, energies=list(energies), serial=card_id)

    def option(self, kind, *, area=None, index=None, in_play_area=None, in_play_index=None):
        return types.SimpleNamespace(type=kind, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=None)

    def obs(self, *, opponent_ids=(1030,), turn=2, bench=()):
        a = self.agent
        gible = self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=0)
        attach = self.option(a.OptionType.ATTACH, area=a.AreaType.HAND, index=1, in_play_area=a.AreaType.ACTIVE, in_play_index=0)
        mine = types.SimpleNamespace(
            hand=[types.SimpleNamespace(id=a.GIBLE), types.SimpleNamespace(id=a.BASIC_FIGHTING)],
            active=[self.pokemon(a.GIBLE)], bench=list(bench), discard=[], prize=[object()] * 6,
            stadium=[], deckCount=30,
        )
        foe = types.SimpleNamespace(
            hand=[], active=[self.pokemon(opponent_ids[0])],
            bench=[self.pokemon(card_id) for card_id in opponent_ids[1:]], discard=[], prize=[],
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], turn=turn),
            select=types.SimpleNamespace(option=[gible, attach], context=a.SelectContext.MAIN, minCount=1, maxCount=1, deck=[]),
        )

    def test_deck_is_byte_identical_to_v35(self):
        deck = (AGENT_DIR / "deck.csv").read_bytes()
        self.assertEqual(deck, (BASELINE_DIR / "deck.csv").read_bytes())
        self.assertEqual(60, len([line for line in deck.splitlines() if line.strip()]))

    def test_85679036_like_visible_starmie_state_benches_gible_one_point_above_attach(self):
        a = self.agent
        obs = self.obs(opponent_ids=(a.STARYU,), turn=2)
        scored = [(a.score_option(obs, option)[0], index, "candidate") for index, option in enumerate(obs.select.option)]
        self.assertEqual(1, max(scored, key=lambda row: (row[0], -row[1]))[1])
        self.assertEqual(0, a.starmie_direct_gible_before_attach_index(obs, scored))
        self.assertEqual([0], a.choose_options(obs))

    def test_dwebble_or_crustle_does_not_trigger(self):
        a = self.agent
        for opponent_id in (344, 345):
            obs = self.obs(opponent_ids=(opponent_id,))
            self.assertIsNone(a.starmie_direct_gible_before_attach_index(obs, [(8500, 0, "Gible"), (8800, 1, "attach")]))
            self.assertEqual([1], a.choose_options(obs))

    def test_no_starmie_marker_does_not_trigger(self):
        a = self.agent
        obs = self.obs(opponent_ids=(999,))
        self.assertIsNone(a.starmie_direct_gible_before_attach_index(obs, [(8500, 0, "Gible"), (8800, 1, "attach")]))
        self.assertEqual([1], a.choose_options(obs))

    def test_turn_three_or_later_does_not_trigger(self):
        a = self.agent
        obs = self.obs(turn=3)
        self.assertIsNone(a.starmie_direct_gible_before_attach_index(obs, [(8500, 0, "Gible"), (8800, 1, "attach")]))
        self.assertEqual([1], a.choose_options(obs))

    def test_two_main_line_bodies_do_not_trigger(self):
        a = self.agent
        obs = self.obs(bench=(self.pokemon(a.GABITE),))
        self.assertIsNone(a.starmie_direct_gible_before_attach_index(obs, [(8500, 0, "Gible"), (8800, 1, "attach")]))
        self.assertEqual([1], a.choose_options(obs))

    def test_non_attachment_top_action_does_not_trigger(self):
        a = self.agent
        obs = self.obs()
        self.assertIsNone(a.starmie_direct_gible_before_attach_index(obs, [(9000, 0, "Gible"), (8500, 1, "attach")]))


if __name__ == "__main__":
    unittest.main()
