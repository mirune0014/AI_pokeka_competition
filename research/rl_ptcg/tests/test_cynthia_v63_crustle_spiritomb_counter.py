"""Focused contract checks for Cynthia Garchomp v63's Crustle counter-route."""

import ast
import copy
import hashlib
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
V58_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v58_core_bridge_before_chip"
V63_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v63_crustle_spiritomb_counter"
REPLAY_DIR = ROOT  / "_local_generated" / "analysis_outputs" / "kaggle_live" / "submission_54666167_cynthia_v58"
V58_MAIN_SHA256 = "8375c5e73d7ad9c1b4e863993a6cbe8bcc96668008bb3ae709b3dc62d6f8d25a"
DECK_SHA256 = "606b44f7d6181c57c6ccdd7ee493c72baf39e684b264886bc01631dbee8d349c"
REPLAY_CASES = {
    85857115: {
        "sha256": "cfc11d0880869d40b68c31f5a90d4cff4abbb9ce18a40e02ba0e0df07b97a366",
        "step": 64,
        "player": 0,
        "first_index": 2,
        "first_type": 7,
        "active_damage": 240,
        "crustle_hp": 190,
    },
    85853253: {
        "sha256": "2f0c890f03a885ab9bbb43080707d7d9afa6ea1e009a8e65b8647b03f56ed1fa",
        "step": 127,
        "player": 0,
        "first_index": 2,
        "first_type": 8,
        "active_damage": 220,
        "crustle_hp": 100,
    },
}
OPTION_FIELDS = (
    "area",
    "index",
    "playerIndex",
    "inPlayArea",
    "inPlayIndex",
    "attackId",
    "number",
)


def install_api_stub():
    api = types.ModuleType("cg.api")
    api.AreaType = types.SimpleNamespace(
        DECK=1, HAND=2, DISCARD=3, ACTIVE=4, BENCH=5, PRIZE=6, STADIUM=7,
        LOOKING=12,
    )
    api.OptionType = types.SimpleNamespace(
        NUMBER=0, YES=1, NO=2, CARD=3, TOOL_CARD=4, ENERGY_CARD=5, ENERGY=6,
        PLAY=7, ATTACH=8, EVOLVE=9, ABILITY=10, DISCARD=11, RETREAT=12,
        ATTACK=13, END=14,
    )
    api.SelectContext = types.SimpleNamespace(
        MAIN=0, SETUP_ACTIVE_POKEMON=1, SETUP_BENCH_POKEMON=2, SWITCH=3,
        TO_ACTIVE=4, TO_BENCH=5, TO_HAND=7, DISCARD=8, TO_DECK=9,
        TO_DECK_BOTTOM=10, DAMAGE=15, HEAL=17, ATTACH_FROM=21, ATTACH_TO=22,
        LOOK=24, DISCARD_CARD_OR_ATTACHED_CARD=29, IS_FIRST=41,
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


def to_object(value):
    if isinstance(value, dict):
        return types.SimpleNamespace(**{key: to_object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [to_object(item) for item in value]
    return value


class CrustleSpiritombCounterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        install_api_stub()
        cls.v58 = load_agent_module("cynthia_v58_for_v63_test", V58_DIR / "main.py")
        cls.v63 = load_agent_module("cynthia_v63_main", V63_DIR / "main.py")

    @staticmethod
    def pokemon(card_id, *, hp=70, max_hp=None, energy_ids=(), serial=None):
        max_hp = hp if max_hp is None else max_hp
        energy_cards = [
            types.SimpleNamespace(id=energy_id, serial=500 + index)
            for index, energy_id in enumerate(energy_ids)
        ]
        return types.SimpleNamespace(
            id=card_id,
            hp=hp,
            maxHp=max_hp,
            energies=[energy.id for energy in energy_cards],
            energyCards=energy_cards,
            tools=[],
            serial=serial,
            appearThisTurn=False,
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

    @staticmethod
    def replay_observation(episode_id, case):
        replay_path = REPLAY_DIR / f"episode_{episode_id}_replay.json"
        replay_bytes = replay_path.read_bytes()
        if hashlib.sha256(replay_bytes).hexdigest() != case["sha256"]:
            raise AssertionError(f"unexpected replay hash for {episode_id}")
        replay = json.loads(replay_bytes)
        raw = replay["steps"][case["step"]][case["player"]]["observation"]
        obs = to_object(raw)
        for option in obs.select.option:
            for field in OPTION_FIELDS:
                if not hasattr(option, field):
                    setattr(option, field, None)
        return obs

    @staticmethod
    def set_options(obs, options, context):
        obs.select.option = options
        obs.select.context = context
        obs.select.minCount = 1
        obs.select.maxCount = 1
        obs.select.effect = None
        obs.select.deck = []

    def assert_fails_closed(self, obs):
        self.assertIsNone(self.v63.crustle_spiritomb_counter_index(obs))
        self.assertEqual(self.v63.choose_options(obs), self.v58.choose_options(obs))

    def attach_selected_energy(self, obs, selected_index):
        a = self.v63
        option = obs.select.option[selected_index]
        self.assertEqual(option.type, a.OptionType.ATTACH)
        energy = a.option_card(obs, option)
        target = a.option_target(obs, option)
        self.assertIn(energy.id, a.ENERGIES)
        self.assertEqual(target.id, a.SPIRITOMB)
        target.energyCards = [energy]
        target.energies = [energy.id]
        a.me(obs).hand.pop(option.index)
        a.me(obs).handCount = len(a.me(obs).hand)
        obs.current.energyAttached = True

    def complete_route(self, source_obs, expected_first_index):
        a = self.v63
        obs = copy.deepcopy(source_obs)
        first_index = a.crustle_spiritomb_counter_index(obs)
        self.assertEqual(first_index, expected_first_index)
        self.assertEqual(a.choose_options(obs), [expected_first_index])
        first_option = obs.select.option[first_index]

        if first_option.type == a.OptionType.PLAY:
            spiritomb_card = a.option_card(obs, first_option)
            self.assertEqual(spiritomb_card.id, a.SPIRITOMB)
            a.me(obs).hand.pop(first_option.index)
            a.me(obs).handCount = len(a.me(obs).hand)
            a.me(obs).bench.append(self.pokemon(a.SPIRITOMB, serial=spiritomb_card.serial))
            spiritomb_index = len(a.me(obs).bench) - 1
            energy_index = next(
                index for index, card in enumerate(a.me(obs).hand)
                if card and card.id in a.ENERGIES
            )
            self.set_options(
                obs,
                [
                    self.option(
                        a.OptionType.ATTACH,
                        area=a.AreaType.HAND,
                        index=energy_index,
                        in_play_area=a.AreaType.ACTIVE,
                        in_play_index=0,
                    ),
                    self.option(
                        a.OptionType.ATTACH,
                        area=a.AreaType.HAND,
                        index=energy_index,
                        in_play_area=a.AreaType.BENCH,
                        in_play_index=spiritomb_index,
                    ),
                    self.option(a.OptionType.RETREAT),
                ],
                a.SelectContext.MAIN,
            )
            attach_index = 1
            self.assertEqual(a.crustle_spiritomb_counter_index(obs), attach_index)
        else:
            self.assertEqual(first_option.type, a.OptionType.ATTACH)
            attach_index = first_index

        self.attach_selected_energy(obs, attach_index)
        self.set_options(
            obs,
            [self.option(a.OptionType.END), self.option(a.OptionType.RETREAT)],
            a.SelectContext.MAIN,
        )
        self.assertEqual(a.crustle_spiritomb_counter_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])

        obs.current.retreated = True
        promotion_options = [
            self.option(
                a.OptionType.CARD,
                area=a.AreaType.BENCH,
                index=index,
                player_index=obs.current.yourIndex,
            )
            for index, _pokemon in enumerate(a.me(obs).bench)
        ]
        self.set_options(obs, promotion_options, a.SelectContext.SWITCH)
        promotion_index = next(
            index for index, option in enumerate(promotion_options)
            if getattr(a.option_card(obs, option), "id", None) == a.SPIRITOMB
            and a.energy_count(a.option_card(obs, option)) >= 1
        )
        self.assertEqual(a.crustle_spiritomb_counter_index(obs), promotion_index)
        self.assertEqual(a.choose_options(obs), [promotion_index])
        promotion_state = copy.deepcopy(obs)

        spiritomb_bench_index = promotion_options[promotion_index].index
        spiritomb = a.me(obs).bench.pop(spiritomb_bench_index)
        garchomp = a.me(obs).active[0]
        a.me(obs).active = [spiritomb]
        a.me(obs).bench.append(garchomp)
        self.set_options(
            obs,
            [
                self.option(a.OptionType.END),
                self.option(a.OptionType.ATTACK, attack_id=a.RAGING_CURSE),
            ],
            a.SelectContext.MAIN,
        )
        self.assertEqual(a.crustle_spiritomb_counter_index(obs), 1)
        self.assertEqual(a.choose_options(obs), [1])
        projected_damage = a.best_damage_for_active(obs, a.RAGING_CURSE)
        self.assertGreaterEqual(projected_damage, a.hp(a.opponent_active(obs)))
        return promotion_state, copy.deepcopy(obs)

    def test_two_frozen_live_surfaces_force_the_approved_first_step(self):
        a = self.v63
        expected_baseline = {85857115: [0], 85853253: [0]}
        for episode_id, case in REPLAY_CASES.items():
            with self.subTest(episode_id=episode_id):
                obs = self.replay_observation(episode_id, case)
                active = a.active_pokemon(obs)
                target = a.opponent_active(obs)

                self.assertEqual(obs.select.context, a.SelectContext.MAIN)
                self.assertEqual(active.id, a.GARCHOMP_EX)
                self.assertEqual(a.damage_on(active), case["active_damage"])
                self.assertEqual(target.id, 345)
                self.assertEqual(a.hp(target), case["crustle_hp"])
                self.assertFalse(obs.current.energyAttached)
                self.assertTrue(any(option.type == a.OptionType.RETREAT for option in obs.select.option))
                self.assertEqual(obs.select.option[case["first_index"]].type, case["first_type"])
                self.assertEqual(self.v58.choose_options(obs), expected_baseline[episode_id])
                self.assertEqual(a.crustle_spiritomb_counter_index(obs), case["first_index"])
                self.assertEqual(a.choose_options(obs), [case["first_index"]])

    def test_both_frozen_routes_reach_legal_lethal_raging_curse(self):
        for episode_id, case in REPLAY_CASES.items():
            with self.subTest(episode_id=episode_id):
                obs = self.replay_observation(episode_id, case)
                self.complete_route(obs, case["first_index"])

    def test_v58_energy_ordering_is_preserved_for_spiritomb(self):
        a = self.v63
        obs = self.replay_observation(85853253, REPLAY_CASES[85853253])
        player = a.me(obs)
        player.hand.append(self.pokemon(a.ROCK_FIGHTING, serial=999))
        player.handCount = len(player.hand)
        spiritomb_index = next(
            index for index, pokemon in enumerate(player.bench)
            if pokemon.id == a.SPIRITOMB
        )
        basic_index = next(index for index, card in enumerate(player.hand) if card.id == a.BASIC_FIGHTING)
        rock_index = next(index for index, card in enumerate(player.hand) if card.id == a.ROCK_FIGHTING)
        options = [
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=rock_index,
                in_play_area=a.AreaType.BENCH,
                in_play_index=spiritomb_index,
            ),
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=basic_index,
                in_play_area=a.AreaType.BENCH,
                in_play_index=spiritomb_index,
            ),
            self.option(a.OptionType.RETREAT),
        ]
        self.set_options(obs, options, a.SelectContext.MAIN)
        expected = max(range(2), key=lambda index: (self.v58.score_attach(obs, options[index])[0], -index))
        self.assertEqual(expected, 0)
        self.assertEqual(a.crustle_spiritomb_counter_index(obs), expected)

    def test_main_predicate_exclusions_fail_closed_to_v58(self):
        a = self.v63
        bench_state = self.replay_observation(85853253, REPLAY_CASES[85853253])
        hand_state = self.replay_observation(85857115, REPLAY_CASES[85857115])
        cases = {}

        obs = copy.deepcopy(bench_state)
        a.opponent_active(obs).id = 344
        cases["wrong defender"] = obs
        obs = copy.deepcopy(bench_state)
        a.active_pokemon(obs).id = a.GABITE
        cases["wrong active"] = obs
        obs = copy.deepcopy(bench_state)
        a.active_pokemon(obs).hp = a.active_pokemon(obs).maxHp
        cases["undamaged Garchomp"] = obs
        obs = copy.deepcopy(bench_state)
        a.opponent_active(obs).hp = 999
        cases["nonlethal projection"] = obs
        obs = copy.deepcopy(bench_state)
        a.me(obs).bench[1].id = a.ROSELIA
        cases["Spiritomb absent"] = obs
        obs = copy.deepcopy(hand_state)
        a.me(obs).bench.append(self.pokemon(9000, serial=999))
        cases["full Bench"] = obs
        obs = copy.deepcopy(hand_state)
        obs.select.option = [
            option for option in obs.select.option
            if not (
                option.type == a.OptionType.PLAY
                and getattr(a.option_card(obs, option), "id", None) == a.SPIRITOMB
            )
        ]
        cases["no direct Spiritomb PLAY"] = obs
        obs = copy.deepcopy(bench_state)
        obs.current.energyAttached = True
        cases["attachment already used"] = obs
        obs = copy.deepcopy(bench_state)
        obs.select.option = [
            option for option in obs.select.option
            if not (
                option.type == a.OptionType.ATTACH
                and getattr(a.option_target(obs, option), "id", None) == a.SPIRITOMB
            )
        ]
        cases["no legal Spiritomb attachment"] = obs
        obs = copy.deepcopy(hand_state)
        obs.select.option = [option for option in obs.select.option if option.type != a.OptionType.ATTACH]
        cases["no current normal attachment proof"] = obs
        obs = copy.deepcopy(bench_state)
        obs.select.option = [option for option in obs.select.option if option.type != a.OptionType.RETREAT]
        cases["no legal free retreat"] = obs
        obs = copy.deepcopy(bench_state)
        obs.select.context = a.SelectContext.LOOK
        cases["wrong context"] = obs
        obs = copy.deepcopy(hand_state)
        a.me(obs).hand = None
        cases["unobservable hand"] = obs
        obs = copy.deepcopy(bench_state)
        a.opponent(obs).active = []
        cases["no opposing active"] = obs

        for name, obs in cases.items():
            with self.subTest(name=name):
                self.assert_fails_closed(obs)

    def test_no_search_acceleration_switch_card_or_boss_substitute(self):
        a = self.v63
        obs = self.replay_observation(85857115, REPLAY_CASES[85857115])
        obs.select.option = [
            option for option in obs.select.option
            if option.type not in {a.OptionType.PLAY, a.OptionType.ATTACH, a.OptionType.RETREAT}
        ]
        obs.select.option.extend(
            [
                self.option(a.OptionType.PLAY, index=1),
                self.option(a.OptionType.PLAY, index=6),
                self.option(a.OptionType.END),
            ]
        )
        self.assert_fails_closed(obs)

    def test_promotion_revalidates_every_public_precondition(self):
        a = self.v63
        source = self.replay_observation(85853253, REPLAY_CASES[85853253])
        promotion, _attack = self.complete_route(source, REPLAY_CASES[85853253]["first_index"])
        cases = {}

        obs = copy.deepcopy(promotion)
        obs.current.retreated = False
        cases["not a retreat selection"] = obs
        obs = copy.deepcopy(promotion)
        obs.select.context = a.SelectContext.TO_ACTIVE
        cases["generic switch context"] = obs
        obs = copy.deepcopy(promotion)
        a.opponent_active(obs).id = 344
        cases["Crustle changed"] = obs
        obs = copy.deepcopy(promotion)
        a.active_pokemon(obs).hp = a.active_pokemon(obs).maxHp
        cases["Garchomp no longer damaged"] = obs
        obs = copy.deepcopy(promotion)
        spiritomb = next(pokemon for pokemon in a.me(obs).bench if pokemon.id == a.SPIRITOMB)
        spiritomb.energyCards = []
        spiritomb.energies = []
        cases["Spiritomb no longer energized"] = obs
        obs = copy.deepcopy(promotion)
        a.opponent_active(obs).hp = 999
        cases["promotion no longer lethal"] = obs
        obs = copy.deepcopy(promotion)
        obs.select.option = [
            option for option in obs.select.option
            if getattr(a.option_card(obs, option), "id", None) != a.SPIRITOMB
        ]
        cases["Spiritomb promotion not legal"] = obs

        for name, obs in cases.items():
            with self.subTest(name=name):
                self.assert_fails_closed(obs)

    def test_attack_revalidates_every_public_precondition(self):
        a = self.v63
        source = self.replay_observation(85853253, REPLAY_CASES[85853253])
        _promotion, attack = self.complete_route(source, REPLAY_CASES[85853253]["first_index"])
        cases = {}

        obs = copy.deepcopy(attack)
        obs.current.retreated = False
        cases["route retreat flag absent"] = obs
        obs = copy.deepcopy(attack)
        a.opponent_active(obs).id = 344
        cases["Crustle changed"] = obs
        obs = copy.deepcopy(attack)
        a.active_pokemon(obs).energyCards = []
        a.active_pokemon(obs).energies = []
        cases["Spiritomb unenergized"] = obs
        obs = copy.deepcopy(attack)
        a.opponent_active(obs).hp = 999
        cases["Raging Curse nonlethal"] = obs
        obs = copy.deepcopy(attack)
        obs.select.option[1].attackId = a.CORKSCREW_DIVE
        cases["Raging Curse not legal"] = obs
        obs = copy.deepcopy(attack)
        for pokemon in a.me(obs).bench:
            if pokemon.id == a.GARCHOMP_EX:
                pokemon.hp = pokemon.maxHp
        cases["no damaged Benched Garchomp"] = obs
        obs = copy.deepcopy(attack)
        a.active_pokemon(obs).id = a.ROSELIA
        cases["wrong attacker"] = obs

        for name, obs in cases.items():
            with self.subTest(name=name):
                self.assert_fails_closed(obs)

    def test_exact_v58_copy_except_isolated_helper_and_call_site(self):
        baseline_files = {
            path.relative_to(V58_DIR)
            for path in V58_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V63_DIR)
            for path in V63_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V58_DIR / "main.py").read_bytes()
        candidate_main = (V63_DIR / "main.py").read_bytes()
        self.assertEqual(hashlib.sha256(baseline_main).hexdigest(), V58_MAIN_SHA256)
        baseline_tree = ast.parse(baseline_main)
        candidate_tree = ast.parse(candidate_main)
        baseline_unchanged = [
            node for node in baseline_tree.body
            if not isinstance(node, ast.FunctionDef) or node.name != "choose_options"
        ]
        candidate_unchanged = [
            node for node in candidate_tree.body
            if not isinstance(node, ast.FunctionDef)
            or node.name not in {"crustle_spiritomb_counter_index", "choose_options"}
        ]
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_unchanged],
            [ast.dump(node, include_attributes=False) for node in baseline_unchanged],
        )

        baseline_choose = next(
            node for node in baseline_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        candidate_choose = next(
            node for node in candidate_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "choose_options"
        )
        expected_hook = ast.parse(
            "counter_index = crustle_spiritomb_counter_index(obs)\n"
            "if counter_index is not None:\n"
            "    return [counter_index]\n"
        ).body
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[:2]],
            [ast.dump(node, include_attributes=False) for node in expected_hook],
        )
        self.assertEqual(
            [ast.dump(node, include_attributes=False) for node in candidate_choose.body[2:]],
            [ast.dump(node, include_attributes=False) for node in baseline_choose.body],
        )

        helper_source = ast.get_source_segment(
            candidate_main.decode(),
            next(
                node for node in candidate_tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "crustle_spiritomb_counter_index"
            ),
        )
        for forbidden in ("85857115", "85853253", "TeamNames", "replay", "episode"):
            self.assertNotIn(forbidden, helper_source)

        baseline_deck = (V58_DIR / "deck.csv").read_bytes()
        candidate_deck = (V63_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(len([line for line in candidate_deck.splitlines() if line.strip()]), 60)


if __name__ == "__main__":
    unittest.main()
