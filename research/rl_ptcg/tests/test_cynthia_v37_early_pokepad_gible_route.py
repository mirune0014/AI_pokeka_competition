"""Focused public-state regression checks for Cynthia Garchomp v37."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v37_early_pokepad_gible_route"
BASELINE_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v35_reliable_development_before_attack"


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
    spec = importlib.util.spec_from_file_location("cynthia_v37_main", AGENT_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EarlyPokePadGibleRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def card(self, card_id):
        return types.SimpleNamespace(id=card_id)

    def pokemon(self, card_id):
        return types.SimpleNamespace(id=card_id, hp=200, energies=[], serial=card_id)

    def option(self, kind, *, area=None, index=None, in_play_area=None, in_play_index=None):
        return types.SimpleNamespace(type=kind, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=None)

    def main_obs(self, *, turn=2, bench=(), opponent_id=344, include_pad=True):
        a = self.agent
        hand = [self.card(a.POKE_PAD), self.card(a.BASIC_FIGHTING)] if include_pad else [self.card(a.BASIC_FIGHTING)]
        options = []
        if include_pad:
            options.append(self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=0))
        options.append(self.option(a.OptionType.ATTACH, area=a.AreaType.HAND, index=len(hand) - 1, in_play_area=a.AreaType.ACTIVE, in_play_index=0))
        mine = types.SimpleNamespace(hand=hand, active=[self.pokemon(a.GIBLE)], bench=list(bench), discard=[], prize=[object()] * 6, stadium=[], deckCount=30)
        foe = types.SimpleNamespace(hand=[], active=[self.pokemon(opponent_id)], bench=[], discard=[], prize=[])
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], turn=turn), select=types.SimpleNamespace(option=options, context=a.SelectContext.MAIN, minCount=1, maxCount=1, deck=[]))

    def target_obs(self, *, turn=2, source=None, include_gible=True):
        a = self.agent
        cards = ([self.card(a.GIBLE)] if include_gible else []) + [self.card(a.GABITE)]
        options = [self.option(a.OptionType.CARD, area=a.AreaType.DECK, index=index) for index in range(len(cards))]
        mine = types.SimpleNamespace(hand=[], active=[self.pokemon(a.GIBLE)], bench=[], discard=[], prize=[object()] * 6, stadium=[], deckCount=30)
        foe = types.SimpleNamespace(hand=[], active=[self.pokemon(344)], bench=[], discard=[], prize=[])
        select = types.SimpleNamespace(option=options, context=a.SelectContext.TO_HAND, minCount=1, maxCount=1, deck=cards)
        if source is not None:
            select.effect = self.card(source)
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], turn=turn), select=select)

    def test_deck_is_byte_identical_to_v35_and_has_60_cards(self):
        deck = (AGENT_DIR / "deck.csv").read_bytes()
        self.assertEqual(deck, (BASELINE_DIR / "deck.csv").read_bytes())
        self.assertEqual(60, len([line for line in deck.splitlines() if line.strip()]))

    def test_crustle_visible_opening_ranks_pokepad_exactly_one_above_energy_attach(self):
        a = self.agent
        obs = self.main_obs(opponent_id=345)
        scored = [(a.score_option(obs, option)[0], index, "candidate") for index, option in enumerate(obs.select.option)]
        self.assertEqual(1, max(scored, key=lambda row: (row[0], -row[1]))[1])
        self.assertEqual(0, a.early_pokepad_before_energy_attach_index(obs, scored))
        self.assertEqual([0], a.choose_options(obs))

    def test_pokepad_resolution_marker_chooses_gible_one_point_above_gabite(self):
        a = self.agent
        obs = self.target_obs(source=a.POKE_PAD)
        scored = [(a.score_option(obs, option)[0], index, "candidate") for index, option in enumerate(obs.select.option)]
        self.assertEqual(1, max(scored, key=lambda row: (row[0], -row[1]))[1])
        self.assertEqual(0, a.early_pokepad_gible_target_index(obs, scored))
        self.assertEqual([0], a.choose_options(obs))

    def test_gold_win_85023194_turn_three_does_not_trigger(self):
        a = self.agent
        obs = self.main_obs(turn=3)
        scored = [(a.score_option(obs, option)[0], index, "candidate") for index, option in enumerate(obs.select.option)]
        self.assertIsNone(a.early_pokepad_before_energy_attach_index(obs, scored))
        self.assertEqual([1], a.choose_options(obs))

    def test_unmarked_or_non_pokepad_target_prompt_preserves_gabite(self):
        a = self.agent
        for source in (None, a.BUDDY_POFFIN):
            obs = self.target_obs(source=source)
            self.assertIsNone(a.early_pokepad_gible_target_index(obs, [(12500, 0, "Gible"), (16000, 1, "Gabite")]))
            self.assertEqual([1], a.choose_options(obs))

    def test_no_gible_target_does_not_trigger(self):
        a = self.agent
        obs = self.target_obs(source=a.POKE_PAD, include_gible=False)
        self.assertIsNone(a.early_pokepad_gible_target_index(obs, [(16000, 0, "Gabite")]))
        self.assertEqual([0], a.choose_options(obs))

    def test_three_main_line_bodies_or_non_attachment_top_do_not_trigger(self):
        a = self.agent
        crowded = self.main_obs(bench=(self.pokemon(a.GIBLE), self.pokemon(a.GABITE)))
        crowded_scored = [(a.score_option(crowded, option)[0], index, "candidate") for index, option in enumerate(crowded.select.option)]
        self.assertIsNone(a.early_pokepad_before_energy_attach_index(crowded, crowded_scored))
        ordinary = self.main_obs()
        self.assertIsNone(a.early_pokepad_before_energy_attach_index(ordinary, [(9000, 0, "Poke Pad"), (8500, 1, "attach")]))


if __name__ == "__main__":
    unittest.main()
