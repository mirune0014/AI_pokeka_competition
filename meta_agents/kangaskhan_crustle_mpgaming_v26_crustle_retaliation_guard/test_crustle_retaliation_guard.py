"""Focused public-state checks for the v26 Crustle trade guard."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


def load_agent_module(path):
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench",
        PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium")
    api.OptionType = types.SimpleNamespace(
        ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach",
        END="end", CARD="card", YES="yes", NO="no")
    api.Pokemon = object
    api.SelectContext = types.SimpleNamespace(MAIN="main")
    api.all_attack = lambda: [types.SimpleNamespace(attackId=479, damage=120)]
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location("candidate_main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CrustleRetaliationGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module(Path(__file__).with_name("main.py"))
        cls.baseline = load_agent_module(
            Path(__file__).parent.parent / "kangaskhan_crustle_mpgaming_v25_runtime_root_compat" / "main.py")

    def state(self, own_hp=140, opponent_hp=130, jumbo=True, attack_id=479):
        energy = lambda card_id: types.SimpleNamespace(id=card_id)
        mine = types.SimpleNamespace(active=[types.SimpleNamespace(id=345, hp=own_hp)], bench=[], discard=[], prize=[], hand=[])
        theirs = types.SimpleNamespace(active=[types.SimpleNamespace(
            id=345, hp=opponent_hp, energies=[energy(1), energy(14), energy(11)])], bench=[], discard=[], prize=[], hand=[])
        options = [types.SimpleNamespace(type="attack", attackId=attack_id)]
        if jumbo:
            options.append(types.SimpleNamespace(type="play", index=0))
            mine.hand = [types.SimpleNamespace(id=1147)]
        obs = types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, turn=5, players=[mine, theirs], looking=[], stadium=[]),
            select=None)
        sel = types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=1, deck=[])
        obs.select = sel
        return obs, sel, mine, theirs

    def test_post_first_jumbo_trade_prefers_second_legal_jumbo(self):
        obs, sel, mine, theirs = self.state()
        self.assertTrue(self.agent.crustle_retaliation_guard(obs, sel, mine, theirs, mine.active[0]))
        self.assertEqual(self.baseline.agent(obs), [0])
        self.assertEqual(self.agent.agent(obs), [1])

    def test_no_second_legal_jumbo_keeps_attack(self):
        obs, sel, mine, theirs = self.state(jumbo=False)
        self.assertFalse(self.agent.crustle_retaliation_guard(obs, sel, mine, theirs, mine.active[0]))
        self.assertEqual(self.agent.agent(obs), [0])

    def test_lethal_attack_keeps_attack(self):
        obs, sel, mine, theirs = self.state(opponent_hp=120)
        self.assertFalse(self.agent.crustle_retaliation_guard(obs, sel, mine, theirs, mine.active[0]))
        self.assertEqual(self.agent.agent(obs), [0])


if __name__ == "__main__":
    unittest.main()
