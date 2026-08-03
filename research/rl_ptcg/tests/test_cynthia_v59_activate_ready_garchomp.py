"""Focused contract checks for Cynthia Garchomp v59's activation route."""

import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V58_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v58_core_bridge_before_chip"
V59_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v59_activate_ready_garchomp"
V58_MAIN_SHA256 = "8375c5e73d7ad9c1b4e863993a6cbe8bcc96668008bb3ae709b3dc62d6f8d25a"
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
    api.all_card_data = lambda: [
        types.SimpleNamespace(cardId=341, name="Cynthia's Roselia", retreatCost=1, hp=70),
        types.SimpleNamespace(cardId=342, name="Cynthia's Roserade", retreatCost=1, hp=130),
        types.SimpleNamespace(cardId=387, name="Cynthia's Spiritomb", retreatCost=1, hp=70),
    ]
    api.to_observation_class = lambda observation: observation
    sys.modules["cg"] = types.ModuleType("cg")
    sys.modules["cg.api"] = api


def load_agent_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActivateReadyGarchompTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v59 = load_agent_module("cynthia_v59_main", V59_DIR / "main.py")

    @staticmethod
    def pokemon(card_id, energy_ids=(), hp=300, serial=None):
        return types.SimpleNamespace(
            id=card_id,
            energies=[types.SimpleNamespace(id=energy_id) for energy_id in energy_ids],
            hp=hp,
            maxHp=hp,
            tools=[],
            serial=serial,
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
        *,
        active_id=342,
        active_energy_ids=(),
        bench=None,
        hand_ids=(),
        options=(),
        context=None,
        opponent_hp=300,
        opponent_active=True,
    ):
        a = self.v59
        if bench is None:
            bench = [self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING,), serial=20)]
        mine = types.SimpleNamespace(
            hand=[self.pokemon(card_id) for card_id in hand_ids],
            handCount=len(hand_ids),
            active=[self.pokemon(active_id, active_energy_ids, serial=10)],
            bench=list(bench),
            benchMax=5,
            discard=[],
            prize=[object() for _ in range(6)],
            deckCount=30,
        )
        foe = types.SimpleNamespace(
            hand=[],
            handCount=0,
            active=[self.pokemon(9000, hp=opponent_hp)] if opponent_active else [],
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
                context=a.SelectContext.MAIN if context is None else context,
                minCount=1,
                maxCount=1,
                deck=[],
                effect=None,
            ),
        )

    def energy_attach(self, hand_index, energy_id):
        a = self.v59
        return self.option(
            a.OptionType.ATTACH,
            area=a.AreaType.HAND,
            index=hand_index,
            in_play_area=a.AreaType.ACTIVE,
            in_play_index=0,
        )

    def test_surfer_is_first_priority_and_choose_options_returns_it_immediately(self):
        a = self.v59
        options = [
            self.energy_attach(2, a.ROCK_FIGHTING),
            self.option(a.OptionType.RETREAT),
            self.option(a.OptionType.PLAY, index=0),
            self.energy_attach(1, a.BASIC_FIGHTING),
        ]
        obs = self.observation(
            hand_ids=(a.SURFER, a.BASIC_FIGHTING, a.ROCK_FIGHTING),
            options=options,
        )
        self.assertEqual(a.activate_ready_garchomp_index(obs), 2)
        self.assertEqual(a.choose_options(obs), [2])

    def test_legal_retreat_precedes_energy_attachment(self):
        a = self.v59
        obs = self.observation(
            hand_ids=(a.BASIC_FIGHTING,),
            options=[self.energy_attach(0, a.BASIC_FIGHTING), self.option(a.OptionType.RETREAT)],
        )
        self.assertEqual(a.activate_ready_garchomp_index(obs), 1)

    def test_basic_attach_precedes_rock_and_uses_lowest_basic_option_index(self):
        a = self.v59
        obs = self.observation(
            hand_ids=(a.ROCK_FIGHTING, a.BASIC_FIGHTING, a.BASIC_FIGHTING),
            options=[
                self.energy_attach(0, a.ROCK_FIGHTING),
                self.energy_attach(1, a.BASIC_FIGHTING),
                self.energy_attach(2, a.BASIC_FIGHTING),
            ],
        )
        self.assertEqual(a.activate_ready_garchomp_index(obs), 1)

    def test_rock_only_attachment_is_used(self):
        a = self.v59
        obs = self.observation(
            hand_ids=(a.ROCK_FIGHTING,),
            options=[self.energy_attach(0, a.ROCK_FIGHTING)],
        )
        self.assertEqual(a.activate_ready_garchomp_index(obs), 0)

    def test_immediate_ko_attack_vetoes_activation(self):
        a = self.v59
        obs = self.observation(
            active_id=a.ROSELIA,
            hand_ids=(a.SURFER,),
            opponent_hp=20,
            options=[
                self.option(a.OptionType.PLAY, index=0),
                self.option(a.OptionType.ATTACK, attack_id=a.SPIKE_STING),
            ],
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))

    def test_zero_energy_bench_garchomp_vetoes_activation(self):
        a = self.v59
        obs = self.observation(
            bench=[self.pokemon(a.GARCHOMP_EX)],
            hand_ids=(a.SURFER,),
            options=[self.option(a.OptionType.PLAY, index=0)],
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))

    def test_active_garchomp_vetoes_activation(self):
        a = self.v59
        obs = self.observation(
            active_id=a.GARCHOMP_EX,
            hand_ids=(a.SURFER,),
            options=[self.option(a.OptionType.PLAY, index=0)],
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))

    def test_unrelated_context_vetoes_activation(self):
        a = self.v59
        obs = self.observation(
            hand_ids=(a.SURFER,),
            options=[self.option(a.OptionType.PLAY, index=0)],
            context=a.SelectContext.TO_HAND,
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))

    def test_missing_opponent_active_or_legal_route_returns_none(self):
        a = self.v59
        with self.subTest(case="no opponent Active"):
            obs = self.observation(
                hand_ids=(a.SURFER,),
                options=[self.option(a.OptionType.PLAY, index=0)],
                opponent_active=False,
            )
            self.assertIsNone(a.activate_ready_garchomp_index(obs))
        with self.subTest(case="no route"):
            obs = self.observation(options=[self.option(a.OptionType.END)])
            self.assertIsNone(a.activate_ready_garchomp_index(obs))
        with self.subTest(case="attach targets Bench"):
            obs = self.observation(
                hand_ids=(a.BASIC_FIGHTING,),
                options=[self.option(
                    a.OptionType.ATTACH,
                    area=a.AreaType.HAND,
                    index=0,
                    in_play_area=a.AreaType.BENCH,
                    in_play_index=0,
                )],
            )
            self.assertIsNone(a.activate_ready_garchomp_index(obs))
        with self.subTest(case="one Energy cannot meet retreat cost"):
            card_data = a.CARD_DB[a.ROSERADE]
            original_retreat_cost = card_data.retreatCost
            try:
                card_data.retreatCost = 2
                obs = self.observation(
                    hand_ids=(a.BASIC_FIGHTING,),
                    options=[self.energy_attach(0, a.BASIC_FIGHTING)],
                )
                self.assertIsNone(a.activate_ready_garchomp_index(obs))
            finally:
                card_data.retreatCost = original_retreat_cost

    def test_episode_85836064_turn7_reconstruction_attaches_active_then_retreats(self):
        a = self.v59
        attach_state = self.observation(
            active_id=a.ROSERADE,
            hand_ids=(a.ROCK_FIGHTING, a.BASIC_FIGHTING),
            options=[
                self.energy_attach(0, a.ROCK_FIGHTING),
                self.energy_attach(1, a.BASIC_FIGHTING),
            ],
        )
        self.assertEqual(a.choose_options(attach_state), [1])

        retreat_state = self.observation(
            active_id=a.ROSERADE,
            active_energy_ids=(a.BASIC_FIGHTING,),
            hand_ids=(a.ROCK_FIGHTING,),
            options=[self.energy_attach(0, a.ROCK_FIGHTING), self.option(a.OptionType.RETREAT)],
        )
        self.assertEqual(a.choose_options(retreat_state), [1])

    def test_surfer_and_retreat_followups_promote_energized_garchomp(self):
        a = self.v59
        bench = [
            self.pokemon(a.ROSELIA, serial=21),
            self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING,), serial=22),
        ]
        options = [
            self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=0),
            self.option(a.OptionType.CARD, area=a.AreaType.BENCH, index=1),
        ]
        for context in (a.SelectContext.TO_ACTIVE, a.SelectContext.SWITCH):
            with self.subTest(context=context):
                obs = self.observation(bench=bench, options=options, context=context)
                self.assertEqual(a.choose_options(obs), [1])

    def test_candidate_deck_is_byte_identical_and_has_exactly_60_cards(self):
        baseline_main = (V58_DIR / "main.py").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V58_MAIN_SHA256)

        baseline_deck = (V58_DIR / "deck.csv").read_bytes()
        candidate_deck = (V59_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(len([line for line in candidate_deck.splitlines() if line.strip()]), 60)


if __name__ == "__main__":
    unittest.main()
