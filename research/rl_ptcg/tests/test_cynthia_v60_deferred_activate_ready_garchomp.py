"""Focused contract checks for Cynthia Garchomp v60's deferred activation."""

import hashlib
import unittest
from pathlib import Path

from research.rl_ptcg.tests import test_cynthia_v59_activate_ready_garchomp as v59_contract


ROOT = Path(__file__).resolve().parents[3]
V59_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v59_activate_ready_garchomp"
V60_DIR = ROOT / "opponents" / "meta_agents" / "cynthia_garchomp_nasuo445_v60_deferred_activate_ready_garchomp"
V59_MAIN_SHA256 = "e72159dd9ff66a7be61ae9afefa79d7b23b8ea9a5f7dbb4559e0eaf416f0e4ad"
DECK_SHA256 = "606b44f7d6181c57c6ccdd7ee493c72baf39e684b264886bc01631dbee8d349c"


class DeferredActivateReadyGarchompTest(v59_contract.ActivateReadyGarchompTest):
    """Run the complete v59 contract against v60, then check the new guard."""

    @classmethod
    def setUpClass(cls):
        v59_contract.install_api_stub()
        cls.v59 = v59_contract.load_agent_module("cynthia_v60_main", V60_DIR / "main.py")

    def test_legal_roserade_evolution_defers_activation(self):
        a = self.v59
        options = [
            self.option(a.OptionType.PLAY, index=0),
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.ACTIVE,
                in_play_index=0,
            ),
        ]
        obs = self.observation(
            active_id=a.ROSELIA,
            hand_ids=(a.SURFER, a.ROSERADE),
            options=options,
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))
        self.assertEqual(a.choose_options(obs), [1])

    def test_legal_gabite_evolution_defers_activation(self):
        a = self.v59
        bench = [
            self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING,), serial=20),
            self.pokemon(a.GIBLE, serial=21),
        ]
        options = [
            self.option(a.OptionType.PLAY, index=0),
            self.option(
                a.OptionType.EVOLVE,
                area=a.AreaType.HAND,
                index=1,
                in_play_area=a.AreaType.BENCH,
                in_play_index=1,
            ),
        ]
        obs = self.observation(
            bench=bench,
            hand_ids=(a.SURFER, a.GABITE),
            options=options,
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))
        self.assertEqual(a.choose_options(obs), [1])

    def test_legal_champions_call_defers_activation(self):
        a = self.v59
        bench = [
            self.pokemon(a.GARCHOMP_EX, (a.BASIC_FIGHTING,), serial=20),
            self.pokemon(a.GABITE, serial=21),
        ]
        options = [
            self.option(a.OptionType.PLAY, index=0),
            self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=1),
        ]
        obs = self.observation(
            bench=bench,
            hand_ids=(a.SURFER,),
            options=options,
        )
        self.assertIsNone(a.activate_ready_garchomp_index(obs))
        self.assertEqual(a.choose_options(obs), [1])

    def test_activation_resumes_after_structural_options_disappear(self):
        a = self.v59
        cases = {
            "Surfer": self.observation(
                hand_ids=(a.SURFER,),
                options=[self.option(a.OptionType.PLAY, index=0)],
            ),
            "retreat": self.observation(
                options=[self.option(a.OptionType.RETREAT)],
            ),
            "Basic attach": self.observation(
                hand_ids=(a.BASIC_FIGHTING,),
                options=[self.energy_attach(0, a.BASIC_FIGHTING)],
            ),
        }
        for route, obs in cases.items():
            with self.subTest(route=route):
                self.assertEqual(a.activate_ready_garchomp_index(obs), 0)
                self.assertEqual(a.choose_options(obs), [0])

    def test_non_structural_legal_actions_do_not_defer_activation(self):
        a = self.v59
        options = [
            self.option(a.OptionType.PLAY, index=1),
            self.option(
                a.OptionType.ATTACH,
                area=a.AreaType.HAND,
                index=3,
                in_play_area=a.AreaType.BENCH,
                in_play_index=0,
            ),
            self.option(a.OptionType.PLAY, index=2),
            self.option(a.OptionType.ATTACK, attack_id=a.LEAF_STEP),
            self.option(a.OptionType.ABILITY, area=a.AreaType.BENCH, index=0),
            self.option(a.OptionType.PLAY, index=0),
        ]
        obs = self.observation(
            hand_ids=(a.SURFER, a.GIBLE, a.HILDA, a.BASIC_FIGHTING),
            options=options,
        )
        self.assertEqual(a.activate_ready_garchomp_index(obs), 5)
        self.assertEqual(a.choose_options(obs), [5])

    def test_candidate_deck_is_byte_identical_and_has_exactly_60_cards(self):
        baseline_files = {
            path.relative_to(V59_DIR)
            for path in V59_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        candidate_files = {
            path.relative_to(V60_DIR)
            for path in V60_DIR.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        self.assertEqual(candidate_files, baseline_files)

        baseline_main = (V59_DIR / "main.py").read_text()
        candidate_main = (V60_DIR / "main.py").read_text()
        self.assertEqual(hashlib.sha256((V59_DIR / "main.py").read_bytes()).hexdigest(), V59_MAIN_SHA256)
        old = '    options = getattr(obs.select, "option", None) or []\n    for index, option in enumerate(options):\n'
        new = '''    options = getattr(obs.select, "option", None) or []
    if any(
        option.type == OptionType.EVOLVE
        or (
            option.type == OptionType.ABILITY
            and getattr(option_card(obs, option), "id", None) == GABITE
        )
        for option in options
    ):
        return None
    for index, option in enumerate(options):
'''
        self.assertEqual(baseline_main.count(old), 1)
        self.assertEqual(candidate_main, baseline_main.replace(old, new, 1))

        baseline_deck = (V59_DIR / "deck.csv").read_bytes()
        candidate_deck = (V60_DIR / "deck.csv").read_bytes()
        self.assertEqual(candidate_deck, baseline_deck)
        self.assertEqual(hashlib.sha256(candidate_deck).hexdigest(), DECK_SHA256)
        self.assertEqual(len([line for line in candidate_deck.splitlines() if line.strip()]), 60)


if __name__ == "__main__":
    unittest.main()
