"""Public-state regression checks for the split v38/v39 Poke Pad ablation."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v35_reliable_development_before_attack"
V38_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v38_early_pokepad_main_only"
V39_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v39_pokepad_gible_target_only"


def load_agent_module(name, agent_dir):
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench", PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium")
    api.OptionType = types.SimpleNamespace(ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat", ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end", NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy")
    api.SelectContext = types.SimpleNamespace(MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active", SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard", DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look", TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", SWITCH="switch", TO_ACTIVE="to_active", ATTACH_TO="attach_to", ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage")
    api.all_attack = lambda: []
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location(name, agent_dir / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PokePadAblationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v38 = load_agent_module("cynthia_v38_main", V38_DIR)
        cls.v39 = load_agent_module("cynthia_v39_main", V39_DIR)

    @staticmethod
    def card(card_id):
        return types.SimpleNamespace(id=card_id)

    @staticmethod
    def pokemon(card_id):
        return types.SimpleNamespace(id=card_id, hp=200, energies=[], serial=card_id)

    @staticmethod
    def option(kind, *, area=None, index=None, in_play_area=None, in_play_index=None):
        return types.SimpleNamespace(type=kind, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=None)

    def main_obs(self, agent, *, turn=2, bench=(), top_is_attachment=True):
        hand = [self.card(agent.POKE_PAD), self.card(agent.BASIC_FIGHTING)]
        attach_type = agent.OptionType.ATTACH if top_is_attachment else agent.OptionType.PLAY
        options = [
            self.option(agent.OptionType.PLAY, area=agent.AreaType.HAND, index=0),
            self.option(attach_type, area=agent.AreaType.HAND, index=1, in_play_area=agent.AreaType.ACTIVE, in_play_index=0),
        ]
        mine = types.SimpleNamespace(hand=hand, active=[self.pokemon(agent.GIBLE)], bench=list(bench), discard=[], prize=[object()] * 6, stadium=[], deckCount=30)
        foe = types.SimpleNamespace(hand=[], active=[self.pokemon(345)], bench=[], discard=[], prize=[])
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], turn=turn), select=types.SimpleNamespace(option=options, context=agent.SelectContext.MAIN, minCount=1, maxCount=1, deck=[]))

    def target_obs(self, agent, *, turn=2, bench=(), source=None, include_gible=True):
        cards = ([self.card(agent.GIBLE)] if include_gible else []) + [self.card(agent.GABITE)]
        options = [self.option(agent.OptionType.CARD, area=agent.AreaType.DECK, index=index) for index in range(len(cards))]
        mine = types.SimpleNamespace(hand=[], active=[self.pokemon(agent.GIBLE)], bench=list(bench), discard=[], prize=[object()] * 6, stadium=[], deckCount=30)
        foe = types.SimpleNamespace(hand=[], active=[self.pokemon(344)], bench=[], discard=[], prize=[])
        select = types.SimpleNamespace(option=options, context=agent.SelectContext.TO_HAND, minCount=1, maxCount=1, deck=cards)
        if source is not None:
            select.effect = self.card(source)
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], turn=turn), select=select)

    def scored(self, agent, obs):
        return [(agent.score_option(obs, option)[0], index, "candidate") for index, option in enumerate(obs.select.option)]

    def test_decks_are_byte_identical_to_v35_and_have_60_cards(self):
        baseline = (BASELINE_DIR / "deck.csv").read_bytes()
        for candidate in (V38_DIR, V39_DIR):
            deck = (candidate / "deck.csv").read_bytes()
            self.assertEqual(baseline, deck)
            self.assertEqual(60, len([line for line in deck.splitlines() if line.strip()]))

    def test_v38_only_changes_early_main_pokepad_before_energy_attachment(self):
        v38_obs = self.main_obs(self.v38)
        v39_obs = self.main_obs(self.v39)
        self.assertEqual(0, self.v38.early_pokepad_before_energy_attach_index(v38_obs, self.scored(self.v38, v38_obs)))
        self.assertEqual([0], self.v38.choose_options(v38_obs))
        self.assertFalse(hasattr(self.v39, "early_pokepad_before_energy_attach_index"))
        self.assertEqual([1], self.v39.choose_options(v39_obs))

    def test_v39_only_changes_source_marked_pokepad_gible_target(self):
        v38_obs = self.target_obs(self.v38, source=self.v38.POKE_PAD)
        v39_obs = self.target_obs(self.v39, source=self.v39.POKE_PAD)
        self.assertFalse(hasattr(self.v38, "effect_source_is_poke_pad"))
        self.assertEqual([1], self.v38.choose_options(v38_obs))
        self.assertEqual(0, self.v39.early_pokepad_gible_target_index(v39_obs, self.scored(self.v39, v39_obs)))
        self.assertEqual([0], self.v39.choose_options(v39_obs))

    def test_v38_main_guard_negatives(self):
        for kwargs, expected in (
            ({"turn": 3}, [1]),
            ({"bench": (self.pokemon(self.v38.GIBLE), self.pokemon(self.v38.GABITE))}, [1]),
            ({"top_is_attachment": False}, [0]),
        ):
            obs = self.main_obs(self.v38, **kwargs)
            self.assertIsNone(self.v38.early_pokepad_before_energy_attach_index(obs, self.scored(self.v38, obs)))
            self.assertEqual(expected, self.v38.choose_options(obs))

    def test_v39_target_guard_negatives(self):
        for kwargs in (
            {"turn": 3, "source": self.v39.POKE_PAD},
            {"bench": (self.pokemon(self.v39.GIBLE), self.pokemon(self.v39.GABITE)), "source": self.v39.POKE_PAD},
            {"source": None},
            {"source": self.v39.POKE_PAD, "include_gible": False},
        ):
            obs = self.target_obs(self.v39, **kwargs)
            self.assertIsNone(self.v39.early_pokepad_gible_target_index(obs, self.scored(self.v39, obs)))
            self.assertEqual([len(obs.select.option) - 1], self.v39.choose_options(obs))


if __name__ == "__main__":
    unittest.main()
