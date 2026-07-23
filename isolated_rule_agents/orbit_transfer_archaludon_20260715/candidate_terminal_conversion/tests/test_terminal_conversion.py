"""Focused checks for the fail-closed terminal-conversion rule."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
BASELINE_DIR = CANDIDATE_DIR.parent / "baseline_exact"
PLAIN_TARGET = 9001
METAL_TARGET = 9002
METAL_RESIST_TARGET = 9003
RISKY_TOOL = 9004


def load_agent(name, directory):
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location(name, directory / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def skill(name, text):
    return types.SimpleNamespace(name=name, text=text)


def card_data(card_id, *, energy_type=3, resistance=None, ex=False, skills=()):
    return types.SimpleNamespace(
        cardId=card_id,
        energyType=energy_type,
        resistance=resistance,
        ex=ex,
        megaEx=False,
        attacks=[],
        skills=list(skills),
        retreatCost=1,
    )


class TerminalConversionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = load_agent("orbit_terminal_baseline", BASELINE_DIR)
        cls.agent = load_agent("orbit_terminal_candidate", CANDIDATE_DIR)
        additions = {
            PLAIN_TARGET: card_data(PLAIN_TARGET),
            METAL_TARGET: card_data(METAL_TARGET, energy_type=cls.agent.METAL_ENERGY),
            METAL_RESIST_TARGET: card_data(
                METAL_RESIST_TARGET,
                resistance=cls.agent.METAL_ENERGY,
            ),
            RISKY_TOOL: card_data(
                RISKY_TOOL,
                skills=(skill("Barrier Tool", "This Pokemon takes 30 less damage from attacks."),),
            ),
        }
        cls.agent.CARD_DB.update(additions)
        cls.baseline.CARD_DB.update(additions)

    @staticmethod
    def card(card_id, serial=1):
        return types.SimpleNamespace(id=card_id, serial=serial, playerIndex=0)

    @staticmethod
    def pokemon(card_id, hp, max_hp=None, *, tools=(), energy_cards=()):
        return types.SimpleNamespace(
            id=card_id,
            serial=card_id,
            hp=hp,
            maxHp=max_hp if max_hp is not None else hp,
            appearThisTurn=False,
            energies=[],
            energyCards=list(energy_cards),
            tools=list(tools),
            preEvolution=[],
        )

    @staticmethod
    def option(option_type, *, index=None, attack_id=None):
        return types.SimpleNamespace(
            type=option_type,
            number=None,
            area=None,
            index=index,
            playerIndex=None,
            inPlayArea=None,
            inPlayIndex=None,
            attackId=attack_id,
            cardId=None,
        )

    def observation(
        self,
        *,
        active=None,
        target=None,
        prizes=1,
        attack_id=None,
        stadium=(),
        include_play=True,
    ):
        a = self.agent
        active = active or self.pokemon(a.DURALUDON, 130, 130)
        target = target or self.pokemon(PLAIN_TARGET, 30, 300)
        play = self.option(a.OptionType.PLAY, index=0)
        attack = self.option(a.OptionType.ATTACK, attack_id=attack_id or 223)
        end = self.option(a.OptionType.END)
        options = ([play] if include_play else []) + [attack, end]

        def player(active_pokemon, *, hand, prize):
            return types.SimpleNamespace(
                active=[active_pokemon],
                bench=[],
                benchMax=5,
                deckCount=40,
                discard=[],
                prize=[None] * prize,
                handCount=len(hand) if hand is not None else 0,
                hand=hand,
                poisoned=False,
                burned=False,
                asleep=False,
                paralyzed=False,
                confused=False,
            )

        me = player(active, hand=[self.card(a.FULL_METAL_LAB)], prize=prizes)
        foe = player(target, hand=None, prize=6)
        current = types.SimpleNamespace(
            turn=9,
            turnActionCount=0,
            yourIndex=0,
            firstPlayer=0,
            supporterPlayed=False,
            stadiumPlayed=False,
            energyAttached=False,
            retreated=False,
            result=-1,
            stadium=list(stadium),
            looking=None,
            players=[me, foe],
        )
        select = types.SimpleNamespace(
            context=a.SelectContext.MAIN,
            minCount=1,
            maxCount=1,
            option=options,
            deck=[],
            effect=None,
        )
        return types.SimpleNamespace(current=current, select=select, logs=[])

    def attack_option(self, obs):
        return next(option for option in obs.select.option if option.type == self.agent.OptionType.ATTACK)

    def assert_play_remains_first(self, obs):
        self.assertEqual(self.agent.choose_options(obs), [0])
        attack = self.attack_option(obs)
        self.assertLess(self.agent.score_option(obs, attack)[0], 20000)

    def test_exact_final_prize_lethal_outranks_high_score_nonattack(self):
        obs = self.observation()
        self.assertEqual(self.baseline.choose_options(obs), [0])
        self.assertEqual(self.agent.choose_options(obs), [1])
        self.assertEqual(self.agent.terminal_conversion_surplus(obs, self.attack_option(obs)), 0)

    def test_nonfinal_ko_and_short_damage_do_not_trigger(self):
        nonfinal = self.observation(prizes=2)
        self.assert_play_remains_first(nonfinal)

        short = self.observation(target=self.pokemon(PLAIN_TARGET, 31, 300))
        self.assert_play_remains_first(short)

    def test_confused_asleep_and_paralyzed_do_not_trigger(self):
        for status in ("confused", "asleep", "paralyzed"):
            with self.subTest(status=status):
                obs = self.observation()
                setattr(obs.current.players[0], status, True)
                self.assert_play_remains_first(obs)

    def test_full_metal_lab_and_resistance_prevent_marginal_false_certificate(self):
        lab = self.observation(
            target=self.pokemon(METAL_TARGET, 10, 300),
            stadium=[self.card(self.agent.FULL_METAL_LAB, 2)],
        )
        self.assertEqual(
            self.agent.conservative_terminal_damage(lab, self.agent.opp_active_pokemon(lab), 223),
            0,
        )
        self.assert_play_remains_first(lab)

        resistant = self.observation(target=self.pokemon(METAL_RESIST_TARGET, 10, 300))
        self.assertEqual(
            self.agent.conservative_terminal_damage(
                resistant,
                self.agent.opp_active_pokemon(resistant),
                223,
            ),
            0,
        )
        self.assert_play_remains_first(resistant)

    def test_visible_prevention_and_risky_effects_fail_closed(self):
        for card_id in (117, 345):
            with self.subTest(card_id=card_id):
                obs = self.observation(target=self.pokemon(card_id, 30, 300))
                self.assertIsNone(
                    self.agent.conservative_terminal_damage(obs, self.agent.opp_active_pokemon(obs), 223)
                )
                self.assert_play_remains_first(obs)

        protected = self.observation()
        self.agent.opp_active_pokemon(protected).protection = "unknown public protection"
        self.assert_play_remains_first(protected)

        risky_tool = self.card(RISKY_TOOL, 3)
        risky = self.observation(
            target=self.pokemon(PLAIN_TARGET, 30, 300, tools=[risky_tool])
        )
        self.assert_play_remains_first(risky)

    def test_ongoing_coated_attack_prevention_fails_closed_for_basic_active(self):
        previous = self.agent._opp_last_attack_id
        try:
            self.agent._opp_last_attack_id = self.agent.COATED_ATTACK
            self.assert_play_remains_first(self.observation())
        finally:
            self.agent._opp_last_attack_id = previous

    def test_raging_hammer_uses_current_damage(self):
        active = self.pokemon(self.agent.DURALUDON, 70, 130)
        target = self.pokemon(PLAIN_TARGET, 140, 300)
        obs = self.observation(active=active, target=target, attack_id=self.agent.RAGING_HAMMER)
        attack = self.attack_option(obs)
        self.assertEqual(self.agent.conservative_terminal_damage(obs, target, attack.attackId), 140)
        self.assertEqual(self.agent.choose_options(obs), [1])

    def test_certified_attacks_tie_by_surplus_then_existing_order(self):
        a = self.agent
        obs = self.observation(target=self.pokemon(PLAIN_TARGET, 30, 300), include_play=False)
        hammer = self.option(a.OptionType.ATTACK, attack_id=223)
        raging = self.option(a.OptionType.ATTACK, attack_id=a.RAGING_HAMMER)
        end = self.option(a.OptionType.END)
        obs.select.option = [hammer, raging, end]
        self.assertEqual(a.choose_options(obs), [1])

        earlier = self.option(a.OptionType.ATTACK, attack_id=223)
        later = self.option(a.OptionType.ATTACK, attack_id=223)
        obs.select.option = [earlier, later, end]
        self.assertEqual(a.choose_options(obs), [0])

    def test_trigger_free_scores_match_exact_baseline_and_certificate_is_recomputed(self):
        obs = self.observation(prizes=2)
        for option in obs.select.option:
            with self.subTest(option_type=option.type):
                self.assertEqual(
                    self.agent.score_option(obs, option),
                    self.baseline.score_option(obs, option),
                )

        obs.current.players[0].prize = [None]
        self.assertGreater(self.agent.score_option(obs, self.attack_option(obs))[0], 20000)
        obs.current.players[0].prize = [None, None]
        self.assertEqual(
            self.agent.score_option(obs, self.attack_option(obs)),
            self.baseline.score_option(obs, self.attack_option(obs)),
        )


if __name__ == "__main__":
    unittest.main()
