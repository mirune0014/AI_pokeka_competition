"""Focused public-state regression checks for Cynthia Garchomp v33."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v33_productive_backup_before_attack"


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
    spec = importlib.util.spec_from_file_location("cynthia_v33_main", AGENT_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductiveBackupBeforeAttackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def option(self, kind, *, area=None, index=None, in_play_area=None, in_play_index=None, attack_id=None):
        return types.SimpleNamespace(type=kind, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=attack_id)

    def pokemon(self, card_id, hp=400, energies=()):
        return types.SimpleNamespace(id=card_id, hp=hp, energies=list(energies), serial=card_id)

    def obs(self, options, hand, *, bench=(), discard=(), target_hp=500, opponent_bench=True, prizes=2):
        a = self.agent
        mine = types.SimpleNamespace(hand=hand, active=[self.pokemon(a.GARCHOMP_EX, energies=(a.BASIC_FIGHTING, a.ROCK_FIGHTING))], bench=list(bench), discard=[types.SimpleNamespace(id=x) for x in discard], prize=[object() for _ in range(prizes)], stadium=[], deckCount=30)
        foe = types.SimpleNamespace(hand=[], active=[self.pokemon(999, hp=target_hp)], bench=[self.pokemon(998)] if opponent_bench else [], discard=[], prize=[])
        return types.SimpleNamespace(current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[]), select=types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=1, deck=[]))

    def scored(self, obs, action_index, action_score=15000):
        a = self.agent
        rows = [(a.score_option(obs, opt)[0], i, "candidate") for i, opt in enumerate(obs.select.option)]
        rows[action_index] = (action_score, action_index, "v23 attack")
        a.attack_score = lambda _obs, attack_id: (action_score, f"attack {attack_id}")
        return rows

    def test_exact_deck_equality(self):
        v32 = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v32_backup_before_attack" / "deck.csv"
        self.assertEqual((AGENT_DIR / "deck.csv").read_bytes(), v32.read_bytes())

    def test_active_ko_blocks_override_and_process_selects_attack(self):
        a = self.agent
        gong = self.option(a.OptionType.PLAY, area="hand", index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        obs = self.obs([gong, attack], [types.SimpleNamespace(id=a.FIGHTING_GONG)], target_hp=100)
        a.best_damage_for_active = lambda *_args: 100
        rows = self.scored(obs, 1)
        self.assertIsNone(a.backup_readiness_before_attack_index(obs, rows))
        self.assertEqual(a.choose_options(obs), [1])

    def test_non_ko_poffin_does_not_override_and_process_selects_attack(self):
        a = self.agent
        poffin = self.option(a.OptionType.PLAY, area="hand", index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        obs = self.obs([poffin, attack], [types.SimpleNamespace(id=a.BUDDY_POFFIN)])
        a.best_damage_for_active = lambda *_args: 0
        rows = self.scored(obs, 1)
        self.assertFalse(a.is_direct_backup_action(obs, poffin))
        self.assertIsNone(a.backup_readiness_before_attack_index(obs, rows))
        self.assertEqual(a.choose_options(obs), [1])

    def test_non_ko_gong_and_direct_gible_still_override(self):
        a = self.agent
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        for card_id in (a.FIGHTING_GONG, a.GIBLE):
            backup = self.option(a.OptionType.PLAY, area="hand", index=0)
            obs = self.obs([backup, attack], [types.SimpleNamespace(id=card_id)])
            a.best_damage_for_active = lambda *_args: 0
            rows = self.scored(obs, 1, action_score=48600)
            self.assertTrue(a.is_direct_backup_action(obs, backup))
            self.assertEqual(a.backup_readiness_before_attack_index(obs, rows), 0)
            self.assertEqual(a.choose_options(obs), [0])

    def test_non_ko_stretcher_evolve_and_bench_attach_remain_eligible(self):
        a = self.agent
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        cases = [
            (self.option(a.OptionType.PLAY, area="hand", index=0), [a.NIGHT_STRETCHER], (), (a.GIBLE,)),
            (self.option(a.OptionType.EVOLVE, area="hand", index=0, in_play_area="bench", in_play_index=0), [a.GABITE], (self.pokemon(a.GIBLE),), ()),
            (self.option(a.OptionType.ATTACH, area="hand", index=0, in_play_area="bench", in_play_index=0), [a.BASIC_FIGHTING], (self.pokemon(a.GIBLE),), ()),
        ]
        for backup, hand_ids, bench, discard in cases:
            obs = self.obs([backup, attack], [types.SimpleNamespace(id=x) for x in hand_ids], bench=bench, discard=discard)
            a.best_damage_for_active = lambda *_args: 0
            rows = self.scored(obs, 1, action_score=48600)
            self.assertTrue(a.is_direct_backup_action(obs, backup))
            self.assertEqual(a.backup_readiness_before_attack_index(obs, rows), 0)

    def test_c1_c4_boundaries(self):
        a = self.agent
        gong = self.option(a.OptionType.PLAY, area="hand", index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        cases = [
            # C1: v23 did not select an attack.
            (self.obs([gong, attack], [types.SimpleNamespace(id=a.FIGHTING_GONG)]), [(20000, 0, "v23 play"), (15000, 1, "attack")]),
            # C2: an energized bench Garchomp already exists.
            (self.obs([gong, attack], [types.SimpleNamespace(id=a.FIGHTING_GONG)], bench=[self.pokemon(a.GARCHOMP_EX, energies=(a.BASIC_FIGHTING,))]), [(1000, 0, "gong"), (15000, 1, "attack")]),
            # C3: no opposing bench remains.
            (self.obs([gong, attack], [types.SimpleNamespace(id=a.FIGHTING_GONG)], opponent_bench=False), [(1000, 0, "gong"), (15000, 1, "attack")]),
            # C4: a prize-clinching active KO remains blocked.
            (self.obs([gong, attack], [types.SimpleNamespace(id=a.FIGHTING_GONG)], target_hp=100, prizes=1), [(1000, 0, "gong"), (15000, 1, "attack")]),
        ]
        for obs, rows in cases:
            a.best_damage_for_active = lambda *_args: 100 if obs.current.players[1].active[0].hp == 100 else 0
            self.assertIsNone(a.backup_readiness_before_attack_index(obs, rows))


if __name__ == "__main__":
    unittest.main()
