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
from test_public_combat_envelope_closure import observation, pokemon  # noqa: E402


def metal(serial, player_index=0):
    return {"id": main.METAL_ENERGY, "serial": serial, "playerIndex": player_index}


def clean_observation(own, opponent, own_bench=(), opponent_bench=(), stadium=()):
    raw = observation(
        own, opponent, own_bench=own_bench,
        opponent_bench=opponent_bench, stadium=stadium,
    )
    for player in raw["current"]["players"]:
        player["hand"] = []
        player["handCount"] = 0
        player["discard"] = []
    raw["current"]["yourIndex"] = 0
    raw["current"]["supporterPlayed"] = False
    raw["current"]["retreated"] = False
    return raw


def set_main_select(raw, options):
    raw["select"] = {
        "type": 0,
        "context": int(main.SelectContext.MAIN),
        "minCount": 1,
        "maxCount": 1,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "option": options,
        "deck": None,
        "contextCard": None,
        "effect": None,
    }


def set_to_active_select(raw, count=1):
    raw["select"] = {
        "type": 1,
        "context": int(main.SelectContext.TO_ACTIVE),
        "minCount": 1,
        "maxCount": 1,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "option": [
            {
                "type": int(main.OptionType.CARD),
                "area": int(main.AreaType.BENCH),
                "index": index,
                "playerIndex": 0,
            }
            for index in range(count)
        ],
        "deck": None,
        "contextCard": None,
        "effect": None,
    }


def turbo_state(
    *, opponent_hp=50, successor_id=main.ARCHALUDON_EX,
    successor_energies=(8, 8, 8), opponent_bench=None,
    opponent_energy=(), hand=(), discard=(), evolve=False,
):
    if opponent_bench is None:
        opponent_bench = (
            pokemon(
                main.CORNERSTONE_OGERPON_EX, 210, [6, 6, 6], 1, 4000,
                max_hp=210,
            ),
        )
    successor_hp = 130 if successor_id == main.DURALUDON else 300
    raw = clean_observation(
        pokemon(main.CINDERACE, 160, [8], 0, 1000, max_hp=160),
        pokemon(119, opponent_hp, opponent_energy, 1, 3000, max_hp=70),
        own_bench=(
            pokemon(
                successor_id, successor_hp, successor_energies, 0, 2000,
                max_hp=successor_hp,
            ),
        ),
        opponent_bench=opponent_bench,
    )
    raw["current"]["players"][0]["hand"] = list(copy.deepcopy(hand))
    raw["current"]["players"][0]["handCount"] = len(hand)
    raw["current"]["players"][0]["discard"] = list(copy.deepcopy(discard))
    options = [{"type": int(main.OptionType.ATTACK), "attackId": 965}]
    if evolve:
        options.append({
            "type": int(main.OptionType.EVOLVE),
            "area": int(main.AreaType.HAND),
            "index": 0,
            "inPlayArea": int(main.AreaType.BENCH),
            "inPlayIndex": 0,
        })
    set_main_select(raw, options)
    return raw


def active_evolution_state(*, status=None, stadium=(), turn=2, first_player=1):
    raw = clean_observation(
        pokemon(main.DURALUDON, 130, [8], 0, 5000, max_hp=130),
        pokemon(119, 70, [], 1, 6000, max_hp=70),
        stadium=stadium,
    )
    player = raw["current"]["players"][0]
    player["hand"] = [{
        "id": main.ARCHALUDON_EX, "serial": 5001, "playerIndex": 0,
    }]
    player["handCount"] = 1
    player["discard"] = [metal(5002), metal(5003)]
    if status:
        player[status] = True
    raw["current"]["turn"] = turn
    raw["current"]["firstPlayer"] = first_player
    set_main_select(raw, [{
        "type": int(main.OptionType.EVOLVE),
        "area": int(main.AreaType.HAND),
        "index": 0,
        "inPlayArea": int(main.AreaType.ACTIVE),
        "inPlayIndex": 0,
    }])
    return raw


def to_active_state(
    *, opponent_hp=70, burned=False, poisoned=False,
    opponent_bench=(), own_bench=None,
):
    if own_bench is None:
        own_bench = (
            pokemon(main.ARCHALUDON_EX, 300, [8, 8, 8], 0, 7000, max_hp=300),
        )
    raw = clean_observation(
        pokemon(main.CINDERACE, 160, [8], 0, 7100, max_hp=160),
        pokemon(119, opponent_hp, [], 1, 7200, max_hp=70),
        own_bench=own_bench,
        opponent_bench=opponent_bench,
    )
    raw["current"]["players"][0]["active"] = []
    raw["current"]["players"][1]["burned"] = burned
    raw["current"]["players"][1]["poisoned"] = poisoned
    # On even turn 2 with player 0 going first, player 1 is ending its turn.
    raw["current"]["turn"] = 2
    raw["current"]["firstPlayer"] = 0
    set_to_active_select(raw, len(own_bench))
    return raw


class PublicH1ExecutionWindowClosureTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None

    def test_h0_execution_lock_cannot_parent_positive_continuity(self):
        cases = (
            ("confused", 2, 1, "UNKNOWN"),
            ("asleep", 2, 1, "LOCKED"),
            ("paralyzed", 2, 1, "LOCKED"),
            (None, 1, 0, "LOCKED"),
        )
        for status, turn, first_player, gate_state in cases:
            with self.subTest(status=status, turn=turn):
                raw = clean_observation(
                    pokemon(
                        main.ARCHALUDON_EX, 300, [8, 8, 8], 0, 8000,
                        max_hp=300,
                    ),
                    pokemon(119, 70, [], 1, 8100, max_hp=70),
                    own_bench=(
                        pokemon(main.DURALUDON, 130, [8, 8, 8], 0, 8200),
                    ),
                )
                if status:
                    raw["current"]["players"][0][status] = True
                raw["current"]["turn"] = turn
                raw["current"]["firstPlayer"] = first_player
                set_main_select(raw, [{
                    "type": int(main.OptionType.ATTACK),
                    "attackId": main.METAL_DEFENDER,
                }])
                plan = main.build_continuity2_plan(main.to_observation_class(raw))
                outgoing = plan["response_envelope"]["h0_outgoing"]
                self.assertFalse(outgoing["exact"])
                self.assertEqual(outgoing["execution_gate"]["state"], gate_state)
                self.assertNotIn(
                    plan["H1_survive"]["readiness"],
                    {"READY", "READY_AFTER_SURVIVAL"},
                )
                self.assertIsNone(plan["H1_after_KO"]["identity"])
                self.assertFalse(any(
                    row["role"] in {"H0", "H1", "H1_survive", "H1_after_KO"}
                    for row in plan["ledger"]["reservations"]
                ))
                self.assertIsNone(plan.get("choice"))

    def test_exact_evolution_clears_status_but_turn_one_and_dizzying_close(self):
        for status in ("confused", "asleep", "paralyzed"):
            with self.subTest(status=status):
                raw = active_evolution_state(status=status)
                plan = main.build_continuity2_plan(main.to_observation_class(raw))
                self.assertEqual(plan["choice"]["kind"], "H0_EVOLVE_ALLOY_ROUTE")
                self.assertEqual(plan["H0"]["readiness"], "READY_AFTER_EVOLVE_ALLOY")
                gate = plan["response_envelope"]["h0_execution_gate"]
                self.assertEqual(gate["state"], "READY")
                self.assertEqual(gate["identity_kind"], "EXACT_EVOLUTION")

        for label, raw, expected_reason in (
            (
                "dizzying",
                active_evolution_state(
                    status="confused", stadium=(main._CONTINUITY_DIZZYING_VALLEY,)
                ),
                "DIZZYING_VALLEY_REAPPLIES_CONFUSION",
            ),
            (
                "turn_one",
                active_evolution_state(
                    status="asleep", turn=1, first_player=0
                ),
                "FIRST_PLAYER_TURN_ONE_ATTACK_LOCK",
            ),
        ):
            with self.subTest(closed=label):
                obs = main.to_observation_class(raw)
                slot = main.continuity_slots(obs)[0]
                evolution = obs.current.players[0].hand[0]
                projected = main._continuity_project_evolved_slot(
                    obs, slot, evolution, 2
                )
                gate = main._continuity_h0_execution_gate(obs, projected)
                self.assertNotEqual(gate["state"], "READY")
                self.assertEqual(gate["reason"], expected_reason)
                plan = main.build_continuity2_plan(obs)
                self.assertFalse(
                    plan.get("choice")
                    and plan["choice"].get("kind") == "H0_EVOLVE_ALLOY_ROUTE"
                )
                self.assertFalse(any(
                    row["role"] == "H0" for row in plan["ledger"]["reservations"]
                ))

    def test_cornerstone_promotion_blocks_base_and_future_manual_before_reserve(self):
        ready_plan = main.build_continuity2_plan(main.to_observation_class(turbo_state()))
        self.assertEqual(
            ready_plan["response_envelope"]["response_route"], "MANDATORY_PROMOTION"
        )
        self.assertEqual(
            [
                row["card_id"]
                for row in ready_plan["response_envelope"][
                    "post_response_active_candidates"
                ]
            ],
            [main.CORNERSTONE_OGERPON_EX],
        )
        self.assertIsNone(ready_plan["H1_after_KO"]["identity"])
        self.assertIn(
            "CORNERSTONE_STANCE_ABILITY_ATTACKER_BLOCKED",
            {row["reason"] for row in ready_plan["H1_after_KO"]["rejected"]},
        )

        manual_raw = turbo_state(
            successor_energies=(8, 8), hand=(metal(2001),)
        )
        manual_plan = main.build_continuity2_plan(
            main.to_observation_class(manual_raw)
        )
        self.assertIsNone(manual_plan["H1_after_KO"]["identity"])
        self.assertIn(
            "CORNERSTONE_STANCE_ABILITY_ATTACKER_BLOCKED",
            {row["reason"] for row in manual_plan["H1_after_KO"]["rejected"]},
        )
        self.assertFalse(any(
            row["role"] == "H1_after_KO"
            for row in manual_plan["ledger"]["reservations"]
        ))

    def test_cornerstone_blocks_real_energy_cert_and_bench_evolve_alloy(self):
        raw = turbo_state(
            successor_energies=(8, 8), hand=(metal(2001),)
        )
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs,
            main.active_pokemon(obs),
            965,
            h0_execution_slot=main.continuity_slots(obs)[0],
        )
        slot = main.continuity_slots(obs)[1]
        transaction = main._continuity_energy_transition(
            obs,
            slot,
            "TURBO",
            1,
            "H1_after_KO",
            energy_cards=[obs.current.players[0].hand[0]],
            source_active_line=main.continuity_slots(obs)[0]["line_key"],
            effect_serial=main.active_pokemon(obs).serial,
        )
        self.assertIsNone(main._continuity_certified_primary_line(
            obs,
            slot,
            acceleration_cap=1,
            current_envelope=envelope,
            acceleration_transaction=transaction,
        ))

        evolve_raw = turbo_state(
            successor_id=main.DURALUDON,
            successor_energies=(8,),
            hand=({
                "id": main.ARCHALUDON_EX, "serial": 2001, "playerIndex": 0,
            },),
            discard=(metal(2002), metal(2003)),
            evolve=True,
        )
        evolve_plan = main.build_continuity2_plan(
            main.to_observation_class(evolve_raw)
        )
        self.assertFalse(
            evolve_plan.get("choice")
            and evolve_plan["choice"].get("kind") == "H1_EVOLVE_SAME_CLASS_TIE"
        )
        protected = {"hand:2001", "discard:2002", "discard:2003"}
        self.assertTrue(protected.isdisjoint({
            row["token"]
            for row in evolve_plan["ledger"]["reservations"]
            if row["role"] == "H1_after_KO"
        }))

    def test_public_retreat_cornerstone_branch_blocks_h1(self):
        raw = turbo_state(
            opponent_hp=70,
            opponent_energy=(5,),
        )
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        envelope = plan["response_envelope"]
        self.assertEqual(
            envelope["response_route"], "ACTIVE_SURVIVES_WITH_EXACT_RETREAT"
        )
        self.assertEqual(
            {row["card_id"] for row in envelope["post_response_active_candidates"]},
            {119, main.CORNERSTONE_OGERPON_EX},
        )
        self.assertIsNone(plan["H1_after_KO"]["identity"])
        self.assertIn(
            "CORNERSTONE_STANCE_ABILITY_ATTACKER_BLOCKED",
            {row["reason"] for row in plan["H1_after_KO"]["rejected"]},
        )

    def test_all_target_control_ignores_chosen_trace_and_accepts_terminal(self):
        allowed_bench = (
            pokemon(main.DURALUDON, 130, [], 1, 4100, max_hp=130),
            pokemon(119, 70, [], 1, 4200, max_hp=70),
        )
        raw = turbo_state(
            opponent_hp=70,
            opponent_energy=(5,),
            opponent_bench=allowed_bench,
        )
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs,
            main.active_pokemon(obs),
            965,
            h0_execution_slot=main.continuity_slots(obs)[0],
        )
        successor = main.continuity_slots(obs)[1]
        gate = main._continuity_h1_primary_gate(obs, successor, envelope)
        self.assertEqual(gate["state"], "READY")
        self.assertEqual(len(gate["target_results"]), 3)
        changed = copy.deepcopy(envelope)
        changed["chosen_response_candidate_serial"] = 999999
        changed_gate = main._continuity_h1_primary_gate(obs, successor, changed)
        self.assertEqual(changed_gate, gate)

        terminal_raw = turbo_state(opponent_bench=())
        terminal_obs = main.to_observation_class(terminal_raw)
        terminal_envelope = main.continuity_response_envelope(
            terminal_obs,
            main.active_pokemon(terminal_obs),
            965,
            h0_execution_slot=main.continuity_slots(terminal_obs)[0],
        )
        terminal_gate = main._continuity_h1_primary_gate(
            terminal_obs,
            main.continuity_slots(terminal_obs)[1],
            terminal_envelope,
        )
        self.assertTrue(terminal_envelope["terminal"])
        self.assertEqual(terminal_gate["state"], "READY")
        self.assertEqual(
            terminal_gate["target_results"][0]["reason"],
            "TERMINAL_VACUOUS_PASS",
        )

    def test_incomplete_target_set_fails_before_manual_reservation(self):
        raw = turbo_state(
            opponent_bench=(), successor_energies=(8, 8), hand=(metal(2001),)
        )
        obs = main.to_observation_class(raw)
        slot = main.continuity_slots(obs)[1]
        incomplete = main._continuity_public_envelope_template()
        incomplete["post_response_active_candidates"] = [{
            "branch_id": "INCOMPLETE",
            "terminal": False,
            "card_id": 119,
            "serial": None,
            "lineage_key": None,
            "hp": 50,
            "max_hp": 70,
            "unknown_reasons": [],
        }]
        ledger = main._continuity_resource_ledger(obs)
        role = main._continuity_future_route(
            obs, slot, ledger, "H1_after_KO", incomplete
        )
        self.assertEqual(role["readiness"], "UNKNOWN")
        self.assertEqual(
            role["reason"], "INCOMPLETE_POST_RESPONSE_TARGET_BRANCH"
        )
        self.assertEqual(ledger["reservations"], [])

    def test_bench_successor_does_not_inherit_h0_special_condition(self):
        raw = turbo_state(
            opponent_hp=70,
            opponent_energy=(),
            opponent_bench=(
                pokemon(main.DURALUDON, 130, [], 1, 4100, max_hp=130),
            ),
        )
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs,
            main.active_pokemon(obs),
            965,
            h0_execution_slot=main.continuity_slots(obs)[0],
        )
        envelope["response_statuses"] = ["CONFUSED"]
        successor = main.continuity_slots(obs)[1]
        self.assertNotEqual(
            envelope["h0_outgoing"]["attacker_serial"], successor["serial"]
        )
        self.assertEqual(
            main._continuity_h1_primary_gate(obs, successor, envelope)["state"],
            "READY",
        )
        same_top = copy.deepcopy(envelope)
        same_top["h0_outgoing"]["attacker_serial"] = successor["serial"]
        self.assertEqual(
            main._continuity_h1_primary_gate(obs, successor, same_top)["state"],
            "UNKNOWN",
        )

    def test_to_active_checkup_projects_burn_poison_and_promotions(self):
        cornerstone = (
            pokemon(
                main.CORNERSTONE_OGERPON_EX, 210, [], 1, 7300, max_hp=210
            ),
        )
        blocked = main.build_continuity2_plan(main.to_observation_class(
            to_active_state(
                opponent_hp=20, burned=True, opponent_bench=cornerstone
            )
        ))
        blocked_branches = blocked["response_envelope"][
            "post_response_active_candidates"
        ]
        self.assertEqual([row["card_id"] for row in blocked_branches], [117])
        self.assertIsNone(blocked["H1_after_KO"]["identity"])
        self.assertEqual(
            blocked["H1_after_KO"]["rejected"][0]["reason"],
            "CORNERSTONE_STANCE_ABILITY_ATTACKER_BLOCKED",
        )

        nonlethal = main.build_continuity2_plan(main.to_observation_class(
            to_active_state(opponent_hp=70, burned=True)
        ))
        nonlethal_branch = nonlethal["response_envelope"][
            "post_response_active_candidates"
        ][0]
        self.assertEqual(nonlethal_branch["hp"], 50)
        self.assertEqual(
            nonlethal["response_envelope"]["opponent_checkup"]["first_damage"],
            20,
        )
        self.assertEqual(nonlethal["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")

        no_status = main.build_continuity2_plan(main.to_observation_class(
            to_active_state(opponent_hp=70)
        ))
        self.assertEqual(
            no_status["response_envelope"]["post_response_active_candidates"][0]["hp"],
            70,
        )
        self.assertEqual(no_status["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")

        poisoned = main.build_continuity2_plan(main.to_observation_class(
            to_active_state(opponent_hp=70, poisoned=True)
        ))
        self.assertTrue(poisoned["response_envelope"]["unknown"])
        self.assertIn(
            "UNKNOWN_POISON_INTENSITY",
            poisoned["response_envelope"]["unknown_reasons"],
        )
        self.assertFalse(
            poisoned.get("choice")
            and poisoned["choice"].get("kind") == "KO_PROMOTE_CERTIFIED_H1"
        )

        terminal = main.build_continuity2_plan(main.to_observation_class(
            to_active_state(opponent_hp=20, burned=True)
        ))
        terminal_branch = terminal["response_envelope"][
            "post_response_active_candidates"
        ][0]
        self.assertTrue(terminal_branch["terminal"])
        self.assertEqual(terminal["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")
        self.assertEqual(
            terminal["H1_after_KO"]["h1_primary_gate"]["state"], "READY"
        )

        multiple = main.build_continuity2_plan(main.to_observation_class(
            to_active_state(
                opponent_hp=20,
                burned=True,
                opponent_bench=(
                    pokemon(main.DURALUDON, 130, [], 1, 7400, max_hp=130),
                    pokemon(119, 70, [], 1, 7500, max_hp=70),
                ),
            )
        ))
        self.assertEqual(
            {
                row["serial"]
                for row in multiple["response_envelope"][
                    "post_response_active_candidates"
                ]
            },
            {7400, 7500},
        )
        self.assertEqual(multiple["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")

    def test_hop_combat_scope_isolated_from_legacy_matchup(self):
        parent = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}
        self.assertEqual(main.HOP_LINE, parent)
        self.assertEqual(main._CONTINUITY_HOP_COMBAT_LINE, parent | {298, 311})
        for card_id in (298, 311):
            raw = clean_observation(
                pokemon(main.DURALUDON, 130, [], 0, 9000),
                pokemon(card_id, main.CARD_DB[card_id].hp, [], 1, 9100),
            )
            self.assertEqual(
                main.detect_matchup(main.to_observation_class(raw)), "generic"
            )
        for card_id in sorted(parent):
            raw = clean_observation(
                pokemon(main.DURALUDON, 130, [], 0, 9000),
                pokemon(card_id, main.CARD_DB[card_id].hp, [], 1, 9100),
            )
            self.assertEqual(
                main.detect_matchup(main.to_observation_class(raw)), "hop"
            )

        for card_id, attack_id, base_damage in ((298, 410, 50), (311, 433, 120)):
            with self.subTest(combat_card=card_id):
                raw = clean_observation(
                    pokemon(
                        card_id,
                        main.CARD_DB[card_id].hp,
                        [8, 8, 8],
                        0,
                        9200,
                        tools=(main._CONTINUITY_HOP_CHOICE_BAND,),
                    ),
                    pokemon(119, 70, [], 1, 9300, max_hp=70),
                    own_bench=(pokemon(304, 150, [], 0, 9400, max_hp=150),),
                    stadium=(main._CONTINUITY_POSTWICK,),
                )
                obs = main.to_observation_class(raw)
                attacker = main.active_pokemon(obs)
                attack = main.ALL_ATTACKS[attack_id]
                self.assertEqual(
                    main._continuity_attack_requirements(attacker, attack), []
                )
                self.assertEqual(
                    main._continuity_outgoing_damage(
                        obs,
                        attacker,
                        attack,
                        main.opp_active_pokemon(obs),
                        aura_sources=main._continuity_in_play_pokemon(obs, 0),
                    ),
                    base_damage + 90,
                )

    def test_unexpected_own_reactive_attachments_fail_closed(self):
        guarded = (
            ("energy", main._CONTINUITY_SPIKY_ENERGY),
            ("tool", main._CONTINUITY_DELUXE_BOMB),
            ("tool", main._CONTINUITY_HYPNOTIZER),
            ("tool", main._CONTINUITY_LUCKY_HELMET),
        )
        for kind, card_id in guarded:
            with self.subTest(kind=kind, card_id=card_id):
                own = pokemon(
                    main.ARCHALUDON_EX, 300, [8, 8, 8], 0, 10000,
                    max_hp=300,
                )
                if kind == "energy":
                    own["energyCards"].append({
                        "id": card_id, "serial": 10001, "playerIndex": 0,
                    })
                else:
                    own["tools"].append({
                        "id": card_id, "serial": 10001, "playerIndex": 0,
                    })
                raw = clean_observation(
                    own,
                    pokemon(119, 70, [], 1, 10100, max_hp=70),
                )
                set_main_select(raw, [{
                    "type": int(main.OptionType.ATTACK),
                    "attackId": main.METAL_DEFENDER,
                }])
                obs = main.to_observation_class(raw)
                slot = main.continuity_slots(obs)[0]
                envelope = main.continuity_response_envelope(
                    obs,
                    main.active_pokemon(obs),
                    main.METAL_DEFENDER,
                    h0_execution_slot=slot,
                )
                self.assertTrue(envelope["unknown"])
                self.assertIn(
                    "UNKNOWN_UNEXPECTED_OWN_REACTIVE_ATTACHMENT",
                    envelope["unknown_reasons"],
                )
                self.assertEqual(
                    envelope["unexpected_own_reactive_attachments"][0]["card_id"],
                    card_id,
                )
                plan = main.build_continuity2_plan(obs)
                self.assertNotIn(
                    plan["H1"]["readiness"],
                    {"READY", "READY_NEXT_TURN", "READY_AFTER_SURVIVAL"},
                )
                self.assertFalse(any(
                    row["role"] in {"H1", "H1_survive", "H1_after_KO"}
                    for row in plan["ledger"]["reservations"]
                ))

    def test_trace_records_exact_identities_and_deduplicates_skills(self):
        raw = turbo_state()
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs,
            main.active_pokemon(obs),
            965,
            h0_execution_slot=main.continuity_slots(obs)[0],
        )
        outgoing = envelope["h0_outgoing"]
        self.assertEqual(outgoing["attacker_serial"], 1000)
        self.assertEqual(outgoing["target_serial"], 3000)
        self.assertEqual(outgoing["attack_id"], 965)
        for branch in envelope["post_response_active_candidates"]:
            self.assertEqual(branch["defeated_identity"]["serial"], 3000)
            self.assertTrue(branch["transition_trace"])
        skill_keys = [
            json.dumps(row, sort_keys=True, separators=(",", ":"))
            for row in envelope["skill_classifications"]
        ]
        self.assertEqual(len(skill_keys), len(set(skill_keys)))


if __name__ == "__main__":
    unittest.main()
