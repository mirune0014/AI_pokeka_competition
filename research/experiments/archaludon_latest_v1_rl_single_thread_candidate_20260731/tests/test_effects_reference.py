from __future__ import annotations

import math
import random
import unittest

import torch

from archaludon_rl.encoders import encode_action, encode_state
from archaludon_rl.effect_features import (
    AttackFact,
    CardFact,
    EffectCatalog,
    FeatureStatus,
    VisibleEffectContracts,
    extract_effect_features,
)
from archaludon_rl.public_state import project_public_state
from archaludon_rl.model import ResidualActorCritic
from archaludon_rl.reference_policy import (
    CANONICAL_REFERENCE_POLICY_CONFIG,
    ReferencePolicy,
    ReferencePolicyConfig,
)
from archaludon_rl.semantic_action import semantic_options

from .helpers import observation


def attack_observation(attack_id: int = 1):
    return observation(options=[{"type": 13, "attackId": attack_id}, {"type": 14}])


class EffectAndReferenceTests(unittest.TestCase):
    def test_named_effect_aliases_change_independently(self):
        obs = attack_observation()
        projection = project_public_state(obs)
        option = semantic_options(obs)[0]
        base_cards = {
            200: CardFact(200, energy_type=8, attacker_class="basic", prize_value=1),
            300: CardFact(300, weakness=8, prize_value=2),
        }
        attack = AttackFact(
            1, printed_damage=100, source_card_id=200, energy_cost=(8,)
        )
        plain = extract_effect_features(
            projection,
            option,
            EffectCatalog(cards=base_cards, attacks={1: attack}),
        )
        self.assertEqual(plain.fields["weakness_multiplier"].value, 2)
        self.assertEqual(plain.fields["effective_damage"].value, 200)

        ability_cards = dict(base_cards)
        ability_cards[300] = CardFact(
            300,
            weakness=8,
            prize_value=2,
            ability_tags=("wall",),
        )
        ability = extract_effect_features(
            projection,
            option,
            EffectCatalog(
                cards=ability_cards,
                attacks={1: attack},
                contracts=VisibleEffectContracts(
                    ability_damage_reduction={"wall": 30}
                ),
            ),
        )
        self.assertEqual(ability.fields["damage_reduction"].value, 30)
        self.assertEqual(ability.fields["effective_damage"].value, 170)

        stadium = extract_effect_features(
            projection,
            option,
            EffectCatalog(
                cards=base_cards,
                attacks={1: attack},
                contracts=VisibleEffectContracts(
                    stadium_damage_reduction={1244: 20}
                ),
            ),
        )
        self.assertEqual(stadium.fields["damage_reduction"].value, 20)

        prevented = extract_effect_features(
            projection,
            option,
            EffectCatalog(
                cards=ability_cards,
                attacks={1: attack},
                contracts=VisibleEffectContracts(
                    ability_prevents_attacker_classes={"wall": ("basic",)}
                ),
            ),
        )
        self.assertTrue(prevented.fields["prevented_attack_damage"].value)
        self.assertEqual(prevented.fields["effective_damage"].value, 0)
        evolved_cards = dict(ability_cards)
        evolved_cards[200] = CardFact(
            200, energy_type=8, attacker_class="evolved", prize_value=1
        )
        not_prevented = extract_effect_features(
            projection,
            option,
            EffectCatalog(
                cards=evolved_cards,
                attacks={1: attack},
                contracts=VisibleEffectContracts(
                    ability_prevents_attacker_classes={"wall": ("basic",)}
                ),
            ),
        )
        self.assertFalse(not_prevented.fields["prevented_attack_damage"].value)
        self.assertGreater(not_prevented.fields["effective_damage"].value, 0)

        obs["current"]["players"][0]["asleep"] = True
        asleep = extract_effect_features(
            project_public_state(obs),
            semantic_options(obs)[0],
            EffectCatalog(cards=base_cards, attacks={1: attack}),
        )
        self.assertFalse(asleep.fields["attack_usable"].value)
        self.assertTrue(asleep.fields["public_attack_lock"].value)

    def test_damage_and_counter_are_not_aliased(self):
        obs = attack_observation(attack_id=2)
        projection = project_public_state(obs)
        option = semantic_options(obs)[0]
        cards = {
            200: CardFact(200, energy_type=8, attacker_class="basic", prize_value=1),
            300: CardFact(300, prize_value=1),
        }
        counters = extract_effect_features(
            projection,
            option,
            EffectCatalog(
                cards=cards,
                attacks={
                    2: AttackFact(
                        2,
                        printed_damage=100,
                        source_card_id=200,
                        damage_kind="counters",
                        counter_amount=10,
                    )
                },
            ),
        )
        self.assertEqual(
            counters.fields["effective_damage"].status,
            FeatureStatus.NOT_APPLICABLE,
        )
        self.assertTrue(counters.fields["places_damage_counters"].value)
        self.assertEqual(counters.fields["damage_counter_amount"].value, 10)

    def test_unmodeled_visible_card_text_keeps_damage_unknown(self):
        obs = attack_observation()
        projection = project_public_state(obs)
        option = semantic_options(obs)[0]
        catalog = EffectCatalog(
            cards={
                200: CardFact(
                    200,
                    energy_type=8,
                    attacker_class="basic",
                    prize_value=1,
                ),
                300: CardFact(
                    300,
                    prize_value=1,
                    damage_modifiers_known=False,
                ),
                1244: CardFact(
                    1244,
                    card_type="stadium",
                    damage_modifiers_known=False,
                ),
            },
            attacks={
                1: AttackFact(
                    1,
                    printed_damage=100,
                    source_card_id=200,
                    energy_cost=(8,),
                )
            },
        )
        features = extract_effect_features(projection, option, catalog)
        self.assertEqual(
            features.fields["effective_damage"].status,
            FeatureStatus.UNKNOWN,
        )
        self.assertEqual(
            features.fields["prevented_attack_damage"].status,
            FeatureStatus.UNKNOWN,
        )

    def test_zero_residual_parity_full_support_reachability_and_sampling(self):
        policy = ReferencePolicy()
        distribution = policy.distribution(4, 2, [0.0] * 4)
        self.assertEqual(policy.deployment_argmax(distribution).index, 2)
        self.assertTrue(all(value > 0 for value in distribution.probabilities))
        diagnostics = policy.reachability_diagnostics(4, 2)
        self.assertTrue(diagnostics["surface_wide_reachable"])
        inversion = diagnostics["inversion_residual"][0]
        residuals = [inversion + 0.05, 0.0, -(inversion + 0.05), 0.0]
        inverted = policy.distribution(4, 2, residuals)
        self.assertEqual(policy.deployment_argmax(inverted).index, 0)
        rng = random.Random(1234)
        seen = {
            policy.training_sample(distribution, rng).index for _ in range(20000)
        }
        self.assertEqual(seen, {0, 1, 2, 3})

    def test_margin3_prior_has_strict_surface_reachability_and_seeded_sampling(self):
        policy = ReferencePolicy()
        cap = CANONICAL_REFERENCE_POLICY_CONFIG.residual_cap
        for option_count in (2, 3, 8, 32):
            for teacher_index in range(option_count):
                zero = policy.distribution(
                    option_count,
                    teacher_index,
                    [0.0] * option_count,
                )
                self.assertEqual(
                    policy.deployment_argmax(zero).index,
                    teacher_index,
                )
                self.assertEqual(
                    sum(
                        probability == max(zero.probabilities)
                        for probability in zero.probabilities
                    ),
                    1,
                )
                self.assertTrue(
                    all(
                        math.isfinite(probability) and probability > 0.0
                        for probability in zero.probabilities
                    )
                )
                self.assertAlmostEqual(sum(zero.probabilities), 1.0, places=12)
                for candidate in range(option_count):
                    residuals = [-cap] * option_count
                    residuals[candidate] = cap
                    inverted = policy.distribution(
                        option_count,
                        teacher_index,
                        residuals,
                    )
                    self.assertEqual(
                        policy.deployment_argmax(inverted).index,
                        candidate,
                    )
                    self.assertEqual(
                        sum(
                            probability == max(inverted.probabilities)
                            for probability in inverted.probabilities
                        ),
                        1,
                    )
                policy.assert_surface_reachable(option_count, teacher_index)
        first = random.Random(728)
        second = random.Random(728)
        distribution = policy.distribution(8, 5, [0.0] * 8)
        self.assertEqual(
            [
                policy.training_sample(distribution, first).index
                for _ in range(1000)
            ],
            [
                policy.training_sample(distribution, second).index
                for _ in range(1000)
            ],
        )

    def test_bad_config_rejects_unreachable_surface(self):
        policy = ReferencePolicy(
            ReferencePolicyConfig(
                teacher_margin=10.0,
                residual_cap=0.1,
                residual_scale=0.1,
                exploration_epsilon=1e-6,
            )
        )
        with self.assertRaises(ValueError):
            policy.assert_surface_reachable(3, 0)

    def test_actual_encoder_and_model_can_invert_teacher_choice(self):
        obs = observation()
        projection = project_public_state(obs)
        options = semantic_options(obs)
        catalog = EffectCatalog()
        actions = [
            encode_action(
                option,
                extract_effect_features(projection, option, catalog),
            )
            for option in options
        ]
        self.assertNotEqual(actions[0], actions[1])
        model = ResidualActorCritic()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        state_tensor = torch.tensor(encode_state(projection), dtype=torch.float32)
        action_tensor = torch.tensor(actions, dtype=torch.float32)
        prior = torch.tensor(
            ReferencePolicy().latest_prior(2, 0),
            dtype=torch.float32,
        )
        reference_config = CANONICAL_REFERENCE_POLICY_CONFIG
        for _ in range(120):
            residuals, _ = model(state_tensor, action_tensor)
            logits = (
                torch.log(prior)
                + reference_config.residual_scale
                * torch.tanh(
                    torch.clamp(
                        residuals,
                        -reference_config.residual_cap,
                        reference_config.residual_cap,
                    )
                )
            )
            loss = torch.nn.functional.cross_entropy(
                logits.unsqueeze(0), torch.tensor([1])
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        predicted, _ = model.predict(encode_state(projection), actions)
        distribution = ReferencePolicy().distribution(2, 0, predicted)
        self.assertEqual(
            ReferencePolicy().deployment_argmax(distribution).index,
            1,
        )


if __name__ == "__main__":
    unittest.main()
