from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from cg.api import OptionType

import _cumulative_parent as policy
import main
import planner_deck_adaptation_v1 as v1
import planner_policy as core


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
FIXTURES = (
    REPO_ROOT
    / "alakazam"
    / "fixtures"
    / "episode_88844273_public_observations"
)
STEP148 = (
    FIXTURES
    / "step_148_energized_kadabra_alakazam_in_hand_main.json"
)
PARENT_CLEAN_STATE = core.parent_state_snapshot(policy)


class PoffinRoleCardinalityFix3Tests(unittest.TestCase):
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
        hp = {741: 60, 742: 80, 743: 310, 305: 70, 66: 140}.get(
            card_id, 70
        )
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
        self.assertGreaterEqual(bench_count, 0)
        roles = [741] * a_count + [305] * n_count
        if roles:
            active_id = roles.pop(0)
        else:
            active_id = 140
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

    def child_raw(
        self,
        *,
        a_count,
        n_count,
        free_bench,
        cards,
        max_count=2,
        min_count=0,
        effect_id=1086,
        effect_serial=9000,
        reorder=None,
    ):
        raw = self.set_roles(
            copy.deepcopy(self.base),
            a_count,
            n_count,
            free_bench,
        )
        owner = raw["current"]["yourIndex"]
        deck = [
            {
                "id": card_id,
                "serial": 9100 + index,
                "playerIndex": owner,
            }
            for index, card_id in enumerate(cards)
        ]
        options = [
            {
                "type": 3,
                "area": 1,
                "index": index,
                "playerIndex": owner,
            }
            for index in range(len(deck))
        ]
        if reorder is not None:
            options = [options[index] for index in reorder]
        raw["select"] = {
            "type": 1,
            "context": 5,
            "minCount": min_count,
            "maxCount": max_count,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": {
                "id": effect_id,
                "serial": effect_serial,
                "playerIndex": owner,
            },
            "deck": deck,
            "option": options,
        }
        return raw

    def main_raw(self, *, a_count, n_count, free_bench):
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

    def set_public_role_copies(self, raw, abra_count, dunsparce_count):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        for card in list(mine["hand"]) + list(mine["discard"]):
            if card["id"] in (741, 305):
                card["id"] = 1152
        targets = list(mine["discard"])
        self.assertGreaterEqual(
            len(targets), abra_count + dunsparce_count
        )
        for index, card in enumerate(targets):
            if index < abra_count:
                card["id"] = 741
            elif index < abra_count + dunsparce_count:
                card["id"] = 305
        return self.reconcile_deck_count(raw)

    def completed_poffin_transaction(self, stage):
        return {
            "rule": v1.RULE_POFFIN_ROLE_CARDINALITY,
            "owner": self.base["current"]["yourIndex"],
            "stage": stage,
            "poffin_trace": {
                "rule": v1.RULE_POFFIN_ROLE_CARDINALITY,
                "parent_action": [4],
                "applied_action": [5],
                "A": 1,
                "N": 0,
                "F": 3,
                "selected_cardinality": 1,
                "selected_candidates": [
                    {"card_id": 305, "card_serial": 9901}
                ],
                "classification": "CHILD_SELECT_1",
                "fail_closed_reason": None,
            },
        }

    def psychic_draw_raw(self):
        raw = copy.deepcopy(self.base)
        owner = raw["current"]["yourIndex"]
        active = raw["current"]["players"][owner]["active"][0]
        raw["current"]["players"][owner]["deckCount"] = 2
        raw["select"] = {
            "type": 9,
            "context": 43,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": {
                "id": active["id"],
                "serial": active["serial"],
                "playerIndex": owner,
            },
            "effect": None,
            "deck": None,
            "option": [{"type": 1}, {"type": 2}],
        }
        return raw

    def parent_prefers_poffin_then_attack(self, calls):
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

    def invoke(self, raw, fallback=None):
        calls = []
        delegate = (
            self.parent_prefers_poffin_then_attack(calls)
            if fallback is None
            else lambda value: calls.append(copy.deepcopy(value)) or fallback
        )
        action = v1.agent(policy, delegate, copy.deepcopy(raw))
        return action, calls

    def selected_serials(self, raw, action):
        return {
            raw["select"]["deck"][
                raw["select"]["option"][index]["index"]
            ]["serial"]
            for index in action
        }

    def arm_main_then_child(self, main_raw, cards=(741, 305)):
        action, _ = self.invoke(main_raw)
        self.assertEqual(action, [0])
        self.assertEqual(
            v1.V1_TRANSACTION["stage"], "await_v4_poffin_child"
        )
        child = copy.deepcopy(main_raw)
        owner = child["current"]["yourIndex"]
        mine = child["current"]["players"][owner]
        poffin = mine["hand"].pop(0)
        mine["handCount"] -= 1
        mine["discard"].append(poffin)
        child["current"]["turnActionCount"] += 1
        deck = [
            {
                "id": card_id,
                "serial": 9200 + index,
                "playerIndex": owner,
            }
            for index, card_id in enumerate(cards)
        ]
        child["select"] = {
            "type": 1,
            "context": 5,
            "minCount": 0,
            "maxCount": 2,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": poffin,
            "deck": deck,
            "option": [
                {
                    "type": 3,
                    "area": 1,
                    "index": index,
                    "playerIndex": owner,
                }
                for index in range(len(deck))
            ],
        }
        return child

    def assert_child_ids(self, raw, expected):
        action, _ = self.invoke(raw, fallback=[0] if raw["select"]["option"] else [])
        ids = [
            raw["select"]["deck"][
                raw["select"]["option"][index]["index"]
            ]["id"]
            for index in action
        ]
        self.assertEqual(ids, expected)
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE["classification"],
            f"CHILD_SELECT_{len(expected)}",
        )
        return action

    def test_a0_n0_capacity_two_selects_primary_abra_and_dunsparce(self):
        raw = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(305, 741, 140),
            reorder=(2, 0, 1),
        )
        self.assert_child_ids(raw, [741, 305])

    def test_a1_n0_two_free_slots_selects_one_dunsparce(self):
        raw = self.child_raw(
            a_count=1,
            n_count=0,
            free_bench=2,
            cards=(741, 305),
        )
        self.assert_child_ids(raw, [305])

    def test_a0_n1_final_slot_abra_exception_selects_one_abra(self):
        raw = self.child_raw(
            a_count=0,
            n_count=1,
            free_bench=1,
            cards=(305, 741),
        )
        self.assert_child_ids(raw, [741])
        self.assertTrue(
            v1.LAST_V4_POFFIN_TRACE["abra_final_slot_exception"]
        )

    def test_a1_n1_final_slot_selects_zero(self):
        raw = self.child_raw(
            a_count=1,
            n_count=1,
            free_bench=1,
            cards=(741, 305),
        )
        self.assert_child_ids(raw, [])

    def test_a2_n2_selects_zero(self):
        raw = self.child_raw(
            a_count=2,
            n_count=2,
            free_bench=1,
            cards=(741, 305),
        )
        self.assert_child_ids(raw, [])

    def test_n2_never_selects_a_third_dunsparce(self):
        raw = self.child_raw(
            a_count=0,
            n_count=2,
            free_bench=3,
            cards=(305, 305, 741),
        )
        action = self.assert_child_ids(raw, [741])
        self.assertNotIn(305, [
            raw["select"]["deck"][
                raw["select"]["option"][index]["index"]
            ]["id"]
            for index in action
        ])

    def test_missing_second_role_target_returns_one(self):
        raw = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(741, 140),
        )
        self.assert_child_ids(raw, [741])

    def test_max_count_one_caps_selection_at_one(self):
        raw = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(305, 741),
            max_count=1,
        )
        self.assert_child_ids(raw, [741])

    def test_option_reorder_preserves_selected_physical_serials(self):
        first = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(305, 741, 140),
        )
        second = copy.deepcopy(first)
        second["select"]["option"].reverse()
        action1, _ = self.invoke(first, fallback=[0])
        serials1 = self.selected_serials(first, action1)
        v1.reset()
        action2, _ = self.invoke(second, fallback=[0])
        self.assertEqual(
            self.selected_serials(second, action2), serials1
        )

    def test_ambiguous_or_nonexact_child_delegates_to_parent(self):
        semantic_duplicate = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(741, 305),
        )
        semantic_duplicate["select"]["option"].append(
            copy.deepcopy(semantic_duplicate["select"]["option"][0])
        )
        action, _ = self.invoke(semantic_duplicate, fallback=[1])
        self.assertEqual(action, [1])
        self.assertIsNone(v1.V1_TRANSACTION)

        for mutation in ("serial", "effect", "required"):
            with self.subTest(mutation=mutation):
                v1.reset()
                raw = self.child_raw(
                    a_count=0,
                    n_count=0,
                    free_bench=3,
                    cards=(741, 305),
                )
                if mutation == "serial":
                    raw["select"]["deck"][1]["serial"] = (
                        raw["select"]["deck"][0]["serial"]
                    )
                elif mutation == "effect":
                    raw["select"]["effect"]["id"] = 1085
                else:
                    raw["select"]["minCount"] = 1
                action, _ = self.invoke(raw, fallback=[1])
                self.assertEqual(action, [1])
                self.assertIsNone(v1.V1_TRANSACTION)

    def test_main_zero_demand_veto_reranks_with_same_parent(self):
        raw = self.main_raw(
            a_count=2, n_count=2, free_bench=1
        )
        action, calls = self.invoke(raw)
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            [option["type"] for option in calls[1]["select"]["option"]],
            [int(OptionType.ATTACK), int(OptionType.END)],
        )
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE["classification"],
            "MAIN_VETO_ZERO_DEMAND",
        )

    def test_main_need_preserves_parent_poffin_and_arms_child(self):
        raw = self.main_raw(
            a_count=1, n_count=0, free_bench=3
        )
        action, calls = self.invoke(raw)
        self.assertEqual(action, [0])
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            v1.V1_TRANSACTION["stage"], "await_v4_poffin_child"
        )
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE["classification"],
            "MAIN_PRESERVE_PARENT_POFFIN",
        )

    def test_both_owner_mirrors_choose_same_card_serials(self):
        raw = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(305, 741, 140),
        )
        action, _ = self.invoke(raw, fallback=[0])
        expected = self.selected_serials(raw, action)
        mirrored = copy.deepcopy(raw)
        mirrored["current"]["players"].reverse()
        mirrored["current"]["yourIndex"] = (
            1 - mirrored["current"]["yourIndex"]
        )
        mirrored["current"]["firstPlayer"] = (
            1 - mirrored["current"]["firstPlayer"]
        )

        def mirror_owner(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "playerIndex" and item in (0, 1):
                        value[key] = 1 - item
                    else:
                        mirror_owner(item)
            elif isinstance(value, list):
                for item in value:
                    mirror_owner(item)

        mirror_owner(mirrored)
        v1.reset()
        action, _ = self.invoke(mirrored, fallback=[0])
        self.assertEqual(
            self.selected_serials(mirrored, action), expected
        )

    def test_owned_duplicate_rebind_and_stale_child_release(self):
        main_raw = self.main_raw(
            a_count=1, n_count=0, free_bench=3
        )
        child = self.arm_main_then_child(main_raw)
        action, _ = self.invoke(child, fallback=[0])
        selected = self.selected_serials(child, action)
        reordered = copy.deepcopy(child)
        reordered["select"]["option"].reverse()
        action, _ = self.invoke(reordered, fallback=[0])
        self.assertEqual(
            self.selected_serials(reordered, action), selected
        )

        v1.reset()
        stale = self.arm_main_then_child(main_raw)
        stale["current"]["players"][
            stale["current"]["yourIndex"]
        ]["bench"].append(
            self.pokemon(stale["current"]["yourIndex"], 140)
        )
        action, calls = self.invoke(stale, fallback=[])
        self.assertEqual(action, [])
        self.assertEqual(len(calls), 1)
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE[
                "completion_fail_closed_reason"
            ],
            "STALE_POST_PLAY_BOARD_DELTA",
        )

    def test_existing_hilda_and_inherited_transactions_keep_precedence(self):
        raw = self.child_raw(
            a_count=0,
            n_count=0,
            free_bench=3,
            cards=(741, 305),
        )
        policy._enriching_reserve_latch = {
            "stage": "await_poffin_bench"
        }
        action, _ = self.invoke(raw, fallback=[1])
        self.assertEqual(action, [1])
        self.assertIsNone(v1.V1_TRANSACTION)

        core.restore_parent_state(policy, PARENT_CLEAN_STATE)
        v1.reset()
        core.INTEGRATED_TRANSACTION = {"kind": "EXISTING_OWNER"}
        action, _ = self.invoke(raw, fallback=[1])
        self.assertEqual(action, [1])
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_episode_88844273_actions_remain_parent_identical(self):
        expected = {67: [0], 98: [0], 121: [4], 148: [0]}
        for path in sorted(FIXTURES.glob("step_*.json")):
            with self.subTest(path=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                v1.reset()
                core.reset_integrated_state()
                core.restore_parent_state(policy, PARENT_CLEAN_STATE)
                action = main.agent(
                    copy.deepcopy(fixture["observation"])
                )
                self.assertEqual(
                    action, expected[fixture["source_step_index"]]
                )

    def test_static_completion_child_reenters_exact_evolution_ko(self):
        v1.V1_TRANSACTION = self.completed_poffin_transaction(
            "await_v4_poffin_complete"
        )
        raw = copy.deepcopy(self.base)
        calls = []
        action = v1.agent(
            policy,
            lambda value: calls.append(value) or [7],
            raw,
        )
        self.assertEqual(action, [0])
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            v1.V1_TRANSACTION["rule"],
            v1.RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
        )

    def test_static_completion_child_reenters_psychic_draw(self):
        v1.V1_TRANSACTION = self.completed_poffin_transaction(
            "await_v4_poffin_complete"
        )
        calls = []
        action = v1.agent(
            policy,
            lambda value: calls.append(value) or [0],
            self.psychic_draw_raw(),
        )
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
            v1.RULE_PSYCHIC_DRAW_OPTIONAL,
        )

    def test_static_main_completion_does_not_skip_normal_arbitration(self):
        v1.V1_TRANSACTION = self.completed_poffin_transaction(
            "await_v4_poffin_main_complete"
        )
        raw = self.main_raw(
            a_count=2, n_count=2, free_bench=1
        )
        calls = []
        action = v1.agent(
            policy,
            self.parent_prefers_poffin_then_attack(calls),
            copy.deepcopy(raw),
        )
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            v1.V1_TRANSACTION["stage"],
            "await_v4_poffin_main_complete",
        )

    def test_static_public_role_depletion_vetoes_main_poffin(self):
        raw = self.main_raw(
            a_count=0, n_count=0, free_bench=3
        )
        self.set_public_role_copies(raw, 4, 3)
        action, calls = self.invoke(raw)
        self.assertEqual(action, [1])
        self.assertEqual(len(calls), 2)
        trace = v1.LAST_V4_POFFIN_TRACE
        self.assertEqual(
            trace["fail_closed_reason"],
            "PUBLIC_ROLE_BASICS_DEPLETED",
        )
        self.assertEqual(
            trace["unknown_role_counts"],
            {"Abra": 0, "Dunsparce": 0},
        )

    def test_static_public_inventory_ambiguity_preserves_parent(self):
        cases = []
        duplicate = self.main_raw(
            a_count=0, n_count=0, free_bench=3
        )
        duplicate["current"]["players"][
            duplicate["current"]["yourIndex"]
        ]["hand"][1]["serial"] = duplicate["current"]["players"][
            duplicate["current"]["yourIndex"]
        ]["hand"][2]["serial"]
        cases.append(("duplicate_serial", duplicate))

        wrong_owner = self.main_raw(
            a_count=0, n_count=0, free_bench=3
        )
        wrong_owner["current"]["players"][
            wrong_owner["current"]["yourIndex"]
        ]["active"][0]["playerIndex"] = (
            1 - wrong_owner["current"]["yourIndex"]
        )
        cases.append(("wrong_owner", wrong_owner))

        bad_partition = self.main_raw(
            a_count=0, n_count=0, free_bench=3
        )
        bad_partition["current"]["players"][
            bad_partition["current"]["yourIndex"]
        ]["deckCount"] += 1
        cases.append(("bad_partition", bad_partition))

        for label, raw in cases:
            with self.subTest(label=label):
                v1.reset()
                action, calls = self.invoke(raw)
                self.assertEqual(action, [0])
                self.assertEqual(len(calls), 1)
                self.assertIsNone(v1.V1_TRANSACTION)

    def test_static_hidden_target_whiff_returns_optional_empty(self):
        main_raw = self.main_raw(
            a_count=0, n_count=0, free_bench=3
        )
        self.set_public_role_copies(main_raw, 3, 3)
        child = self.arm_main_then_child(main_raw, cards=())
        action, calls = self.invoke(child, fallback=[])
        self.assertEqual(action, [])
        self.assertEqual(calls, [])
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE["fail_closed_reason"],
            "HIDDEN_ZONE_TARGET_WHIFF",
        )
        self.assertIn(
            "HIDDEN_ZONE_TARGET_WHIFF",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_static_rerank_owner_original_callback_duplicate_rebinds(self):
        raw = self.main_raw(
            a_count=2, n_count=2, free_bench=1
        )
        calls = []
        owner_transaction = {"kind": "STATIC_REVIEW_OWNER"}

        def establish_owner(value):
            calls.append(copy.deepcopy(value))
            has_poffin = any(
                option.get("type") == int(OptionType.PLAY)
                for option in value["select"]["option"]
            )
            if has_poffin:
                return [0]
            core.INTEGRATED_TRANSACTION = owner_transaction
            return [0]

        self.assertEqual(
            v1.agent(policy, establish_owner, copy.deepcopy(raw)),
            [1],
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(core.INTEGRATED_TRANSACTION, owner_transaction)
        self.assertEqual(
            v1.V1_TRANSACTION["stage"],
            "await_v4_poffin_main_complete",
        )

        def must_not_run(_):
            self.fail("duplicate callback re-executed parent owner")

        self.assertEqual(
            v1.agent(policy, must_not_run, copy.deepcopy(raw)),
            [1],
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(core.INTEGRATED_TRANSACTION, owner_transaction)

    def test_static_uncertified_rerank_preserves_parent_honestly(self):
        raw = self.main_raw(
            a_count=2, n_count=2, free_bench=1
        )
        calls = []

        def fail_filtered(value):
            calls.append(copy.deepcopy(value))
            if any(
                option.get("type") == int(OptionType.PLAY)
                for option in value["select"]["option"]
            ):
                return [0]
            raise RuntimeError("uncertified filtered parent")

        action = v1.agent(
            policy, fail_filtered, copy.deepcopy(raw)
        )
        self.assertEqual(action, [0])
        self.assertEqual(len(calls), 2)
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE["classification"],
            "MAIN_RERANK_UNCERTIFIED_PARENT_PRESERVED",
        )
        self.assertEqual(
            v1.LAST_V4_POFFIN_TRACE["fail_closed_reason"],
            "PARENT_RERANK_NOT_CERTIFIED",
        )
        self.assertNotIn(
            "MAIN_VETO_ZERO_DEMAND",
            v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
        )

    def test_static_completion_trace_preserves_original_poffin_axis(self):
        main_raw = self.main_raw(
            a_count=1, n_count=0, free_bench=3
        )
        child = self.arm_main_then_child(main_raw)
        action, _ = self.invoke(child, fallback=[0])
        self.assertTrue(action)
        before = copy.deepcopy(v1.LAST_V4_POFFIN_TRACE)
        protected = {
            key: copy.deepcopy(before[key])
            for key in (
                "parent_action",
                "applied_action",
                "A",
                "N",
                "F",
                "selected_cardinality",
                "selected_candidates",
                "classification",
            )
        }
        calls = []
        action = v1.agent(
            policy,
            lambda value: calls.append(value) or [7],
            copy.deepcopy(self.base),
        )
        self.assertEqual(action, [0])
        self.assertEqual(len(calls), 1)
        after = v1.LAST_V4_POFFIN_TRACE
        for key, value in protected.items():
            self.assertEqual(after[key], value)
        self.assertEqual(after["completion_parent_action"], [7])
        self.assertEqual(after["completion_applied_action"], [0])
        self.assertEqual(
            after["completion_selected_rule"],
            v1.RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
        )


if __name__ == "__main__":
    unittest.main()
