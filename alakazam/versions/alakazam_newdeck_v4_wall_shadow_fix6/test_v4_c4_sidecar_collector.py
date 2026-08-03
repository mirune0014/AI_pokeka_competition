from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from verification import c4_sidecar_collector as collector
import planner_wall_shadow_fix6 as c4


CLOSURE = "C" * 64
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CHECKED_WRITER = REPO_ROOT / "infrastructure" / "tools" / "alakazam_staged_metrics.py"
RAW_SIDECAR_FIXTURE = (
    REPO_ROOT
    / "alakazam"
    / "metrics"
    / "formal_frozen_7opp_50seed"
    / "runs"
    / "frozen"
    / "alakazam_mirror"
    / "seed_202608500"
    / "seat_0"
    / "sidecars"
    / "game_0000.jsonl"
)
DURABLE_OBSERVATION = (
    REPO_ROOT
    / "alakazam"
    / "fixtures"
    / "episode_88844273_public_observations"
    / "step_067_first_alakazam_ko_forced_promotion.json"
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest().upper()


def metric_observation(index: int, seat: int = 0) -> dict:
    option = {
        "area": 5,
        "index": 0,
        "playerIndex": seat,
        "type": 3,
    }
    return {
        "turn": 4 + index,
        "turn_action_count": index,
        "your_index": seat,
        "first_player": index % 2,
        "result": -1,
        "context": 4,
        "select_type": 1,
        "min_count": 1,
        "max_count": 1,
        "option_count": 1,
        "options": [
            {
                "option_index": 0,
                "type": 3,
                "area": 5,
                "index": 0,
                "player_index": seat,
                "card_id": 66,
                "serial": 201,
                "attack_id": None,
                "in_play_area": None,
                "in_play_index": None,
                "raw": option,
            }
        ],
        "own_hand": [[743, 299]],
        "own_active": [741, 200],
        "own_active_hp": 50,
        "own_active_energy": [],
        "own_bench": [[66, 201]],
        "own_discard": [],
        "opponent_active": [676, 310],
        "opponent_active_hp": 110,
        "opponent_active_energy": [[6, 3100]],
        "logs_raw": [],
        "log_serial_fields": [],
    }


def rebind_trace_public(value: dict, observation: dict) -> dict:
    result = copy.deepcopy(value)
    material = collector._canonical_public_state_material(observation)
    if material is None:
        raise AssertionError("test observation is not canonical")
    public_fingerprint = collector._fingerprint(material)
    result["public_state_material"] = material
    result["public_state_fingerprint"] = public_fingerprint
    pair_material = result.get("pair_material")
    if (
        isinstance(pair_material, dict)
        and pair_material.get("public_state_fingerprint")
        != public_fingerprint
    ):
        pair_material["public_state_fingerprint"] = public_fingerprint
        result["pair_id"] = collector._fingerprint(pair_material)
    return result


def wall_metrics() -> dict:
    envelope = {
        "status": "SUPPORTED",
        "continuity": "REPEATABLE_READY",
        "final_safety_cap": 70,
        "promotion_threats": [],
        "unsupported_reasons": [],
    }
    return {
        "protected_readiness": "CERTIFIED",
        "hold_turns": 1,
        "own_prize_loss": 0,
        "gust_exposure": 1,
        "resource_loss": 1,
        "lost_draw3": 3,
        "safe_release": {
            "class": "CERTIFIED",
            "reason": "EXACT_SAFE_RELEASE_AND_EXCHANGE",
            "release_target": {
                "certified": True,
                "attacker_serial": 299,
                "attacker_card_id": 743,
                "attacker_current_hp": 140,
                "attack_id": 1072,
                "attack_binding": "TEST_EXACT_ATTACK",
                "target_prize_value": 1,
            },
            "backup_certified": True,
            "opponent_continuation": "REPEATABLE_READY",
            "opponent_safety_cap": 70,
            "post_release_opponent_envelope": envelope,
            "prize_exchange_non_worsening": True,
        },
        "final_prize_outcome": False,
        "remaining_hp": 140,
        "final_safety_cap": 70,
        "survival_margin": 70,
        "hold_entry_turn": 4,
        "hold_deadline": 5,
    }


def candidate_rows(decision_class: str, semantic_key: dict) -> list[dict]:
    unavailable = {
        "decision_point": None,
        "legality": "UNAVAILABLE",
        "option_index": None,
        "semantic_action_key": None,
        "wall": None,
        "rejection_codes": [],
        "unsupported_reasons": [],
        "structural_reasons": [],
        "metrics": {},
        "pareto_vector": None,
        "wall_class": "REJECTED",
        "certification": "UNAVAILABLE",
    }
    if decision_class == "STRICT":
        certification = "STRICT"
        wall_class = collector.STRICT
        rejection_codes = []
        unsupported_reasons = []
    else:
        certification = "PRESERVE_CHANCE"
        wall_class = collector.CHANCE
        rejection_codes = ["RELEASE_POSSIBLE_ONLY"]
        unsupported_reasons = ["RELEASE_POSSIBLE_ONLY"]
    reusable = {
        "kind": "CERTIFIED_REUSABLE_WALL",
        "decision_point": "A_FORCED_PROMOTION",
        "legality": "EXACT",
        "option_index": 1,
        "semantic_action_key": copy.deepcopy(semantic_key),
        "wall": {"serial": 201, "card_id": 66},
        "rejection_codes": rejection_codes,
        "unsupported_reasons": unsupported_reasons,
        "structural_reasons": [],
        "metrics": wall_metrics(),
        "pareto_vector": {
            "protected_readiness": 1,
            "safe_release": 1,
            "resource_loss": -1,
        },
        "wall_class": wall_class,
        "certification": certification,
    }
    no_wall = {
        **copy.deepcopy(unavailable),
        "kind": "NO_WALL_OR_UNKNOWN",
        "wall_class": "PARENT_FALLBACK",
        "certification": "AVAILABLE",
    }
    return [
        {**copy.deepcopy(unavailable), "kind": "RUN_AWAY_ACCELERATION"},
        reusable,
        {
            **copy.deepcopy(unavailable),
            "kind": "CERTIFIED_SACRIFICE_WALL",
        },
        no_wall,
    ]


def outcome_events(decision_id: str, *, complete: bool) -> list[dict]:
    events = [
        {
            "event": "PARENT_AGREEMENT",
            "decision_id": decision_id,
            "turn": 4,
        }
    ]
    if complete:
        events.extend(
            [
                {
                    "event": "WALL_ACTIVE",
                    "decision_id": decision_id,
                    "wall_serial": 201,
                    "turn": 4,
                },
                {
                    "event": "WALL_ATTACKED",
                    "decision_id": decision_id,
                    "wall_serial": 201,
                    "hp_before": 140,
                    "hp_after": 100,
                    "turn": 5,
                },
                {
                    "event": "WALL_SURVIVED",
                    "decision_id": decision_id,
                    "wall_serial": 201,
                    "hp": 100,
                    "turn": 5,
                },
                {
                    "event": "DISTANCE_IMPROVED",
                    "decision_id": decision_id,
                    "distance_before": [0, 1, 4, 3],
                    "distance_after": [0, 1, 1, 0],
                    "turn": 5,
                },
                {
                    "event": "RUN_AWAY_RELEASED",
                    "decision_id": decision_id,
                    "source_serial": 201,
                    "turn": 6,
                },
                {
                    "event": "PROMOTION_DESTINATION",
                    "decision_id": decision_id,
                    "destination_serial": 299,
                    "destination_card_id": 743,
                    "protected_destination": True,
                    "turn": 6,
                },
                {
                    "event": "PROTECTED_ATTACKER_ATTACKED",
                    "decision_id": decision_id,
                    "attacker_serial": 299,
                    "attack_id": 1072,
                    "turn": 7,
                },
                {
                    "event": "OPPONENT_CONTINUITY_OBSERVED",
                    "decision_id": decision_id,
                    "attacker_serial": 310,
                    "turn": 8,
                },
            ]
        )
    return events


def trace(
    index: int,
    decision_class: str,
    *,
    agreement: bool = False,
    complete: bool = False,
) -> dict:
    decision_id = digest(f"decision:{index}")
    semantic_key = {
        "type": 3,
        "serial": 201,
        "card_id": 66,
        "area": 5,
    }
    rows = candidate_rows(decision_class, semantic_key)
    events = (
        outcome_events(decision_id, complete=complete)
        if agreement
        else []
    )
    option_keys = [copy.deepcopy(semantic_key)]
    public_material = collector._canonical_public_state_material(
        metric_observation(index, index % 2)
    )
    if public_material is None:
        raise AssertionError("test observation is not canonical")
    public_fingerprint = collector._fingerprint(public_material)
    expose_projection = {
        "projection": "EXPOSE_STATE",
        "fixture_index": index,
    }
    wall_alternative = {
        "kind": "CERTIFIED_REUSABLE_WALL",
        "semantic_action_key": copy.deepcopy(semantic_key),
        "wall": {"serial": 201, "card_id": 66},
        "bypass": "NO_PUBLIC_ARMED_BYPASS",
    }
    wall_projection = {
        "projection": "WALL_STATE",
        "alternatives": [copy.deepcopy(wall_alternative)],
        "chosen": copy.deepcopy(wall_alternative),
    }
    pair_material = {
        "public_state_fingerprint": public_fingerprint,
        "decision_point": "A_FORCED_PROMOTION",
        "semantic_action_keys": copy.deepcopy(option_keys),
        "protected_serial": 200,
        "wall_serials": [201],
    }
    pair_id = collector._fingerprint(pair_material)
    return {
        "schema_version": collector.SCHEMA_VERSION,
        "rule_version": collector.RULE_VERSION,
        "parent_closure_sha256": collector.PARENT_CLOSURE_SHA256,
        "candidate_closure_sha256": CLOSURE,
        "analyzer_component_sha256": collector.ANALYZER_SHA256,
        "state_machine": ["CAPTURE", "RETURN_EXACT_PARENT_ACTION"],
        "decision_point": "A_FORCED_PROMOTION",
        "pair_id": pair_id,
        "decision_id": decision_id,
        "raw_parent_action": [0],
        "parent_action": [0],
        "proposed_action": [1],
        "applied_action": [0],
        "action_python_type": "builtins.list",
        "action_identity": {
            "value_equal": True,
            "type_equal": True,
            "order_equal": True,
            "returned_parent_object_unchanged": True,
        },
        "semantic_option_keys": copy.deepcopy(option_keys),
        "semantic_parent_action_keys": [copy.deepcopy(semantic_key)],
        "semantic_proposed_action_keys": [copy.deepcopy(semantic_key)],
        "public_state_material": public_material,
        "public_state_fingerprint": public_fingerprint,
        "pair_material": pair_material,
        "game_boundary_fingerprint": digest(f"boundary:{index}"),
        "parent_post_fingerprint": collector._fingerprint(
            expose_projection
        ),
        "candidate_post_fingerprint": collector._fingerprint(
            wall_projection
        ),
        "expose_state_fingerprint": collector._fingerprint(
            expose_projection
        ),
        "wall_state_fingerprint": collector._fingerprint(
            wall_projection
        ),
        "expose_projection": expose_projection,
        "wall_projection": wall_projection,
        "protected_line": {
            "line_id": 200,
            "top_serial": 200,
            "top_card_id": 741,
        },
        "importance": "IMPORTANT",
        "distance_before": {
            "route_class": "CERTIFIED",
            "turn_delay": 1,
        },
        "distance_without_line": {
            "route_class": "POSSIBLE",
            "turn_delay": 3,
        },
        "threat": {
            "status": "SUPPORTED",
            "continuity": "REPEATABLE_READY",
        },
        "damage_floor": 70,
        "damage_cap": 70,
        "continuity": "REPEATABLE_READY",
        "wall_candidates": copy.deepcopy(rows[1:3]),
        "candidate_rows": rows,
        "run_away_value": copy.deepcopy(rows[0]),
        "reusable_wall_value": copy.deepcopy(rows[1]),
        "sacrifice_wall_value": copy.deepcopy(rows[2]),
        "bypass": "NO_PUBLIC_ARMED_BYPASS",
        "refusal_progress": (
            "CERTIFIED" if decision_class == "STRICT" else "POSSIBLE"
        ),
        "safe_release": copy.deepcopy(rows[1]["metrics"]["safe_release"]),
        "gust_exposure_turns": 1,
        "wall_class": rows[1]["wall_class"],
        "arbitration_reason": "ONLY_STRICT_WALL",
        "outcome_status": (
            "PARENT_AGREEMENT"
            if agreement
            else "COUNTERFACTUAL_UNOBSERVED"
        ),
        "outcome_events": events,
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
        "premium_power_pro_multiplicity": {
            "deck_limit": 4,
            "stack_max": 0,
        },
        "evidenced_policy_cap": 70,
        "safety_cap": 70,
        "hold_entry_turn": 4,
        "hold_deadline": 5,
        "distance_progress_by_turn": [],
        "rejection_codes": [],
        "unsupported_reasons": [],
        "structural_reasons": [],
        "parser_source": "TEST_EXACT",
        "metric_exception": None,
        "c2_trace_rule_version": "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
    }


def passing_traces(
    *,
    strict_count: int = 24,
    chance_count: int = 40,
    agreements: int = 12,
    completes: int = 8,
) -> list[dict]:
    values = []
    for index in range(strict_count + chance_count):
        values.append(
            trace(
                index,
                "STRICT" if index < strict_count else "PRESERVE_CHANCE",
                agreement=index < agreements,
                complete=index < completes,
            )
        )
    return values


class C4SidecarCollectorTests(unittest.TestCase):
    opponents = ("alakazam_mirror", "alpha_deck", "beta_deck")

    def write_suite(
        self,
        root: Path,
        traces: list[dict],
        *,
        version: str = "candidate",
        opponents: tuple[str, ...] | None = None,
        all_seat: int | None = None,
        placements: list[tuple[str, int]] | None = None,
        observations: list[dict] | None = None,
        bind_public: bool = True,
    ) -> list[Path]:
        opponents = opponents or self.opponents
        paths = []
        for index, value in enumerate(traces):
            if placements is None:
                opponent = opponents[index % len(opponents)]
                seat = index % 2 if all_seat is None else all_seat
            else:
                opponent, seat = placements[index]
            observation = (
                copy.deepcopy(observations[index])
                if observations is not None
                else metric_observation(index, seat)
            )
            bound_value = (
                rebind_trace_public(value, observation)
                if bind_public
                else copy.deepcopy(value)
            )
            game = index
            seed_base = 1000
            common = {
                "version": version,
                "opponent": opponent,
                "policy_seat": seat,
                "seed_base": seed_base,
                "seed": seed_base + game,
                "game": game,
                "callback_ordinal": 0,
            }
            rows = [
                {
                    **common,
                    "event": "CALL_START",
                    "observation": observation,
                },
                {
                    **common,
                    "event": "CALL_END",
                    "selected_action": [0],
                    "structurally_valid": True,
                    "exception": None,
                    "version_trace_name": "LAST_STAGED_POLICY_TRACE",
                    "version_trace": bound_value,
                },
            ]
            path = (
                root
                / "runs"
                / version
                / opponent
                / f"seed_{seed_base}"
                / f"seat_{seat}"
                / "sidecars"
                / f"game_{game:04d}.jsonl"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "".join(
                    json.dumps(row, sort_keys=True) + "\n" for row in rows
                ),
                encoding="utf-8",
                newline="\n",
            )
            paths.append(path)
        return paths

    def collect(self, root: Path | list[Path]):
        return collector.collect_suite(
            root, expected_candidate_closure=CLOSURE
        )

    def mutate_end(self, path: Path, mutation) -> None:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        mutation(rows[1])
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )

    def test_complete_threshold_suite_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(root, passing_traces())
            rows, summary = self.collect(root)
        self.assertEqual(len(rows), 64)
        self.assertEqual(summary["strict_unique_state_count"], 24)
        self.assertEqual(summary["preserve_chance_unique_state_count"], 40)
        self.assertEqual(summary["natural_parent_agreement_count"], 12)
        self.assertEqual(
            summary["trace_complete_observed_wall_outcome_count"], 8
        )
        self.assertEqual(summary["overall_gate"], "PASS")
        self.assertFalse(summary["counterfactual_counted_as_success"])
        self.assertFalse(summary["win_rate_aggregated"])
        self.assertFalse(
            summary["json_object_identity_independently_reconstructable"]
        )

    def test_required_closure_and_shortfall_semantics(self):
        with self.assertRaises(TypeError):
            collector.collect_suite(Path("."))
        for bad in ("c" * 64, "C" * 63, ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                collector.collect_suite(
                    Path("."), expected_candidate_closure=bad
                )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(root, [trace(0, "STRICT")])
            _, summary = self.collect(root)
        self.assertEqual(summary["integrity_gate"], "PASS")
        self.assertEqual(summary["overall_gate"], "INSUFFICIENT_EVIDENCE")

    def test_independent_integrity_mutations_fail(self):
        mutations = {
            "sparse": lambda end: end["version_trace"].pop("threat"),
            "rule": lambda end: end["version_trace"].update(
                rule_version="WRONG"
            ),
            "parent_closure": lambda end: end["version_trace"].update(
                parent_closure_sha256="A" * 64
            ),
            "candidate_closure": lambda end: end["version_trace"].update(
                candidate_closure_sha256="D" * 64
            ),
            "analyzer": lambda end: end["version_trace"].update(
                analyzer_component_sha256="A" * 64
            ),
            "metric": lambda end: end["version_trace"].update(
                metric_exception="RuntimeError"
            ),
            "selected_value": lambda end: end.update(selected_action=[1]),
            "selected_bool": lambda end: end.update(selected_action=[True]),
            "type": lambda end: end["version_trace"].update(
                action_python_type="builtins.tuple"
            ),
            "order": lambda end: end["version_trace"]["action_identity"].update(
                order_equal=False
            ),
            "self_identity": lambda end: end["version_trace"][
                "action_identity"
            ].update(returned_parent_object_unchanged=False),
            "structural": lambda end: end.update(structurally_valid=False),
            "wrapper": lambda end: end.update(exception="RuntimeError"),
            "strict_with_unsupported": lambda end: end["version_trace"][
                "candidate_rows"
            ][1]["unsupported_reasons"].append("UNSUPPORTED"),
            "candidate_applied": lambda end: end["version_trace"].update(
                outcome_status="CANDIDATE_APPLIED"
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "suite"
                path = self.write_suite(
                    root, [trace(0, "STRICT")]
                )[0]
                self.mutate_end(path, mutation)
                _, summary = self.collect(root)
                self.assertEqual(summary["overall_gate"], "FAIL")

    def test_each_reach_gate_is_independently_observable(self):
        cases = {
            "strict_states": (
                passing_traces(strict_count=23, chance_count=41),
                {},
            ),
            "chance_states": (
                passing_traces(strict_count=25, chance_count=39),
                {},
            ),
            "both_seats": (passing_traces(), {"all_seat": 0}),
            "three_opponents": (
                passing_traces(),
                {"opponents": ("alpha_deck", "beta_deck")},
            ),
            "two_non_mirror": (
                passing_traces(),
                {
                    "opponents": (
                        "alakazam_mirror",
                        "other_mirror",
                        "alpha_deck",
                    )
                },
            ),
            "natural_agreements": (
                passing_traces(agreements=11, completes=8),
                {},
            ),
            "complete_outcomes": (
                passing_traces(agreements=12, completes=7),
                {},
            ),
        }
        strict_bucket_placements = [
            (
                "alpha_deck"
                if index < 24
                else self.opponents[index % len(self.opponents)],
                index % 2,
            )
            for index in range(64)
        ]
        cases["two_strict_buckets"] = (
            passing_traces(),
            {"placements": strict_bucket_placements},
        )
        for gate, (values, kwargs) in cases.items():
            with self.subTest(gate=gate), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "suite"
                self.write_suite(root, values, **kwargs)
                _, summary = self.collect(root)
                self.assertEqual(summary["integrity_gate"], "PASS")
                self.assertEqual(
                    summary["reach_checks"][gate],
                    "INSUFFICIENT_EVIDENCE",
                )

    def test_same_pair_in_another_game_does_not_inflate_state_count(self):
        first = trace(0, "STRICT")
        second = copy.deepcopy(first)
        second["decision_id"] = digest("decision:other-game")
        second["outcome_events"] = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(
                root,
                [first, second],
                all_seat=0,
                observations=[
                    metric_observation(0, 0),
                    metric_observation(0, 0),
                ],
            )
            _, summary = self.collect(root)
        self.assertEqual(summary["strict_unique_state_count"], 1)
        self.assertEqual(summary["same_pair_additional_game_count"], 1)

    def test_outcomes_cannot_be_joined_across_games(self):
        first = trace(0, "STRICT", agreement=True, complete=False)
        second = trace(1, "STRICT")
        second["outcome_events"] = [
            event
            for event in outcome_events(
                first["decision_id"], complete=True
            )
            if event["event"] != "PARENT_AGREEMENT"
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(root, [first, second])
            _, summary = self.collect(root)
        self.assertEqual(summary["overall_gate"], "FAIL")
        self.assertEqual(summary["orphan_outcome_event_group_count"], 1)
        self.assertEqual(
            summary["trace_complete_observed_wall_outcome_count"], 0
        )

    def test_multi_suite_manifest_is_order_independent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            suite_a = root / "suite_a"
            suite_b = root / "suite_b"
            self.write_suite(
                suite_a, [trace(0, "STRICT")], version="candidate_a"
            )
            self.write_suite(
                suite_b, [trace(1, "PRESERVE_CHANCE")], version="candidate_b"
            )
            _, first = self.collect([suite_b, suite_a])
            _, second = self.collect([suite_a, suite_b])
        self.assertEqual(first["suite_count"], 2)
        self.assertEqual(
            first["input_manifest_sha256"],
            second["input_manifest_sha256"],
        )
        self.assertEqual(first["input_files"], second["input_files"])

    def test_cross_suite_duplicates_empty_inputs_and_order_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            suite_a = root / "suite_a"
            suite_b = root / "suite_b"
            self.write_suite(suite_a, [trace(0, "STRICT")])
            self.write_suite(suite_b, [trace(0, "STRICT")])
            _, duplicate = self.collect([suite_a, suite_b])
            self.assertEqual(duplicate["overall_gate"], "FAIL")
            self.assertGreater(duplicate["duplicate_callback_key_count"], 0)

        with tempfile.TemporaryDirectory() as temp:
            empty_suite = Path(temp) / "empty"
            empty_suite.mkdir()
            _, empty = self.collect(empty_suite)
            self.assertEqual(empty["overall_gate"], "FAIL")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            path = self.write_suite(root, [trace(0, "STRICT")])[0]
            path.write_text("", encoding="utf-8")
            _, empty_sidecar = self.collect(root)
            self.assertEqual(empty_sidecar["overall_gate"], "FAIL")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            path = self.write_suite(root, [trace(0, "STRICT")])[0]
            rows = path.read_text(encoding="utf-8").splitlines()
            path.write_text(
                rows[1] + "\n" + rows[0] + "\n",
                encoding="utf-8",
                newline="\n",
            )
            _, out_of_order = self.collect(root)
            self.assertEqual(out_of_order["overall_gate"], "FAIL")
            self.assertGreater(
                out_of_order["callback_end_order_fault_count"], 0
            )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            path = self.write_suite(root, [trace(0, "STRICT")])[0]
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            for row in rows:
                row["callback_ordinal"] = 1
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
                newline="\n",
            )
            _, ordinal_gap = self.collect(root)
            self.assertEqual(ordinal_gap["overall_gate"], "FAIL")
            self.assertGreater(
                ordinal_gap["callback_end_order_fault_count"], 0
            )

    def test_checked_writer_and_raw_fixture_use_zero_based_ordinals(self):
        writer = CHECKED_WRITER.read_text(encoding="utf-8")
        self.assertIn("callback_ordinal = 0", writer)
        raw = [
            json.loads(line)
            for line in RAW_SIDECAR_FIXTURE.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
        self.assertGreaterEqual(len(raw), 2)
        self.assertEqual(
            [raw[0]["event"], raw[1]["event"]],
            ["CALL_START", "CALL_END"],
        )
        self.assertEqual(
            [raw[0]["callback_ordinal"], raw[1]["callback_ordinal"]],
            [0, 0],
        )
        suite = RAW_SIDECAR_FIXTURE.parents[6]
        identity = collector._path_identity(
            suite, RAW_SIDECAR_FIXTURE
        )
        start_ok, start_key = collector._event_identity(raw[0], identity)
        end_ok, end_key = collector._event_identity(raw[1], identity)
        self.assertTrue(start_ok)
        self.assertTrue(end_ok)
        self.assertEqual(start_key, end_key)
        self.assertEqual(start_key[-1], 0)

    def test_pair_id_is_recomputed_and_same_state_cannot_be_faked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            path = self.write_suite(root, [trace(0, "STRICT")])[0]
            self.mutate_end(
                path,
                lambda end: end["version_trace"].update(
                    pair_id=digest("supplied-fake-pair")
                ),
            )
            _, summary = self.collect(root)
        self.assertEqual(summary["overall_gate"], "FAIL")
        self.assertEqual(summary["strict_unique_state_count"], 0)

        values = []
        shared = trace(0, "STRICT")
        for index in range(64):
            value = copy.deepcopy(shared)
            value["decision_id"] = digest(f"fake-decision:{index}")
            value["pair_id"] = digest(f"fake-pair:{index}")
            value["outcome_events"] = []
            value["outcome_status"] = "COUNTERFACTUAL_UNOBSERVED"
            values.append(value)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(
                root,
                values,
                all_seat=0,
                observations=[
                    metric_observation(0, 0) for _ in values
                ],
                bind_public=False,
            )
            _, summary = self.collect(root)
        self.assertEqual(summary["overall_gate"], "FAIL")
        self.assertEqual(summary["strict_unique_state_count"], 0)
        self.assertEqual(summary["preserve_chance_unique_state_count"], 0)

    def test_strict_metric_fields_are_fail_closed(self):
        mutations = {
            "protected_readiness": lambda metrics: metrics.update(
                protected_readiness=None
            ),
            "remaining_hp": lambda metrics: metrics.update(
                remaining_hp=None
            ),
            "safety_cap": lambda metrics: metrics.update(
                final_safety_cap=None
            ),
            "margin": lambda metrics: metrics.update(
                survival_margin=69
            ),
            "deadline": lambda metrics: metrics.update(hold_deadline=6),
            "hold": lambda metrics: metrics.update(hold_turns=None),
            "prize": lambda metrics: metrics.update(own_prize_loss=None),
            "gust": lambda metrics: metrics.update(gust_exposure=None),
            "resource": lambda metrics: metrics.update(resource_loss=None),
            "draw": lambda metrics: metrics.update(lost_draw3=None),
            "final_prize": lambda metrics: metrics.update(
                final_prize_outcome=True
            ),
            "safe_release": lambda metrics: metrics.update(
                safe_release=None
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "suite"
                path = self.write_suite(
                    root, [trace(0, "STRICT")]
                )[0]

                def mutate(end):
                    metrics = end["version_trace"]["candidate_rows"][1][
                        "metrics"
                    ]
                    mutation(metrics)

                self.mutate_end(path, mutate)
                _, summary = self.collect(root)
                self.assertEqual(summary["overall_gate"], "FAIL")

    def test_run_away_and_trading_metrics_require_mechanism_specific_fields(self):
        semantic_key = {
            "type": 3,
            "serial": 201,
            "card_id": 66,
            "area": 5,
        }
        run = candidate_rows("STRICT", semantic_key)[0]
        run.update(
            {
                "legality": "EXACT",
                "wall": {"serial": 201, "card_id": 66},
                "metrics": {
                    "certified_draw_count": 3,
                    "certified_draw_damage_delta": 60,
                    "drawn_card_identities": "POSSIBLE",
                    "conversion": {
                        "promotion_serial": 299,
                        "damage": 160,
                        "ko": True,
                        "terminal_win": False,
                        "safe_prize_exchange": False,
                        "attack_id": 1072,
                        "attack_binding": "TEST_EXACT_ATTACK",
                        "target_serial": 310,
                        "target_prize_value": 1,
                        "conversion": "CURRENT_REPEATABLE_THREAT_KO",
                    },
                },
            }
        )
        self.assertTrue(
            collector._strict_wall_metrics_ok(
                run, "RUN_AWAY_ACCELERATION"
            )
        )
        for path, value in (
            (("certified_draw_count",), None),
            (("certified_draw_damage_delta",), 40),
            (("conversion", "ko"), None),
            (("conversion", "attack_binding"), None),
            (("conversion", "target_prize_value"), None),
        ):
            with self.subTest(run_path=path):
                malformed = copy.deepcopy(run)
                target = malformed["metrics"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assertFalse(
                    collector._strict_wall_metrics_ok(
                        malformed, "RUN_AWAY_ACCELERATION"
                    )
                )

        sacrifice = copy.deepcopy(
            candidate_rows("STRICT", semantic_key)[1]
        )
        sacrifice["kind"] = "CERTIFIED_SACRIFICE_WALL"
        sacrifice["wall"] = {"serial": 201, "card_id": 305}
        sacrifice["metrics"]["own_prize_loss"] = 1
        sacrifice["metrics"]["lost_draw3"] = 0
        release = sacrifice["metrics"]["safe_release"]
        release.update(
            {
                "reason": "EXACT_TRADING_POST_ATTACK_SAFE_EXCHANGE",
                "release_mode": "TRADING_PLACES_POST_ATTACK",
                "backup_serial": 399,
                "opponent_safety_cap": 70,
                "immediate_opponent_threat": {
                    "status": "SUPPORTED",
                    "continuity": "REPEATABLE_READY",
                    "final_safety_cap": 40,
                    "unsupported_reasons": [],
                },
            }
        )
        release["post_release_opponent_envelope"][
            "final_safety_cap"
        ] = 30
        release["release_target"].update(
            combined_safety_cap=70,
            own_prize_value=1,
        )
        self.assertTrue(
            collector._strict_wall_metrics_ok(
                sacrifice, "CERTIFIED_SACRIFICE_WALL"
            )
        )
        for path, value in (
            (("release_mode",), None),
            (("backup_serial",), None),
            (("immediate_opponent_threat", "continuity"), None),
            (("release_target", "combined_safety_cap"), 69),
            (("release_target", "own_prize_value"), 2),
        ):
            with self.subTest(sacrifice_path=path):
                malformed = copy.deepcopy(sacrifice)
                target = malformed["metrics"]["safe_release"]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assertFalse(
                    collector._strict_wall_metrics_ok(
                        malformed, "CERTIFIED_SACRIFICE_WALL"
                    )
                )

    def test_parent_agreement_requires_exact_semantic_parent_mechanism(self):
        mutations = {
            "proposed_serial": lambda value: value[
                "semantic_proposed_action_keys"
            ][0].update(serial=999),
            "parent_serial": lambda value: value[
                "semantic_parent_action_keys"
            ][0].update(serial=999),
            "chosen_serial": lambda value: value["candidate_rows"][1][
                "semantic_action_key"
            ].update(serial=999),
            "chosen_class": lambda value: value.update(
                wall_class=collector.CHANCE
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "suite"
                path = self.write_suite(
                    root,
                    [trace(0, "STRICT", agreement=True)],
                )[0]
                self.mutate_end(
                    path,
                    lambda end: mutation(end["version_trace"]),
                )
                _, summary = self.collect(root)
                self.assertEqual(summary["overall_gate"], "FAIL")

    def test_each_adverse_outcome_is_a_counterexample(self):
        base = trace(0, "STRICT", agreement=True)
        decision = {"row": base["candidate_rows"][1]}
        decision_id = base["decision_id"]
        agreement = {
            "event": "PARENT_AGREEMENT",
            "decision_id": decision_id,
            "turn": 4,
        }
        release = {
            "event": "RUN_AWAY_RELEASED",
            "decision_id": decision_id,
            "source_serial": 201,
            "turn": 5,
        }
        protected_promotion = {
            "event": "PROMOTION_DESTINATION",
            "decision_id": decision_id,
            "destination_serial": 299,
            "destination_card_id": 743,
            "protected_destination": True,
            "turn": 5,
        }
        protected_attack = {
            "event": "PROTECTED_ATTACKER_ATTACKED",
            "decision_id": decision_id,
            "attacker_serial": 299,
            "attack_id": 1072,
            "turn": 6,
        }
        cases = {
            "GUST_OR_SNIPE_BYPASS": [
                agreement,
                {
                    "event": "GUST_OR_SNIPE_BYPASS",
                    "decision_id": decision_id,
                    "turn": 5,
                },
            ],
            "REFUSAL_WITHOUT_PROGRESS": [
                agreement,
                {
                    "event": "OPPONENT_REFUSED",
                    "decision_id": decision_id,
                    "wall_serial": 201,
                    "turn": 5,
                },
            ],
            "UNSAFE_RELEASE_DESTINATION": [
                agreement,
                release,
                {
                    **protected_promotion,
                    "destination_serial": 999,
                    "protected_destination": False,
                },
            ],
            "PROTECTED_NOT_READY_AFTER_RELEASE": [
                agreement,
                release,
                protected_promotion,
                {
                    "event": "GAME_END",
                    "decision_id": decision_id,
                    "result": 0,
                    "turn": 6,
                },
            ],
            "OPPONENT_CONTINUITY_FAILURE": [
                agreement,
                release,
                protected_promotion,
                protected_attack,
                {
                    "event": "GAME_END",
                    "decision_id": decision_id,
                    "result": 1,
                    "turn": 7,
                },
            ],
        }
        for expected, events in cases.items():
            with self.subTest(expected=expected):
                valid, observed = collector._outcome_semantics(
                    decision, copy.deepcopy(events)
                )
                self.assertTrue(valid)
                self.assertIn(expected, observed)

        invalid_wall = [
            agreement,
            {
                "event": "WALL_ACTIVE",
                "decision_id": decision_id,
                "wall_serial": 999,
                "turn": 5,
            },
        ]
        invalid_order = [
            agreement,
            {
                **protected_promotion,
                "turn": 4,
            },
        ]
        self.assertFalse(
            collector._outcome_semantics(decision, invalid_wall)[0]
        )
        self.assertFalse(
            collector._outcome_semantics(decision, invalid_order)[0]
        )

    def test_one_counterexample_blocks_otherwise_passing_suite(self):
        values = passing_traces()
        adverse = values[8]
        adverse["outcome_events"].append(
            {
                "event": "GUST_OR_SNIPE_BYPASS",
                "decision_id": adverse["decision_id"],
                "turn": 5,
            }
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(root, values)
            _, summary = self.collect(root)
        self.assertEqual(summary["integrity_gate"], "PASS")
        self.assertEqual(
            summary["reach_checks"]["no_counterexamples"],
            "INSUFFICIENT_EVIDENCE",
        )
        self.assertEqual(summary["observed_counterexample_count"], 1)
        self.assertEqual(
            summary["observed_counterexamples"],
            ["GUST_OR_SNIPE_BYPASS"],
        )
        self.assertEqual(summary["overall_gate"], "INSUFFICIENT_EVIDENCE")

    def test_raw_observation_binding_rejects_trace_nonces_without_inflation(self):
        observation = metric_observation(0, 0)
        values = []
        for index in range(64):
            value = rebind_trace_public(
                trace(0, "STRICT"), observation
            )
            value["decision_id"] = digest(f"raw-nonce-decision:{index}")
            value["public_state_material"] = {
                **copy.deepcopy(value["public_state_material"]),
                "nonce": index,
            }
            value["public_state_fingerprint"] = collector._fingerprint(
                value["public_state_material"]
            )
            value["pair_material"]["public_state_fingerprint"] = value[
                "public_state_fingerprint"
            ]
            value["pair_id"] = collector._fingerprint(
                value["pair_material"]
            )
            value["outcome_status"] = "COUNTERFACTUAL_UNOBSERVED"
            value["outcome_events"] = []
            values.append(value)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(
                root,
                values,
                all_seat=0,
                observations=[copy.deepcopy(observation) for _ in values],
                bind_public=False,
            )
            _, summary = self.collect(root)
        self.assertEqual(summary["overall_gate"], "FAIL")
        self.assertEqual(summary["raw_public_state_binding_fault_count"], 64)
        self.assertEqual(summary["strict_unique_state_count"], 0)
        self.assertEqual(summary["preserve_chance_unique_state_count"], 0)

    def test_production_base_trace_is_valid_nondecision_evidence(self):
        raw = json.loads(
            DURABLE_OBSERVATION.read_text(encoding="utf-8")
        )["observation"]
        spec = importlib.util.spec_from_file_location(
            "_c4_checked_writer_for_test", CHECKED_WRITER
        )
        writer = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(writer)
        observation = writer.observation_snapshot(raw)
        value = c4._base_trace(raw, [0], None)
        value["candidate_closure_sha256"] = CLOSURE
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "suite"
            self.write_suite(
                root,
                [value],
                all_seat=raw["current"]["yourIndex"],
                observations=[observation],
                bind_public=False,
            )
            _, summary = self.collect(root)
        self.assertEqual(summary["integrity_gate"], "PASS")
        self.assertEqual(summary["overall_gate"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(summary["sparse_trace_or_row_fault_count"], 0)
        self.assertEqual(summary["raw_public_state_binding_fault_count"], 0)

    def test_cli_exit_codes_distinguish_integrity_from_shortfall(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            suite = root / "suite"
            path = self.write_suite(suite, [trace(0, "STRICT")])[0]
            rows_out = root / "rows.jsonl"
            summary_out = root / "summary.json"
            argv = [
                "collector",
                str(suite),
                "--rows-out",
                str(rows_out),
                "--summary-out",
                str(summary_out),
                "--candidate-closure",
                CLOSURE,
            ]
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(
                io.StringIO()
            ):
                self.assertEqual(collector.main(), 0)
            self.assertEqual(
                json.loads(summary_out.read_text(encoding="utf-8"))[
                    "overall_gate"
                ],
                "INSUFFICIENT_EVIDENCE",
            )

            self.mutate_end(
                path,
                lambda end: end["version_trace"].update(
                    candidate_closure_sha256="D" * 64
                ),
            )
            with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(
                io.StringIO()
            ):
                self.assertEqual(collector.main(), 2)


if __name__ == "__main__":
    unittest.main()
