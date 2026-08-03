import copy
from pathlib import Path
from types import SimpleNamespace
import os
import sys
import unittest


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CANDIDATE_DIR))
sys.path.insert(0, str(TEST_DIR))

import main  # noqa: E402
import test_continuity2_phase_b as phase_b  # noqa: E402


def set_pokemon(pokemon, card_id, hp, energies, player_index, serial):
    pokemon.update({
        "id": card_id,
        "serial": serial,
        "playerIndex": player_index,
        "hp": hp,
        "maxHp": hp,
        "appearThisTurn": False,
        "preEvolution": [],
        "tools": [],
        "energies": list(energies),
        "energyCards": [
            {
                # Colorless is an attack requirement, not a physical Energy ID.
                "id": energy if energy else 1,
                "serial": serial + index + 1,
                "playerIndex": player_index,
            }
            for index, energy in enumerate(energies)
        ],
    })


class Continuity2AdversarialTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None
        os.environ.pop(main._CONTINUITY_TRACE_ENV, None)

    def test_actual_phantom_dive_separates_bench_counters_and_rejects_40_hp(self):
        raw = phase_b.observation(86162625, 97, 0)
        # Keep the current Dragapult outside Metal Defender's H0 KO range so
        # this remains the non-KO Phantom Dive spread invariant.  Mandatory
        # promotion after a real H0 KO is covered by the closure suite.
        opponent = raw["current"]["players"][1]["active"][0]
        opponent["hp"] = opponent["maxHp"]
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        envelope = plan["response_envelope"]
        self.assertEqual(envelope["bench_damage_max"], 0)
        self.assertEqual(envelope["bench_counters_max"], 60)
        self.assertEqual(envelope["bench_total_max"], 60)
        self.assertEqual(envelope["bench_spread_max"], 0)
        dura = next(
            slot for slot in main.continuity_slots(main.to_observation_class(raw))
            if slot["card_id"] == main.DURALUDON and slot["hp"] == 40
        )
        self.assertEqual(
            main._continuity_bench_threat(
                main.to_observation_class(raw), envelope, dura
            ),
            60,
        )

    def test_mind_bend_survival_is_unknown_and_survival_cards_cannot_overwrite(self):
        raw = phase_b.observation(86162213, 38, 0)
        raw["current"]["stadium"] = []
        own = raw["current"]["players"][0]["active"][0]
        own["hp"] = own["maxHp"] = 180
        opponent = raw["current"]["players"][1]["active"][0]
        set_pokemon(opponent, 112, 110, [5, 0], 1, 8800)
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        self.assertEqual(plan["response_envelope"]["response_statuses"], ["CONFUSED"])
        self.assertEqual(plan["H1_survive"]["readiness"], "UNKNOWN")
        self.assertEqual(
            plan["H1_survive"]["reason"],
            "UNKNOWN_RESPONSE_EFFECT",
        )
        self.assertTrue(any(
            reason.startswith("UNSUPPORTED_VISIBLE_SKILL:112:")
            for reason in plan["response_envelope"]["unknown_reasons"]
        ))
        self.assertIsNone(plan["choice"])

    def test_spiky_energy_is_pre_response_reactive_damage(self):
        raw = phase_b.observation(86162213, 38, 0)
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        envelope = plan["response_envelope"]
        self.assertEqual(envelope["reactive_counters"], 20)
        self.assertEqual(envelope["active_damage_max"], 90)
        self.assertEqual(envelope["active_total_max"], 110)
        self.assertEqual(plan["choice"]["card_id"], main.JUMBO_ICE_CREAM)

    def test_reactives_require_damage_and_reactive_ko_fails_closed(self):
        blocked = phase_b.observation(86162213, 38, 0)
        own = blocked["current"]["players"][0]["active"][0]
        set_pokemon(own, main.ARCHALUDON_EX, 300, [8, 8, 8], 0, 8810)
        opponent = blocked["current"]["players"][1]["active"][0]
        opponent["tools"] = [{"id": 1167, "serial": 8820, "playerIndex": 1}]
        obs = main.to_observation_class(blocked)
        envelope = main.continuity_response_envelope(obs, main.active_pokemon(obs), 253)
        self.assertEqual(envelope["reactive_counters"], 0)

        reactive_ko = phase_b.observation(86162213, 38, 0)
        reactive_ko["current"]["stadium"] = []
        own = reactive_ko["current"]["players"][0]["active"][0]
        own["hp"] = own["maxHp"] = 100
        opponent = reactive_ko["current"]["players"][1]["active"][0]
        opponent["tools"] = [{"id": 1167, "serial": 8821, "playerIndex": 1}]
        obs = main.to_observation_class(reactive_ko)
        envelope = main.continuity_response_envelope(obs, main.active_pokemon(obs), 1212)
        self.assertEqual(envelope["reactive_counters"], 140)  # Bomb 120 + Spiky 20.
        self.assertTrue(envelope["unknown"])
        self.assertIn("REACTIVE_KO_REQUIRES_MIDTURN_PROMOTION", envelope["unknown_reasons"])

    def test_hypnotizer_asleep_wake_coin_is_unknown(self):
        raw = phase_b.observation(86162213, 38, 0)
        raw["current"]["stadium"] = []
        opponent = raw["current"]["players"][1]["active"][0]
        set_pokemon(opponent, 408, 70, [2], 1, 8825)
        opponent["tools"] = [{"id": 1154, "serial": 8827, "playerIndex": 1}]
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs, main.active_pokemon(obs), main.COATED_ATTACK
        )
        self.assertFalse(envelope["unknown"])
        self.assertEqual(envelope["reactive_statuses"], ["ASLEEP"])
        self.assertEqual(
            main._continuity_response_attack_gate(
                envelope, main.active_pokemon(obs)
            ),
            ("UNKNOWN", "VISIBLE_RESPONSE_ASLEEP_WAKE_COIN"),
        )

    def test_response_modifiers_belt_postwick_lucky_and_break_ground(self):
        belt_raw = phase_b.observation(86162213, 38, 0)
        own = belt_raw["current"]["players"][0]["active"][0]
        set_pokemon(own, main.ARCHALUDON_EX, 300, [8, 8, 8], 0, 8830)
        opponent = belt_raw["current"]["players"][1]["active"][0]
        opponent["tools"] = [{"id": 1158, "serial": 8840, "playerIndex": 1}]
        opponent["energyCards"] = [
            {"id": 18, "serial": 8841 + index, "playerIndex": 1}
            for index in range(3)
        ]
        obs = main.to_observation_class(belt_raw)
        belt = main._continuity_incoming_profile(
            obs, main.opp_active_pokemon(obs), main.ALL_ATTACKS[479], main.active_pokemon(obs)
        )
        self.assertEqual(belt["active_damage"], 140)

        postwick_raw = phase_b.observation(86162213, 38, 0)
        postwick_raw["current"]["stadium"] = [
            {"id": 1255, "serial": 8850, "playerIndex": 1}
        ]
        opponent = postwick_raw["current"]["players"][1]["active"][0]
        set_pokemon(opponent, 289, 140, [6, 0, 0], 1, 8860)
        obs = main.to_observation_class(postwick_raw)
        ground = main._continuity_incoming_profile(
            obs, main.opp_active_pokemon(obs), main.ALL_ATTACKS[399], main.active_pokemon(obs)
        )
        self.assertEqual(ground["active_damage"], 170)
        self.assertEqual(ground["bench_damage"], 0)
        self.assertEqual(ground["bench_counters"], 0)

        lucky_raw = phase_b.observation(86162213, 38, 0)
        lucky_raw["current"]["stadium"] = []
        opponent = lucky_raw["current"]["players"][1]["active"][0]
        set_pokemon(opponent, 743, 140, [5], 1, 8870)
        opponent["tools"] = [{"id": 1156, "serial": 8872, "playerIndex": 1}]
        lucky_raw["current"]["players"][1]["handCount"] = 3
        obs = main.to_observation_class(lucky_raw)
        lucky = main.continuity_response_envelope(obs, main.active_pokemon(obs), 1212)
        self.assertEqual(lucky["lucky_helmet_draw"], 2)
        self.assertEqual(lucky["active_counters_max"], 100)

    def test_neutral_zone_detects_ex_and_mega_ex_without_rulebox_attribute(self):
        raw = phase_b.observation(86162213, 38, 0)
        raw["current"]["stadium"] = [
            {"id": 1247, "serial": 8880, "playerIndex": 1}
        ]
        own = raw["current"]["players"][0]["active"][0]
        set_pokemon(own, 678, 340, [6, 6], 0, 8890)
        opponent = raw["current"]["players"][1]["active"][0]
        set_pokemon(opponent, 112, 110, [5, 0], 1, 8895)
        obs = main.to_observation_class(raw)
        self.assertEqual(
            main._continuity_outgoing_block(
                main.active_pokemon(obs), main.opp_active_pokemon(obs), obs
            ),
            "NEUTRALIZATION_ZONE_RULE_BOX_DAMAGE_BLOCKED",
        )
        own_pokemon = main.active_pokemon(obs)
        own_pokemon.id = main.DURALUDON
        self.assertIsNone(
            main._continuity_outgoing_block(
                own_pokemon, main.opp_active_pokemon(obs), obs
            )
        )

    def test_effect_whitelist_and_visible_unknown_modifiers_fail_closed(self):
        raw = phase_b.observation(86162213, 38, 0)
        raw["current"]["stadium"] = []
        obs = main.to_observation_class(raw)
        unknown = SimpleNamespace(
            attackId=999002,
            name="Unreviewed",
            damage=120,
            text="During the next turn, apply an unreviewed effect.",
        )
        profile = main._continuity_incoming_profile(
            obs, main.opp_active_pokemon(obs), unknown, main.active_pokemon(obs)
        )
        self.assertEqual(profile["status"], "UNKNOWN")
        self.assertEqual(profile["unknown_reason"], "UNSUPPORTED_NONEMPTY_ATTACK_TEXT")
        cosmic = main._continuity_incoming_profile(
            obs,
            main.opp_active_pokemon(obs),
            main.ALL_ATTACKS[980],
            main.active_pokemon(obs),
        )
        self.assertEqual(cosmic["status"], "UNKNOWN")

        cases = (
            ("tools", {"id": 9999, "serial": 8891, "playerIndex": 1},
             "UNSUPPORTED_VISIBLE_TOOL:9999"),
            ("energyCards", {"id": 13, "serial": 8892, "playerIndex": 1},
             "UNSUPPORTED_VISIBLE_SPECIAL_ENERGY:13"),
        )
        for field, card, reason in cases:
            with self.subTest(field=field):
                mutated = phase_b.observation(86162213, 38, 0)
                getattr_target = mutated["current"]["players"][1]["active"][0]
                getattr_target[field] = list(getattr_target.get(field, [])) + [card]
                converted = main.to_observation_class(mutated)
                envelope = main.continuity_response_envelope(
                    converted, main.active_pokemon(converted), 1212
                )
                self.assertTrue(envelope["unknown"])
                self.assertIn(reason, envelope["unknown_reasons"])

        stadium = phase_b.observation(86162213, 38, 0)
        stadium["current"]["stadium"] = [
            {"id": 1264, "serial": 8893, "playerIndex": 1}
        ]
        converted = main.to_observation_class(stadium)
        envelope = main.continuity_response_envelope(
            converted, main.active_pokemon(converted), 1212
        )
        self.assertIn("UNSUPPORTED_VISIBLE_STADIUM:1264", envelope["unknown_reasons"])

    def test_coated_attack_blocks_basic_survivor_and_basic_successor(self):
        raw = phase_b.observation(86162213, 38, 0)
        raw["current"]["stadium"] = [
            {"id": main.FULL_METAL_LAB, "serial": 8900, "playerIndex": 0}
        ]
        own = raw["current"]["players"][0]["active"][0]
        set_pokemon(own, main.DURALUDON, 130, [8, 8, 8], 0, 8910)
        bench = copy.deepcopy(own)
        bench["serial"] = 8920
        bench["energyCards"] = [
            {"id": 8, "serial": 8921 + index, "playerIndex": 0}
            for index in range(3)
        ]
        raw["current"]["players"][0]["bench"] = [bench]
        opponent = raw["current"]["players"][1]["active"][0]
        set_pokemon(opponent, main.ARCHALUDON, 180, [8, 8, 8], 1, 8930)
        for option in raw["select"]["option"]:
            if option.get("type") == int(main.OptionType.ATTACK):
                option["attackId"] = main.RAGING_HAMMER
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        self.assertTrue(plan["response_envelope"]["next_turn_basic_damage_block"])
        self.assertEqual(plan["H1_survive"]["readiness"], "ATTACK_LOCKED")
        self.assertIn(
            "COATED_ATTACK_BLOCKS_BASIC_SUCCESSOR_DAMAGE",
            {item["reason"] for item in plan["H1_after_KO"]["rejected"]},
        )

    def test_retreat_exact_serials_idempotence_and_adversarial_abandon(self):
        fixture = phase_b.Continuity2PhaseBTests()
        start, first, second, switch = fixture._paid_retreat_observations()
        self.assertEqual(main.agent(copy.deepcopy(start)), [0])
        self.assertEqual(main._CONTINUITY_PENDING["payment_serials"], [9501, 9502])
        owners = {
            item["token"]: item["owner"]
            for item in main.CONTINUITY_LATEST_TRACE["ledger"]["resources"]
        }
        self.assertEqual(owners["budget:retreat_now"], "RETREAT_TRANSACTION")
        self.assertEqual(owners["attached:9501"], "RETREAT_TRANSACTION")
        self.assertEqual(owners["attached:9502"], "RETREAT_TRANSACTION")
        self.assertEqual(main.agent(copy.deepcopy(first)), [0])
        repeat = copy.deepcopy(main._CONTINUITY_PENDING)
        self.assertEqual(main.agent(copy.deepcopy(first)), [0])
        self.assertEqual(main._CONTINUITY_PENDING, repeat)
        self.assertEqual(main.agent(copy.deepcopy(second)), [0])
        self.assertEqual(main.agent(copy.deepcopy(switch)), [0])

        self.setUp()
        start, first, _, _ = fixture._paid_retreat_observations()
        main.agent(copy.deepcopy(start))
        first["current"]["players"][0]["active"][0]["energyCards"][0]["serial"] = 9599
        main.agent(first)
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")
        self.assertIsNone(main.CONTINUITY_LATEST_TRACE["choice"])

        self.setUp()
        start, first, _, _ = fixture._paid_retreat_observations()
        main.agent(copy.deepcopy(start))
        active = first["current"]["players"][0]["active"][0]
        set_pokemon(active, main.CINDERACE, 160, [8, 8], 0, 77770)
        main.agent(first)
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

    def test_zero_cost_retreat_binds_source_destination_and_budget(self):
        self.assertEqual(main.agent(phase_b.observation(86160574, 48, 1)), [10])
        pending = main._CONTINUITY_PENDING
        self.assertEqual(pending["source_active_line"], "p1:line:666:73")
        self.assertEqual(pending["line_key"], "p1:line:169:64")
        self.assertEqual(pending["payment_serials"], [])
        owners = {
            item["token"]: item["owner"]
            for item in main.CONTINUITY_LATEST_TRACE["ledger"]["resources"]
        }
        self.assertEqual(owners["budget:retreat_now"], "RETREAT_TRANSACTION")

    def test_alloy_uses_reserved_serial_after_option_reorder(self):
        def mutate(raw, evolved):
            player = raw["current"]["players"][0]
            player["bench"] = []
            phase_b.set_energy(player["active"][0], 2, 0, first_serial=8950)
            metal_indices = [
                index for index, card in enumerate(player["discard"])
                if card and card["id"] == main.METAL_ENERGY
            ]
            player["discard"][metal_indices[0]]["serial"] = 9992
            player["discard"][metal_indices[1]]["serial"] = 9991
            if evolved:
                player["active"][0]["preEvolution"] = [
                    {"id": main.DURALUDON, "serial": 3, "playerIndex": 0}
                ]
            return raw

        start = mutate(phase_b.observation(86160056, 35, 0), False)
        self.assertEqual(main.agent(start), [0])
        self.assertEqual(main._CONTINUITY_PENDING["reserved_energy_serials"], [9991])
        activate = mutate(phase_b.observation(86160056, 36, 0), True)
        self.assertEqual(main.agent(activate), [0])
        attach = mutate(phase_b.observation(86160056, 37, 0), True)
        self.assertEqual(main.agent(attach), [1])
        owners = {
            item["token"]: item["owner"]
            for item in main.CONTINUITY_LATEST_TRACE["ledger"]["resources"]
        }
        self.assertEqual(owners["discard:9991"], "H0")
        self.assertIsNone(owners["discard:9992"])

    def test_pending_turbo_never_retargets_and_role_identity_is_exact(self):
        self.assertEqual(main.agent(phase_b.observation(86160574, 28, 1)), [0])
        bound = main._CONTINUITY_PENDING["line_key"]
        callback = phase_b.observation(86160574, 29, 1)
        player = callback["current"]["players"][1]
        def raw_lineage(pokemon):
            ancestors = pokemon.get("preEvolution") or []
            root = next(
                (card for card in ancestors if card and card["id"] == main.DURALUDON),
                ancestors[0] if ancestors else pokemon,
            )
            return f"p1:line:{root['id']}:{root['serial']}"

        player["bench"] = [
            pokemon for pokemon in player["bench"] if raw_lineage(pokemon) != bound
        ]
        self.assertEqual(main.agent(callback), [])
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

        self.setUp()
        self.assertEqual(main.agent(phase_b.observation(86160574, 28, 1)), [0])
        callback = phase_b.observation(86160574, 29, 1)
        self.assertEqual(main.agent(callback), [0, 1, 2])
        pending = main._CONTINUITY_PENDING
        trace = main.CONTINUITY_LATEST_TRACE
        self.assertEqual(
            trace["H1_after_KO"]["identity"]["line_key"], pending["line_key"]
        )
        self.assertEqual(
            {item["line_key"] for item in pending["assigned_energy"]},
            {pending["line_key"]},
        )
        self.assertEqual(
            {item["role"] for item in pending["assigned_energy"]}, {"H1_after_KO"}
        )

    def test_missing_alloy_and_retreat_targets_clear_pending(self):
        self.assertEqual(main.agent(phase_b.observation(86160056, 35, 0)), [0])
        activate = phase_b.observation(86160056, 36, 0)
        activate["current"]["players"][0]["active"] = []
        main.agent(activate)
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

        self.setUp()
        fixture = phase_b.Continuity2PhaseBTests()
        start, first, _, _ = fixture._paid_retreat_observations()
        main.agent(start)
        first["current"]["players"][0]["bench"] = []
        main.agent(first)
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")


if __name__ == "__main__":
    unittest.main()
