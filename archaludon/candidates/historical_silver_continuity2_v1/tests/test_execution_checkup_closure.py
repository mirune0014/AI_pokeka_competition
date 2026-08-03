import copy
from pathlib import Path
import sys
import unittest


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CANDIDATE_DIR))
sys.path.insert(0, str(TEST_DIR))

import main  # noqa: E402
import test_continuity2_phase_b as phase_b  # noqa: E402
from test_public_combat_envelope_closure import observation, pokemon  # noqa: E402


def metal(serial, player_index=0):
    return {"id": main.METAL_ENERGY, "serial": serial, "playerIndex": player_index}


def dragapult(serial=900, player_index=1):
    return pokemon(121, 320, [2, 5], player_index, serial)


def set_main_select(raw, options):
    raw["select"]["context"] = int(main.SelectContext.MAIN)
    raw["select"]["option"] = options
    raw["select"]["minCount"] = 1
    raw["select"]["maxCount"] = 1
    raw["select"]["effect"] = None
    raw["select"]["contextCard"] = None


class ExecutionCheckupClosureTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None

    def _acceleration_case(self, opponent, opponent_bench=()):
        raw = observation(
            pokemon(main.DURALUDON, 130, [8], 0, 100, max_hp=130),
            opponent,
            opponent_bench=opponent_bench,
        )
        player = raw["current"]["players"][0]
        player["hand"] = [metal(1001), metal(1002)]
        player["handCount"] = 2
        obs = main.to_observation_class(copy.deepcopy(raw))
        slot = main.continuity_slots(obs)[0]
        cards = list(obs.current.players[0].hand)
        transaction = main._continuity_energy_transition(
            obs,
            slot,
            "ALLOY",
            2,
            "H0",
            energy_cards=cards,
            source_active_line=slot["line_key"],
            effect_serial=777,
        )
        return raw, obs, slot, transaction

    def test_acceleration_projects_fatal_dreepy_dragapult_promotion(self):
        raw, obs, slot, transaction = self._acceleration_case(
            pokemon(119, 50, [], 1, 200, max_hp=70),
            (dragapult(201),),
        )
        projected = main._continuity_project_energy_transaction(
            obs, slot, transaction, 2
        )
        route = main._continuity_attack_route(
            obs, projected, legal_attack_ids=None, primary_only=True
        )
        envelope = main.continuity_response_envelope(
            obs, projected["pokemon"], route["attack_id"]
        )
        self.assertEqual(projected["energy_values"], [8, 8, 8])
        self.assertEqual(slot["energy_values"], [8])
        self.assertEqual(raw["current"]["players"][0]["active"][0]["energies"], [8])
        self.assertEqual(envelope["response_route"], "MANDATORY_PROMOTION")
        self.assertEqual(envelope["active_total_max"], 200)
        self.assertIsNone(main._continuity_certified_primary_line(
            obs,
            slot,
            acceleration_cap=3,
            acceleration_transaction=transaction,
        ))

    def test_acceleration_non_ko_and_binding_controls(self):
        _, obs, slot, transaction = self._acceleration_case(
            pokemon(main.DURALUDON, 130, [], 1, 210, max_hp=130)
        )
        certificate = main._continuity_certified_primary_line(
            obs,
            slot,
            acceleration_cap=3,
            acceleration_transaction=transaction,
        )
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate["execution_slot"]["energy_count"], 3)
        self.assertEqual(certificate["response_envelope"]["response_route"], "ACTIVE_SURVIVES")
        self.assertEqual(certificate["response_envelope"]["h0_outgoing"]["damage"], 80)
        self.assertIsNone(main._continuity_certified_primary_line(
            obs, slot, acceleration_cap=1, acceleration_transaction=transaction
        ))
        self.assertIsNone(main._continuity_certified_primary_line(
            obs, slot, acceleration_cap=3, acceleration_transaction=None
        ))
        synthetic = main._continuity_energy_transition(
            obs,
            slot,
            "TURBO",
            2,
            "H1_after_KO",
            source_active_line="p0:line:666:999",
            effect_serial=999,
            allow_synthetic=True,
        )
        self.assertIsNone(main._continuity_certified_primary_line(
            obs, slot, acceleration_cap=3, acceleration_transaction=synthetic
        ))

    def test_manual_now_uses_projected_ko_route_and_rejects_bench_h1(self):
        raw = observation(
            pokemon(main.ARCHALUDON_EX, 300, [8, 8], 0, 300, max_hp=300),
            pokemon(119, 50, [], 1, 301, max_hp=70),
            own_bench=(pokemon(main.DURALUDON, 30, [8, 8, 8], 0, 302, max_hp=130),),
            opponent_bench=(dragapult(303),),
        )
        player = raw["current"]["players"][0]
        player["hand"] = [metal(304)]
        player["handCount"] = 1
        set_main_select(raw, [
            {
                "type": int(main.OptionType.ATTACH),
                "area": int(main.AreaType.HAND),
                "index": 0,
                "inPlayArea": int(main.AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
            {"type": int(main.OptionType.END)},
        ])
        plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
        self.assertEqual(plan["choice"]["kind"], "H0_LAST_MANUAL_PREREQUISITE")
        self.assertEqual(plan["H0"]["identity"]["energy_count"], 3)
        self.assertEqual(plan["H0_execution_transition"]["energy_serials"], [304])
        self.assertEqual(plan["response_envelope"]["response_route"], "MANDATORY_PROMOTION")
        self.assertEqual(plan["response_envelope"]["bench_counters_max"], 60)
        self.assertIsNone(plan["H1_after_KO"]["identity"])
        self.assertEqual(raw["current"]["players"][0]["active"][0]["energies"], [8, 8])

    def _promotion_case(self, hp):
        raw = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 400, max_hp=160),
            pokemon(119, 50, [], 1, 401, max_hp=70),
            opponent_bench=(dragapult(402),),
        )
        player = raw["current"]["players"][0]
        player["active"] = []
        player["bench"] = [
            pokemon(main.ARCHALUDON_EX, hp, [8, 8], 0, 403, max_hp=300)
        ]
        player["hand"] = [metal(404)]
        player["handCount"] = 1
        raw["select"]["context"] = int(main.SelectContext.TO_ACTIVE)
        raw["select"]["option"] = [{
            "type": int(main.OptionType.CARD),
            "area": int(main.AreaType.BENCH),
            "index": 0,
        }]
        raw["select"]["minCount"] = 1
        raw["select"]["maxCount"] = 1
        return raw

    def test_to_active_future_manual_projects_before_certification(self):
        damaged = main.build_continuity2_plan(
            main.to_observation_class(self._promotion_case(150))
        )
        self.assertEqual(
            (damaged.get("choice") or {}).get("kind"), "KO_PROMOTE_CERTIFIED_H1"
        )
        self.assertEqual(damaged["H1_after_KO"]["readiness"], "READY_NEXT_TURN")
        self.assertEqual(damaged["H1_after_KO"]["identity"]["hp"], 150)
        self.assertEqual(damaged["response_envelope"]["active_total_max"], 0)
        self.assertEqual(damaged["response_envelope"]["payable_attacks"], [])

        safe = main.build_continuity2_plan(
            main.to_observation_class(self._promotion_case(300))
        )
        self.assertEqual(safe["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")
        self.assertEqual(safe["H1_after_KO"]["readiness"], "READY_NEXT_TURN")
        self.assertEqual(safe["H1_after_KO"]["identity"]["energy_count"], 3)
        self.assertEqual(
            safe["response_envelope"]["response_route"],
            "TO_ACTIVE_PRE_H1_CHECKUP",
        )

    def test_burn_checkup_ko_routes_to_dragapult(self):
        raw = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 500, max_hp=160),
            pokemon(119, 70, [], 1, 501, max_hp=70),
            opponent_bench=(dragapult(502),),
        )
        raw["current"]["players"][1]["burned"] = True
        envelope = main.continuity_response_envelope(
            main.to_observation_class(raw),
            defensive_attack_id=965,
        )
        self.assertFalse(envelope["unknown"])
        self.assertEqual(envelope["opponent_checkup"]["outcome"], "CHECKUP_KO")
        self.assertEqual(envelope["response_route"], "MANDATORY_PROMOTION")
        self.assertEqual(envelope["active_total_max"], 200)

        terminal_raw = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 510, max_hp=160),
            pokemon(119, 70, [], 1, 511, max_hp=70),
        )
        terminal_raw["current"]["players"][1]["burned"] = True
        terminal = main.continuity_response_envelope(
            main.to_observation_class(terminal_raw), defensive_attack_id=965
        )
        self.assertFalse(terminal["unknown"])
        self.assertEqual(terminal["opponent_checkup"]["outcome"], "CHECKUP_KO")
        self.assertEqual(terminal["response_route"], "NO_VISIBLE_RESPONSE_TERMINAL")
        self.assertTrue(terminal["terminal"])

    def test_poison_intensity_is_unknown_for_all_visible_promotion_shapes(self):
        benches = (
            (),
            (pokemon(main.CORNERSTONE_OGERPON_EX, 210, [], 1, 610),),
            (
                pokemon(main.CORNERSTONE_OGERPON_EX, 210, [], 1, 611),
                pokemon(345, 140, [], 1, 612),
            ),
        )
        for index, opponent_bench in enumerate(benches):
            with self.subTest(bench_count=len(opponent_bench)):
                raw = observation(
                    pokemon(main.CINDERACE, 160, [8], 0, 600 + index, max_hp=160),
                    pokemon(119, 60, [], 1, 620 + index, max_hp=70),
                    opponent_bench=opponent_bench,
                )
                raw["current"]["players"][1]["poisoned"] = True
                envelope = main.continuity_response_envelope(
                    main.to_observation_class(raw), defensive_attack_id=965
                )
                self.assertTrue(envelope["unknown"])
                self.assertIn("UNKNOWN_POISON_INTENSITY", envelope["unknown_reasons"])
                self.assertEqual(
                    envelope["opponent_checkup"]["outcome"],
                    "UNKNOWN_POISON_INTENSITY",
                )

        # A known zero-damage block proves that poison remains unresolved at
        # both low and high visible HP; the boolean state cannot encode whether
        # Tainted Horn's eight-counter poison is lingering.
        for hp in (11, 80):
            with self.subTest(blocked_hp=hp):
                blocked = observation(
                    pokemon(main.CINDERACE, 160, [8], 0, 640 + hp, max_hp=160),
                    pokemon(
                        main.CORNERSTONE_OGERPON_EX, hp, [], 1, 660 + hp,
                        max_hp=210,
                    ),
                )
                blocked["current"]["players"][1]["poisoned"] = True
                blocked_envelope = main.continuity_response_envelope(
                    main.to_observation_class(blocked), defensive_attack_id=965
                )
                self.assertTrue(blocked_envelope["h0_outgoing"]["exact"])
                self.assertEqual(blocked_envelope["h0_outgoing"]["damage"], 0)
                self.assertTrue(blocked_envelope["unknown"])
                self.assertIn(
                    "UNKNOWN_POISON_INTENSITY",
                    blocked_envelope["unknown_reasons"],
                )

        mixed = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 750, max_hp=160),
            pokemon(119, 80, [], 1, 751, max_hp=80),
            opponent_bench=(dragapult(752),),
        )
        mixed["current"]["players"][1]["poisoned"] = True
        mixed["current"]["players"][1]["burned"] = True
        mixed_envelope = main.continuity_response_envelope(
            main.to_observation_class(mixed), defensive_attack_id=965
        )
        self.assertTrue(mixed_envelope["unknown"])
        self.assertEqual(
            [row["status"] for row in mixed_envelope["opponent_checkup"]["components"]],
            ["POISONED", "BURNED"],
        )
        self.assertEqual(mixed_envelope["opponent_checkup"]["first_damage"], 20)
        self.assertEqual(
            mixed_envelope["opponent_checkup"]["outcome"],
            "UNKNOWN_POISON_INTENSITY",
        )

        direct = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 630, max_hp=160),
            pokemon(119, 50, [], 1, 631, max_hp=70),
            opponent_bench=(dragapult(632),),
        )
        direct["current"]["players"][1]["poisoned"] = True
        direct_envelope = main.continuity_response_envelope(
            main.to_observation_class(direct), defensive_attack_id=965
        )
        self.assertNotIn("UNKNOWN_POISON_INTENSITY", direct_envelope["unknown_reasons"])
        self.assertEqual(direct_envelope["response_route"], "MANDATORY_PROMOTION")

        direct_terminal = copy.deepcopy(direct)
        direct_terminal["current"]["players"][1]["bench"] = []
        terminal_envelope = main.continuity_response_envelope(
            main.to_observation_class(direct_terminal), defensive_attack_id=965
        )
        self.assertNotIn(
            "UNKNOWN_POISON_INTENSITY", terminal_envelope["unknown_reasons"]
        )
        self.assertEqual(
            terminal_envelope["response_route"], "NO_VISIBLE_RESPONSE_TERMINAL"
        )

    def test_bench_damage_carries_into_h1_hp_and_raging_hammer(self):
        raw = observation(
            pokemon(main.DURALUDON, 130, [8, 8, 8], 0, 700, max_hp=130),
            pokemon(main.DURALUDON, 130, [], 1, 701, max_hp=130),
        )
        obs = main.to_observation_class(raw)
        slot = main.continuity_slots(obs)[0]
        current_envelope = {
            "unknown": False,
            "payable_attacks": [{
                "status": "KNOWN", "bench_damage": 0, "bench_counters": 20,
            }],
            "reactive_statuses": [],
            "response_statuses": [],
            "next_turn_basic_damage_block": False,
            "h0_outgoing": {"attacker_serial": slot["serial"]},
            "post_response_active_candidates": [{
                "branch_id": "CONTROL_ACTIVE_SURVIVES",
                "card_id": main.opp_active_pokemon(obs).id,
                "serial": main.opp_active_pokemon(obs).serial,
                "lineage_key": main.continuity_lineage_key(
                    main.opp_active_pokemon(obs), 1
                ),
                "hp": main.opp_active_pokemon(obs).hp,
                "max_hp": main.opp_active_pokemon(obs).maxHp,
                "source_route": "CONTROL_ACTIVE_STAYS",
                "defeated_identity": None,
                "terminal": False,
                "transition_trace": [],
                "unknown_reasons": [],
            }],
        }
        certificate = main._continuity_certified_primary_line(
            obs, slot, current_envelope=current_envelope
        )
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate["carried_bench_threat"], 20)
        self.assertEqual(certificate["execution_slot"]["hp"], 110)
        self.assertEqual(certificate["route"]["damage"], 100)
        self.assertIs(certificate["response_envelope"], current_envelope)
        self.assertEqual(certificate["h1_primary_gate"]["state"], "READY")
        self.assertEqual(slot["hp"], 130)

    def test_exact_energy_count_and_evolution_alloy_never_double_add(self):
        raw = observation(
            pokemon(main.ARCHALUDON_EX, 300, [8, 8], 0, 800, max_hp=300),
            pokemon(main.DURALUDON, 130, [], 1, 801, max_hp=130),
        )
        player = raw["current"]["players"][0]
        player["hand"] = [metal(802)]
        player["handCount"] = 1
        obs = main.to_observation_class(copy.deepcopy(raw))
        slot = main.continuity_slots(obs)[0]
        transaction = main._continuity_energy_transition(
            obs,
            slot,
            "MANUAL_NOW",
            1,
            "H0",
            energy_cards=list(obs.current.players[0].hand),
        )
        certificate = main._continuity_certified_primary_line(
            obs, slot, acceleration_cap=1, acceleration_transaction=transaction
        )
        self.assertEqual(certificate["execution_slot"]["energy_count"], 3)
        self.assertEqual(slot["energy_count"], 2)

        powered_raw = observation(
            pokemon(main.ARCHALUDON_EX, 300, [8, 8, 8], 0, 810, max_hp=300),
            pokemon(main.DURALUDON, 130, [], 1, 811, max_hp=130),
        )
        powered_obs = main.to_observation_class(powered_raw)
        powered_slot = main.continuity_slots(powered_obs)[0]
        powered = main._continuity_certified_primary_line(powered_obs, powered_slot)
        self.assertIsNotNone(powered)
        self.assertEqual(powered["execution_slot"]["energy_count"], 3)
        self.assertIsNone(powered["execution_transition"])

        evolve_raw = phase_b.observation(86160056, 35, 0)
        evolve_obs = main.to_observation_class(copy.deepcopy(evolve_raw))
        evolve_slot = next(
            item for item in main.continuity_slots(evolve_obs)
            if item["area"] == int(main.AreaType.ACTIVE)
        )
        evolve_option = next(
            option for option in evolve_obs.select.option
            if option.type == main.OptionType.EVOLVE
            and main.option_card(evolve_obs, option).id == main.ARCHALUDON_EX
        )
        evolved = main._continuity_project_evolved_slot(
            evolve_obs, evolve_slot, main.option_card(evolve_obs, evolve_option), 2
        )
        self.assertEqual(evolved["energy_count"], 3)
        evolved_certificate = main._continuity_certified_primary_line(
            evolve_obs, evolved
        )
        self.assertIsNotNone(evolved_certificate)
        self.assertEqual(evolved_certificate["execution_slot"]["energy_count"], 3)
        self.assertEqual(evolve_slot["energy_count"], 1)

    def test_ice_recomputes_raging_hammer_and_response_route_from_healed_h0(self):
        raw = observation(
            pokemon(main.DURALUDON, 50, [8, 8, 8], 0, 900, max_hp=130),
            pokemon(1031, 150, [3], 1, 901, max_hp=330),
            opponent_bench=(dragapult(902),),
            stadium=(main.FULL_METAL_LAB,),
        )
        player = raw["current"]["players"][0]
        player["hand"] = [{"id": main.JUMBO_ICE_CREAM, "serial": 903, "playerIndex": 0}]
        player["handCount"] = 1
        set_main_select(raw, [
            {
                "type": int(main.OptionType.PLAY),
                "area": int(main.AreaType.HAND),
                "index": 0,
            },
            {"type": int(main.OptionType.ATTACK), "attackId": main.RAGING_HAMMER},
            {"type": int(main.OptionType.END)},
        ])
        plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
        self.assertEqual(plan["choice"]["kind"], "SURVIVAL_PLAY")
        self.assertEqual(plan["H0_execution_transition"]["kind"], "HEAL")
        self.assertEqual(plan["H0"]["identity"]["hp"], 130)
        self.assertEqual(plan["H0"]["attack"]["damage"], 80)
        self.assertEqual(plan["response_envelope"]["h0_outgoing"]["damage"], 80)
        self.assertTrue(plan["response_envelope"]["response_route"].startswith("ACTIVE_SURVIVES"))
        self.assertEqual(raw["current"]["players"][0]["active"][0]["hp"], 50)

    def test_burn_non_ko_uses_post_checkup_hp_for_hammer_and_rescue(self):
        raw = observation(
            pokemon(main.DURALUDON, 130, [8, 8, 8], 0, 920, max_hp=130),
            pokemon(
                main.DURALUDON, 130, [8, 8, 8], 1, 921,
                tools=(main._CONTINUITY_RESCUE_BOARD,), max_hp=130,
            ),
            opponent_bench=(pokemon(main.CINDERACE, 160, [], 1, 922, max_hp=160),),
        )
        raw["current"]["players"][1]["burned"] = True
        envelope = main.continuity_response_envelope(
            main.to_observation_class(raw), defensive_attack_id=main.RAGING_HAMMER
        )
        current = next(
            candidate for candidate in envelope["response_candidates"]
            if candidate["serial"] == 921
        )
        self.assertFalse(envelope["unknown"])
        self.assertEqual(envelope["opponent_checkup"]["hp_after_first_checkup"], 30)
        self.assertEqual(current["identity"]["hp"], 30)
        self.assertEqual(current["active_attack_total_max"], 180)
        self.assertEqual(envelope["response_route"], "ACTIVE_SURVIVES_WITH_EXACT_RETREAT")

    def test_burn_second_checkup_coin_fails_closed_at_ko_boundary(self):
        raw = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 930, max_hp=160),
            pokemon(119, 80, [], 1, 931, max_hp=80),
        )
        raw["current"]["players"][1]["burned"] = True
        envelope = main.continuity_response_envelope(
            main.to_observation_class(raw), defensive_attack_id=965
        )
        current = next(
            candidate for candidate in envelope["response_candidates"]
            if candidate["serial"] == 931
        )
        self.assertEqual(envelope["opponent_checkup"]["hp_after_first_checkup"], 10)
        self.assertEqual(envelope["opponent_checkup"]["outcome"], "ACTIVE_SURVIVES")
        self.assertTrue(envelope["unknown"])
        self.assertIn("OPPONENT_BURN_CURE_COIN", envelope["unknown_reasons"])
        self.assertEqual(
            current["second_checkup"]["outcome"], "UNKNOWN_BURN_CURE_COIN"
        )

    def test_checkup_ko_removes_aura_but_retains_precheckup_reaction(self):
        aura_active = pokemon(304, 70, [1, 1, 1], 1, 932, max_hp=150)
        aura_active["energyCards"].append({
            "id": main._CONTINUITY_SPIKY_ENERGY,
            "serial": 1932,
            "playerIndex": 1,
        })
        raw = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 933, max_hp=160),
            aura_active,
            opponent_bench=(pokemon(310, 120, [1, 1, 1], 1, 934),),
        )
        raw["current"]["players"][1]["burned"] = True
        envelope = main.continuity_response_envelope(
            main.to_observation_class(raw), defensive_attack_id=965
        )
        self.assertFalse(envelope["unknown"])
        self.assertEqual(envelope["opponent_checkup"]["outcome"], "CHECKUP_KO")
        self.assertEqual(envelope["reactive_counters"], 20)
        self.assertTrue(any(
            row["serial"] == 1932 for row in envelope["reaction_sources"]
        ))
        self.assertEqual(envelope["active_damage_max"], 80)
        self.assertFalse(any(
            row["card_id"] == 304 for row in envelope["modifier_sources"]
        ))

    def test_own_checkup_reaction_order_and_simultaneous_ko_fail_closed(self):
        spiky = observation(
            pokemon(main.CINDERACE, 30, [8], 0, 940, max_hp=160),
            pokemon(119, 70, [main._CONTINUITY_SPIKY_ENERGY], 1, 941, max_hp=70),
        )
        spiky["current"]["players"][0]["burned"] = True
        spiky_envelope = main.continuity_response_envelope(
            main.to_observation_class(spiky), defensive_attack_id=965
        )
        self.assertTrue(spiky_envelope["unknown"])
        self.assertEqual(spiky_envelope["reactive_counters"], 20)
        self.assertEqual(spiky_envelope["own_checkup"]["hp_after_h0"], 10)
        self.assertEqual(
            spiky_envelope["own_checkup"]["outcome"],
            "OWN_CHECKUP_KO_REQUIRES_PROMOTION",
        )
        self.assertEqual(spiky_envelope["response_candidates"], [])

        simultaneous = observation(
            pokemon(main.CINDERACE, 20, [8], 0, 950, max_hp=160),
            pokemon(119, 70, [], 1, 951, max_hp=70),
            own_bench=(pokemon(main.DURALUDON, 130, [8, 8, 8], 0, 952, max_hp=130),),
            opponent_bench=(dragapult(953),),
        )
        simultaneous["current"]["players"][0]["burned"] = True
        simultaneous["current"]["players"][1]["burned"] = True
        both = main.continuity_response_envelope(
            main.to_observation_class(simultaneous), defensive_attack_id=965
        )
        self.assertEqual(both["opponent_checkup"]["outcome"], "CHECKUP_KO")
        self.assertIn(
            "SIMULTANEOUS_CHECKUP_KO_REQUIRES_PROMOTIONS",
            both["unknown_reasons"],
        )

    def test_poisoned_ten_hp_active_cannot_certify_safe_bench_successor(self):
        raw = observation(
            pokemon(main.CINDERACE, 10, [8], 0, 960, max_hp=160),
            dragapult(961),
            own_bench=(
                pokemon(main.DURALUDON, 130, [8, 8, 8], 0, 962, max_hp=130),
            ),
        )
        raw["current"]["players"][0]["poisoned"] = True
        set_main_select(raw, [
            {"type": int(main.OptionType.ATTACK), "attackId": 965},
            {"type": int(main.OptionType.END)},
        ])
        plan = main.build_continuity2_plan(
            main.to_observation_class(copy.deepcopy(raw))
        )
        self.assertTrue(plan["response_envelope"]["unknown"])
        self.assertIn(
            "UNKNOWN_POISON_INTENSITY",
            plan["response_envelope"]["unknown_reasons"],
        )
        self.assertIsNone(plan["H1_after_KO"]["identity"])

    def test_cape_projection_adds_exact_tool_once_without_mutation(self):
        raw = phase_b.observation(86162213, 38, 0)
        player = raw["current"]["players"][0]
        hand = player["hand"]
        hand[1]["id"] = main.HERO_CAPE
        cape_serial = hand[1]["serial"]
        raw["select"]["option"][1] = {
            "type": int(main.OptionType.ATTACH),
            "area": int(main.AreaType.HAND),
            "index": 1,
            "inPlayArea": int(main.AreaType.ACTIVE),
            "inPlayIndex": 0,
        }
        source_active = copy.deepcopy(player["active"][0])
        plan = main.build_continuity2_plan(
            main.to_observation_class(copy.deepcopy(raw))
        )
        self.assertEqual(plan["choice"]["kind"], "CAPE_SURVIVAL_BREAKPOINT")
        self.assertEqual(plan["H0_execution_transition"]["serial"], cape_serial)
        self.assertEqual(plan["H0"]["identity"]["hp"], source_active["hp"] + 100)
        self.assertEqual(
            plan["H0"]["identity"]["max_hp"], source_active["maxHp"] + 100
        )
        cape_rows = [
            row for row in plan["response_envelope"]["attachment_classifications"]
            if row["kind"] == "TOOL" and row["card_id"] == main.HERO_CAPE
        ]
        self.assertEqual(len(cape_rows), 1)
        self.assertEqual(cape_rows[0]["serial"], cape_serial)
        self.assertEqual(player["active"][0], source_active)

    def test_future_bench_does_not_inherit_status_and_evolution_clears_it(self):
        raw = observation(
            pokemon(main.CINDERACE, 160, [8], 0, 970, max_hp=160),
            pokemon(main.DURALUDON, 130, [], 1, 971, max_hp=130),
            own_bench=(pokemon(main.DURALUDON, 130, [8, 8, 8], 0, 972, max_hp=130),),
        )
        raw["current"]["players"][0]["poisoned"] = True
        obs = main.to_observation_class(raw)
        future = obs.current.players[0].bench[0]
        envelope = main.continuity_response_envelope(
            obs, future, main.RAGING_HAMMER
        )
        self.assertFalse(envelope["own_checkup"]["applied"])
        self.assertNotIn("UNKNOWN_POISON_INTENSITY", envelope["unknown_reasons"])

        evolve_raw = phase_b.observation(86160056, 35, 0)
        evolve_raw["current"]["players"][0]["poisoned"] = True
        evolve_plan = main.build_continuity2_plan(
            main.to_observation_class(copy.deepcopy(evolve_raw))
        )
        self.assertEqual(evolve_plan["H0"]["identity"]["card_id"], main.ARCHALUDON_EX)
        self.assertFalse(evolve_plan["response_envelope"]["own_checkup"]["applied"])
        self.assertNotIn(
            "UNKNOWN_POISON_INTENSITY",
            evolve_plan["response_envelope"]["unknown_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
