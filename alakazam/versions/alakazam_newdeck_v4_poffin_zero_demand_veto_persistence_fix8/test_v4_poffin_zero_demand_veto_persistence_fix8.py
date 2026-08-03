from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest import mock

from cg.api import OptionType

import _cumulative_parent as policy
import main
import planner_deck_adaptation_v1 as v1
import planner_policy as core


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STEP148 = (
    REPO_ROOT
    / "alakazam"
    / "fixtures"
    / "episode_88844273_public_observations"
    / "step_148_energized_kadabra_alakazam_in_hand_main.json"
)
PARENT_CLEAN_STATE = core.parent_state_snapshot(policy)


class PoffinZeroDemandVetoPersistenceFix8Tests(unittest.TestCase):
    def setUp(self):
        v1.reset()
        core.reset_integrated_state()
        core.restore_parent_state(policy, PARENT_CLEAN_STATE)
        self.base = json.loads(
            STEP148.read_text(encoding="utf-8")
        )["observation"]
        self.next_serial = 5000

    def tearDown(self):
        v1.reset()
        core.reset_integrated_state()
        core.restore_parent_state(policy, PARENT_CLEAN_STATE)

    def pokemon(self, owner, card_id):
        hp = {
            741: 60,
            742: 80,
            743: 310,
            305: 70,
            66: 140,
        }.get(card_id, 70)
        serial = self.next_serial
        self.next_serial += 1
        return {
            "appearThisTurn": False,
            "energies": [],
            "energyCards": [],
            "hp": hp,
            "id": card_id,
            "maxHp": hp,
            "playerIndex": owner,
            "preEvolution": [],
            "serial": serial,
            "tools": [],
        }

    def set_roles(self, raw, a_count, n_count, free_bench):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        bench_count = mine["benchMax"] - free_bench
        roles = [741] * a_count + [305] * n_count
        active_id = roles.pop(0) if roles else 140
        self.assertLessEqual(len(roles), bench_count)
        mine["active"] = [self.pokemon(owner, active_id)]
        mine["bench"] = [
            self.pokemon(owner, card_id) for card_id in roles
        ]
        while len(mine["bench"]) < bench_count:
            mine["bench"].append(self.pokemon(owner, 140))
        return raw

    def reconcile_deck_count(self, raw):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        public = list(mine["hand"]) + list(mine["discard"])
        for pokemon in list(mine["active"]) + list(mine["bench"]):
            public.append(pokemon)
            public.extend(pokemon.get("preEvolution", ()))
            public.extend(pokemon.get("energyCards", ()))
            public.extend(pokemon.get("tools", ()))
        hidden_prizes = 0
        for card in mine["prize"]:
            if card is None:
                hidden_prizes += 1
            else:
                public.append(card)
        public.extend(
            card
            for card in raw["current"]["stadium"]
            if card["playerIndex"] == owner
        )
        mine["deckCount"] = 60 - len(public) - hidden_prizes
        self.assertGreaterEqual(mine["deckCount"], 0)
        return raw

    def main_raw(self, *, a_count=2, n_count=2, free_bench=1):
        raw = self.set_roles(
            copy.deepcopy(self.base),
            a_count,
            n_count,
            free_bench,
        )
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        mine["hand"][0] = {
            "id": 1086,
            "serial": 9000,
            "playerIndex": owner,
        }
        raw["select"] = {
            "type": 0,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": None,
            "deck": None,
            "option": [
                {"type": 7, "index": 0},
                {"type": 13, "attackId": 1071},
                {"type": 14},
            ],
        }
        return self.reconcile_deck_count(raw)

    @staticmethod
    def parent_prefers_poffin_then_attack(calls):
        def choose(raw):
            calls.append(copy.deepcopy(raw))
            owner = raw["current"]["yourIndex"]
            hand = raw["current"]["players"][owner]["hand"]
            for index, option in enumerate(raw["select"]["option"]):
                if (
                    option.get("type") == int(OptionType.PLAY)
                    and hand[option["index"]]["id"] == 1086
                ):
                    return [index]
            for index, option in enumerate(raw["select"]["option"]):
                if option.get("type") == int(OptionType.ATTACK):
                    return [index]
            return [0]

        return choose

    def invoke(self, raw, delegate=None):
        calls = []
        if delegate is None:
            delegate = self.parent_prefers_poffin_then_attack(calls)
        action = v1.agent(policy, delegate, copy.deepcopy(raw))
        return action, calls

    def arm(self, raw=None):
        raw = self.main_raw() if raw is None else raw
        action, calls = self.invoke(raw)
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 2)
        self.assertIsNotNone(v1.POFFIN_ZERO_DEMAND_LATCH)
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["stage"], "ARM"
        )
        return raw

    def test_initial_zero_demand_veto_arms_and_reranks(self):
        raw = self.arm()
        trace = v1.LAST_V4_POFFIN_ZERO_VETO_TRACE
        self.assertEqual(
            trace["reason"], "ZERO_NORMAL_CAPACITY_NO_ABRA_EXCEPTION"
        )
        self.assertEqual(trace["parent_action"], [0])
        self.assertEqual(trace["proposed_action"], [1])
        self.assertEqual(trace["applied_action"], [1])
        self.assertEqual(len(trace["eligibility"]["poffin_play_keys"]), 1)
        self.assertEqual(
            raw["select"]["option"][trace["applied_action"][0]]["attackId"],
            1071,
        )

    def test_same_eligibility_persists_across_callbacks_and_action_count(self):
        raw = self.arm()
        eligibility_hash = v1.POFFIN_ZERO_DEMAND_LATCH["sha256"]
        repeated = copy.deepcopy(raw)
        repeated["current"]["turnActionCount"] += 3
        action, _ = self.invoke(repeated)
        self.assertEqual(action, [1])
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["stage"], "HOLD"
        )
        self.assertEqual(
            v1.POFFIN_ZERO_DEMAND_LATCH["sha256"], eligibility_hash
        )

    def test_energy_attachment_does_not_break_eligibility(self):
        raw = self.main_raw()
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        mine["hand"][1] = {
            "id": 5,
            "serial": 9902,
            "playerIndex": owner,
        }
        self.reconcile_deck_count(raw)
        self.arm(raw)
        eligibility_hash = v1.POFFIN_ZERO_DEMAND_LATCH["sha256"]

        attached = copy.deepcopy(raw)
        attached_mine = attached["current"]["players"][owner]
        energy = attached_mine["hand"].pop(1)
        attached_mine["handCount"] -= 1
        attached_mine["active"][0]["energies"].append(5)
        attached_mine["active"][0]["energyCards"].append(energy)
        attached["current"]["energyAttached"] = True
        attached["current"]["turnActionCount"] += 1
        self.reconcile_deck_count(attached)
        action, _ = self.invoke(attached)
        self.assertEqual(action, [1])
        self.assertEqual(
            v1.POFFIN_ZERO_DEMAND_LATCH["sha256"], eligibility_hash
        )
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["stage"], "HOLD"
        )

    def test_a_n_f_changes_release_positive_demand(self):
        for name, counts, expected_action, expected_latch in (
            ("A", (1, 2, 2), [0], False),
            ("N", (2, 1, 2), [0], False),
            ("F", (2, 2, 2), [1], True),
        ):
            with self.subTest(name=name):
                v1.reset()
                raw = self.arm()
                changed = self.main_raw(
                    a_count=counts[0],
                    n_count=counts[1],
                    free_bench=counts[2],
                )
                changed["current"]["turn"] = raw["current"]["turn"]
                changed["current"]["turnActionCount"] = (
                    raw["current"]["turnActionCount"] + 1
                )
                action, calls = self.invoke(changed)
                self.assertEqual(action, expected_action)
                self.assertEqual(
                    len(calls), 2 if expected_latch else 1
                )
                self.assertEqual(
                    v1.POFFIN_ZERO_DEMAND_LATCH is not None,
                    expected_latch,
                )
                stages = [
                    row["stage"]
                    for row in v1.V4_POFFIN_ZERO_VETO_TRACE_HISTORY
                ]
                self.assertIn("RELEASE", stages)

    def test_public_inventory_change_releases_then_recomputes(self):
        raw = self.arm()
        previous_hash = v1.POFFIN_ZERO_DEMAND_LATCH["sha256"]
        changed = copy.deepcopy(raw)
        owner = changed["current"]["yourIndex"]
        mine = changed["current"]["players"][owner]
        replacement = next(
            card
            for card in mine["discard"]
            if card["id"] not in (741, 305)
        )
        replacement["id"] = 305
        changed["current"]["turnActionCount"] += 1
        self.reconcile_deck_count(changed)
        action, _ = self.invoke(changed)
        self.assertEqual(action, [1])
        self.assertNotEqual(
            v1.POFFIN_ZERO_DEMAND_LATCH["sha256"], previous_hash
        )
        tail = v1.V4_POFFIN_ZERO_VETO_TRACE_HISTORY[-2:]
        self.assertEqual(
            [(row["stage"], row["reason"]) for row in tail],
            [
                ("RELEASE", "ELIGIBILITY_CHANGED"),
                ("ARM", "PUBLIC_ROLE_BASICS_DEPLETED"),
            ],
        )

    def test_turn_change_rollback_reset_and_handshake_clear(self):
        raw = self.arm()
        changed_turn = copy.deepcopy(raw)
        changed_turn["current"]["turn"] += 1
        action, _ = self.invoke(
            changed_turn,
            delegate=lambda _: [1],
        )
        self.assertEqual(action, [1])
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)

        raw = self.arm()
        rollback = copy.deepcopy(raw)
        v1.POFFIN_ZERO_DEMAND_LATCH["last_action_count"] = 5
        rollback["current"]["turnActionCount"] = 4
        action, _ = self.invoke(rollback, delegate=lambda _: [1])
        self.assertEqual(action, [1])
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)

        self.arm()
        with self.assertRaises(v1.UnrecoverableObservationFault):
            v1.agent(policy, lambda _: [0], {"select": None})
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)

        self.arm()
        v1.reset()
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)
        self.assertEqual(v1.V4_POFFIN_ZERO_VETO_TRACE_HISTORY, [])

    def test_runtime_handshake_returns_deck_and_clears_latch(self):
        self.arm()
        deck = main.agent(
            {"select": None, "current": None, "logs": []}
        )
        self.assertEqual(deck, policy.my_deck)
        self.assertEqual(len(deck), 60)
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)
        self.assertEqual(v1.V4_POFFIN_ZERO_VETO_TRACE_HISTORY, [])

    def test_active_transaction_has_precedence(self):
        raw = self.arm()
        core.INTEGRATED_TRANSACTION = {"kind": "TEST_OWNER"}
        parent_action = [0]
        action, _ = self.invoke(raw, delegate=lambda _: parent_action)
        self.assertIs(action, parent_action)
        self.assertIsNotNone(v1.POFFIN_ZERO_DEMAND_LATCH)
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["reason"],
            "ACTIVE_TRANSACTION_PRECEDENCE",
        )

    def test_inherited_entry_completion_rechecks_and_vetoes(self):
        raw = self.main_raw()
        core.INTEGRATED_TRANSACTION = {"kind": "COMPLETES_HERE"}
        calls = []

        def complete_then_choose(value):
            calls.append(copy.deepcopy(value))
            core.INTEGRATED_TRANSACTION = None
            return (
                [0]
                if any(
                    option.get("type") == int(OptionType.PLAY)
                    for option in value["select"]["option"]
                )
                else [0]
            )

        action, _ = self.invoke(raw, delegate=complete_then_choose)
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["source"],
            "INHERITED_ENTRY_POST_DELEGATE",
        )

    def test_v1_completion_rechecks_and_vetoes(self):
        raw = self.main_raw()
        v1.V1_TRANSACTION = {
            "rule": v1.RULE_XEROSIC,
            "stage": "await_xerosic_verify",
        }
        calls = []
        delegate = self.parent_prefers_poffin_then_attack(calls)
        with mock.patch.object(v1, "_verify_xerosic", return_value=True):
            action = v1.agent(policy, delegate, copy.deepcopy(raw))
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["source"],
            "V1_COMPLETION_POST_DELEGATE",
        )

    def test_unique_stable_rebind_preserves_physical_nonpoffin_card(self):
        raw = self.main_raw()
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        serial = 9901
        mine["hand"][1] = {
            "id": 1081,
            "serial": serial,
            "playerIndex": owner,
        }
        raw["select"]["option"].insert(
            1, {"type": 7, "index": 1}
        )
        self.reconcile_deck_count(raw)

        def choose(value):
            hand = value["current"]["players"][owner]["hand"]
            for index, option in enumerate(value["select"]["option"]):
                if (
                    option.get("type") == int(OptionType.PLAY)
                    and hand[option["index"]]["id"] == 1086
                ):
                    return [index]
            for index, option in enumerate(value["select"]["option"]):
                if (
                    option.get("type") == int(OptionType.PLAY)
                    and hand[option["index"]]["serial"] == serial
                ):
                    return [index]
            return [0]

        action, _ = self.invoke(raw, delegate=choose)
        self.assertEqual(action, [1])
        selected = raw["select"]["option"][action[0]]
        self.assertEqual(mine["hand"][selected["index"]]["serial"], serial)

    def test_missing_and_ambiguous_rebind_fail_closed(self):
        raw = self.main_raw()
        obs = policy.to_observation_class(copy.deepcopy(raw))
        eligibility, error = v1._v4_poffin_zero_eligibility(
            policy, obs, raw
        )
        self.assertIsNone(error)
        delegate_pre = v1._delegate_state_snapshot(policy)
        real_key = v1.runtime_model.stable_option_key

        def missing_key(parent, parsed, option):
            if (
                len(parsed.select.option) == 2
                and option.type == parent.OptionType.ATTACK
            ):
                return ("FILTERED_ONLY",)
            return real_key(parent, parsed, option)

        with mock.patch.object(
            v1.runtime_model,
            "stable_option_key",
            side_effect=missing_key,
        ):
            action, reason = v1._v4_filtered_parent_rerank(
                policy,
                lambda _: [0],
                copy.deepcopy(raw),
                obs,
                delegate_pre,
                eligibility["poffin_rows"],
            )
        self.assertIsNone(action)
        self.assertIn("REBIND_AMBIGUOUS", reason)

        def ambiguous_key(parent, parsed, option):
            if len(parsed.select.option) == 2:
                return (
                    ("DUP",)
                    if option.type == parent.OptionType.ATTACK
                    else ("FILTERED_END",)
                )
            if option.type in (
                parent.OptionType.ATTACK,
                parent.OptionType.END,
            ):
                return ("DUP",)
            return real_key(parent, parsed, option)

        with mock.patch.object(
            v1.runtime_model,
            "stable_option_key",
            side_effect=ambiguous_key,
        ):
            action, reason = v1._v4_filtered_parent_rerank(
                policy,
                lambda _: [0],
                copy.deepcopy(raw),
                obs,
                delegate_pre,
                eligibility["poffin_rows"],
            )
        self.assertIsNone(action)
        self.assertIn("REBIND_AMBIGUOUS", reason)

    def test_rerank_failure_returns_original_parent_object(self):
        raw = self.main_raw()
        parent_action = [0]

        def fail_filtered(value):
            if len(value["select"]["option"]) == 3:
                return parent_action
            raise RuntimeError("filtered failure")

        action, _ = self.invoke(raw, delegate=fail_filtered)
        self.assertIs(action, parent_action)
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["stage"],
            "FAIL_CLOSED",
        )

    def test_nonfire_action_and_poffin_child_are_parent_identical(self):
        positive = self.main_raw(a_count=1, n_count=0, free_bench=3)
        parent_action = [0]
        action, _ = self.invoke(
            positive, delegate=lambda _: parent_action
        )
        self.assertIs(action, parent_action)
        self.assertIsNone(v1.POFFIN_ZERO_DEMAND_LATCH)

        latched = self.arm()
        latch_hash = v1.POFFIN_ZERO_DEMAND_LATCH["sha256"]
        child = copy.deepcopy(latched)
        owner = child["current"]["yourIndex"]
        child_mine = child["current"]["players"][owner]
        poffin = child_mine["hand"].pop(0)
        child_mine["handCount"] -= 1
        child_mine["discard"].append(poffin)
        child["current"]["turnActionCount"] += 1
        child["select"] = {
            "type": 1,
            "context": 5,
            "minCount": 0,
            "maxCount": 2,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": poffin,
            "deck": [
                {"id": 741, "serial": 9910, "playerIndex": owner},
                {"id": 305, "serial": 9911, "playerIndex": owner},
            ],
            "option": [
                {"type": 3, "area": 1, "index": 0, "playerIndex": owner},
                {"type": 3, "area": 1, "index": 1, "playerIndex": owner},
            ],
        }
        child_action = [1, 0]
        action, _ = self.invoke(
            child, delegate=lambda _: child_action
        )
        self.assertIs(action, child_action)
        self.assertEqual(action, [1, 0])
        self.assertEqual(
            v1.POFFIN_ZERO_DEMAND_LATCH["sha256"], latch_hash
        )
        self.assertEqual(
            v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["reason"],
            "NON_MAIN_CALLBACK",
        )

    def test_cynthia_and_marnie_style_multicallback_regressions(self):
        with self.subTest(kind="Cynthia_veto_then_immediate_reproposal"):
            raw = self.arm()
            repeated = copy.deepcopy(raw)
            repeated["current"]["turnActionCount"] += 1
            action, _ = self.invoke(repeated)
            self.assertEqual(action, [1])
            self.assertEqual(
                v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["stage"], "HOLD"
            )

        with self.subTest(kind="Marnie_veto_other_action_then_reproposal"):
            v1.reset()
            raw = self.arm()
            middle = copy.deepcopy(raw)
            middle["current"]["turnActionCount"] += 1
            parent_attack = [1]
            action, _ = self.invoke(
                middle, delegate=lambda _: parent_attack
            )
            self.assertIs(action, parent_attack)
            self.assertEqual(
                v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["reason"],
                "PARENT_SELECTED_NON_POFFIN",
            )
            repeated = copy.deepcopy(raw)
            repeated["current"]["turnActionCount"] += 2
            action, _ = self.invoke(repeated)
            self.assertEqual(action, [1])
            self.assertEqual(
                v1.LAST_V4_POFFIN_ZERO_VETO_TRACE["stage"], "HOLD"
            )


if __name__ == "__main__":
    unittest.main()
