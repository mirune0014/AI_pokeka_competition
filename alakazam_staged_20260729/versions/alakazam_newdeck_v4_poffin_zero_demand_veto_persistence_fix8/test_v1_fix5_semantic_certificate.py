from __future__ import annotations

import copy
from dataclasses import replace
import unittest

from cg.api import CardType, EnergyType, Option, Pokemon, Skill

import planner_deck_adaptation_v1 as v1
import test_v1_runtime_completion as runtime_tests


class V1Fix5SemanticCertificateTests(unittest.TestCase):
    def setUp(self):
        self.rt = runtime_tests.V1RuntimeCompletionTests(methodName="runTest")
        self.rt.setUp()
        self.fx = self.rt.fx
        self.policy = self.rt.policy

    def tearDown(self):
        self.rt.tearDown()

    def articuno(self, serial=600):
        return Pokemon(414, serial, 120, 120, False, [], [], [], [])

    def mewtwo(self, serial=601, *, energy=None):
        energies = [] if energy is None else [EnergyType.COLORLESS]
        cards = [] if energy is None else [energy]
        return Pokemon(431, serial, 100, 280, False, energies, cards, [], [])

    def main_with_target(self, target, *, hand_count=15, bench=()):
        obs, _ = self.fx.main_obs(
            hand_ids=[1152] * hand_count,
            target_hp=100,
            options_card_ids=[],
        )
        obs.current.players[1].active = [target]
        obs.current.players[1].bench = list(bench)
        return obs

    def candidate(self, function, obs):
        public = v1._main_envelope(self.policy, obs)
        self.assertIsNotNone(public)
        snap = v1.model.public_snapshot(self.policy, obs)
        self.assertIsNotNone(snap)
        return function(self.policy, obs, snap, public)

    def hammer_observation(self, target):
        obs, _ = self.fx.main_obs(
            hand_ids=[1081] + [1152] * 7,
            target_hp=140,
            options_card_ids=[1081],
        )
        obs.current.players[1].active = [target]
        return obs

    def test_hammer_precomputes_grass_and_preserves_non_grass_and_cape(self):
        grow = self.fx.card(18, 1, 501)
        crustle = Pokemon(
            345, 500, 140, 170, False,
            [EnergyType.GRASS], [grow], [], [],
        )
        candidate = self.candidate(v1._candidate_hammer, self.hammer_observation(crustle))
        self.assertIsNotNone(candidate)
        transaction = candidate[1]
        self.assertEqual(transaction["energy_area"], int(self.policy.AreaType.ACTIVE))
        self.assertEqual(transaction["pokemon_index"], 0)
        self.assertEqual(transaction["pokemon_serial"], 500)
        self.assertEqual(transaction["energy_index"], 0)
        self.assertEqual(
            (transaction["energy_id"], transaction["energy_serial"], transaction["energy_owner"]),
            (18, 501, 1),
        )
        self.assertEqual(transaction["target_before_fingerprint"][2:4], (140, 170))
        self.assertEqual(transaction["target_expected_after_fingerprint"][2:4], (120, 150))
        self.assertEqual(transaction["target_expected_after_fingerprint"][6:8], ((), ()))

        for tools, maximum in (([], 300), ([self.fx.card(1159, 1, 502)], 400)):
            with self.subTest(hero_cape=bool(tools)):
                kangaskhan = Pokemon(
                    756, 510, 140, maximum, False,
                    [EnergyType.GRASS], [grow], tools, [],
                )
                public = v1._public_state(
                    self.policy, self.hammer_observation(kangaskhan)
                )
                certificate = v1._hammer_target_certificate(
                    self.policy,
                    public,
                    0,
                    self.policy.AreaType.ACTIVE,
                    0,
                    kangaskhan,
                    0,
                    grow,
                )
                self.assertIsNotNone(certificate)
                self.assertEqual(certificate[1][2:4], (140, maximum))

    def test_hammer_target_metadata_is_fail_closed_before_play(self):
        grow = self.fx.card(18, 1, 521)
        target = Pokemon(
            345, 520, 140, 170, False,
            [EnergyType.GRASS], [grow], [], [],
        )
        original = self.policy.card_table[345]
        mutations = {
            "missing": None,
            "card_id": replace(original, cardId=999),
            "card_type": replace(original, cardType=CardType.ITEM),
            "missing_energy_type": replace(original, energyType=None),
            "boolean_energy_type": replace(original, energyType=True),
            "out_of_enum_energy_type": replace(original, energyType=99),
        }
        try:
            for name, mutated in mutations.items():
                with self.subTest(mutation=name):
                    if mutated is None:
                        self.policy.card_table.pop(345, None)
                    else:
                        self.policy.card_table[345] = mutated
                    obs = self.hammer_observation(copy.deepcopy(target))
                    public = v1._main_envelope(self.policy, obs)
                    if public is not None:
                        snap = v1.model.public_snapshot(self.policy, obs)
                        self.assertIsNone(
                            v1._candidate_hammer(self.policy, obs, snap, public)
                        )
                    self.policy.card_table[345] = original
        finally:
            self.policy.card_table[345] = original

        invalid_hp = copy.deepcopy(target)
        invalid_hp.hp = 20
        invalid_hp.maxHp = 40
        self.assertIsNone(
            self.candidate(v1._candidate_hammer, self.hammer_observation(invalid_hp))
        )

    def test_hammer_duplicate_target_serial_is_nonfire(self):
        grow = self.fx.card(18, 1, 531)
        target = Pokemon(
            345, 530, 140, 170, False,
            [EnergyType.GRASS], [grow], [], [],
        )
        obs = self.hammer_observation(target)
        duplicate = Pokemon(140, 530, 100, 210, False, [], [], [], [])
        obs.current.players[1].bench = [duplicate]
        self.assertIsNone(v1._main_envelope(self.policy, obs))
        self.assertEqual(self.fx.call(obs, [2]), [2])
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_hammer_advance_binds_before_and_every_energy_field(self):
        start, child, _ = self.rt.hammer_chain()
        self.assertEqual(self.rt.invoke(start, [1], 1), [0])
        base = copy.deepcopy(v1.V1_TRANSACTION)
        self.assertIsNotNone(v1._advance_hammer(self.policy, child, copy.deepcopy(base)))

        changed_before = copy.deepcopy(base)
        values = list(changed_before["target_before_fingerprint"])
        values[2] += 1
        changed_before["target_before_fingerprint"] = tuple(values)
        self.assertIsNone(v1._advance_hammer(self.policy, child, changed_before))

        mutations = {
            "index": lambda obs: setattr(obs.select.option[0], "energyIndex", 1),
            "owner": lambda obs: setattr(obs.select.option[0], "playerIndex", 0),
            "field_index": lambda obs: setattr(obs.select.option[0], "index", 1),
            "serial": lambda obs: setattr(
                obs.current.players[1].active[0].energyCards[0], "serial", 9999
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                malformed = copy.deepcopy(child)
                mutate(malformed)
                self.assertIsNone(
                    v1._advance_hammer(self.policy, malformed, copy.deepcopy(base))
                )

    def test_hammer_verifier_uses_stored_expected_and_rejects_mutations(self):
        start, child, verify = self.rt.hammer_chain()
        self.assertEqual(self.rt.invoke(start, [1], 1), [0])
        self.assertEqual(self.rt.invoke(child, [0], 0), [0])
        transaction = copy.deepcopy(v1.V1_TRANSACTION)
        original_helper = v1._fingerprint_without_energy
        v1._fingerprint_without_energy = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("verifier recomputed removal semantics")
        )
        try:
            self.assertTrue(v1._verify_hammer(self.policy, verify, transaction))
        finally:
            v1._fingerprint_without_energy = original_helper

        changed_expected = copy.deepcopy(transaction)
        values = list(changed_expected["target_expected_after_fingerprint"])
        values[2] += 1
        changed_expected["target_expected_after_fingerprint"] = tuple(values)
        self.assertFalse(v1._verify_hammer(self.policy, verify, changed_expected))

        unexpected_row = copy.deepcopy(verify)
        unexpected_row.current.players[1].bench.append(
            Pokemon(140, 7777, 100, 210, False, [], [], [], [])
        )
        self.assertFalse(v1._verify_hammer(self.policy, unexpected_row, transaction))

    def test_repelling_veil_exact_active_and_bench_sources(self):
        target = self.mewtwo()
        for area in ("active", "bench"):
            with self.subTest(source_area=area):
                obs = self.main_with_target(target)
                if area == "active":
                    obs.current.players[1].active = [self.articuno()]
                    obs.current.players[1].bench = [target]
                else:
                    obs.current.players[1].bench = [self.articuno()]
                self.assertIs(
                    v1._repelling_veil_state(self.policy, obs.current, target, 1),
                    True,
                )

    def test_repelling_veil_blocks_all_five_powerful_hand_certificate_sites(self):
        energy = self.fx.card(11, 1, 611)
        target = self.mewtwo(610, energy=energy)
        obs = self.main_with_target(target, bench=[self.articuno(612)])
        self.assertFalse(v1._powerful_hand_ko(self.policy, obs, 15))
        self.assertFalse(
            v1._hammer_enables_current_ko(
                self.policy, obs, self.policy.AreaType.ACTIVE, target, 0
            )
        )

        target_obs = self.main_with_target(self.articuno(613))
        target_obs.current.players[1].bench = [self.mewtwo(614)]
        self.assertFalse(
            v1._target_powerful_hand_ko(
                self.policy, target_obs, target_obs.current.players[1].bench[0], 15
            )
        )

        active_obs, _ = self.fx.main_obs(
            hand_ids=[743] + [1152] * 13,
            target_hp=100,
            options_card_ids=[],
        )
        active_obs.current.players[0].active = [self.fx.kadabra(False)]
        active_obs.current.players[1].active = [self.mewtwo(620)]
        active_obs.current.players[1].bench = [self.articuno(621)]
        active_obs.select.option = [
            Option(
                self.policy.OptionType.EVOLVE,
                area=self.policy.AreaType.HAND,
                index=0,
                inPlayArea=self.policy.AreaType.ACTIVE,
                inPlayIndex=0,
            ),
            Option(self.policy.OptionType.END),
        ]
        self.assertIsNone(self.candidate(v1._candidate_alakazam, active_obs))
        active_obs.current.players[1].bench = []
        self.assertIsNotNone(self.candidate(v1._candidate_alakazam, active_obs))

        ready_obs, _ = self.fx.bench_alakazam_observation()
        while ready_obs.current.players[0].handCount < 14:
            ready_obs.current.players[0].hand.append(
                self.fx.card(1152, 0, 8000 + ready_obs.current.players[0].handCount)
            )
            ready_obs.current.players[0].handCount += 1
        ready_obs.current.players[1].active = [self.mewtwo(630)]
        ready_obs.current.players[1].bench = [self.articuno(631)]
        self.assertIsNone(
            self.candidate(v1._candidate_alakazam_ready_bench, ready_obs)
        )
        ready_obs.current.players[1].bench = []
        self.assertIsNotNone(
            self.candidate(v1._candidate_alakazam_ready_bench, ready_obs)
        )

    def test_no_articuno_control_and_attacking_side_articuno_do_not_block(self):
        target = self.mewtwo()
        obs = self.main_with_target(target)
        self.assertTrue(v1._powerful_hand_ko(self.policy, obs, 15))
        obs.current.players[0].bench = [self.articuno(650)]
        self.assertIs(
            v1._repelling_veil_state(self.policy, obs.current, target, 1),
            False,
        )
        self.assertTrue(
            v1._v1_powerful_hand_target_is_publicly_clear(
                self.policy, obs.current, target, 1
            )
        )

    def test_non_team_rocket_basic_and_evolved_team_rocket_are_not_protected(self):
        source = self.articuno()
        ordinary = Pokemon(140, 660, 100, 210, False, [], [], [], [])
        obs = self.main_with_target(ordinary, bench=[source])
        self.assertIs(
            v1._repelling_veil_state(self.policy, obs.current, ordinary, 1),
            False,
        )
        evolved = Pokemon(
            401, 661, 100, 130, False, [], [], [],
            [self.fx.card(400, 1, 662)],
        )
        obs.current.players[1].active = [evolved]
        self.assertIs(
            v1._repelling_veil_state(self.policy, obs.current, evolved, 1),
            False,
        )

    def test_articuno_metadata_mutations_and_malformed_public_source_fail_closed(self):
        target = self.mewtwo()
        obs = self.main_with_target(target, bench=[self.articuno()])
        original = self.policy.card_table[414]
        skill = original.skills[0]
        mutations = {
            "card_id": replace(original, cardId=999),
            "name": replace(original, name="Team Rocket Articuno"),
            "skill_name": replace(original, skills=[replace(skill, name="Repelling Veil")]),
            "skill_text": replace(original, skills=[replace(skill, text=skill.text + " ")]),
            "skill_count": replace(original, skills=[skill, copy.deepcopy(skill)]),
            "basic": replace(original, basic=False),
            "card_type": replace(original, cardType=CardType.ITEM),
        }
        try:
            for name, mutated in mutations.items():
                with self.subTest(mutation=name):
                    self.policy.card_table[414] = mutated
                    self.assertIsNone(
                        v1._repelling_veil_state(
                            self.policy, obs.current, target, 1
                        )
                    )
        finally:
            self.policy.card_table[414] = original
        obs.current.players[1].bench[0].hp = 0
        self.assertIsNone(
            v1._repelling_veil_state(self.policy, obs.current, target, 1)
        )

    def test_team_rocket_name_near_misses_and_skill_text_only_do_not_classify(self):
        target = self.mewtwo()
        obs = self.main_with_target(target, bench=[self.articuno()])
        original = self.policy.card_table[431]
        near_misses = (
            "Team Rocket Mewtwo ex",
            "Team Rocket\u2019s Mewtwo ex".replace("\x19", "\u2019"),
            "Mewtwo ex Team Rocket",
            "Team Rocket's ",
        )
        try:
            for name in near_misses:
                with self.subTest(name=name):
                    self.policy.card_table[431] = replace(original, name=name)
                    self.assertIs(
                        v1._repelling_veil_state(
                            self.policy, obs.current, target, 1
                        ),
                        False,
                    )
            ordinary = Pokemon(140, 680, 100, 210, False, [], [], [], [])
            ordinary_data = self.policy.card_table[140]
            self.policy.card_table[140] = replace(
                ordinary_data,
                skills=[Skill("Mention", "Basic Team Rocket's Pokemon")],
            )
            self.assertIs(
                v1._repelling_veil_state(
                    self.policy, obs.current, ordinary, 1
                ),
                False,
            )
            self.policy.card_table[140] = ordinary_data
        finally:
            self.policy.card_table[431] = original

    def test_protected_boss_never_starts_transaction(self):
        target = self.mewtwo(701)
        obs, _ = self.fx.main_obs(
            hand_ids=[1182] + [1152] * 14,
            target_hp=200,
            opponent_bench=[target],
            options_card_ids=[1182],
        )
        obs.current.players[0].prize = [None, None]
        obs.current.players[1].active = [self.articuno(702)]
        self.assertIsNone(self.candidate(v1._candidate_boss, obs))
        fallback = [len(obs.select.option) - 1]
        self.assertEqual(self.fx.call(obs, fallback), fallback)
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertNotEqual(
            v1.LAST_V1_PACKAGE_TRACE["selected_rule"], v1.RULE_BOSS
        )


if __name__ == "__main__":
    unittest.main()