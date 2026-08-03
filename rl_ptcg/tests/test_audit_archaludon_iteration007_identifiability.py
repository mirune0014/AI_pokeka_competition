from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import torch

from tools import audit_archaludon_iteration007_identifiability as audit


def semantic_option(
    option_type: int,
    *,
    engine_index: int = 0,
    card_id: int | None = None,
) -> dict:
    payload = {
        "option_type": option_type,
        "source_card_id": None,
        "target_card_id": None,
        "fields": {
            "area": None,
            "attackId": None,
            "cardId": card_id,
            "count": None,
            "energyIndex": None,
            "inPlayArea": None,
            "inPlayIndex": None,
            "number": None,
            "specialConditionType": None,
            "toolIndex": None,
        },
    }
    identity = hashlib.sha256(audit.canonical_json_bytes(payload)).hexdigest()
    return {"engine_index": engine_index, "identity": identity, "payload": payload}


def target_row(
    ordinal: int,
    episode: str,
    value: float,
    weight: float,
    **extra,
) -> dict:
    row = {
        "ppo_row_ordinal": ordinal,
        "episode_id": episode,
        "decision_index": ordinal,
        "raw_gae_float64": value,
        "normalized_training_advantage_float32": value,
        "monte_carlo_advantage": value,
        "loss_weight": weight,
    }
    row.update(extra)
    return row


class CanonicalIdentityTests(unittest.TestCase):
    def test_actions_legal_multiset_and_public_projection_are_canonical(self):
        first = semantic_option(7, engine_index=91, card_id=2)
        duplicate = copy.deepcopy(first)
        duplicate["engine_index"] = 3
        second = semantic_option(8, engine_index=5, card_id=1)

        action = audit.canonical_semantic_action(first)
        self.assertNotIn("engine_index", bytes.fromhex(action["canonical_json_bytes_hex"]).decode())
        self.assertEqual(action["sha256"].lower(), first["identity"])

        legal = audit.canonical_legal_multiset([second, first, duplicate])
        self.assertEqual(len(legal["sorted_semantic_identities"]), 3)
        self.assertEqual(
            legal["sorted_semantic_identities"].count(action["sha256"]), 2
        )
        self.assertEqual(
            legal["sorted_semantic_identities"],
            sorted(legal["sorted_semantic_identities"]),
        )

        left = audit.canonical_public_projection({"z": 1, "a": [True, 2]})
        right = audit.canonical_public_projection({"a": [True, 2], "z": 1})
        self.assertEqual(left, right)

    def test_selected_latent_is_exact_192_float32_hidden_concat(self):
        class SyntheticModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.state_encoder = torch.nn.Linear(2, 96)
                self.action_encoder = torch.nn.Linear(3, 96)

        torch.manual_seed(17)
        model = SyntheticModel()
        row = {
            "state_vector": [0.25, -0.5],
            "action_vectors": [[1.0, 2.0, 3.0], [-1.0, 0.0, 1.0]],
            "final_action": [1],
        }
        latent = audit.selected_frozen_latent(model, row)
        self.assertEqual(latent["shape"], [192])
        self.assertEqual(latent["byte_count"], 192 * 4)
        self.assertEqual(len(latent["values_float32"]), 192)
        self.assertEqual(
            latent["sha256"],
            hashlib.sha256(bytes.fromhex(latent["raw_bytes_hex"])).hexdigest().upper(),
        )


class CollisionAndPolarityTests(unittest.TestCase):
    def test_inclusive_robust_polarity_and_irreducible_conflict_mass(self):
        self.assertEqual(audit.robust_sign(1e-6), "positive")
        self.assertEqual(audit.robust_sign(-1e-6), "negative")
        self.assertEqual(audit.robust_sign(0.999e-6), "neutral")
        rows = [
            target_row(0, "p1", 1e-6, 1.0, identity="same"),
            target_row(1, "p2", 2.0, 4.0, identity="same"),
            target_row(2, "n1", -1e-6, 2.0, identity="same"),
            target_row(3, "n2", -3.0, 3.0, identity="same"),
        ]
        level = audit.analyze_collision_level(
            rows, level="synthetic", key_function=lambda row: row["identity"]
        )
        domain = level["classes"][0]["domains"]["normalized_training_advantage"]
        self.assertTrue(domain["exact_conflict"])
        self.assertTrue(domain["strong_cross_trajectory_conflict"])
        self.assertEqual(domain["unweighted_irreducible_wrong_sign_mass"], 2)
        self.assertEqual(domain["weighted_irreducible_wrong_sign_mass"], 5.0)

    def test_exact_o_to_x_collapse_requires_distinct_opaque_observations(self):
        rows = [
            target_row(
                ordinal,
                episode,
                value,
                1.0,
                X_sha256="X",
                L_sha256="L",
                a_sha256="a",
                O_sha256=f"O{ordinal}",
                priority_group=True,
                stage32_oriented_probability_delta=0.0,
            )
            for ordinal, episode, value in (
                (0, "p1", 1.0),
                (1, "p2", 1.0),
                (2, "n1", -1.0),
                (3, "n2", -1.0),
            )
        ]
        evidence = audit.analyze_o_to_x_collapses(rows)
        self.assertEqual(evidence["collapse_classes"], 1)
        self.assertEqual(evidence["collapsed_rows"], 4)
        self.assertEqual(evidence["evidentiary_rows"], [0, 1, 2, 3])
        self.assertEqual(evidence["evidentiary_induced_mass_total"], 2.0)
        self.assertEqual(
            evidence[
                "threshold_numerator_induced_mass_capped_by_priority_weight"
            ],
            2.0,
        )
        self.assertEqual(
            evidence["threshold_denominator_priority_anti_or_neutral_loss_weight"],
            4.0,
        )
        self.assertEqual(evidence["threshold_fraction"], 0.5)
        self.assertEqual(evidence["classes"][0]["distinct_O_plus_L_plus_a_classes"], 4)

    def test_o_to_x_subtracts_conflict_already_present_within_each_o_class(self):
        rows = []
        ordinal = 0
        for opaque, weight in (("O1", 1.0), ("O2", 2.0)):
            for sign, suffix in ((1.0, "p"), (-1.0, "n")):
                rows.append(
                    target_row(
                        ordinal,
                        f"{opaque}-{suffix}",
                        sign,
                        weight,
                        X_sha256="X",
                        L_sha256="L",
                        a_sha256="a",
                        O_sha256=opaque,
                        priority_group=True,
                        stage32_oriented_probability_delta=0.0,
                    )
                )
                ordinal += 1
        evidence = audit.analyze_o_to_x_collapses(rows)
        collision = evidence["classes"][0]
        self.assertEqual(collision["mass_X"], 3.0)
        self.assertEqual(collision["mass_O_inherited"], 3.0)
        self.assertEqual(collision["representation_induced_mass"], 0.0)
        self.assertFalse(collision["evidentiary_representation_collapse"])
        self.assertEqual(evidence["threshold_fraction"], 0.0)


class NearIdentityTests(unittest.TestCase):
    def test_atomic_public_diff_requires_identical_leaf_paths_and_bool_precedes_numeric(self):
        differences = audit.atomic_public_diff(
            {"flag": False, "nested": {"count": 2}},
            {"flag": True, "nested": {"count": 3}},
        )
        self.assertEqual([row["path"] for row in differences], ["/flag", "/nested/count"])
        self.assertTrue(all(row["one_unit"] for row in differences))
        self.assertEqual(differences[0]["left"]["type"], "boolean")

        missing = audit.atomic_public_diff({"items": [1]}, {"items": [1, 2]})
        self.assertEqual(missing[0]["right"]["value"], 2)
        self.assertFalse(missing[0]["one_unit"])

    def test_multiset_symmetric_difference_sums_absolute_count_differences(self):
        evidence = audit.multiset_symmetric_difference(["a", "a", "b"], ["a", "c", "c"])
        self.assertEqual(evidence["left_only"], ["a", "b"])
        self.assertEqual(evidence["right_only"], ["c", "c"])
        self.assertEqual(evidence["size"], 4)

    def test_mad_mutual_knn_ignores_zero_mad_and_breaks_ties_by_row_id(self):
        rows = [
            target_row(
                ordinal,
                f"e{ordinal}",
                1.0,
                1.0,
                X_values_float32=[x, 7.0],
                L_sha256="L",
                a_sha256="a",
            )
            for ordinal, x in ((0, 0.0), (1, 1.0), (2, -1.0))
        ]
        evidence = audit.mad_scaled_mutual_knn(
            rows, neighbors_per_row=1, retain_fraction=1.0
        )
        self.assertEqual(evidence["active_dimensions"], [0])
        self.assertEqual(evidence["zero_mad_dimensions"], [1])
        self.assertEqual(len(evidence["pairs"]), 1)
        pair = evidence["pairs"][0]
        self.assertEqual(pair["left_row_id"]["ppo_row_ordinal"], 0)
        self.assertEqual(pair["right_row_id"]["ppo_row_ordinal"], 1)
        self.assertGreater(pair["distance"], 0.0)

    def test_public_legal_and_latent_pairs_are_merged_and_agreement_uses_unique_pairs(self):
        common = {
            "a_sha256": "a",
            "decision_index": 0,
        }
        rows = [
            target_row(
                0,
                "e0",
                1.0,
                1.0,
                **common,
                P_sha256="P0",
                P_value={"count": 0},
                L_sha256="L0",
                L_identities=["x"],
                X_values_float32=[0.0, 7.0],
            ),
            target_row(
                1,
                "e1",
                -1.0,
                1.0,
                **common,
                P_sha256="P1",
                P_value={"count": 1},
                L_sha256="L0",
                L_identities=["x"],
                X_values_float32=[1.0, 7.0],
            ),
            target_row(
                2,
                "e2",
                1.0,
                1.0,
                **common,
                P_sha256="P0",
                P_value={"count": 0},
                L_sha256="L2",
                L_identities=["x", "y"],
                X_values_float32=[2.0, 7.0],
            ),
        ]
        pairs, evidence = audit._build_near_neighbors(rows)
        self.assertEqual(len(pairs), 2)
        merged = next(
            pair
            for pair in pairs
            if pair["left_row_id"]["ppo_row_ordinal"] == 0
            and pair["right_row_id"]["ppo_row_ordinal"] == 1
        )
        self.assertIn("public_one_unit", merged["relations"])
        self.assertIn("latent_mutual_5nn_lowest_nonzero_1_percent", merged["relations"])
        legal = next(
            pair
            for pair in pairs
            if pair["left_row_id"]["ppo_row_ordinal"] == 0
            and pair["right_row_id"]["ppo_row_ordinal"] == 2
        )
        self.assertEqual(legal["relations"], ["legal_multiset_one_or_two"])
        agreement = evidence["target_agreement"]
        self.assertEqual(agreement["unique_emitted_pair_count_denominator"], 2)
        self.assertEqual(agreement["agreeing_pair_count_numerator"], 1)
        self.assertEqual(agreement["fraction"], 0.5)
        self.assertEqual(len(agreement["all_unique_emitted_pairs"]), 2)


class CreditAndBalanceTests(unittest.TestCase):
    def test_gae_lag_buckets_and_monte_carlo_decomposition(self):
        rows = [
            {"decision_index": 4, "reward": 0.0, "value": 0.5},
            {"decision_index": 9, "reward": 1.0, "value": 0.25},
        ]
        evidence = audit.gae_decomposition_for_episode(rows)
        first, last = evidence
        self.assertAlmostEqual(first["delta"], 0.99 * 0.25 - 0.5)
        self.assertAlmostEqual(last["delta"], 0.75)
        self.assertAlmostEqual(first["gae_lag_0"], -0.2525)
        self.assertAlmostEqual(first["gae_lag_1"], 0.99 * 0.95 * 0.75)
        self.assertAlmostEqual(first["raw_gae"], -0.2525 + 0.99 * 0.95 * 0.75)
        self.assertAlmostEqual(first["discounted_realized_return"], 0.99)
        self.assertAlmostEqual(first["monte_carlo_advantage"], 0.49)
        self.assertEqual(first["terminal_distance"], 1)
        self.assertEqual(last["bootstrap_mask"], 0.0)

    def test_history_uses_immediate_recorded_protected_empty_and_multi_actions(self):
        first_option = semantic_option(7, engine_index=0)
        second_option = semantic_option(8, engine_index=1)

        def decision(
            index: int, *, eligible: bool, count: int, selected: list[int]
        ) -> dict:
            return {
                "decision_index": index,
                "ppo_eligible": eligible,
                "final_action": selected,
                "legal_semantic_options": [first_option, second_option],
                "public_projection": {"count": count},
            }

        episode = {
            "decisions": [
                decision(1, eligible=True, count=1, selected=[0]),
                decision(2, eligible=False, count=2, selected=[0, 1]),
                decision(3, eligible=False, count=3, selected=[]),
                decision(4, eligible=True, count=4, selected=[0]),
            ]
        }
        history = audit.public_history_by_decision(episode)
        self.assertEqual(set(history), {1, 2, 3, 4})
        lag_one = history[4]["previous_action_1"]
        self.assertEqual(
            json.loads(bytes.fromhex(lag_one["canonical_json_bytes_hex"])), []
        )
        lag_two = history[4]["previous_action_2"]
        self.assertEqual(len(lag_two["semantic_identities"]), 2)
        delta_one = history[4]["previous_public_state_delta_1"]
        self.assertEqual(delta_one["from_decision_index"], 3)
        self.assertEqual(delta_one["to_decision_index"], 4)
        delta_two = history[4]["previous_public_state_delta_2"]
        self.assertEqual(delta_two["from_decision_index"], 2)
        self.assertEqual(delta_two["to_decision_index"], 3)
        emitted_for_ppo = {
            row["decision_index"]: history[row["decision_index"]]
            for row in episode["decisions"]
            if row["ppo_eligible"]
        }
        self.assertEqual(set(emitted_for_ppo), {1, 4})

    def test_value_credit_uses_class_irreducible_mass_and_caps_credit(self):
        rows = [
            target_row(
                0,
                "resolved-p",
                1.0,
                2.0,
                O_sha256="resolved",
                L_sha256="L",
                a_sha256="a",
                monte_carlo_advantage=1.0,
            ),
            target_row(
                1,
                "resolved-n",
                -1.0,
                1.0,
                O_sha256="resolved",
                L_sha256="L",
                a_sha256="a",
                monte_carlo_advantage=1.0,
            ),
            target_row(
                2,
                "conflict-flip",
                1.0,
                2.0,
                O_sha256="conflict",
                L_sha256="L",
                a_sha256="a",
                monte_carlo_advantage=-1.0,
            ),
            target_row(
                3,
                "conflict-negative",
                -1.0,
                3.0,
                O_sha256="conflict",
                L_sha256="L",
                a_sha256="a",
                monte_carlo_advantage=-1.0,
            ),
            target_row(
                4,
                "conflict-positive",
                1.0,
                1.0,
                O_sha256="conflict",
                L_sha256="L",
                a_sha256="a",
                monte_carlo_advantage=1.0,
            ),
        ]
        evidence = audit.analyze_value_credit_attribution(rows)
        self.assertEqual(evidence["baseline_irreducible_mass_denominator"], 4.0)
        self.assertEqual(evidence["credited_changed_or_resolved_mass_numerator"], 3.0)
        self.assertEqual(evidence["credited_fraction"], 0.75)
        by_o = {row["O_sha256"]: row for row in evidence["classes"]}
        self.assertTrue(by_o["resolved"]["MC_resolves_class"])
        self.assertEqual(by_o["resolved"]["credited_changed_or_resolved_mass"], 1.0)
        self.assertFalse(by_o["conflict"]["MC_resolves_class"])
        self.assertEqual(by_o["conflict"]["robust_sign_flipped_loss_weight"], 2.0)
        self.assertEqual(by_o["conflict"]["credited_changed_or_resolved_mass"], 2.0)

    def test_ess_weighted_median_top_share_and_leave_one_out(self):
        self.assertAlmostEqual(audit.effective_sample_size([1.0, 1.0, 2.0]), 16.0 / 6.0)
        self.assertEqual(audit.weighted_median([3.0, 1.0, 2.0], [1.0, 1.0, 2.0]), 2.0)
        self.assertEqual(audit.top_fraction_weight_share([8.0, 1.0, 1.0]), 0.8)
        rows = [
            {"episode_id": "a", "target": -1.0, "weight": 1.0},
            {"episode_id": "b", "target": 2.0, "weight": 1.0},
            {"episode_id": "c", "target": 3.0, "weight": 1.0},
        ]
        result = audit.leave_one_trajectory_out_range(
            rows, value_field="target", weight_field="weight"
        )
        self.assertEqual(result["trajectory_count"], 3)
        self.assertEqual(result["minimum"], -1.0)
        self.assertEqual(result["maximum"], 2.0)

    def test_sparse_group_balance_keeps_all_32_trajectories_in_every_diagnostic(self):
        universe = [f"e{index:02d}" for index in range(32)]
        rows = [
            target_row(
                0,
                "e00",
                1.0,
                1.0,
                raw_gae_float64=1.0,
                monte_carlo_advantage=1.0,
                stage32_oriented_probability_delta=-1.0,
                P_sha256="P0",
            ),
            target_row(
                1,
                "e01",
                -1.0,
                1.0,
                raw_gae_float64=-1.0,
                monte_carlo_advantage=-1.0,
                stage32_oriented_probability_delta=2.0,
                P_sha256="P1",
            ),
        ]
        evidence = audit.group_balance_statistics(
            rows, trajectory_universe=universe
        )
        self.assertEqual(evidence["nominal_trajectory_count"], 32)
        self.assertEqual(evidence["nonzero_trajectory_count"], 2)
        self.assertEqual(evidence["effective_trajectory_sample_size"], 2.0)
        self.assertEqual(evidence["trajectory_ESS_input_count_including_zero_weights"], 32)
        self.assertEqual(
            sum(
                row["nonzero"]
                for row in evidence["trajectory_loss_weights_including_zeros"]
            ),
            2,
        )
        self.assertEqual(evidence["top_10_percent_trajectory_count"], 4)
        loto = evidence["leave_one_trajectory_out_target_range"]
        self.assertEqual(loto["trajectory_count"], 32)
        self.assertEqual(len(loto["by_omitted_trajectory"]), 32)
        zero_weight_omission = next(
            row
            for row in loto["by_omitted_trajectory"]
            if row["omitted_trajectory"] == "e31"
        )
        self.assertEqual(zero_weight_omission["weighted_median"], -1.0)


class GradientAndClassificationTests(unittest.TestCase):
    def test_clipped_ppo_ascent_has_analytical_gradient_and_common_830_denominator(self):
        theta = torch.tensor(math.log(1.05), dtype=torch.float64, requires_grad=True)
        ratio = torch.exp(theta)
        advantage = torch.tensor(2.0, dtype=torch.float64)
        term, active = audit.clipped_ppo_ascent_term(ratio, advantage)
        gradient = torch.autograd.grad(term / audit.EXPECTED_ROWS, theta)[0]
        self.assertFalse(active)
        self.assertAlmostEqual(
            float(gradient), 1.05 * 2.0 / audit.EXPECTED_ROWS, places=12
        )

        clipped_theta = torch.tensor(
            math.log(1.2), dtype=torch.float64, requires_grad=True
        )
        clipped_term, clipped_active = audit.clipped_ppo_ascent_term(
            torch.exp(clipped_theta), advantage
        )
        clipped_gradient = torch.autograd.grad(
            clipped_term / audit.EXPECTED_ROWS, clipped_theta
        )[0]
        self.assertTrue(clipped_active)
        self.assertEqual(float(clipped_gradient), 0.0)

        negative_theta = torch.tensor(
            math.log(0.8), dtype=torch.float64, requires_grad=True
        )
        negative_term, negative_active = audit.clipped_ppo_ascent_term(
            torch.exp(negative_theta), torch.tensor(-3.0, dtype=torch.float64)
        )
        negative_gradient = torch.autograd.grad(
            negative_term / audit.EXPECTED_ROWS, negative_theta
        )[0]
        self.assertTrue(negative_active)
        self.assertEqual(float(negative_gradient), 0.0)

    def test_signed_gradient_records_fixed_behavior_ratio_and_clipped_rows(self):
        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.residual_head = torch.nn.Sequential(torch.nn.Linear(1, 1))
                torch.nn.init.zeros_(self.residual_head[0].weight)
                torch.nn.init.zeros_(self.residual_head[0].bias)

            def forward(self, state, actions):
                del state
                return self.residual_head(actions).squeeze(-1), torch.tensor(0.0)

        def distribution(residuals, *, teacher_index, reference_config):
            del teacher_index, reference_config
            return torch.softmax(residuals, dim=0), torch.log_softmax(residuals, dim=0)

        current_logprob = -math.log(2.0)
        row = target_row(
            7,
            "episode",
            1.0,
            1.0,
            behavior_logprob_float64=current_logprob - math.log(1.2),
            _source_row={
                "state_vector": [0.0],
                "action_vectors": [[1.0], [0.0]],
                "teacher_action": [0],
                "final_action": [0],
            },
        )
        record, vector = audit._aggregate_signed_gradient(
            TinyModel(),
            [row],
            distribution_function=distribution,
            reference_config=None,
        )
        self.assertEqual(record["full_batch_denominator"], 830)
        self.assertTrue(record["fixed_behavior_logprobabilities_used"])
        self.assertAlmostEqual(record["PPO_ratio"]["minimum"], 1.2, places=6)
        self.assertEqual(record["clipped_active_row_count"], 1)
        self.assertEqual(record["clipped_active_row_ids"][0]["ppo_row_ordinal"], 7)
        self.assertEqual(len(record["per_row_PPO_ratio_and_clip_activity"]), 1)
        self.assertTrue(
            record["per_row_PPO_ratio_and_clip_activity"][0]["clipped_active"]
        )
        self.assertTrue(torch.equal(vector, torch.zeros_like(vector)))

    def test_cosine_and_parameter_delta_projection(self):
        gradient = torch.tensor([1.0, 0.0])
        favorable = audit.gradient_delta_projection(gradient, torch.tensor([2.0, 0.0]))
        adverse = audit.gradient_delta_projection(gradient, torch.tensor([-1.0, 0.0]))
        self.assertEqual(favorable["cosine"], 1.0)
        self.assertTrue(favorable["favorable_ascent_projection"])
        self.assertEqual(adverse["cosine"], -1.0)
        self.assertFalse(adverse["favorable_ascent_projection"])
        self.assertIsNone(audit.vector_cosine(torch.zeros(2), torch.ones(2)))

    def test_classification_thresholds_and_update16_fail_closed(self):
        matrix = audit.classify_causes(
            {
                "representation_collision_fraction": 0.5,
                "temporal_conflict_reduction_fraction": 0.5,
                "temporal_priority_rows_covered": 9,
                "temporal_failed_groups_covered": 2,
                "value_credit_changed_or_resolved_fraction": 0.5,
                "dataset_imbalance_group_passes": ["END:positive"],
                "near_neighbor_target_agreement": 1.0,
                "gae_mc_sign_agreement": 1.0,
                "reweighting_preserves_direction": True,
                "all_six_group_derivatives_favorable": True,
                "intermediate_parameter_evidence_complete": False,
            }
        )
        self.assertTrue(matrix["representation_collision"]["evidenced"])
        self.assertTrue(matrix["missing_temporal_information"]["evidenced"])
        self.assertTrue(matrix["value_or_credit_conflict"]["evidenced"])
        self.assertTrue(matrix["dataset_imbalance"]["evidenced"])
        self.assertFalse(matrix["mere_optimization_failure"]["evidenced"])
        self.assertTrue(
            matrix["mere_optimization_failure"][
                "ineligible_because_update16_parameters_unavailable"
            ]
        )

        eligible = audit.classify_causes(
            {
                "representation_collision_fraction": 0.0,
                "temporal_conflict_reduction_fraction": 0.0,
                "value_credit_changed_or_resolved_fraction": 0.0,
                "dataset_imbalance_group_passes": [],
                "near_neighbor_target_agreement": 0.9,
                "gae_mc_sign_agreement": 0.9,
                "reweighting_preserves_direction": True,
                "all_six_group_derivatives_favorable": True,
                "intermediate_parameter_evidence_complete": True,
            }
        )
        self.assertTrue(eligible["mere_optimization_failure"]["evidenced"])


class DeterminismAndBoundaryTests(unittest.TestCase):
    @staticmethod
    def _synthetic_payloads() -> dict[str, bytes]:
        return {
            name: audit.canonical_json_bytes({"name": name}, newline=True)
            for name in set(audit.REQUIRED_OUTPUT_FILES) - {"manifest.json"}
        }

    def test_published_temporal_semantics_name_all_recorded_decisions(self):
        source = Path(audit.__file__).read_text(encoding="utf-8")
        self.assertNotIn("prior_two_PPO_actions", source)
        self.assertNotIn("preceding PPO-eligible rows", source)
        self.assertIn("prior_two_recorded_actions_and_public_deltas", source)
        self.assertIn("immediately preceding recorded decisions", source)

    def test_canonical_json_and_publication_are_deterministic_and_exact(self):
        self.assertEqual(
            audit.canonical_json_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}'
        )
        payloads = self._synthetic_payloads()
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            first = parent / "first"
            second = parent / "second"
            result1 = audit.publish_canonical_artifacts(
                first, payloads=payloads, manifest_core={"schema_version": "synthetic"}
            )
            result2 = audit.publish_canonical_artifacts(
                second, payloads=payloads, manifest_core={"schema_version": "synthetic"}
            )
            self.assertEqual(result1["manifest_file_sha256"], result2["manifest_file_sha256"])
            self.assertEqual(
                sorted(path.name for path in first.iterdir()),
                sorted(audit.REQUIRED_OUTPUT_FILES),
            )
            for name in audit.REQUIRED_OUTPUT_FILES:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())

    def test_exact_guarded_tree_snapshot_includes_duplicate_audit_sidecars(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "rollouts"
            (root / "episodes").mkdir(parents=True)
            (root / "audit").mkdir()
            (root / "run_manifest.json").write_bytes(b"manifest")
            (root / "episodes" / "episode.json").write_bytes(b"episode")
            (root / "audit" / "trace_a.json").write_bytes(b"trace-a")
            (root / "audit" / "trace_b.json").write_bytes(b"trace-b")
            snapshot, buffers = audit.exact_guarded_tree_snapshot_with_buffers(root)
            self.assertEqual(snapshot["directory_count"], 2)
            self.assertEqual(snapshot["file_count"], 4)
            self.assertEqual(
                set(buffers),
                {
                    "run_manifest.json",
                    "episodes/episode.json",
                    "audit/trace_a.json",
                    "audit/trace_b.json",
                },
            )
            self.assertEqual(
                [row["path"] for row in snapshot["files"]],
                sorted(buffers, key=lambda value: value.encode("utf-8")),
            )

    def test_clean_room_import_rejects_a_preexisting_private_alias(self):
        alias = "_iteration007_identifiability_clean_room_6b95c5b6"
        with tempfile.TemporaryDirectory() as temporary:
            candidate = Path(temporary)
            package = candidate / "archaludon_rl"
            package.mkdir()
            (package / "__init__.py").write_bytes(b"")
            sys.modules[alias] = types.ModuleType(alias)
            try:
                with self.assertRaisesRegex(RuntimeError, "already exists"):
                    audit.import_clean_room_candidate(candidate)
            finally:
                sys.modules.pop(alias, None)

    def test_safe_checkpoint_loader_passes_retained_bytes_and_weights_only(self):
        clean_room = types.SimpleNamespace()
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "checkpoint.pt"
            checkpoint.write_bytes(b"guarded-checkpoint-bytes")
            loader = audit._safe_checkpoint_loader(
                clean_room, {checkpoint: b"guarded-checkpoint-bytes"}
            )
            with mock.patch.object(
                audit.torch, "load", side_effect=RuntimeError("stop after boundary")
            ) as torch_load:
                with self.assertRaisesRegex(RuntimeError, "stop after boundary"):
                    loader(checkpoint)
            args, kwargs = torch_load.call_args
            self.assertEqual(args[0].getvalue(), b"guarded-checkpoint-bytes")
            self.assertEqual(kwargs["map_location"], "cpu")
            self.assertIs(kwargs["weights_only"], True)

    def test_plan_hash_and_schema_validation_fail_closed_on_synthetic_copy(self):
        real_plan = audit.repo_root() / Path(*audit.PLAN_RELATIVE_PATH.parts)
        payload = real_plan.read_bytes()
        digest = hashlib.sha256(payload).hexdigest().upper()
        self.assertEqual(digest, audit.PLAN_SHA256)
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "plan.json"
            copied.write_bytes(payload)
            loaded = audit.load_and_validate_plan(
                copied,
                digest,
                expected_path=copied,
                expected_sha256=digest,
            )
            self.assertEqual(loaded["plan_id"], audit.PLAN_ID)
            with self.assertRaisesRegex(ValueError, "supplied plan SHA"):
                audit.load_and_validate_plan(
                    copied,
                    "0" * 64,
                    expected_path=copied,
                    expected_sha256=digest,
                )
            tampered = bytearray(payload)
            tampered[-2] = ord(" ")
            copied.write_bytes(tampered)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                audit.load_and_validate_plan(
                    copied,
                    digest,
                    expected_path=copied,
                    expected_sha256=digest,
                )

    def test_output_collision_stops_before_real_execution(self):
        plan = audit.repo_root() / Path(*audit.PLAN_RELATIVE_PATH.parts)
        with tempfile.TemporaryDirectory() as temporary:
            collision = Path(temporary) / "already_exists"
            collision.mkdir()
            with mock.patch.object(audit, "execute_read_only_audit") as execute:
                with self.assertRaises(FileExistsError):
                    audit.run_audit(
                        plan_path=plan,
                        plan_sha256=audit.PLAN_SHA256,
                        output_dir=collision,
                    )
                execute.assert_not_called()

    def test_adam_guard_turns_construction_into_failure_and_restores_symbol(self):
        original = torch.optim.Adam
        with self.assertRaisesRegex(RuntimeError, "forbidden"):
            with audit.AdamConstructionGuard() as guard:
                torch.optim.Adam([torch.nn.Parameter(torch.tensor(0.0))])
        self.assertEqual(guard.attempts, 1)
        self.assertIs(torch.optim.Adam, original)

    def test_swallowed_alternate_optimizer_attempt_prevents_any_publication(self):
        payloads = self._synthetic_payloads()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must_not_exist"
            with audit.ReadOnlyOperationGuard() as guard:
                try:
                    torch.optim.SGD([torch.nn.Parameter(torch.tensor(0.0))], lr=0.1)
                except RuntimeError:
                    pass
                with self.assertRaisesRegex(RuntimeError, "safety verdict failed"):
                    audit.publish_canonical_artifacts(
                        output,
                        payloads=payloads,
                        manifest_core={"schema_version": "synthetic"},
                        safety_check=lambda: guard.assert_clean(
                            phase="synthetic publication"
                        ),
                    )
            self.assertGreaterEqual(guard.attempts, 1)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_swallowed_candidate_training_entrypoint_prevents_publication(self):
        alias = "_iteration007_identifiability_clean_room_6b95c5b6"
        module_name = alias + ".synthetic_training"
        module = types.ModuleType(module_name)
        module.train = lambda: "unsafe"
        sys.modules[module_name] = module
        try:
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "must_not_exist"
                with audit.ReadOnlyOperationGuard() as guard:
                    guard.install_candidate_entrypoint_guards(alias)
                    try:
                        module.train()
                    except RuntimeError:
                        pass
                    with self.assertRaisesRegex(RuntimeError, "safety verdict failed"):
                        audit.publish_canonical_artifacts(
                            output,
                            payloads=self._synthetic_payloads(),
                            manifest_core={"schema_version": "synthetic"},
                            safety_check=lambda: guard.assert_clean(
                                phase="synthetic entrypoint publication"
                            ),
                        )
                self.assertEqual(guard.attempts, 1)
                self.assertFalse(output.exists())
        finally:
            sys.modules.pop(module_name, None)

    def test_audit_implementation_snapshot_binds_script_and_focused_test(self):
        snapshot, buffers = audit.audit_implementation_snapshot_with_buffers(
            audit.repo_root()
        )
        self.assertEqual(snapshot["file_count"], 2)
        self.assertEqual(set(buffers), {path.as_posix() for path in audit.AUDIT_IMPLEMENTATION_RELATIVE_PATHS})
        for record in snapshot["files"]:
            self.assertEqual(
                hashlib.sha256(buffers[record["path"]]).hexdigest().upper(),
                record["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
