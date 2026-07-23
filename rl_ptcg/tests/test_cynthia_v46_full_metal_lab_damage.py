"""Focused Full Metal Lab damage checks for Cynthia Garchomp v46."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_PATH = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v46_full_metal_lab_damage" / "main.py"

METAL_TARGET = 9001
NON_METAL_TARGET = 9002


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
        TO_BENCH="to_bench", ATTACH_TO="attach_to", ATTACH_FROM="attach_from",
        HEAL="heal", DAMAGE="damage")
    api.all_attack = lambda: []
    api.all_card_data = lambda: [
        types.SimpleNamespace(
            cardId=METAL_TARGET, name="Metal target", hp=300,
            energyType=types.SimpleNamespace(value=8), ex=True, megaEx=False),
        types.SimpleNamespace(
            cardId=NON_METAL_TARGET, name="Grass target", hp=300,
            energyType=1, ex=False, megaEx=False),
    ]
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api
    spec = importlib.util.spec_from_file_location("cynthia_v46_main", AGENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FullMetalLabDamageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    def pokemon(self, card_id, *, hp=300, energies=(), max_hp=None, energy_type=None):
        return types.SimpleNamespace(
            id=card_id,
            hp=hp,
            maxHp=max_hp if max_hp is not None else hp,
            energies=[types.SimpleNamespace(id=energy_id) for energy_id in energies],
            tools=[],
            energyType=energy_type,
        )

    def option(self, option_type, *, area=None, index=None, player_index=None, attack_id=None):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=player_index,
            inPlayArea=None,
            inPlayIndex=None,
            attackId=attack_id,
        )

    def observation(
        self,
        *,
        target,
        roserades=2,
        stadium_id=None,
        active=None,
        opponent_bench=None,
        hand=None,
        options=None,
        context=None,
    ):
        a = self.agent
        if active is None:
            active = self.pokemon(
                a.GARCHOMP_EX,
                hp=320,
                energies=(a.BASIC_FIGHTING, a.ROCK_FIGHTING),
            )
        bench = [self.pokemon(a.ROSERADE, hp=120) for _ in range(roserades)]
        mine = types.SimpleNamespace(
            hand=list(hand or []),
            active=[active],
            bench=bench,
            discard=[],
            prize=[object() for _ in range(6)],
            stadium=[],
            deckCount=30,
        )
        foe = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=[target],
            bench=list(opponent_bench or []),
            discard=[],
            prize=[object() for _ in range(6)],
            stadium=[],
            deckCount=30,
        )
        stadium = [types.SimpleNamespace(id=stadium_id)] if stadium_id is not None else []
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, foe],
                looking=[],
                stadium=stadium,
            ),
            select=types.SimpleNamespace(
                option=list(options or []),
                context=context if context is not None else a.SelectContext.MAIN,
                minCount=1,
                maxCount=max(1, len(options or [])),
                deck=[],
            ),
        )

    def test_buster_damage_matrix_preserves_non_lab_and_non_metal_values(self):
        a = self.agent
        metal = self.pokemon(METAL_TARGET, energy_type=1)
        non_metal = self.pokemon(NON_METAL_TARGET, energy_type=8)

        no_stadium = self.observation(target=metal)
        self.assertEqual(a.best_damage_for_active(no_stadium, metal, a.DRACONIC_BUSTER), 320)

        lab_metal = self.observation(target=metal, stadium_id=a.FULL_METAL_LAB)
        self.assertEqual(a.best_damage_for_active(lab_metal, metal, a.DRACONIC_BUSTER), 290)

        lab_non_metal = self.observation(target=non_metal, stadium_id=a.FULL_METAL_LAB)
        self.assertEqual(a.best_damage_for_active(lab_non_metal, non_metal, a.DRACONIC_BUSTER), 320)

        other_stadium = self.observation(target=metal, stadium_id=a.FOREST)
        self.assertEqual(a.best_damage_for_active(other_stadium, metal, a.DRACONIC_BUSTER), 320)

    def test_actual_target_is_required(self):
        a = self.agent
        target = self.pokemon(METAL_TARGET)
        obs = self.observation(target=target)
        with self.assertRaises(TypeError):
            a.best_damage_for_active(obs, attack_id=a.DRACONIC_BUSTER)

    def test_lab_metal_corkscrew_with_one_roserade_is_100_and_not_a_ko(self):
        a = self.agent
        target = self.pokemon(METAL_TARGET, hp=120, max_hp=300)
        attack = self.option(a.OptionType.ATTACK, attack_id=a.CORKSCREW_DIVE)
        obs = self.observation(
            target=target,
            roserades=1,
            stadium_id=a.FULL_METAL_LAB,
            options=[attack],
        )

        self.assertEqual(a.best_damage_for_active(obs, target, a.CORKSCREW_DIVE), 100)
        self.assertFalse(a.is_immediate_corkscrew_ko(obs, attack))
        self.assertEqual(a.attack_score(obs, a.CORKSCREW_DIVE), (15000, "Corkscrew Dive draw"))

    def test_lab_reduction_clamps_damage_at_zero(self):
        a = self.agent
        target = self.pokemon(METAL_TARGET)
        roselia = self.pokemon(a.ROSELIA, hp=70)
        obs = self.observation(
            target=target,
            roserades=0,
            stadium_id=a.FULL_METAL_LAB,
            active=roselia,
        )
        self.assertEqual(a.best_damage_for_active(obs, target, a.SPIKE_STING), 0)

    def test_buster_admissibility_and_attack_scoring_use_defending_active(self):
        a = self.agent
        full_hp_target = self.pokemon(METAL_TARGET, hp=300, max_hp=300)
        full_hp_obs = self.observation(target=full_hp_target, stadium_id=a.FULL_METAL_LAB)
        self.assertFalse(a.is_approved_buster_conversion(full_hp_obs))
        self.assertEqual(
            a.attack_score(full_hp_obs, a.DRACONIC_BUSTER),
            (14999, "Draconic Buster rejected conversion"),
        )

        damaged_target = self.pokemon(METAL_TARGET, hp=290, max_hp=300)
        damaged_obs = self.observation(target=damaged_target, stadium_id=a.FULL_METAL_LAB)
        self.assertTrue(a.is_approved_buster_conversion(damaged_obs))
        score, reason = a.attack_score(damaged_obs, a.DRACONIC_BUSTER)
        self.assertEqual(reason, "Draconic Buster KO")
        self.assertEqual(score, 43400)

    def test_boss_target_ranking_uses_each_prospective_target(self):
        a = self.agent
        current_metal = self.pokemon(METAL_TARGET, hp=300, max_hp=300)
        bench_metal = self.pokemon(METAL_TARGET, hp=300, max_hp=300)
        bench_non_metal = self.pokemon(NON_METAL_TARGET, hp=300, max_hp=300)
        obs = self.observation(
            target=current_metal,
            stadium_id=a.FULL_METAL_LAB,
            opponent_bench=[bench_metal, bench_non_metal],
        )

        self.assertEqual(a.boss_target_score(obs, bench_metal)[1], "Boss pressure")
        self.assertEqual(a.boss_target_score(obs, bench_non_metal)[1], "Boss KO Grass target")
        self.assertIs(a.best_boss_target(obs), bench_non_metal)

    def test_boss_play_scoring_uses_best_prospective_target(self):
        a = self.agent
        current_non_metal = self.pokemon(NON_METAL_TARGET, hp=300, max_hp=300)
        bench_metal = self.pokemon(METAL_TARGET, hp=300, max_hp=300)
        boss = types.SimpleNamespace(id=a.BOSS)
        play_boss = self.option(a.OptionType.PLAY, index=0)
        obs = self.observation(
            target=current_non_metal,
            stadium_id=a.FULL_METAL_LAB,
            opponent_bench=[bench_metal],
            hand=[boss],
            options=[play_boss],
        )

        self.assertEqual(a.score_play(obs, play_boss), (3600, "Boss pressure"))

    def test_damage_context_uses_each_proposed_target(self):
        a = self.agent
        current_non_metal = self.pokemon(NON_METAL_TARGET, hp=300, max_hp=300)
        bench_metal = self.pokemon(METAL_TARGET, hp=300, max_hp=300)
        bench_non_metal = self.pokemon(NON_METAL_TARGET, hp=300, max_hp=300)
        metal_option = self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=0, player_index=1)
        non_metal_option = self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=1, player_index=1)
        obs = self.observation(
            target=current_non_metal,
            stadium_id=a.FULL_METAL_LAB,
            opponent_bench=[bench_metal, bench_non_metal],
            options=[metal_option, non_metal_option],
            context=a.SelectContext.DAMAGE,
        )

        self.assertEqual(a.score_target(obs, metal_option)[1], "damage")
        self.assertEqual(a.score_target(obs, non_metal_option)[1], "damage KO")


if __name__ == "__main__":
    unittest.main()
