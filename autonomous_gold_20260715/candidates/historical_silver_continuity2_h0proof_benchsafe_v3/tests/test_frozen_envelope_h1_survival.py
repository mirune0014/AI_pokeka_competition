import copy
import json
from pathlib import Path
import sys
import unittest


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CANDIDATE_DIR))
sys.path.insert(0, str(TEST_DIR))

import main  # noqa: E402
import test_continuity2_phase_a as phase_a  # noqa: E402
import test_continuity2_phase_b as phase_b  # noqa: E402
from test_public_combat_envelope_closure import (  # noqa: E402
    observation as combat_observation,
    pokemon as combat_pokemon,
)
from test_transaction_bound_h0_proof import (  # noqa: E402
    acceleration_owners,
    turbo_pair,
)


def metal(serial, player_index=1):
    return {"id": main.METAL_ENERGY, "serial": serial, "playerIndex": player_index}


def reindex_pokemon(card, player_index):
    card["playerIndex"] = player_index
    for child in (
        list(card.get("energyCards", []))
        + list(card.get("tools", []))
        + list(card.get("preEvolution", []))
    ):
        child["playerIndex"] = player_index
    return card


class FrozenEnvelopeH1SurvivalTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None

    def _starmie_turbo_start(self, hp=30):
        raw = phase_b.observation(86160574, 28, 1)
        starmie = copy.deepcopy(
            phase_a.replay_observation(86161083, 74, 1)
            ["current"]["players"][0]["active"][0]
        )
        raw["current"]["players"][0]["active"] = [starmie]
        unsafe = raw["current"]["players"][1]["bench"][0]
        raw["current"]["players"][1]["bench"] = [unsafe]
        unsafe["hp"] = hp
        unsafe["energies"] = []
        unsafe["energyCards"] = []
        return raw

    def _starmie_turbo_callback(self, start):
        callback = phase_b.observation(86160574, 29, 1)
        callback["current"] = copy.deepcopy(start["current"])
        return callback

    def _force_unsafe_turbo_parent(self, start):
        obs = main.to_observation_class(copy.deepcopy(start))
        plan = main.build_continuity2_plan(obs)
        slot = next(
            item for item in main.continuity_slots(obs)
            if item["area"] == int(main.AreaType.BENCH)
        )
        turbo_row = main._continuity_sorted_options(
            obs,
            lambda option: (
                option.type == main.OptionType.ATTACK and option.attackId == 965
            ),
        )[0]
        transaction = main._continuity_energy_transition(
            obs,
            slot,
            "TURBO",
            3,
            "H1_after_KO",
            source_active_line=main.continuity_lineage_key(
                main.active_pokemon(obs), obs.current.yourIndex
            ),
            effect_serial=main.active_pokemon(obs).serial,
            trigger_keys=[turbo_row[0]],
            allow_synthetic=True,
        )
        provisional = {
            "line_key": slot["line_key"],
            "card_id": slot["card_id"],
            "serial": slot["serial"],
            "deficit": 3,
            "attack_id": main.RAGING_HAMMER,
            "bench_threat": 50,
            "response_survival_marker": "RESPONSE_SURVIVAL_READY",
            "envelope_sha256": main._continuity_json_sha256(
                plan["response_envelope"]
            ),
        }
        provisional["record_sha256"] = main._continuity_json_sha256(provisional)
        transaction["provisional_target"] = provisional
        plan["passive_transaction_start"] = transaction
        main._continuity_commit_transaction(obs, plan, [turbo_row[1]])
        self.assertIsNotNone(main._CONTINUITY_PENDING)

    def _shared_alloy_execution(self, hp):
        raw = self._starmie_turbo_start(hp)
        player = raw["current"]["players"][1]
        player["discard"].extend([metal(9800), metal(9801), metal(9802)])
        obs = main.to_observation_class(copy.deepcopy(raw))
        plan = main.build_continuity2_plan(obs)
        slot = next(
            item for item in main.continuity_slots(obs)
            if item["area"] == int(main.AreaType.BENCH)
        )
        cards = [
            card for card in obs.current.players[1].discard
            if card.id == main.METAL_ENERGY and card.serial >= 9800
        ]
        transaction = main._continuity_energy_transition(
            obs,
            slot,
            "ALLOY",
            3,
            "H1_after_KO",
            energy_cards=cards,
            source_active_line=main.continuity_lineage_key(
                main.active_pokemon(obs), obs.current.yourIndex
            ),
            effect_serial=9900,
        )
        execution = main._continuity_validate_acceleration_execution(
            obs, [slot], transaction, plan["response_envelope"]
        )
        return execution

    def _alloy_attach_from_target_failure(self, mode):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None
        for step, expected in ((35, [0]), (36, [0]), (37, [0, 1])):
            self.assertEqual(
                main.agent(copy.deepcopy(phase_b.observation(86160056, step, 0))),
                expected,
            )
        self.assertIsNotNone(main._CONTINUITY_PENDING)

        callback = phase_b.observation(86160056, 38, 0)
        exact = copy.deepcopy(callback["select"]["option"][0])
        wrong = copy.deepcopy(callback["select"]["option"][1])
        if mode == "wrong_only":
            callback["select"]["option"] = [wrong]
            expected_action = [0]
            expected_reason = "ABANDON_H0_PROOF_TARGET_OPTION_ABSENT"
        elif mode == "empty_optional":
            callback["select"]["option"] = []
            callback["select"]["minCount"] = 0
            callback["select"]["maxCount"] = 1
            expected_action = []
            expected_reason = "ABANDON_H0_PROOF_TARGET_OPTION_ABSENT"
        elif mode == "duplicate":
            callback["select"]["option"] = [exact, copy.deepcopy(exact)]
            expected_action = [0]
            expected_reason = "ABANDON_H0_PROOF_TARGET_OPTION_DUPLICATE"
        else:
            raise AssertionError(mode)

        bind_calls = []
        ledger_pairs = []
        original_bind = main._continuity_bind_acceleration_resources
        original_fail = main._continuity_fail_closed_callback

        def tracking_bind(ledger, transaction):
            bind_calls.append(main._continuity_json_clone(ledger))
            return original_bind(ledger, transaction)

        def tracking_fail(obs, plan, reason):
            before = main._continuity_json_clone(plan["ledger"])
            result = original_fail(obs, plan, reason)
            after = main._continuity_json_clone(plan["ledger"])
            ledger_pairs.append((before, after))
            return result

        main._continuity_bind_acceleration_resources = tracking_bind
        main._continuity_fail_closed_callback = tracking_fail
        try:
            action = main.agent(copy.deepcopy(callback))
        finally:
            main._continuity_bind_acceleration_resources = original_bind
            main._continuity_fail_closed_callback = original_fail

        trace = copy.deepcopy(main.CONTINUITY_LATEST_TRACE)
        self.assertEqual(action, expected_action)
        self.assertEqual(len(bind_calls), 0)
        self.assertEqual(len(ledger_pairs), 1)
        before, after = ledger_pairs[0]
        self.assertEqual(before, after)
        self.assertEqual(trace["ledger"], before)
        self.assertEqual(
            trace["ledger"]["reservations"], before["reservations"]
        )
        self.assertEqual(
            trace["pending_event"]["reason"], expected_reason
        )
        self.assertNotEqual(
            trace["H1_after_KO"]["readiness"], "READY_AFTER_ALLOY_NOW"
        )
        self.assertEqual(acceleration_owners(trace), {})
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(len(action), len(set(action)))
        self.assertTrue(all(
            0 <= index < len(callback["select"]["option"])
            for index in action
        ))
        self.assertGreaterEqual(len(action), callback["select"]["minCount"])
        self.assertLessEqual(len(action), callback["select"]["maxCount"])
        return {
            "action": action,
            "reason": trace["pending_event"]["reason"],
            "choice_kind": trace["choice"]["kind"],
            "choice_exact_count": trace["choice"]["exact_count"],
            "ledger": trace["ledger"],
        }

    def test_exact_root_p1_main_rejects_30_hp_under_50_spread(self):
        raw = self._starmie_turbo_start(30)
        obs = main.to_observation_class(copy.deepcopy(raw))
        plan = main.build_continuity2_plan(obs)
        self.assertEqual(plan["response_envelope"]["bench_spread_max"], 50)
        slot = next(
            item for item in main.continuity_slots(obs)
            if item["area"] == int(main.AreaType.BENCH)
        )
        survival = main._continuity_response_survival_certificate(
            obs, slot, plan["response_envelope"]
        )
        self.assertEqual(survival["bench_threat"], 50)
        self.assertEqual(
            survival["reason"],
            "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_KO",
        )
        self.assertIsNone(survival["marker"])
        target, deficit = main._continuity_turbo_target(
            obs,
            [slot],
            plan,
            pre_h0_envelope=plan["response_envelope"],
        )
        self.assertIsNone(target)
        self.assertEqual(deficit, 0)
        self.assertIsNone(plan.get("passive_transaction_start"))
        self.assertEqual(main.agent(copy.deepcopy(raw)), [0])
        self.assertIsNone(main._CONTINUITY_PENDING)

    def test_forced_unsafe_turbo_callback_fails_closed_without_ownership(self):
        start = self._starmie_turbo_start(30)
        self._force_unsafe_turbo_parent(start)
        callback = self._starmie_turbo_callback(start)
        first = main.agent(copy.deepcopy(callback))
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(first, [])
        self.assertEqual(trace["choice"]["kind"], "H0_PROOF_FAIL_CLOSED_ZERO")
        self.assertEqual(
            trace["pending_event"]["reason"],
            "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_KO",
        )
        self.assertNotEqual(trace["H1_after_KO"]["readiness"], "READY_AFTER_TURBO")
        self.assertEqual(acceleration_owners(trace), {})
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.agent(copy.deepcopy(callback)), first)
        self.assertEqual(acceleration_owners(main.CONTINUITY_LATEST_TRACE), {})

    def test_survival_boundary_is_exact_and_json_safe(self):
        envelope = {
            "unknown": False,
            "payable_attacks": [{
                "status": "KNOWN", "bench_damage": 30, "bench_counters": 20,
            }],
        }
        for hp, expected_state, expected_hp in (
            (50, "UNSAFE", 0),
            (51, "READY", 1),
        ):
            with self.subTest(hp=hp):
                raw = combat_observation(
                    combat_pokemon(main.DURALUDON, hp, [], 0, 100 + hp, max_hp=130),
                    combat_pokemon(main.DURALUDON, 130, [], 1, 200 + hp, max_hp=130),
                )
                obs = main.to_observation_class(raw)
                slot = main.continuity_slots(obs)[0]
                before = copy.deepcopy(main._continuity_public_slot(slot))
                certificate = main._continuity_response_survival_certificate(
                    obs, slot, envelope
                )
                json.dumps(certificate, sort_keys=True)
                self.assertEqual(certificate["state"], expected_state)
                self.assertEqual(certificate["hp_after"], expected_hp)
                self.assertEqual(main._continuity_public_slot(slot), before)
                if expected_state == "READY":
                    self.assertEqual(certificate["marker"], "RESPONSE_SURVIVAL_READY")
                    self.assertEqual(certificate["post_threat_slot"]["hp"], 1)
                else:
                    self.assertIsNone(certificate["marker"])

    def test_damage_counter_composition_and_full_metal_lab(self):
        envelope = {
            "unknown": False,
            "payable_attacks": [{
                "status": "KNOWN", "bench_damage": 40, "bench_counters": 20,
            }],
        }
        threats = []
        for stadium in ((), (main.FULL_METAL_LAB,)):
            raw = combat_observation(
                combat_pokemon(main.DURALUDON, 100, [], 0, 300, max_hp=130),
                combat_pokemon(main.DURALUDON, 130, [], 1, 301, max_hp=130),
                stadium=stadium,
            )
            obs = main.to_observation_class(raw)
            certificate = main._continuity_response_survival_certificate(
                obs, main.continuity_slots(obs)[0], envelope
            )
            threats.append(certificate["bench_threat"])
        self.assertEqual(threats, [60, 30])

    def test_safe_turbo_real_serial_lifecycle_is_deterministic(self):
        start, callback = turbo_pair("normal")
        self.assertEqual(main.agent(copy.deepcopy(start)), [0])
        provisional = copy.deepcopy(main._CONTINUITY_PENDING["provisional_target"])
        self.assertEqual(provisional["deficit"], 3)
        self.assertTrue(all(
            item["serial"] < 0
            for item in main._CONTINUITY_PENDING["assigned_energy"]
        ))
        first = main.agent(copy.deepcopy(callback))
        first_pending = copy.deepcopy(main._CONTINUITY_PENDING)
        self.assertEqual(first, [0, 1, 2])
        self.assertEqual(
            main.CONTINUITY_LATEST_TRACE["H1_after_KO"]
            ["response_survival_marker"],
            "RESPONSE_SURVIVAL_READY",
        )
        self.assertTrue(all(
            item["serial"] >= 0 for item in first_pending["assigned_energy"]
        ))
        self.assertEqual(main.agent(copy.deepcopy(callback)), first)
        self.assertEqual(main._CONTINUITY_PENDING, first_pending)

    def test_turbo_callback_board_deficit_change_fails_before_binding(self):
        outcomes = []
        for run in range(2):
            main._CONTINUITY_PENDING = None
            main._CONTINUITY_PENDING_EVENT = None
            main.CONTINUITY_LATEST_TRACE = None
            start, callback = turbo_pair("normal")
            self.assertEqual(main.agent(copy.deepcopy(start)), [0])
            sealed = copy.deepcopy(
                main._CONTINUITY_PENDING["provisional_target"]
            )
            self.assertEqual(sealed["deficit"], 3)

            target = next(
                card
                for card in callback["current"]["players"][1]["bench"]
                if card["serial"] == sealed["serial"]
            )
            target["energies"].append(main.METAL_ENERGY)
            target["energyCards"].append(metal(99990 + run))
            self.assertEqual(
                main._CONTINUITY_PENDING["provisional_target"], sealed
            )
            callback_obs = main.to_observation_class(copy.deepcopy(callback))
            callback_slot = next(
                slot for slot in main.continuity_slots(callback_obs)
                if slot["line_key"] == sealed["line_key"]
            )
            self.assertEqual(main._continuity_primary_deficit(callback_slot), 2)

            action = main.agent(copy.deepcopy(callback))
            trace = copy.deepcopy(main.CONTINUITY_LATEST_TRACE)
            outcomes.append((action, trace["pending_event"]["reason"]))
            self.assertEqual(action, [])
            self.assertEqual(
                trace["pending_event"]["reason"],
                "ABANDON_H0_PROOF_TURBO_PROVISIONAL_DEFICIT_MISMATCH",
            )
            self.assertEqual(
                trace["choice"]["kind"], "H0_PROOF_FAIL_CLOSED_ZERO"
            )
            self.assertNotEqual(
                trace["H1_after_KO"]["readiness"], "READY_AFTER_TURBO"
            )
            self.assertEqual(acceleration_owners(trace), {})
            self.assertIsNone(trace["pending_transaction"])
            self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(outcomes[0], outcomes[1])

    def test_alloy_attach_from_wrong_only_target_fails_before_binding(self):
        first = self._alloy_attach_from_target_failure("wrong_only")
        second = self._alloy_attach_from_target_failure("wrong_only")
        self.assertEqual(first, second)

    def test_alloy_attach_from_empty_optional_fails_without_binding(self):
        first = self._alloy_attach_from_target_failure("empty_optional")
        second = self._alloy_attach_from_target_failure("empty_optional")
        self.assertEqual(first, second)
        self.assertEqual(first["action"], [])
        self.assertEqual(first["choice_kind"], "H0_PROOF_FAIL_CLOSED_ZERO")

    def test_alloy_attach_from_duplicate_target_fails_before_binding(self):
        first = self._alloy_attach_from_target_failure("duplicate")
        second = self._alloy_attach_from_target_failure("duplicate")
        self.assertEqual(first, second)

    def test_turbo_provisional_identity_and_deficit_mutations_fail_closed(self):
        cases = (
            ("identity", "ABANDON_H0_PROOF_TURBO_PROVISIONAL_HASH_MISMATCH"),
            ("deficit", "ABANDON_H0_PROOF_TURBO_PROVISIONAL_HASH_MISMATCH"),
        )
        for kind, expected in cases:
            with self.subTest(kind=kind):
                self.setUp()
                start, callback = turbo_pair("normal")
                self.assertEqual(main.agent(copy.deepcopy(start)), [0])
                record = main._CONTINUITY_PENDING["provisional_target"]
                if kind == "identity":
                    record["serial"] += 1
                else:
                    record["deficit"] = 4
                payload = copy.deepcopy(record)
                payload.pop("record_sha256")
                record["record_sha256"] = main._continuity_json_sha256(payload)
                self.assertEqual(main.agent(copy.deepcopy(callback)), [])
                trace = main.CONTINUITY_LATEST_TRACE
                self.assertEqual(trace["pending_event"]["reason"], expected)
                self.assertEqual(acceleration_owners(trace), {})
                self.assertIsNone(main._CONTINUITY_PENDING)

    def test_active_alloy_keeps_h0_and_drops_unsafe_optional_h1_atomically(self):
        raw = phase_b.observation(86160056, 35, 0)
        raw["current"]["stadium"] = []
        player = raw["current"]["players"][0]
        opponent = raw["current"]["players"][1]
        phase_b.set_energy(player["active"][0], 2, 0, 99420)
        phase_b.set_energy(player["bench"][0], 2, 0, 99430)
        player["bench"][0]["hp"] = 30
        player["hand"].extend([metal(99450, 0), metal(99451, 0)])
        player["handCount"] = len(player["hand"])
        opponent["active"] = [{
            "id": main.DURALUDON, "serial": 880, "playerIndex": 1,
            "hp": 130, "maxHp": 130, "appearThisTurn": False,
            "energies": [], "energyCards": [], "tools": [], "preEvolution": [],
        }]
        starmie = copy.deepcopy(
            phase_a.replay_observation(86161083, 74, 1)
            ["current"]["players"][0]["active"][0]
        )
        opponent["bench"] = [reindex_pokemon(starmie, 1)]
        plan = main.build_continuity2_plan(
            main.to_observation_class(copy.deepcopy(raw))
        )
        self.assertEqual(plan["choice"]["kind"], "H0_EVOLVE_ALLOY_ROUTE")
        self.assertEqual(plan["H0"]["readiness"], "READY_AFTER_EVOLVE_ALLOY")
        self.assertEqual(plan["response_envelope"]["bench_spread_max"], 50)
        self.assertEqual(
            [item["role"] for item in plan["transaction_start"]["target_queue"]],
            ["H0"],
        )
        self.assertFalse(any(
            item["role"] == "H1_after_KO"
            for item in plan["ledger"]["reservations"]
        ))
        self.assertIsNone(plan["H1_after_KO"]["identity"])

    def test_unsafe_bench_alloy_main_and_shared_validator_fail_closed(self):
        raw = phase_b.observation(86161083, 74, 1)
        raw["current"]["stadium"] = []
        target = raw["current"]["players"][1]["bench"][1]
        phase_b.set_energy(target, 1, 1, 9450)
        target["hp"] = 30
        target["maxHp"] = 500
        raw["current"]["players"][1]["discard"].extend([
            metal(9460), metal(9461),
        ])
        plan = main.build_continuity2_plan(
            main.to_observation_class(copy.deepcopy(raw))
        )
        self.assertNotEqual(
            (plan.get("choice") or {}).get("kind"), "H1_EVOLVE_SAME_CLASS_TIE"
        )
        self.assertFalse(any(
            item["role"] == "H1_after_KO"
            for item in plan["ledger"]["reservations"]
        ))

        execution = self._shared_alloy_execution(30)
        self.assertFalse(execution["valid"])
        self.assertEqual(
            execution["reason"],
            "ABANDON_H0_PROOF_ACCELERATED_H1_RESPONSE_KO",
        )
        self.assertEqual(execution["h1_certificates"], [])

    def test_safe_alloy_lifecycle_retains_proof_and_post_threat_certificate(self):
        proof_hashes = []
        markers = []
        for step in (35, 36, 37, 38, 39):
            raw = phase_b.observation(86160056, step, 0)
            player = raw["current"]["players"][0]
            phase_b.set_energy(player["active"][0], 2, 0, 99420)
            if player["bench"]:
                phase_b.set_energy(player["bench"][0], 2, 0, 99430)
            if step == 35:
                player["hand"].append(metal(99450, 0))
                player["handCount"] = len(player["hand"])
            main.agent(copy.deepcopy(raw))
            proof_hashes.append(
                main._CONTINUITY_PENDING["h0_proof"]["proof_sha256"]
            )
            markers.append(
                main.CONTINUITY_LATEST_TRACE["H1_after_KO"].get(
                    "response_survival_marker"
                )
            )
        self.assertEqual(len(set(proof_hashes)), 1)
        self.assertEqual(markers, ["RESPONSE_SURVIVAL_READY"] * 5)
        sealed = main._CONTINUITY_PENDING["h1_publication_certificate"]
        self.assertEqual(
            sealed["certificates"][0]["response_survival_marker"],
            "RESPONSE_SURVIVAL_READY",
        )

    def test_shared_safe_alloy_certificate_publishes_only_post_threat_hp(self):
        execution = self._shared_alloy_execution(51)
        self.assertTrue(execution["valid"])
        certificate = execution["h1_certificates"][0]
        self.assertEqual(certificate["slot"]["hp"], 1)
        self.assertEqual(certificate["bench_threat"], 50)
        self.assertEqual(
            certificate["response_survival_marker"], "RESPONSE_SURVIVAL_READY"
        )


if __name__ == "__main__":
    unittest.main()
