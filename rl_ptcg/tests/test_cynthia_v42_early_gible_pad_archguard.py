"""Focused public-state checks for the Cynthia Garchomp v42 Archaludon guard."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v42_early_gible_pad_archguard"
BASELINE_DIR = ROOT / "meta_agents" / "cynthia_garchomp_nasuo445_v35_reliable_development_before_attack"


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
    spec = importlib.util.spec_from_file_location("cynthia_v42_main", AGENT_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExposedGiblePadToGabiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = load_agent_module()

    @staticmethod
    def card(card_id):
        return types.SimpleNamespace(id=card_id)

    @staticmethod
    def pokemon(card_id, *, hp=200, energies=(), appear_this_turn=False):
        return types.SimpleNamespace(id=card_id, hp=hp, energies=list(energies), serial=card_id, appearThisTurn=appear_this_turn)

    @staticmethod
    def option(kind, *, area=None, index=None, in_play_area=None, in_play_index=None, attack_id=None):
        return types.SimpleNamespace(type=kind, area=area, index=index, playerIndex=None, inPlayArea=in_play_area, inPlayIndex=in_play_index, attackId=attack_id)

    def main_obs(self, *, hand_ids=(), active_id=None, active_energies=(), gible_appeared=False, target_hp=200, opponent_active_id=999, context=None, options=None, turn=3):
        a = self.agent
        active_id = a.GIBLE if active_id is None else active_id
        hand = [self.card(card_id) for card_id in hand_ids]
        if options is None:
            options = [
                self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=0),
                self.option(a.OptionType.ATTACK, attack_id=a.ROCK_HURL),
            ]
        mine = types.SimpleNamespace(
            hand=hand,
            active=[self.pokemon(active_id, energies=active_energies, appear_this_turn=gible_appeared)],
            bench=[], discard=[], prize=[object()] * 6, stadium=[], deckCount=30,
        )
        foe = types.SimpleNamespace(hand=[], active=[self.pokemon(opponent_active_id, hp=target_hp)], bench=[], discard=[], prize=[])
        return types.SimpleNamespace(
            current=types.SimpleNamespace(yourIndex=0, players=[mine, foe], looking=[], stadium=[], turn=turn),
            select=types.SimpleNamespace(option=options, context=a.SelectContext.MAIN if context is None else context, minCount=1, maxCount=1, deck=[], effect=a.POKE_PAD),
        )

    def scored(self, obs):
        a = self.agent
        return [(a.score_option_with_champions_call_order(obs, option)[0], index, "v35") for index, option in enumerate(obs.select.option)]

    def test_deck_is_byte_identical_to_v35(self):
        deck = (AGENT_DIR / "deck.csv").read_bytes()
        self.assertEqual(deck, (BASELINE_DIR / "deck.csv").read_bytes())
        self.assertEqual(60, len([line for line in deck.splitlines() if line.strip()]))

    def test_eligible_exposed_gible_promotes_pad_over_low_attack_by_one(self):
        a = self.agent
        obs = self.main_obs(hand_ids=(a.POKE_PAD,))
        scored = self.scored(obs)
        self.assertEqual(1, max(scored, key=lambda row: (row[0], -row[1]))[1])
        self.assertEqual(0, a.exposed_gible_pokepad_index(obs, scored))
        self.assertEqual([0], a.choose_options(obs))

    def test_eligible_exposed_gible_promotes_pad_over_lower_value_setup_by_one(self):
        a = self.agent
        options = [
            self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=0),
            self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=1),
        ]
        obs = self.main_obs(hand_ids=(a.POKE_PAD, a.HILDA), options=options)
        scored = self.scored(obs)
        self.assertEqual(1, max(scored, key=lambda row: (row[0], -row[1]))[1])
        self.assertEqual(0, a.exposed_gible_pokepad_index(obs, scored))
        self.assertEqual([0], a.choose_options(obs))

    def test_newly_played_gible_does_not_trigger(self):
        a = self.agent
        obs = self.main_obs(hand_ids=(a.POKE_PAD,), gible_appeared=True)
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([1], a.choose_options(obs))

    def test_after_turn_three_does_not_trigger(self):
        a = self.agent
        obs = self.main_obs(hand_ids=(a.POKE_PAD,), turn=4)
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([1], a.choose_options(obs))

    def test_visible_archaludon_line_disables_pad_overlay(self):
        a = self.agent
        for opponent_id in (a.DURALUDON, a.ARCHALUDON_EX):
            with self.subTest(opponent_id=opponent_id):
                obs = self.main_obs(hand_ids=(a.POKE_PAD,), opponent_active_id=opponent_id)
                self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
                self.assertEqual([1], a.choose_options(obs))

    def test_gabite_already_in_hand_does_not_trigger(self):
        a = self.agent
        obs = self.main_obs(hand_ids=(a.POKE_PAD, a.GABITE))
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([1], a.choose_options(obs))

    def test_immediate_ko_does_not_trigger(self):
        a = self.agent
        obs = self.main_obs(hand_ids=(a.POKE_PAD,), target_hp=20)
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([1], a.choose_options(obs))

    def test_active_garchomp_completion_attachment_does_not_trigger(self):
        a = self.agent
        options = [
            self.option(a.OptionType.PLAY, area=a.AreaType.HAND, index=0),
            self.option(a.OptionType.ATTACH, area=a.AreaType.HAND, index=1, in_play_area=a.AreaType.ACTIVE, in_play_index=0),
        ]
        obs = self.main_obs(hand_ids=(a.POKE_PAD, a.BASIC_FIGHTING), active_id=a.GARCHOMP_EX, active_energies=(a.BASIC_FIGHTING,), options=options)
        obs.current.players[0].bench = [self.pokemon(a.GIBLE, appear_this_turn=False)]
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([1], a.choose_options(obs))

    def test_no_legal_pad_does_not_trigger(self):
        a = self.agent
        options = [self.option(a.OptionType.ATTACK, attack_id=a.ROCK_HURL)]
        obs = self.main_obs(hand_ids=(), options=options)
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([0], a.choose_options(obs))

    def test_non_main_context_does_not_trigger_and_inherited_pad_target_prefers_gabite(self):
        a = self.agent
        target_options = [
            self.option(a.OptionType.CARD, area=a.AreaType.DECK, index=0),
            self.option(a.OptionType.CARD, area=a.AreaType.DECK, index=1),
        ]
        obs = self.main_obs(context=a.SelectContext.TO_HAND, options=target_options)
        obs.select.deck = [self.card(a.GIBLE), self.card(a.GABITE)]
        self.assertIsNone(a.exposed_gible_pokepad_index(obs, self.scored(obs)))
        self.assertEqual([1], a.choose_options(obs))


if __name__ == "__main__":
    unittest.main()
