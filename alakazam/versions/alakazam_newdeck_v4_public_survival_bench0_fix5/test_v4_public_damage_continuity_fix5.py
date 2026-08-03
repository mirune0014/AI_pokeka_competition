from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import _cumulative_parent as parent
import planner_public_damage_continuity as damage


REPLAY = Path(r"C:\Users\amuam\Downloads\88843743.json")


class PublicDamageContinuityFix5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        cls.observations = {
            index: replay["steps"][index][1]["observation"]
            for index in (22, 23, 24, 27)
        }

    def ledger(self, **overrides):
        value = {
            "boundary_certified": True,
            "ambiguous": False,
            "same_battle_power_pro_seen": True,
            "family_marker_ids": [673, 675, 676],
            "committed_current_turn": [],
            "unavailable": [27],
            "power_pro_seen_serials": [27],
            "last_attack_by_serial": {},
            "turn": 4,
        }
        value.update(overrides)
        if "power_pro_seen_serials" not in overrides:
            value["power_pro_seen_serials"] = sorted(
                set(value["committed_current_turn"])
                | set(value["unavailable"])
            )
        return value

    def test_two_current_turn_power_pro_copies_commit_plus_60(self):
        row = damage.premium_power_pro_envelope(
            self.ledger(
                committed_current_turn=[20, 21],
                unavailable=[20, 21],
            ),
            phase="current",
        )
        self.assertEqual(row["premium_floor"], 60)
        self.assertEqual(row["premium_cap"], 120)
        self.assertEqual(row["committed_serials"], [20, 21])

    def test_frozen_attack_and_defense_metadata_match_engine_api(self):
        exact_text = {
            976: "",
            977: "",
            978: "This Pokémon also does 70 damage to itself.",
            979: "",
            980: (
                "If you don’t have Lunatone on your Bench, this attack does "
                "nothing. This attack’s damage isn’t affected by Weakness "
                "or Resistance."
            ),
            981: (
                "During your next turn, this Pokémon can’t use "
                "Accelerating Stab."
            ),
            982: (
                "Attach up to 3 Basic {F} Energy cards from your discard "
                "pile to your Benched Pokémon in any way you like."
            ),
            983: (
                "During your next turn, this Pokémon can’t use Mega Brave."
            ),
        }
        for attack_id, expected in damage.ATTACK_ROWS.items():
            attack = parent.attack_table[attack_id]
            self.assertEqual(attack.damage, expected["base"])
            self.assertEqual(
                tuple(int(energy) for energy in attack.energies),
                expected["cost"],
            )
            self.assertEqual(
                parent.card_table[expected["pokemon_id"]].energyType,
                parent.EnergyType.FIGHTING,
            )
            self.assertEqual(attack.text, exact_text[attack_id])
        for card_id, expected in damage.OWN_DEFENSE.items():
            card = parent.card_table[card_id]
            self.assertEqual(
                None if card.weakness is None else int(card.weakness),
                expected["weakness"],
            )
            self.assertEqual(
                None if card.resistance is None else int(card.resistance),
                expected["resistance"],
            )

    def test_four_legal_power_pro_copies_cap_at_plus_120(self):
        row = damage.premium_power_pro_envelope(
            self.ledger(
                committed_current_turn=[20, 21, 22, 23],
                unavailable=[20, 21, 22, 23],
            ),
            phase="current",
        )
        self.assertEqual(row["premium_floor"], 120)
        self.assertEqual(row["premium_cap"], 120)
        self.assertEqual(
            row["premium_power_pro_multiplicity"]["stack_max"], 4
        )

    def test_direct_discard_adds_no_floor_and_reduces_cap(self):
        row = damage.premium_power_pro_envelope(
            self.ledger(committed_current_turn=[], unavailable=[27]),
            phase="current",
        )
        self.assertEqual(row["premium_floor"], 0)
        self.assertEqual(row["premium_cap"], 90)

    def test_duplicate_committed_serial_counts_once(self):
        row = damage.premium_power_pro_envelope(
            self.ledger(
                committed_current_turn=[26, 26],
                unavailable=[26, 27],
            ),
            phase="current",
        )
        self.assertEqual(row["premium_floor"], 30)
        self.assertEqual(row["premium_cap"], 90)

    def test_recovery_raises_future_cap(self):
        before = damage.premium_power_pro_envelope(
            self.ledger(unavailable=[26, 27]), phase="future"
        )
        after = damage.premium_power_pro_envelope(
            self.ledger(unavailable=[27]), phase="future"
        )
        self.assertEqual(before["premium_cap"], 60)
        self.assertEqual(after["premium_cap"], 90)

    def test_current_and_future_stack_formula_differ(self):
        ledger = self.ledger(
            committed_current_turn=[26], unavailable=[26, 27]
        )
        current = damage.premium_power_pro_envelope(
            ledger, phase="current"
        )
        future = damage.premium_power_pro_envelope(ledger, phase="future")
        self.assertEqual(
            (current["premium_floor"], current["premium_cap"]), (30, 90)
        )
        self.assertEqual(
            (future["premium_floor"], future["premium_cap"]), (0, 60)
        )

    def test_ambiguous_boundary_is_unknown(self):
        for ledger in (
            self.ledger(boundary_certified=False),
            self.ledger(ambiguous=True),
        ):
            row = damage.premium_power_pro_envelope(
                ledger, phase="future"
            )
            self.assertEqual(row["status"], damage.UNKNOWN)
            self.assertIsNone(row["premium_cap"])

    def test_family_marker_without_revealed_power_pro_has_no_cap(self):
        row = damage.premium_power_pro_envelope(
            self.ledger(same_battle_power_pro_seen=False), phase="future"
        )
        self.assertEqual(row["status"], damage.UNKNOWN)
        self.assertIn(
            "ARCHETYPE_COMMON_UNCONFIRMED", row["unsupported_reasons"]
        )

    def test_episode_88843743_obs27_selects_exact_shaymin(self):
        decision = damage.evaluate_survival_decision(
            copy.deepcopy(self.observations[27]),
            [3],
            self.ledger(),
        )
        self.assertEqual(
            decision["guard_class"],
            "CAP_LOW_COST_BOARDOUT_AVOIDANCE",
        )
        self.assertEqual(decision["proposed_action"], [2])
        self.assertEqual(
            (
                decision["selected_basic"]["card_id"],
                decision["selected_basic"]["serial"],
            ),
            (343, 81),
        )
        cosmic = next(
            row
            for row in decision["damage_rows"]
            if row["attack_id"] == 980
        )
        self.assertIsNone(cosmic["damage_floor"])
        self.assertEqual(cosmic["damage_cap"], 160)
        self.assertTrue(cosmic["cap_ko"])
        self.assertEqual(decision["evidenced_policy_cap"], 160)
        self.assertEqual(decision["safety_cap"], 160)

    def test_floor_boardout_uses_low_cost_basic(self):
        obs = copy.deepcopy(self.observations[27])
        opponent = obs["current"]["players"][0]
        opponent["active"][0].update(
            {
                "id": 674,
                "serial": 3,
                "hp": 150,
                "maxHp": 150,
                "energies": [6, 6, 6],
                "energyCards": [
                    {"id": 6, "playerIndex": 0, "serial": serial}
                    for serial in (35, 36, 37)
                ],
                "tools": [],
            }
        )
        decision = damage.evaluate_survival_decision(
            obs, [3], self.ledger()
        )
        self.assertEqual(
            decision["guard_class"], "FLOOR_BOARDOUT_AVOIDANCE"
        )
        self.assertEqual(decision["selected_basic"]["card_id"], 343)

    def test_cap_only_never_uses_arbitrary_basic(self):
        obs = copy.deepcopy(self.observations[27])
        hand = obs["current"]["players"][1]["hand"]
        hand[5] = {"id": 140, "playerIndex": 1, "serial": 81}
        decision = damage.evaluate_survival_decision(
            obs, [3], self.ledger()
        )
        self.assertIsNone(decision["selected_basic"])
        self.assertEqual(
            decision["guard_class"],
            "HIGH_COUNTERMEASURE_COST_NO_ACTION",
        )

    def test_powerful_hand_ko_to_nonko_is_rejected(self):
        obs = copy.deepcopy(self.observations[27])
        mine = obs["current"]["players"][1]
        theirs = obs["current"]["players"][0]
        mine["active"][0]["id"] = 743
        mine["active"][0]["hp"] = 140
        mine["active"][0]["maxHp"] = 140
        mine["hand"] = mine["hand"][:5]
        mine["handCount"] = 5
        theirs["active"][0]["hp"] = 90
        obs["select"]["option"] = [
            {"type": 7, "index": 4},
            {"type": 13, "attackId": 1072},
            {"type": 14},
        ]
        mine["hand"][4] = {"id": 343, "playerIndex": 1, "serial": 81}
        decision = damage.evaluate_survival_decision(
            obs, [1], self.ledger()
        )
        self.assertEqual(
            decision["guard_failure"],
            "PARENT_TACTICAL_OUTCOME_DEGRADED",
        )
        self.assertEqual(
            decision["guard_class"],
            "HIGH_COUNTERMEASURE_COST_NO_ACTION",
        )

    def test_parent_attack_removes_same_threat(self):
        obs = copy.deepcopy(self.observations[27])
        opponent = obs["current"]["players"][0]
        opponent["active"][0]["hp"] = 50
        opponent["bench"] = []
        # Super Psy Bolt is 60 after Makuhita's Psychic Weakness.
        decision = damage.evaluate_survival_decision(
            obs,
            [3],
            self.ledger(
                unavailable=[], power_pro_seen_serials=[27]
            ),
        )
        self.assertEqual(
            decision["guard_failure"], "THREAT_REMOVED_BY_PARENT"
        )
        self.assertIsNone(decision["selected_basic"])

    def test_exact_current_ko_is_preserved_with_bench_threat(self):
        obs = copy.deepcopy(self.observations[27])
        obs["current"]["players"][0]["active"][0]["hp"] = 50
        decision = damage.evaluate_survival_decision(
            obs, [3], self.ledger()
        )
        self.assertEqual(
            decision["current_attack_before"]["outcome"], "KO"
        )
        self.assertEqual(
            decision["current_attack_after"]["outcome"], "KO"
        )
        self.assertFalse(
            decision["current_attack_before"]["terminal_win"]
        )
        self.assertEqual(
            decision["guard_class"],
            "CAP_LOW_COST_BOARDOUT_AVOIDANCE",
        )
        self.assertEqual(
            decision["promotion_removal_context"],
            "PARENT_ACTIVE_THREAT_REMOVAL_WITH_RESIDUAL",
        )
        self.assertEqual(decision["evidenced_policy_cap"], 160)
        self.assertEqual(decision["selected_threat"]["zone"], "BENCH")
        self.assertEqual(decision["selected_threat"]["attack_id"], 980)

    def test_last_prize_terminal_ko_is_preserved(self):
        obs = copy.deepcopy(self.observations[27])
        obs["current"]["players"][0]["active"][0]["hp"] = 50
        obs["current"]["players"][1]["prize"] = [None]
        decision = damage.evaluate_survival_decision(
            obs, [3], self.ledger()
        )
        for projection in (
            decision["current_attack_before"],
            decision["current_attack_after"],
        ):
            self.assertTrue(projection["ko"])
            self.assertTrue(projection["last_prize_win"])
            self.assertTrue(projection["terminal_win"])
        self.assertEqual(decision["selected_basic"]["card_id"], 343)

    def test_parent_end_is_supported_without_raw_index_replay(self):
        decision = damage.evaluate_survival_decision(
            copy.deepcopy(self.observations[27]),
            [4],
            self.ledger(),
        )
        self.assertEqual(
            decision["outcome_linkage"]["semantic_parent_action"],
            ["END", None],
        )
        self.assertEqual(decision["selected_basic"]["card_id"], 343)
        self.assertEqual(
            decision["current_attack_before"]["outcome"], "END"
        )

    def test_active_above_cap_keeps_parent(self):
        obs = copy.deepcopy(self.observations[27])
        own_active = obs["current"]["players"][1]["active"][0]
        own_active["hp"] = 300
        own_active["maxHp"] = 300
        decision = damage.evaluate_survival_decision(
            obs, [3], self.ledger()
        )
        self.assertEqual(
            decision["guard_failure"], "NO_SUPPORTED_BOARDOUT_THREAT"
        )
        self.assertIsNone(decision["selected_basic"])

    def test_supporter_first_parent_action_is_preserved(self):
        decision = damage.evaluate_survival_decision(
            copy.deepcopy(self.observations[24]),
            [3],
            self.ledger(),
        )
        self.assertEqual(
            decision["guard_failure"], "PARENT_NOT_ATTACK_OR_END"
        )
        self.assertIsNone(decision["selected_basic"])

    def test_unknown_parent_attack_is_fail_closed(self):
        obs = copy.deepcopy(self.observations[27])
        obs["select"]["option"][3]["attackId"] = 9999
        decision = damage.evaluate_survival_decision(
            obs, [3], self.ledger()
        )
        self.assertEqual(
            decision["guard_failure"],
            "PARENT_OR_CANDIDATE_PROJECTION_UNKNOWN",
        )
        self.assertEqual(decision["guard_class"], "UNSUPPORTED_NO_ACTION")

    def test_abra_only_outranks_shaymin_with_exact_future_route(self):
        obs = copy.deepcopy(self.observations[27])
        mine = obs["current"]["players"][1]
        mine["hand"].append(
            {"id": 741, "playerIndex": 1, "serial": 90}
        )
        mine["hand"].append({"id": 5, "playerIndex": 1, "serial": 91})
        mine["handCount"] += 2
        obs["select"]["option"].insert(0, {"type": 7, "index": 9})
        # Original attack option moves from 3 to 4.
        decision = damage.evaluate_survival_decision(
            obs, [4], self.ledger()
        )
        self.assertEqual(decision["selected_basic"]["card_id"], 741)
        self.assertEqual(
            decision["selected_basic"]["independent_board_value"],
            "CERTIFIED_NEXT_ATTACKER_DISTANCE",
        )

    def test_projected_fingerprints_are_separate(self):
        decision = damage.evaluate_survival_decision(
            copy.deepcopy(self.observations[27]),
            [3],
            self.ledger(),
        )
        self.assertIsNotNone(decision["parent_post_fingerprint"])
        self.assertIsNotNone(decision["candidate_post_fingerprint"])
        self.assertNotEqual(
            decision["parent_post_fingerprint"],
            decision["candidate_post_fingerprint"],
        )

    def test_power_pro_requires_three_distinct_markers_and_solrock(self):
        for markers in ([673, 676], [673, 674, 675]):
            row = damage.premium_power_pro_envelope(
                self.ledger(family_marker_ids=markers),
                phase="future",
            )
            self.assertEqual(row["status"], damage.UNKNOWN)
            self.assertIn(
                "FIGHTING_FAMILY_MARKER_MISSING",
                row["unsupported_reasons"],
            )

    def test_power_pro_serial_sets_are_strict_and_consistent(self):
        ledgers = (
            self.ledger(committed_current_turn=[-1], unavailable=[-1]),
            self.ledger(
                committed_current_turn=["26"],
                unavailable=["26"],
                power_pro_seen_serials=["26"],
            ),
            self.ledger(
                committed_current_turn=[20],
                unavailable=[20, 21, 22, 23],
                power_pro_seen_serials=[20, 21, 22, 23, 24],
            ),
            self.ledger(
                committed_current_turn=[20],
                unavailable=[21],
                power_pro_seen_serials=[21],
            ),
        )
        for ledger in ledgers:
            row = damage.premium_power_pro_envelope(
                ledger, phase="future"
            )
            self.assertEqual(row["status"], damage.UNKNOWN)

    def test_current_turn_committed_copy_may_be_recovered(self):
        row = damage.premium_power_pro_envelope(
            self.ledger(
                committed_current_turn=[26],
                unavailable=[27],
                power_pro_seen_serials=[26, 27],
            ),
            phase="current",
        )
        self.assertEqual(row["status"], "CERTIFIED")
        self.assertEqual(row["premium_floor"], 30)
        self.assertEqual(row["premium_cap"], 90)
        self.assertEqual(
            row["premium_power_pro_multiplicity"]["stack_max"], 3
        )

    def test_hariyama_self_ko_is_not_repeatable_ready(self):
        obs = copy.deepcopy(self.observations[27])
        hariyama = obs["current"]["players"][0]["active"][0]
        hariyama.update(
            {
                "id": 674,
                "hp": 70,
                "maxHp": 150,
                "energies": [6, 6, 6],
                "energyCards": [
                    {"id": 6, "playerIndex": 0, "serial": serial}
                    for serial in (35, 36, 37)
                ],
                "tools": [],
            }
        )
        rows, failures = damage.opponent_damage_rows(obs, self.ledger())
        self.assertEqual(failures, [])
        attack = next(row for row in rows if row["attack_id"] == 978)
        self.assertEqual(attack["continuity"], damage.NO_READY_ATTACK)
        self.assertEqual(attack["self_damage"], 70)

    def test_inactive_and_unsupported_attacks_emit_shadow_continuity(self):
        obs = copy.deepcopy(self.observations[27])
        makuhita = obs["current"]["players"][0]["active"][0]
        makuhita["energies"] = []
        makuhita["energyCards"] = []
        rows, failures = damage.opponent_damage_rows(obs, self.ledger())
        self.assertEqual(failures, [])
        hundred_rending = next(
            row for row in rows if row["attack_id"] == 977
        )
        self.assertEqual(
            hundred_rending["continuity"], damage.NO_READY_ATTACK
        )
        self.assertFalse(hundred_rending["cap_ko"])
        makuhita["tools"] = [
            {"id": 9999, "playerIndex": 0, "serial": 98}
        ]
        rows, failures = damage.opponent_damage_rows(obs, self.ledger())
        self.assertEqual(failures, [])
        hundred_rending = next(
            row for row in rows if row["attack_id"] == 977
        )
        self.assertEqual(
            hundred_rending["continuity"], damage.UNKNOWN
        )
        self.assertFalse(hundred_rending["cap_ko"])


if __name__ == "__main__":
    unittest.main()
