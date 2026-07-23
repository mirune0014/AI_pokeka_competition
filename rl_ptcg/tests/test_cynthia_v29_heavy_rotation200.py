"""Focused heavy-damage retreat rotation checks for Cynthia Garchomp v29."""
import csv
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v29_heavy_rotation200" / "main.py"
V23_DECK_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve" / "deck.csv"
V29_DECK_PATH = AGENT_PATH.parent / "deck.csv"


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
    spec = importlib.util.spec_from_file_location("cynthia_v29_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HeavyRotation200Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def pokemon(self, card_id, *, damage=0, energies=0):
        return types.SimpleNamespace(
            id=card_id,
            hp=330 - damage,
            maxHp=330,
            energies=[types.SimpleNamespace(id=6) for _ in range(energies)],
        )

    def observation(self, active, bench=None, opponent_active=None):
        mine = types.SimpleNamespace(hand=[], active=[active] if active else [], bench=bench or [], discard=[], prize=[], stadium=[], deckCount=30)
        opponent = types.SimpleNamespace(hand=[], active=[opponent_active] if opponent_active else [], bench=[], discard=[], prize=[])
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[]),
            select=types.SimpleNamespace(option=[], context="main", minCount=1, maxCount=1, deck=[]),
        )

    def test_damage_200_rotates_heavy_active_garchomp_to_ready_backup(self):
        a = self.agent
        obs = self.observation(self.pokemon(a.GARCHOMP_EX, damage=200, energies=1), [self.pokemon(a.GARCHOMP_EX, energies=2)])
        self.assertTrue(a.should_rotate_heavy_garchomp(obs))
        self.assertEqual(a.score_retreat(obs, None), (19000, "rotate heavy Garchomp to ready backup"))

    def test_damage_190_does_not_rotate(self):
        a = self.agent
        obs = self.observation(self.pokemon(a.GARCHOMP_EX, damage=190, energies=1), [self.pokemon(a.GARCHOMP_EX, energies=2)])
        self.assertFalse(a.should_rotate_heavy_garchomp(obs))
        self.assertEqual(a.score_retreat(obs, None), (-2500, "keep Garchomp active"))

    def test_bench_garchomp_with_one_energy_does_not_rotate(self):
        a = self.agent
        obs = self.observation(self.pokemon(a.GARCHOMP_EX, damage=200, energies=1), [self.pokemon(a.GARCHOMP_EX, energies=1)])
        self.assertFalse(a.should_rotate_heavy_garchomp(obs))

    def test_ready_gabite_does_not_count_as_backup_garchomp(self):
        a = self.agent
        obs = self.observation(self.pokemon(a.GARCHOMP_EX, damage=200, energies=1), [self.pokemon(a.GABITE, energies=2)])
        self.assertFalse(a.should_rotate_heavy_garchomp(obs))

    def test_fresh_active_garchomp_does_not_rotate(self):
        a = self.agent
        obs = self.observation(self.pokemon(a.GARCHOMP_EX, damage=0, energies=1), [self.pokemon(a.GARCHOMP_EX, energies=2)])
        self.assertFalse(a.should_rotate_heavy_garchomp(obs))

    def test_ko_attack_score_remains_above_rotation_score(self):
        a = self.agent
        obs = self.observation(
            self.pokemon(a.GARCHOMP_EX, damage=200, energies=2),
            [self.pokemon(a.GARCHOMP_EX, energies=2)],
            self.pokemon(999, damage=230),
        )
        self.assertGreater(a.attack_score(obs, a.CORKSCREW_DIVE)[0], 19000)

    def test_deck_is_exactly_unchanged_and_has_sixty_cards(self):
        with V23_DECK_PATH.open(newline="") as v23_file, V29_DECK_PATH.open(newline="") as v29_file:
            v23_cards = [row[0] for row in csv.reader(v23_file) if row]
            v29_cards = [row[0] for row in csv.reader(v29_file) if row]
        self.assertEqual(len(v29_cards), 60)
        self.assertEqual(v29_cards, v23_cards)


if __name__ == "__main__":
    unittest.main()
