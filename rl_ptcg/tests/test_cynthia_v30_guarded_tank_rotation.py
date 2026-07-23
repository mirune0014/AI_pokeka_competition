"""Focused guarded-tank retreat rotation checks for Cynthia Garchomp v30."""
import csv
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v30_guarded_tank_rotation" / "main.py"
V23_DECK_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve" / "deck.csv"
V30_DECK_PATH = AGENT_PATH.parent / "deck.csv"


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
    spec = importlib.util.spec_from_file_location("cynthia_v30_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GuardedTankRotationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def pokemon(self, card_id, *, damage=0, energies=0, max_hp=330):
        return types.SimpleNamespace(
            id=card_id,
            hp=max_hp - damage,
            maxHp=max_hp,
            energies=[types.SimpleNamespace(id=6) for _ in range(energies)],
        )

    def option(self, option_type, *, attack_id=None):
        return types.SimpleNamespace(
            type=option_type,
            area=None,
            index=None,
            playerIndex=None,
            inPlayArea=None,
            inPlayIndex=None,
            attackId=attack_id,
        )

    def observation(self, active, bench=None, opponent_active=None, options=None):
        mine = types.SimpleNamespace(hand=[], active=[active], bench=bench or [], discard=[], prize=[], stadium=[], deckCount=30)
        opponent = types.SimpleNamespace(hand=[], active=[opponent_active] if opponent_active else [], bench=[], discard=[], prize=[])
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[]),
            select=types.SimpleNamespace(option=options or [], context="main", minCount=1, maxCount=1, deck=[]),
        )

    def guarded_observation(self, *, damage, active_energy, backup_energy=2, opponent_active=None, options=None):
        a = self.agent
        return self.observation(
            self.pokemon(a.GARCHOMP_EX, damage=damage, energies=active_energy),
            [self.pokemon(a.GARCHOMP_EX, energies=backup_energy)],
            opponent_active,
            options,
        )

    def test_320_damage_with_two_energy_rotates(self):
        obs = self.guarded_observation(damage=320, active_energy=2)
        self.assertTrue(self.agent.should_rotate_guarded_tank_garchomp(obs))
        self.assertEqual(self.agent.score_retreat(obs, None), (19000, "rotate guarded Garchomp to ready backup"))

    def test_220_damage_with_four_energy_rotates(self):
        obs = self.guarded_observation(damage=220, active_energy=4)
        self.assertTrue(self.agent.should_rotate_guarded_tank_garchomp(obs))

    def test_290_damage_with_three_energy_does_not_rotate(self):
        self.assertFalse(self.agent.should_rotate_guarded_tank_garchomp(self.guarded_observation(damage=290, active_energy=3)))

    def test_280_damage_with_two_energy_does_not_rotate(self):
        self.assertFalse(self.agent.should_rotate_guarded_tank_garchomp(self.guarded_observation(damage=280, active_energy=2)))

    def test_260_damage_with_two_energy_does_not_rotate(self):
        self.assertFalse(self.agent.should_rotate_guarded_tank_garchomp(self.guarded_observation(damage=260, active_energy=2)))

    def test_visible_immediate_ko_remains_attack_preferred(self):
        a = self.agent
        retreat = self.option(a.OptionType.RETREAT)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        obs = self.guarded_observation(
            damage=320,
            active_energy=2,
            opponent_active=self.pokemon(999, damage=230),
            options=[retreat, attack],
        )
        self.assertGreater(a.attack_score(obs, a.CORKSCREW_DIVE)[0], a.score_retreat(obs, retreat)[0])
        self.assertEqual(a.choose_options(obs), [1])

    def test_unready_backup_does_not_rotate(self):
        self.assertFalse(self.agent.should_rotate_guarded_tank_garchomp(self.guarded_observation(damage=320, active_energy=2, backup_energy=1)))

    def test_deck_is_exactly_unchanged_and_has_sixty_cards(self):
        with V23_DECK_PATH.open(newline="") as v23_file, V30_DECK_PATH.open(newline="") as v30_file:
            v23_cards = [row[0] for row in csv.reader(v23_file) if row]
            v30_cards = [row[0] for row in csv.reader(v30_file) if row]
        self.assertEqual(len(v30_cards), 60)
        self.assertEqual(v30_cards, v23_cards)


if __name__ == "__main__":
    unittest.main()
