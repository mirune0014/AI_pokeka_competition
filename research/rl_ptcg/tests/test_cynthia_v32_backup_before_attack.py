"""Focused public-state ordering checks for Cynthia Garchomp v32."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
AGENT_PATH = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v32_backup_before_attack" / "main.py"


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
    spec = importlib.util.spec_from_file_location("cynthia_v32_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BackupBeforeAttackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def option(self, option_type, *, area=None, index=None, in_play_area=None, in_play_index=None, attack_id=None):
        return types.SimpleNamespace(type=option_type, area=area, index=index, playerIndex=None,
                                     inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=attack_id)

    def pokemon(self, card_id, hp=400, energies=()):
        return types.SimpleNamespace(id=card_id, hp=hp, energies=list(energies), serial=card_id)

    def observation(self, options, hand, *, active_energy=(6,), bench=(), discard=(), opponent_bench=True, prizes=2, target_hp=500):
        a = self.agent
        mine = types.SimpleNamespace(
            hand=hand,
            active=[self.pokemon(a.GARCHOMP_EX, energies=active_energy)],
            bench=list(bench), discard=[types.SimpleNamespace(id=x) for x in discard],
            prize=[object() for _ in range(prizes)], stadium=[], deckCount=30)
        opponent = types.SimpleNamespace(
            hand=[], active=[self.pokemon(999, hp=target_hp)],
            bench=[self.pokemon(998)] if opponent_bench else [], discard=[], prize=[])
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, opponent], looking=[], stadium=[]),
            select=types.SimpleNamespace(option=options, context="main", minCount=1, maxCount=1, deck=[]))

    def set_attack_scores(self, obs, score=15000):
        self.agent.attack_score = lambda _obs, attack_id: (score, f"attack {attack_id}")
        return obs

    def test_a1_a2_night_stretcher_precedes_corkscrew_and_buster(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.NIGHT_STRETCHER)]
        for attack_id in (a.CORKSCREW_DIVE, a.DRACONIC_BUSTER):
            stretch = self.option(a.OptionType.PLAY, area="hand", index=0)
            attack = self.option(a.OptionType.ATTACK, attack_id=attack_id)
            energies = (6,) if attack_id == a.CORKSCREW_DIVE else (6, 20)
            obs = self.set_attack_scores(
                self.observation([stretch, attack], hand, active_energy=energies, discard=[a.GIBLE]),
                48600,
            )
            self.assertEqual(a.backup_readiness_before_attack_index(obs, [
                (a.score_option(obs, stretch)[0], 0, "stretcher"), (48600, 1, "attack")]), 0)
            self.assertEqual(a.choose_options(obs), [0])

    def test_a3_a4_poffin_precedes_corkscrew_and_buster(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.BUDDY_POFFIN)]
        for attack_id in (a.CORKSCREW_DIVE, a.DRACONIC_BUSTER):
            poffin = self.option(a.OptionType.PLAY, area="hand", index=0)
            attack = self.option(a.OptionType.ATTACK, attack_id=attack_id)
            energies = (6,) if attack_id == a.CORKSCREW_DIVE else (6, 20)
            obs = self.set_attack_scores(self.observation([poffin, attack], hand, active_energy=energies), 48600)
            self.assertEqual(a.choose_options(obs), [0])

    def test_other_named_direct_backup_routes_are_eligible(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=x) for x in (a.GIBLE, a.FIGHTING_GONG, a.GABITE, a.GARCHOMP_EX, a.BASIC_FIGHTING)]
        gible = self.pokemon(a.GIBLE)
        gabite = self.pokemon(a.GABITE)
        options = [
            self.option(a.OptionType.PLAY, area="hand", index=0),
            self.option(a.OptionType.PLAY, area="hand", index=1),
            self.option(a.OptionType.EVOLVE, area="hand", index=2, in_play_area="bench", in_play_index=0),
            self.option(a.OptionType.EVOLVE, area="hand", index=3, in_play_area="bench", in_play_index=1),
            self.option(a.OptionType.ATTACH, area="hand", index=4, in_play_area="bench", in_play_index=0),
        ]
        obs = self.observation(options, hand, bench=[gible, gabite])
        self.assertTrue(a.is_direct_backup_action(obs, options[0]))
        self.assertFalse(a.is_direct_backup_action(obs, options[1]))  # Gong requires no backup body.
        self.assertTrue(a.is_direct_backup_action(obs, options[2]))
        self.assertTrue(a.is_direct_backup_action(obs, options[3]))
        self.assertTrue(a.is_direct_backup_action(obs, options[4]))
        gong_obs = self.observation([options[1]], hand)
        self.assertTrue(a.is_direct_backup_action(gong_obs, options[1]))

    def test_c1_non_attack_development_is_unchanged(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.BASIC_FIGHTING)]
        preload = self.option(a.OptionType.ATTACH, area="hand", index=0, in_play_area="bench", in_play_index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        bench = [self.pokemon(a.GARCHOMP_EX, energies=(6,))]
        obs = self.set_attack_scores(self.observation([preload, attack], hand, active_energy=(6, 20), bench=bench), 12000)
        self.assertIsNone(a.backup_readiness_before_attack_index(obs, [(14200, 0, "preload"), (12000, 1, "attack")]))
        self.assertEqual(a.choose_options(obs), [0])

    def test_c2_c3_c4_leave_guard_inactive(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.BUDDY_POFFIN)]
        poffin = self.option(a.OptionType.PLAY, area="hand", index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        cases = [
            self.observation([poffin, attack], hand, bench=[self.pokemon(a.GARCHOMP_EX, energies=(6,))]),
            self.observation([poffin, attack], hand, opponent_bench=False),
            self.observation([poffin, attack], hand, prizes=1, target_hp=10),
        ]
        for obs in cases:
            self.set_attack_scores(obs, 15000)
            scored = [(a.score_option(obs, poffin)[0], 0, "poffin"), (15000, 1, "attack")]
            self.assertIsNone(a.backup_readiness_before_attack_index(obs, scored))
            self.assertEqual(a.choose_options(obs), [1])

    def test_unrelated_support_and_retreat_are_never_promoted(self):
        a = self.agent
        hand = [types.SimpleNamespace(id=a.ROSELIA)]
        support = self.option(a.OptionType.PLAY, area="hand", index=0)
        retreat = self.option(a.OptionType.RETREAT)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        obs = self.set_attack_scores(self.observation([support, retreat, attack], hand), 15000)
        scored = [(a.score_option(obs, support)[0], 0, "support"), (a.score_option(obs, retreat)[0], 1, "retreat"), (15000, 2, "attack")]
        self.assertIsNone(a.backup_readiness_before_attack_index(obs, scored))
        self.assertEqual(a.choose_options(obs), [2])


if __name__ == "__main__":
    unittest.main()
