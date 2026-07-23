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


def pokemon(card_id, hp, energies, player_index, serial, tools=(), max_hp=None):
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": player_index,
        "hp": hp,
        "maxHp": hp if max_hp is None else max_hp,
        "appearThisTurn": False,
        "preEvolution": [],
        "tools": [
            {"id": card_id_, "serial": serial + 1000 + index,
             "playerIndex": player_index}
            for index, card_id_ in enumerate(tools)
        ],
        "energies": list(energies),
        "energyCards": [
            {"id": energy if energy else 1, "serial": serial + 100 + index,
             "playerIndex": player_index}
            for index, energy in enumerate(energies)
        ],
    }


def observation(own, opponent, own_bench=(), opponent_bench=(), stadium=()):
    raw = phase_b.observation(86162213, 38, 0)
    raw["current"]["yourIndex"] = 0
    raw["current"]["stadium"] = [
        {"id": card_id, "serial": 99000 + index, "playerIndex": 0}
        for index, card_id in enumerate(stadium)
    ]
    players = raw["current"]["players"]
    players[0]["active"] = [copy.deepcopy(own)]
    players[0]["bench"] = copy.deepcopy(list(own_bench))
    players[1]["active"] = [copy.deepcopy(opponent)]
    players[1]["bench"] = copy.deepcopy(list(opponent_bench))
    for state in players:
        for field in ("poisoned", "burned", "asleep", "paralyzed", "confused"):
            state[field] = False
    return raw


class PublicCombatEnvelopeClosureTests(unittest.TestCase):
    def test_closed_skill_classifier_has_no_legal_fallthrough(self):
        legal = [data for data in main.CARD_DB.values() if data.skills]
        classes = [main._continuity_response_skill_class(data) for data in legal]
        self.assertTrue(legal)
        self.assertEqual(len(classes), len(legal))
        self.assertTrue(set(classes) <= {
            main._CONTINUITY_SKILL_EXACT,
            main._CONTINUITY_SKILL_SAFE,
            main._CONTINUITY_SKILL_UNSUPPORTED,
        })
        self.assertNotIn(None, classes)
        for card_id in (79, 710, 896, 1027, 330, 716):
            self.assertEqual(
                main._continuity_response_skill_class(card_id),
                main._CONTINUITY_SKILL_UNSUPPORTED,
            )
        original = main.CARD_DB[304].skills[0].text
        main.CARD_DB[304].skills[0].text = "deliberately unrelated prose"
        try:
            self.assertEqual(
                main._continuity_response_skill_class(304),
                main._CONTINUITY_SKILL_EXACT,
            )
        finally:
            main.CARD_DB[304].skills[0].text = original

    def test_all_eight_aura_memberships_and_stacking_are_exact(self):
        target_basic = main.to_observation_class(observation(
            pokemon(169, 130, [8], 0, 100), pokemon(119, 70, [], 1, 200)
        )).current.players[0].active[0]
        target_evolution = main.to_observation_class(observation(
            pokemon(190, 300, [8, 8, 8], 0, 101), pokemon(119, 70, [], 1, 201)
        )).current.players[0].active[0]
        cases = (
            (80, 192, target_basic, 20, 80),
            (155, 119, target_evolution, 30, 169),
            (202, 716, target_basic, 10, 202),
            (304, 310, target_basic, 30, 169),
            (322, 716, target_basic, 20, 169),
            (342, 380, target_basic, 30, 169),
            (481, 119, target_basic, 20, None),
            (685, 685, target_basic, 30, 169),
        )
        for source_id, attacker_id, target, expected, ineligible_id in cases:
            with self.subTest(source=source_id):
                attacker = main.to_observation_class(observation(
                    pokemon(target.id, target.hp, [], 0, 300),
                    pokemon(attacker_id, 200, [], 1, 400),
                )).current.players[1].active[0]
                sources = [
                    main.to_observation_class(observation(
                        pokemon(169, 130, [], 0, 301),
                        pokemon(source_id, 200, [], 1, 500 + index),
                    )).current.players[1].active[0]
                    for index in range(2)
                ]
                total, rows = main._continuity_board_aura_bonus(
                    sources, attacker, target
                )
                self.assertEqual(total, expected if source_id == 304 else 2 * expected)
                self.assertEqual([row["card_id"] for row in rows], [source_id, source_id])
                if ineligible_id is not None:
                    bad_attacker = copy.copy(attacker)
                    bad_attacker.id = ineligible_id
                    bad_target = target_basic if source_id != 155 else target_basic
                    bad, _ = main._continuity_board_aura_bonus(
                        sources, bad_attacker, bad_target
                    )
                    self.assertEqual(bad, 0)

        active_snorlax = main.to_observation_class(observation(
            pokemon(169, 130, [], 0, 580),
            pokemon(304, 150, [1, 1, 1], 1, 581),
        )).current.players[1].active[0]
        active_bonus, _ = main._continuity_board_aura_bonus(
            [active_snorlax], active_snorlax, target_basic
        )
        self.assertEqual(active_bonus, 30)

    def test_pre_wr_order_postwick_fml_resistance_and_no_bench_bonus(self):
        raw = observation(
            pokemon(169, 130, [8], 0, 600),
            pokemon(78, 90, [2], 1, 601),
            opponent_bench=(pokemon(202, 70, [], 1, 602),
                            pokemon(322, 110, [], 1, 603)),
            stadium=(main.FULL_METAL_LAB,),
        )
        obs = main.to_observation_class(raw)
        profile = main._continuity_incoming_profile(
            obs, main.opp_active_pokemon(obs), main.ALL_ATTACKS[92],
            main.active_pokemon(obs), aura_sources=main._continuity_in_play_pokemon(obs, 1)
        )
        self.assertEqual(profile["pre_weakness_additive"], 30)
        self.assertEqual(profile["active_damage"], 90)  # (30+30)*2, then FML -30.

        resistance_raw = observation(
            pokemon(38, 100, [], 0, 610),
            pokemon(685, 180, [6, 6, 1], 1, 611),
        )
        resistance_obs = main.to_observation_class(resistance_raw)
        resistance = main._continuity_incoming_profile(
            resistance_obs, main.opp_active_pokemon(resistance_obs),
            main.ALL_ATTACKS[991], main.active_pokemon(resistance_obs),
            aura_sources=main._continuity_in_play_pokemon(resistance_obs, 1),
        )
        self.assertEqual(resistance["active_damage"], 130)  # 130+30 aura-30 Resistance.

        hop_raw = observation(
            pokemon(169, 130, [], 0, 620),
            pokemon(310, 120, [1, 1, 1], 1, 621),
            opponent_bench=(pokemon(304, 150, [], 1, 622),
                            pokemon(304, 150, [], 1, 623)),
            stadium=(main.FULL_METAL_LAB, main._CONTINUITY_POSTWICK),
        )
        # A legal state has one Stadium; use Postwick here, then assert FML separately.
        hop_raw["current"]["stadium"] = [{
            "id": main._CONTINUITY_POSTWICK, "serial": 99620, "playerIndex": 0,
        }]
        hop_obs = main.to_observation_class(hop_raw)
        hop = main._continuity_incoming_profile(
            hop_obs, main.opp_active_pokemon(hop_obs), main.ALL_ATTACKS[432],
            main.active_pokemon(hop_obs),
            aura_sources=main._continuity_in_play_pokemon(hop_obs, 1),
        )
        self.assertEqual(hop["active_damage"], 140)  # 80+30 nonstacking+30 Postwick.
        self.assertEqual((hop["bench_damage"], hop["bench_counters"]), (0, 0))

    def test_hop_choice_band_reduces_one_colorless_and_only_boosts_hop(self):
        raw = observation(
            pokemon(169, 130, [], 0, 700),
            pokemon(310, 120, [1, 1], 1, 701,
                    tools=(main._CONTINUITY_HOP_CHOICE_BAND,)),
        )
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(obs)
        self.assertFalse(envelope["unknown"])
        self.assertEqual([row["attack_id"] for row in envelope["payable_attacks"]], [432])
        self.assertEqual(envelope["active_damage_max"], 110)
        self.assertEqual(envelope["bench_total_max"], 0)

        non_hop_raw = observation(
            pokemon(190, 300, [8, 8, 8], 0, 710),
            pokemon(169, 130, [8, 8], 1, 711,
                    tools=(main._CONTINUITY_HOP_CHOICE_BAND,)),
        )
        non_hop = main.continuity_response_envelope(
            main.to_observation_class(non_hop_raw)
        )
        self.assertFalse(non_hop["unknown"])
        self.assertEqual(
            [row["attack_id"] for row in non_hop["payable_attacks"]], [223]
        )
        self.assertEqual(non_hop["active_damage_max"], 30)

    def test_silent_cost_and_unsupported_combat_skills_fail_closed(self):
        own_bench = tuple(
            pokemon(169, 130, [], 0, 800 + index) for index in range(4)
        )
        for card_id, energies in ((79, [2]), (710, [1])):
            with self.subTest(cost_skill=card_id):
                obs = main.to_observation_class(observation(
                    pokemon(190, 300, [8, 8, 8], 0, 810),
                    pokemon(card_id, main.CARD_DB[card_id].hp, energies, 1, 820),
                    own_bench=own_bench,
                ))
                envelope = main.continuity_response_envelope(obs)
                self.assertTrue(envelope["unknown"])
                self.assertEqual(envelope["payable_attacks"], [])
                self.assertTrue(any(
                    reason.startswith(f"UNSUPPORTED_VISIBLE_SKILL:{card_id}:")
                    for reason in envelope["unknown_reasons"]
                ))

        for card_id in (896, 1027, 330, 716, 104):
            with self.subTest(unsupported_skill=card_id):
                obs = main.to_observation_class(observation(
                    pokemon(190, 300, [8, 8, 8], 0, 830),
                    pokemon(card_id, main.CARD_DB[card_id].hp, [], 1, 840),
                ))
                envelope = main.continuity_response_envelope(
                    obs, main.active_pokemon(obs), main.METAL_DEFENDER
                )
                self.assertTrue(envelope["unknown"])
                self.assertFalse(envelope["h0_outgoing"]["exact"])
                self.assertTrue(any(
                    reason.startswith(f"UNSUPPORTED_VISIBLE_SKILL:{card_id}:")
                    for reason in envelope["unknown_reasons"]
                ))

    def test_mandatory_promotion_is_adversarial_and_removes_koed_aura(self):
        dragapult = pokemon(121, 320, [2, 5], 1, 902)
        raw = observation(
            pokemon(190, 180, [8, 8, 8], 0, 900, max_hp=300),
            pokemon(119, 50, [], 1, 901, max_hp=70),
            opponent_bench=(pokemon(119, 70, [5], 1, 903), dragapult),
        )
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs, main.active_pokemon(obs), main.METAL_DEFENDER
        )
        self.assertEqual(envelope["response_route"], "MANDATORY_PROMOTION")
        self.assertFalse(envelope["unknown"])
        self.assertEqual(envelope["active_damage_max"], 200)
        self.assertEqual(envelope["bench_counters_max"], 60)
        self.assertEqual(envelope["chosen_response_candidate_serial"], 902)
        self.assertEqual(
            {row["serial"] for row in envelope["response_candidates"]}, {902, 903}
        )

        aura_raw = observation(
            pokemon(190, 300, [8, 8, 8], 0, 910),
            pokemon(304, 50, [], 1, 911, max_hp=150),
            opponent_bench=(pokemon(310, 120, [1, 1, 1], 1, 912),),
        )
        aura_obs = main.to_observation_class(aura_raw)
        aura = main.continuity_response_envelope(
            aura_obs, main.active_pokemon(aura_obs), main.METAL_DEFENDER
        )
        self.assertEqual(aura["response_route"], "MANDATORY_PROMOTION")
        self.assertEqual(aura["active_damage_max"], 80)
        self.assertFalse(any(
            row["card_id"] == 304 for row in aura["modifier_sources"]
        ))

        unsupported_raw = observation(
            pokemon(190, 300, [8, 8, 8], 0, 920),
            pokemon(119, 50, [], 1, 921, max_hp=70),
            opponent_bench=(pokemon(896, 330, [], 1, 922),),
        )
        unsupported_obs = main.to_observation_class(unsupported_raw)
        unsupported = main.continuity_response_envelope(
            unsupported_obs, main.active_pokemon(unsupported_obs), main.METAL_DEFENDER
        )
        self.assertEqual(unsupported["response_route"], "MANDATORY_PROMOTION")
        self.assertTrue(unsupported["unknown"])
        self.assertEqual(unsupported["chosen_response_candidate_serial"], 922)

    def test_empty_bench_terminal_retains_current_target_reaction(self):
        raw = observation(
            pokemon(840, 180, [8, 8, 8], 0, 930),
            pokemon(119, 40, [0], 1, 931, tools=(), max_hp=70),
        )
        raw["current"]["players"][1]["active"][0]["energyCards"] = [{
            "id": main._CONTINUITY_SPIKY_ENERGY, "serial": 1931, "playerIndex": 1,
        }]
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs, main.active_pokemon(obs), main.COATED_ATTACK
        )
        self.assertEqual(envelope["response_route"], "NO_VISIBLE_RESPONSE_TERMINAL")
        self.assertTrue(envelope["terminal"])
        self.assertEqual(envelope["response_candidates"], [])
        self.assertEqual(envelope["reactive_counters"], 20)
        self.assertEqual(envelope["active_total_max"], 20)

    def test_non_ko_current_and_public_retreat_candidates_include_status_fail_closed(self):
        raw = observation(
            pokemon(666, 160, [8], 0, 940),
            pokemon(119, 70, [5], 1, 941),
            opponent_bench=(pokemon(121, 320, [2, 5], 1, 942),),
        )
        obs = main.to_observation_class(raw)
        envelope = main.continuity_response_envelope(
            obs, main.active_pokemon(obs), 965
        )
        self.assertEqual(
            envelope["response_route"], "ACTIVE_SURVIVES_WITH_EXACT_RETREAT"
        )
        self.assertFalse(envelope["unknown"])
        self.assertEqual(
            {row["serial"] for row in envelope["response_candidates"]}, {941, 942}
        )
        self.assertEqual(envelope["active_damage_max"], 200)
        self.assertEqual(envelope["bench_counters_max"], 60)

        for status in ("asleep", "paralyzed"):
            with self.subTest(status=status):
                status_raw = copy.deepcopy(raw)
                status_raw["current"]["players"][1][status] = True
                status_obs = main.to_observation_class(status_raw)
                status_envelope = main.continuity_response_envelope(
                    status_obs, main.active_pokemon(status_obs), 965
                )
                self.assertEqual(status_envelope["response_route"], "VISIBLE_SWITCH_UNKNOWN")
                self.assertTrue(status_envelope["unknown"])
                self.assertIn(
                    f"UNKNOWN_VISIBLE_RETREAT_STATUS:{status.upper()}",
                    status_envelope["unknown_reasons"],
                )
                self.assertIn(942, {
                    row["serial"] for row in status_envelope["response_candidates"]
                })

        switch_raw = observation(
            pokemon(666, 160, [8], 0, 950),
            pokemon(119, 70, [], 1, 951),
            opponent_bench=(pokemon(184, 220, [], 1, 952),),
        )
        switch_obs = main.to_observation_class(switch_raw)
        switch = main.continuity_response_envelope(
            switch_obs, main.active_pokemon(switch_obs), 965
        )
        self.assertEqual(switch["response_route"], "VISIBLE_SWITCH_UNKNOWN")
        self.assertTrue(switch["unknown"])
        self.assertIn("UNKNOWN_VISIBLE_SWITCH_ROUTE", switch["unknown_reasons"])
        self.assertIn(952, {row["serial"] for row in switch["response_candidates"]})

    def test_public_retreat_tools_and_post_h0_rescue_hp_are_closed(self):
        bench = (pokemon(121, 320, [2, 5], 1, 972),)
        for tool_id in (main.AIR_BALLOON, main._CONTINUITY_RESCUE_BOARD):
            with self.subTest(zero_cost_tool=tool_id):
                raw = observation(
                    pokemon(666, 160, [8], 0, 970),
                    pokemon(119, 70, [], 1, 971, tools=(tool_id,)),
                    opponent_bench=bench,
                )
                obs = main.to_observation_class(raw)
                envelope = main.continuity_response_envelope(
                    obs, main.active_pokemon(obs), 965
                )
                self.assertEqual(
                    envelope["response_route"], "ACTIVE_SURVIVES_WITH_EXACT_RETREAT"
                )
                self.assertFalse(envelope["unknown"])
                self.assertIn(972, {
                    row["serial"] for row in envelope["response_candidates"]
                })

        gravity_raw = observation(
            pokemon(666, 160, [8], 0, 980),
            pokemon(119, 70, [5], 1, 981, tools=(main.GRAVITY_GEMSTONE,)),
            opponent_bench=bench,
        )
        gravity_obs = main.to_observation_class(gravity_raw)
        gravity = main.continuity_response_envelope(
            gravity_obs, main.active_pokemon(gravity_obs), 965
        )
        self.assertEqual(gravity["response_route"], "ACTIVE_SURVIVES")
        self.assertEqual(
            {row["serial"] for row in gravity["response_candidates"]}, {981}
        )

        # Turbo Flare leaves 20 HP. Rescue Board's public low-HP clause must
        # use that post-H0 HP, while Gravity's modifier order stays fail-closed.
        combo_raw = observation(
            pokemon(666, 160, [8], 0, 990, tools=(main.GRAVITY_GEMSTONE,)),
            pokemon(119, 70, [], 1, 991,
                    tools=(main._CONTINUITY_RESCUE_BOARD,)),
            opponent_bench=bench,
        )
        combo_obs = main.to_observation_class(combo_raw)
        combo = main.continuity_response_envelope(
            combo_obs, main.active_pokemon(combo_obs), 965
        )
        self.assertEqual(combo["response_route"], "VISIBLE_SWITCH_UNKNOWN")
        self.assertTrue(combo["unknown"])
        self.assertIn(
            "UNKNOWN_VISIBLE_RETREAT_MODIFIER_ORDER", combo["unknown_reasons"]
        )
        self.assertIn(972, {row["serial"] for row in combo["response_candidates"]})


if __name__ == "__main__":
    unittest.main()
