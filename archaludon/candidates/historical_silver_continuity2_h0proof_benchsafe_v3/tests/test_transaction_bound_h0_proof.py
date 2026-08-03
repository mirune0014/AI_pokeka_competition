import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CANDIDATE_DIR))
sys.path.insert(0, str(TEST_DIR))

import main  # noqa: E402
import test_continuity2_phase_b as phase_b  # noqa: E402


def pokemon(card_id, serial, hp, max_hp, player_index, energies=(), pre=()):
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": player_index,
        "hp": hp,
        "maxHp": max_hp,
        "appearThisTurn": False,
        "energies": list(energies),
        "energyCards": [
            {
                "id": main.METAL_ENERGY,
                "serial": serial * 10 + index,
                "playerIndex": player_index,
            }
            for index, _ in enumerate(energies)
        ],
        "tools": [],
        "preEvolution": list(pre),
    }


def turbo_pair(kind="normal"):
    if kind == "normal":
        return (
            phase_b.observation(86160574, 28, 1),
            phase_b.observation(86160574, 29, 1),
        )
    start = phase_b.observation(86160574, 28, 1)
    start["select"]["option"] = [
        {"type": int(main.OptionType.ATTACK), "attackId": 965},
        {"type": int(main.OptionType.END)},
    ]
    own = start["current"]["players"][1]
    own["bench"][0] = pokemon(
        main.ARCHALUDON_EX,
        640,
        300,
        300,
        1,
        (8, 8) if kind == "checkup_cornerstone" else (),
        ({"id": main.DURALUDON, "serial": 64, "playerIndex": 1},),
    )
    opponent = start["current"]["players"][0]
    if kind == "checkup_cornerstone":
        opponent["active"] = [pokemon(119, 170, 70, 70, 0)]
        opponent["bench"] = [
            pokemon(main.CORNERSTONE_OGERPON_EX, 171, 210, 210, 0)
        ]
        opponent["burned"] = True
        callback_hp = 20
    elif kind == "direct_ko":
        opponent["active"] = [pokemon(119, 170, 50, 70, 0)]
        opponent["bench"] = [pokemon(119, 171, 70, 70, 0)]
        opponent["burned"] = False
        callback_hp = 0
    else:
        raise AssertionError(kind)
    callback = phase_b.observation(86160574, 29, 1)
    callback["current"] = copy.deepcopy(start["current"])
    callback["current"]["players"][0]["active"][0]["hp"] = callback_hp
    return start, callback


def acceleration_owners(trace):
    return {
        row["token"]: row.get("owner")
        for row in trace["ledger"]["resources"]
        if row["token"].startswith("capability:")
        or row["token"].startswith("effect_energy:")
    }


class TransactionBoundH0ProofTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None
        os.environ.pop(main._CONTINUITY_TRACE_ENV, None)

    def test_checkup_ko_cornerstone_uses_frozen_branch_and_safe_non_ex_line(self):
        start, callback = turbo_pair("checkup_cornerstone")
        self.assertEqual(main.agent(copy.deepcopy(start)), [0])
        proof = copy.deepcopy(main._CONTINUITY_PENDING["h0_proof"])
        self.assertEqual(proof["envelope"]["h0_outgoing"]["transition"], "CHECKUP_KO")
        self.assertEqual(
            [row["card_id"] for row in proof["envelope"]["post_response_active_candidates"]],
            [main.CORNERSTONE_OGERPON_EX],
        )
        provisional = main._CONTINUITY_PENDING["provisional_target"]
        self.assertEqual(provisional["line_key"], "p1:line:169:65")
        self.assertEqual(provisional["attack_id"], main.RAGING_HAMMER)
        self.assertEqual(
            provisional["response_survival_marker"], "RESPONSE_SURVIVAL_READY"
        )

        self.assertEqual(main.agent(copy.deepcopy(callback)), [0, 1, 2])
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(trace["H1_after_KO"]["readiness"], "READY_AFTER_TURBO")
        self.assertEqual(trace["H1_after_KO"]["identity"]["line_key"], "p1:line:169:65")
        self.assertNotEqual(trace["H1_after_KO"]["identity"]["line_key"], "p1:line:169:64")
        self.assertEqual(
            trace["H1_after_KO"]["attack"]["attack_id"], main.RAGING_HAMMER
        )
        self.assertEqual(
            trace["H1_after_KO"]["response_survival_marker"],
            "RESPONSE_SURVIVAL_READY",
        )
        target_serials = {
            row["target_serial"]
            for row in trace["H1_after_KO"]["h1_primary_gate"]["target_results"]
            if not row["terminal"]
        }
        self.assertEqual(target_serials, {171})
        owners = acceleration_owners(trace)
        self.assertEqual(
            {token for token in owners if token.startswith("effect_energy:")},
            {"effect_energy:93", "effect_energy:117", "effect_energy:113"},
        )

    def test_direct_ko_ignores_stale_zero_hp_active_and_uses_promoted_responder(self):
        start, callback = turbo_pair("direct_ko")
        self.assertEqual(main.agent(copy.deepcopy(start)), [0])
        first = copy.deepcopy(main._CONTINUITY_PENDING)
        self.assertEqual(main.agent(copy.deepcopy(callback)), [0, 1, 2])
        updated = main._CONTINUITY_PENDING
        self.assertEqual(
            updated["h0_proof"]["proof_sha256"],
            first["h0_proof"]["proof_sha256"],
        )
        self.assertEqual(
            updated["h0_proof"]["post_response_targets_sha256"],
            first["h0_proof"]["post_response_targets_sha256"],
        )
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(trace["H1_after_KO"]["readiness"], "READY_AFTER_TURBO")
        target_serials = {
            row["target_serial"]
            for row in trace["H1_after_KO"]["h1_primary_gate"]["target_results"]
            if not row["terminal"]
        }
        self.assertEqual(target_serials, {171})
        self.assertNotIn(170, target_serials)

    def test_normal_surviving_target_turbo_lifecycle_stays_positive(self):
        start, callback = turbo_pair("normal")
        self.assertEqual(main.agent(start), [0])
        proof_hash = main._CONTINUITY_PENDING["h0_proof"]["proof_sha256"]
        self.assertEqual(main.agent(callback), [0, 1, 2])
        self.assertEqual(
            main._CONTINUITY_PENDING["h0_proof"]["proof_sha256"], proof_hash
        )
        self.assertEqual(
            main.CONTINUITY_LATEST_TRACE["H1_after_KO"]["readiness"],
            "READY_AFTER_TURBO",
        )
        self.assertEqual(
            len(main._CONTINUITY_PENDING["assigned_energy"]), 3
        )

    def test_turbo_attack_locks_choose_ready_zero_cost_retreat_without_proof(self):
        for state in ("confused", "asleep", "paralyzed", "turn1"):
            with self.subTest(state=state):
                self.setUp()
                raw = phase_b.observation(86160574, 28, 1)
                player = raw["current"]["players"][1]
                phase_b.set_energy(player["bench"][0], 3, 1, 99000)
                raw["current"]["players"][0]["active"][0]["hp"] = 50
                raw["select"]["option"].append(
                    {"type": int(main.OptionType.RETREAT)}
                )
                if state == "turn1":
                    raw["current"]["turn"] = 1
                    raw["current"]["firstPlayer"] = 1
                else:
                    player[state] = True
                plan = main.build_continuity2_plan(
                    main.to_observation_class(copy.deepcopy(raw))
                )
                self.assertNotEqual(
                    (plan.get("choice") or {}).get("kind"), "TURBO_VISIBLE_KO"
                )
                self.assertEqual(plan["choice"]["kind"], "RETREAT_BOUND_ROUTE")
                self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
                self.assertEqual(main._CONTINUITY_PENDING["kind"], "RETREAT")
                self.assertEqual(
                    main._CONTINUITY_PENDING["h0_proof_policy"], "FORBIDDEN"
                )
                self.assertIsNone(main._CONTINUITY_PENDING["h0_proof"])

    def test_exact_ready_direct_ko_still_precedes_development_retreat_and_seals(self):
        raw = phase_b.observation(86160574, 28, 1)
        player = raw["current"]["players"][1]
        phase_b.set_energy(player["bench"][0], 3, 1, 99100)
        raw["current"]["players"][0]["active"][0]["hp"] = 50
        raw["select"]["option"].append({"type": int(main.OptionType.RETREAT)})
        self.assertEqual(main.agent(copy.deepcopy(raw)), [0])
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["choice"]["kind"], "TURBO_VISIBLE_KO")
        self.assertEqual(main._CONTINUITY_PENDING["kind"], "TURBO")
        self.assertEqual(
            main._CONTINUITY_PENDING["h0_proof_policy"],
            "REQUIRED_FOR_POSITIVE_CONTINUITY",
        )
        self.assertIsNotNone(main._CONTINUITY_PENDING["h0_proof"])

    def test_each_proof_or_scope_mutation_abandons_before_reservation(self):
        def mutate_envelope(transaction):
            transaction["h0_proof"]["envelope"]["unknown"] = True

        def mutate_target_hash(transaction):
            transaction["h0_proof"]["post_response_targets_sha256"] = "0" * 64

        def mutate_proof_hash(transaction):
            transaction["h0_proof"]["proof_sha256"] = "1" * 64

        def mutate_effect(transaction):
            transaction["effect_serial"] += 1

        def mutate_source(transaction):
            transaction["source_active_line"] += ":mutated"

        def mutate_turn(transaction):
            transaction["turn"] += 1

        def mutate_trigger_hash(transaction):
            transaction["h0_proof"]["trigger_key_sha256"] = "2" * 64

        cases = {
            "envelope": mutate_envelope,
            "target_hash": mutate_target_hash,
            "proof_hash": mutate_proof_hash,
            "effect_serial": mutate_effect,
            "source_lineage": mutate_source,
            "turn": mutate_turn,
            "trigger_hash": mutate_trigger_hash,
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                self.setUp()
                start, callback = turbo_pair("normal")
                self.assertEqual(main.agent(start), [0])
                mutate(main._CONTINUITY_PENDING)
                self.assertEqual(main.agent(callback), [])
                trace = main.CONTINUITY_LATEST_TRACE
                self.assertTrue(
                    trace["pending_event"]["reason"].startswith(
                        "ABANDON_H0_PROOF_"
                    )
                )
                self.assertEqual(acceleration_owners(trace), {})
                self.assertIsNone(main._CONTINUITY_PENDING)

    def test_pendingless_turbo_cannot_reconstruct_positive_certificate(self):
        _, callback = turbo_pair("normal")
        self.assertEqual(main.agent(callback), [])
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(trace["choice"]["kind"], "H0_PROOF_FAIL_CLOSED_ZERO")
        self.assertNotEqual(trace["H1_after_KO"]["readiness"], "READY_AFTER_TURBO")
        self.assertIsNone(trace["h0_proof_sha256"])
        self.assertEqual(acceleration_owners(trace), {})

    def test_planner_alloy_keeps_one_proof_through_every_child_callback(self):
        hashes = []
        envelope_hashes = []
        for step in (35, 36, 37, 38, 39):
            raw = phase_b.observation(86160056, step, 0)
            player = raw["current"]["players"][0]
            phase_b.set_energy(player["active"][0], 2, 0, 99420)
            if player["bench"]:
                phase_b.set_energy(player["bench"][0], 2, 0, 99430)
            if step == 35:
                player["hand"].append(
                    {"id": main.METAL_ENERGY, "serial": 99450, "playerIndex": 0}
                )
                player["handCount"] = len(player["hand"])
            expected = {35: [0], 36: [0], 37: [0, 1], 38: [0], 39: [1]}
            self.assertEqual(main.agent(copy.deepcopy(raw)), expected[step])
            proof = main._CONTINUITY_PENDING["h0_proof"]
            hashes.append(proof["proof_sha256"])
            envelope_hashes.append(proof["envelope_sha256"])
            if step > 35:
                self.assertEqual(
                    main.CONTINUITY_LATEST_TRACE["callback_envelope_source"],
                    "TRANSACTION_FROZEN_PRE_H0",
                )
        self.assertEqual(len(set(hashes)), 1)
        self.assertEqual(len(set(envelope_hashes)), 1)
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(
            {row["role"] for row in main._CONTINUITY_PENDING["target_queue"]},
            {"H0", "H1_after_KO"},
        )
        self.assertEqual(trace["envelope_sha256"], envelope_hashes[0])

    def test_pendingless_alloy_is_action_valid_but_never_certified(self):
        activate = phase_b.observation(86160056, 36, 0)
        self.assertEqual(main.agent(activate), [1])
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(trace["choice"]["kind"], "ALLOY_DECLINE")
        self.assertIsNone(trace["h0_proof_sha256"])
        self.assertNotIn(
            trace["H1_after_KO"]["readiness"],
            {"READY_AFTER_ALLOY_NOW", "READY_AFTER_EVOLVE_ALLOY"},
        )
        self.assertEqual(acceleration_owners(trace), {})

        self.setUp()
        attach = phase_b.observation(86160056, 37, 0)
        action = main.agent(attach)
        self.assertGreaterEqual(len(action), attach["select"]["minCount"])
        self.assertLessEqual(len(action), attach["select"]["maxCount"])
        self.assertIsNone(main.CONTINUITY_LATEST_TRACE["h0_proof_sha256"])
        self.assertEqual(acceleration_owners(main.CONTINUITY_LATEST_TRACE), {})

    def test_retreat_transactions_never_carry_h0_proof(self):
        fixture = phase_b.Continuity2PhaseBTests()
        paid, first, _, _ = fixture._paid_retreat_observations()
        self.assertEqual(main.agent(copy.deepcopy(paid)), [0])
        self.assertEqual(main._CONTINUITY_PENDING["h0_proof_policy"], "FORBIDDEN")
        self.assertIsNone(main._CONTINUITY_PENDING["h0_proof"])
        self.assertEqual(main.agent(copy.deepcopy(first)), [0])
        self.assertIsNone(main._CONTINUITY_PENDING["h0_proof"])

        self.setUp()
        self.assertEqual(main.agent(phase_b.observation(86160574, 48, 1)), [10])
        self.assertEqual(main._CONTINUITY_PENDING["h0_proof_policy"], "FORBIDDEN")
        self.assertIsNone(main._CONTINUITY_PENDING["h0_proof"])
        self.assertEqual(main.agent(phase_b.observation(86160574, 49, 1)), [0])
        self.assertIsNone(main._CONTINUITY_PENDING["h0_proof"])

        self.setUp()
        self.assertEqual(main.agent(phase_b.observation(86160574, 28, 1)), [0])
        self.assertEqual(
            main._CONTINUITY_PENDING["h0_proof"]["source_phase"],
            "PRE_H0_EXECUTION",
        )

    def test_turbo_binding_failure_publishes_no_role_or_partial_owner(self):
        start, callback = turbo_pair("normal")
        self.assertEqual(main.agent(start), [0])
        with mock.patch.object(
            main, "_continuity_bind_acceleration_resources", return_value=False
        ):
            self.assertEqual(main.agent(callback), [])
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertNotEqual(trace["H1_after_KO"]["readiness"], "READY_AFTER_TURBO")
        self.assertEqual(
            trace["pending_event"]["reason"],
            "ABANDON_H0_PROOF_TURBO_ATOMIC_BINDING_FAILED",
        )
        self.assertEqual(acceleration_owners(trace), {})
        self.assertIsNone(main._CONTINUITY_PENDING)

    def test_active_alloy_replacement_failure_preserves_existing_ownership(self):
        raw = phase_b.observation(86160056, 35, 0)
        captured = {}
        original = main._continuity_atomic_replace_role_reservations

        def forced_failure(ledger, role, claims):
            captured["before_resources"] = copy.deepcopy(ledger["resources"])
            captured["before_reservations"] = copy.deepcopy(ledger["reservations"])
            failed = original(
                ledger,
                role,
                list(claims) + [
                    ("missing:forced", "H1_after_KO", "forced atomic failure")
                ],
            )
            captured["after_resources"] = copy.deepcopy(ledger["resources"])
            captured["after_reservations"] = copy.deepcopy(ledger["reservations"])
            return failed

        with mock.patch.object(
            main,
            "_continuity_atomic_replace_role_reservations",
            side_effect=forced_failure,
        ):
            main.build_continuity2_plan(main.to_observation_class(raw))
        self.assertEqual(captured["before_resources"], captured["after_resources"])
        self.assertEqual(
            captured["before_reservations"], captured["after_reservations"]
        )

    def test_repeated_callback_keeps_action_hash_and_single_ownership(self):
        start, callback = turbo_pair("normal")
        self.assertEqual(main.agent(start), [0])
        first_action = main.agent(copy.deepcopy(callback))
        first_pending = copy.deepcopy(main._CONTINUITY_PENDING)
        first_hash = first_pending["h0_proof"]["proof_sha256"]
        second_action = main.agent(copy.deepcopy(callback))
        second_pending = main._CONTINUITY_PENDING
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(first_action, second_action)
        self.assertEqual(second_pending["h0_proof"]["proof_sha256"], first_hash)
        self.assertEqual(first_pending, second_pending)
        owned = acceleration_owners(trace)
        self.assertEqual(len(owned), len(set(owned)))
        reservation_tokens = [row["token"] for row in trace["ledger"]["reservations"]]
        self.assertEqual(len(reservation_tokens), len(set(reservation_tokens)))


if __name__ == "__main__":
    unittest.main()
