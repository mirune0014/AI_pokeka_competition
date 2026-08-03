"""Focused contract checks for Cynthia Garchomp v57's Roserade support role."""

import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V52_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v52_prebuster_backup_attach"
V57_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v57_roserade_support_role"
V52_MAIN_SHA256 = "2ef986b5e59559e591268358ce11aa9bb6633f9d2d49b80fa54676d5d5e930c7"
DECK_SHA256 = "606b44f7d6181c57c6ccdd7ee493c72baf39e684b264886bc01631dbee8d349c"


def install_api_stub():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        HAND="hand", DISCARD="discard", ACTIVE="active", BENCH="bench",
        PRIZE="prize", LOOKING="looking", DECK="deck", STADIUM="stadium",
    )
    api.OptionType = types.SimpleNamespace(
        ATTACK="attack", PLAY="play", EVOLVE="evolve", ATTACH="attach", RETREAT="retreat",
        ABILITY="ability", DISCARD="discard", CARD="card", YES="yes", NO="no", END="end",
        NUMBER="number", TOOL_CARD="tool_card", ENERGY_CARD="energy_card", ENERGY="energy",
    )
    api.SelectContext = types.SimpleNamespace(
        MAIN="main", IS_FIRST="is_first", SETUP_ACTIVE_POKEMON="setup_active",
        SETUP_BENCH_POKEMON="setup_bench", DISCARD="discard",
        DISCARD_CARD_OR_ATTACHED_CARD="discard_attached", TO_HAND="to_hand", LOOK="look",
        TO_DECK="to_deck", TO_DECK_BOTTOM="to_deck_bottom", TO_BENCH="to_bench",
        SWITCH="switch", TO_ACTIVE="to_active", ATTACH_TO="attach_to",
        ATTACH_FROM="attach_from", HEAL="heal", DAMAGE="damage",
    )
    api.all_attack = lambda: []
    api.all_card_data = lambda: []
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api


def load_agent_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoseradeSupportRoleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v52 = load_agent_module("cynthia_v52_for_v57_test", V52_DIR / "main.py")
        cls.v57 = load_agent_module("cynthia_v57_main", V57_DIR / "main.py")

    @staticmethod
    def pokemon(card_id, energy_ids=(), hp=300):
        return types.SimpleNamespace(
            id=card_id,
            energies=[types.SimpleNamespace(id=energy_id) for energy_id in energy_ids],
            hp=hp,
            maxHp=hp,
            tools=[],
            serial=None,
        )

    @staticmethod
    def option(
        option_type,
        *,
        area=None,
        index=None,
        player_index=None,
        in_play_area=None,
        in_play_index=None,
        attack_id=None,
    ):
        return types.SimpleNamespace(
            type=option_type,
            area=area,
            index=index,
            playerIndex=player_index,
            inPlayArea=in_play_area,
            inPlayIndex=in_play_index,
            attackId=attack_id,
            number=None,
        )

    def observation(
        self,
        agent,
        *,
        active_id,
        active_energy_ids=(),
        bench=(),
        hand_ids=(),
        options=(),
        context=None,
        visible_deck_ids=(),
    ):
        mine = types.SimpleNamespace(
            hand=[self.pokemon(card_id) for card_id in hand_ids],
            handCount=len(hand_ids),
            active=[self.pokemon(active_id, active_energy_ids)],
            bench=[self.pokemon(card_id, energies) for card_id, energies in bench],
            benchMax=5,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        foe = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=[self.pokemon(9000)],
            bench=[],
            benchMax=5,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        return types.SimpleNamespace(
            current=types.SimpleNamespace(
                yourIndex=0,
                players=[mine, foe],
                looking=[],
                stadium=[],
            ),
            select=types.SimpleNamespace(
                option=list(options),
                context=agent.SelectContext.MAIN if context is None else context,
                minCount=1,
                maxCount=1,
                deck=[self.pokemon(card_id) for card_id in visible_deck_ids],
                effect=None,
            ),
        )

    def boss_play_observation(self, agent, active_id, *, bench=(), include_surfer=False, retreat=False):
        hand_ids = [agent.BOSS]
        options = [self.option(agent.OptionType.PLAY, index=0)]
        if include_surfer:
            hand_ids.append(agent.SURFER)
            options.append(self.option(agent.OptionType.PLAY, index=1))
        if retreat:
            options.append(self.option(agent.OptionType.RETREAT))
        return self.observation(
            agent,
            active_id=active_id,
            bench=bench,
            hand_ids=hand_ids,
            options=options,
        )

    def boss_acquisition_observation(self, agent, active_id):
        option = self.option(agent.OptionType.CARD, area=agent.AreaType.DECK, index=0)
        return self.observation(
            agent,
            active_id=active_id,
            options=[option],
            context=agent.SelectContext.TO_HAND,
            visible_deck_ids=[agent.BOSS],
        ), option

    def test_main_attacker_role_excludes_only_roserade(self):
        a = self.v57
        expected = {
            a.ROSERADE: False,
            a.GARCHOMP_EX: True,
            a.SPIRITOMB: True,
        }
        for active_id, is_main_attacker in expected.items():
            with self.subTest(active_id=active_id):
                obs = self.observation(a, active_id=active_id)
                self.assertIs(a.active_is_main_attacker(obs), is_main_attacker)

    def test_roserade_boss_play_and_acquisition_use_existing_save_branches(self):
        a = self.v57
        play_obs = self.boss_play_observation(a, a.ROSERADE)
        self.assertEqual(a.score_play(play_obs, play_obs.select.option[0]), (-400, "save Boss until attacker ready"))

        take_obs, take_boss = self.boss_acquisition_observation(a, a.ROSERADE)
        self.assertEqual(a.score_to_hand(take_obs, take_boss), (1700, "take Boss"))

    def test_garchomp_and_spiritomb_boss_scores_are_unchanged(self):
        for card_name in ("GARCHOMP_EX", "SPIRITOMB"):
            with self.subTest(active=card_name):
                active_id = getattr(self.v57, card_name)
                v52_play = self.boss_play_observation(self.v52, active_id)
                v57_play = self.boss_play_observation(self.v57, active_id)
                self.assertEqual(
                    self.v57.score_play(v57_play, v57_play.select.option[0]),
                    self.v52.score_play(v52_play, v52_play.select.option[0]),
                )
                self.assertEqual(
                    self.v57.score_play(v57_play, v57_play.select.option[0]),
                    (3600, "Boss pressure"),
                )

                v52_take, v52_boss = self.boss_acquisition_observation(self.v52, active_id)
                v57_take, v57_boss = self.boss_acquisition_observation(self.v57, active_id)
                self.assertEqual(
                    self.v57.score_to_hand(v57_take, v57_boss),
                    self.v52.score_to_hand(v52_take, v52_boss),
                )
                self.assertEqual(self.v57.score_to_hand(v57_take, v57_boss), (5200, "take Boss"))

    def test_ready_benched_garchomp_keeps_surfer_retreat_and_followup_boss(self):
        a = self.v57
        ready_garchomp = [(a.GARCHOMP_EX, (a.BASIC_FIGHTING, a.ROCK_FIGHTING))]

        surfer_obs = self.boss_play_observation(
            a,
            a.ROSERADE,
            bench=ready_garchomp,
            include_surfer=True,
        )
        self.assertEqual(a.score_play(surfer_obs, surfer_obs.select.option[1]), (13000, "Surfer to Garchomp"))
        self.assertEqual(a.choose_options(surfer_obs), [1])

        retreat_obs = self.boss_play_observation(
            a,
            a.ROSERADE,
            bench=ready_garchomp,
            retreat=True,
        )
        self.assertEqual(a.score_retreat(retreat_obs, retreat_obs.select.option[1]), (12500, "retreat to Garchomp"))
        self.assertEqual(a.choose_options(retreat_obs), [1])

        switch_option = self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=0)
        switch_obs = self.observation(
            a,
            active_id=a.ROSERADE,
            bench=ready_garchomp,
            options=[switch_option],
            context=a.SelectContext.SWITCH,
        )
        self.assertEqual(a.choose_options(switch_obs), [0])
        followup_boss = self.boss_play_observation(a, a.GARCHOMP_EX)
        self.assertEqual(a.score_play(followup_boss, followup_boss.select.option[0]), (3600, "Boss pressure"))

    def test_candidate_is_exact_v52_except_attacker_set_and_deck_has_no_grass(self):
        baseline_files = {
            path.relative_to(V52_DIR)
            for path in V52_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V57_DIR)
            for path in V57_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V52_DIR / "main.py").read_bytes()
        candidate_main = (V57_DIR / "main.py").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V52_MAIN_SHA256)
        old = b"active.id in {GARCHOMP_EX, ROSERADE, SPIRITOMB}"
        new = b"active.id in {GARCHOMP_EX, SPIRITOMB}"
        self.assertEqual(baseline_main.count(old), 1)
        self.assertEqual(candidate_main, baseline_main.replace(old, new, 1))

        baseline_deck = (V52_DIR / "deck.csv").read_bytes()
        candidate_deck = (V57_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        deck = [int(line) for line in candidate_deck.splitlines() if line.strip()]
        self.assertEqual(len(deck), 60)
        self.assertNotIn(1, deck)
        self.assertNotIn(18, deck)


if __name__ == "__main__":
    unittest.main()
