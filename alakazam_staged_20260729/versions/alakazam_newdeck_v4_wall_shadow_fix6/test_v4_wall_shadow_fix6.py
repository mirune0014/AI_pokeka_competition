from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import main
import planner_wall_shadow_fix6 as c4
from verification import c4_sidecar_collector as collector


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
FIXTURE_88843743 = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "fixtures"
    / "episode_88843743_public_observations"
)
FIXTURE_88844273 = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "fixtures"
    / "episode_88844273_public_observations"
)


def pokemon(
    card_id,
    serial,
    owner,
    hp,
    *,
    energies=(),
    energy_serial_start=None,
    pre_evolution=(),
):
    return {
        "appearThisTurn": False,
        "energies": list(energies),
        "energyCards": [
            {
                "id": energy,
                "playerIndex": owner,
                "serial": (
                    serial * 10
                    if energy_serial_start is None
                    else energy_serial_start
                )
                + index,
            }
            for index, energy in enumerate(energies)
        ],
        "hp": hp,
        "id": card_id,
        "maxHp": hp,
        "playerIndex": owner,
        "preEvolution": [
            {
                "id": stage_id,
                "playerIndex": owner,
                "serial": stage_serial,
            }
            for stage_id, stage_serial in pre_evolution
        ],
        "serial": serial,
        "tools": [],
    }


def c2_trace(
    *,
    route_class="CERTIFIED",
    delay=1,
    importance="UNIQUE",
    projected_damage=140,
    line_id=200,
    top_serial=200,
    second_ready=False,
):
    distance = {
        "route_class": route_class,
        "turn_delay": delay,
        "main_actions": delay,
        "forced_prompts": 0,
        "projected_powerful_hand_damage": projected_damage,
        "witness": {
            "template": "TEST_PUBLIC_WITNESS",
            "steps": [],
            "missing_requirements": [],
            "unsupported_reasons": [],
        },
    }
    rows = [
        {
            "line_id": line_id,
            "location": "BENCH",
            "top_card_id": 741,
            "top_serial": top_serial,
            "stack_serials": [top_serial],
            "stack_card_ids": [741],
            "energy_units": [],
            "primary_distance": copy.deepcopy(distance),
        }
    ]
    importance_rows = [
        {
            "line_id": line_id,
            "importance": importance,
            "reason": (
                "ONLY_LIVE_ALAKAZAM_LINE"
                if importance == "UNIQUE"
                else "TEST_IMPORTANCE"
            ),
            "after_removal_primary": {
                **copy.deepcopy(distance),
                "route_class": "POSSIBLE",
                "turn_delay": 3,
                "main_actions": 3,
            },
        }
    ]
    if second_ready:
        rows.append(
            {
                "line_id": 299,
                "location": "BENCH",
                "top_card_id": 743,
                "top_serial": 299,
                "stack_serials": [297, 298, 299],
                "stack_card_ids": [741, 742, 743],
                "energy_units": [5],
                "primary_distance": {
                    **copy.deepcopy(distance),
                    "turn_delay": 0,
                },
            }
        )
        importance_rows.append(
            {
                "line_id": 299,
                "importance": "REDUNDANT",
                "reason": "TEST_BACKUP",
                "after_removal_primary": copy.deepcopy(distance),
            }
        )
    return {
        "schema_version": 4,
        "rule_version": "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
        "metric_exception": None,
        "route_rows": rows,
        "line_importance_rows": importance_rows,
        "best_primary_route": copy.deepcopy(distance),
    }


class WallShadowFix6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads(
            (
                FIXTURE_88843743 / "step_023_run_away_after.json"
            ).read_text(encoding="utf-8")
        )
        cls.template = fixture["observation"]

    def setUp(self):
        c4.reset()

    def forced_raw(
        self,
        *,
        include_reusable=True,
        include_sacrifice=False,
        parent_serial=200,
        opponent_prizes=5,
    ):
        raw = copy.deepcopy(self.template)
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]
        mine["active"] = []
        line = pokemon(741, 200, owner, 50)
        bench = [line]
        if include_reusable:
            bench.append(
                pokemon(
                    66,
                    201,
                    owner,
                    140,
                    pre_evolution=((305, 211),),
                )
            )
        if include_sacrifice:
            bench.append(
                pokemon(305, 203, owner, 70, energies=(5,))
            )
        mine["bench"] = bench
        mine["deckCount"] = 20
        mine["prize"] = [None] * 4
        theirs["active"] = [
            pokemon(26, 300, 1 - owner, 120, energies=(1, 1))
        ]
        theirs["bench"] = [
            pokemon(26, 301, 1 - owner, 120, energies=(1, 1))
        ]
        theirs["prize"] = [None] * opponent_prizes
        theirs["discard"] = []
        raw["current"]["stadium"] = []
        raw["select"].update(
            {
                "context": 4,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {
                        "area": 5,
                        "index": index,
                        "playerIndex": owner,
                        "type": 3,
                    }
                    for index in range(len(bench))
                ],
            }
        )
        parent_index = next(
            index
            for index, card in enumerate(bench)
            if card["serial"] == parent_serial
        )
        return raw, [parent_index]

    def analyze(self, raw, action, trace=None, state=None):
        return c4.analyze(
            copy.deepcopy(raw),
            action,
            c2_trace=c2_trace() if trace is None else trace,
            state=c4.fresh_state() if state is None else state,
        )

    def certified_environment(self, raw, *, trace=None):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]
        if not any(card["serial"] == 299 for card in mine["bench"]):
            mine["bench"].append(
                pokemon(
                    743,
                    299,
                    owner,
                    140,
                    energies=(5,),
                    pre_evolution=((741, 297), (742, 298)),
                )
            )
        if not any(card["serial"] == 399 for card in mine["bench"]):
            mine["bench"].append(
                pokemon(
                    743,
                    399,
                    owner,
                    140,
                    energies=(5,),
                    pre_evolution=((741, 397), (742, 398)),
                )
            )
        mine["handCount"] = 8
        theirs["active"] = [
            pokemon(676, 310, 1 - owner, 110, energies=(6,))
        ]
        theirs["bench"] = [
            pokemon(673, 311, 1 - owner, 80),
            pokemon(674, 312, 1 - owner, 140),
            pokemon(675, 313, 1 - owner, 110),
            pokemon(676, 314, 1 - owner, 110),
            pokemon(678, 315, 1 - owner, 340),
        ]
        theirs["discard"] = [
            {
                "id": 1141,
                "playerIndex": 1 - owner,
                "serial": 800 + index,
            }
            for index in range(4)
        ]
        value = c2_trace(second_ready=True) if trace is None else trace
        value["line_importance_rows"][0]["importance"] = "IMPORTANT"
        value["line_importance_rows"][0]["reason"] = (
            "REMOVAL_WORSENS_PRIMARY_ROUTE"
        )
        value["route_rows"][1]["primary_distance"]["witness"]["steps"] = [
            {"kind": "EXACT_PROMOTION", "serial": 299}
        ]
        second_backup = copy.deepcopy(value["route_rows"][1])
        second_backup.update(
            {
                "line_id": 399,
                "top_serial": 399,
                "stack_serials": [397, 398, 399],
            }
        )
        second_backup["primary_distance"]["witness"]["steps"] = [
            {"kind": "EXACT_PROMOTION", "serial": 399}
        ]
        value["route_rows"].append(second_backup)
        value["line_importance_rows"].append(
            {
                "line_id": 399,
                "importance": "REDUNDANT",
                "reason": "TEST_SECOND_BACKUP",
                "after_removal_primary": copy.deepcopy(
                    value["best_primary_route"]
                ),
            }
        )
        return value

    def exact_delay_one_trading_environment(
        self, raw, *, include_ready_backups=False
    ):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]
        protected = next(
            card for card in mine["bench"] if card["serial"] == 200
        )
        protected.update(
            {
                "id": 742,
                "hp": 50,
                "maxHp": 80,
                "appearThisTurn": True,
                "preEvolution": [
                    {
                        "id": 741,
                        "playerIndex": owner,
                        "serial": 190,
                    }
                ],
            }
        )
        mine["bench"] = [
            card
            for card in mine["bench"]
            if card["serial"] not in (299, 399)
        ]
        if include_ready_backups:
            mine["bench"].extend(
                [
                    pokemon(
                        743,
                        serial,
                        owner,
                        140,
                        energies=(5,),
                        pre_evolution=(
                            (741, serial - 2),
                            (742, serial - 1),
                        ),
                    )
                    for serial in (299, 399)
                ]
            )
        mine["hand"] = [
            {"id": 743, "playerIndex": owner, "serial": 901},
            {"id": 5, "playerIndex": owner, "serial": 902},
        ]
        mine["handCount"] = 8
        theirs["active"] = [
            pokemon(676, 310, 1 - owner, 110, energies=(6,))
        ]
        theirs["bench"] = [
            pokemon(
                675,
                311,
                1 - owner,
                110,
                energies=(6, 6),
            ),
            *[
                pokemon(
                    674,
                    312 + index,
                    1 - owner,
                    150,
                    energies=(6,),
                )
                for index in range(2)
            ],
        ]
        theirs["handCount"] = 5
        theirs["deckCount"] = 20
        theirs["discard"] = [
            {
                "id": c4.PREMIUM_POWER_PRO,
                "playerIndex": 1 - owner,
                "serial": 800 + index,
            }
            for index in range(4)
        ] + [
            {
                "id": card_id,
                "playerIndex": 1 - owner,
                "serial": 810 + index,
            }
            for index, card_id in enumerate((673, 675, 676))
        ]
        distance = {
            "route_class": "CERTIFIED",
            "turn_delay": 1,
            "main_actions": 2,
            "forced_prompts": 1,
            "projected_powerful_hand_damage": 120,
            "witness": {
                "template": "EXACT_ONE_TURN_ALAKAZAM",
                "steps": [
                    {
                        "kind": "EVOLVE_FUTURE_SELF_TURN",
                        "source_serial": 901,
                        "turn_delay": 1,
                    },
                    {
                        "kind": "ATTACH_PSYCHIC_FUTURE_SELF_TURN",
                        "source_serial": 902,
                        "source_card_id": 5,
                        "turn_delay": 1,
                    },
                ],
                "missing_requirements": [],
                "unsupported_reasons": [],
            },
        }
        after = copy.deepcopy(distance)
        after.update(
            {
                "route_class": "POSSIBLE",
                "turn_delay": 3,
                "main_actions": 3,
            }
        )
        value = {
            "schema_version": 4,
            "rule_version": "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
            "metric_exception": None,
            "route_rows": [
                {
                    "line_id": 190,
                    "location": "BENCH",
                    "top_card_id": 742,
                    "top_serial": 200,
                    "stack_serials": [190, 200],
                    "stack_card_ids": [741, 742],
                    "energy_units": [],
                    "primary_distance": distance,
                }
            ],
            "line_importance_rows": [
                {
                    "line_id": 190,
                    "importance": "IMPORTANT",
                    "reason": "REMOVAL_WORSENS_PRIMARY_ROUTE",
                    "after_removal_primary": after,
                }
            ],
            "best_primary_route": copy.deepcopy(distance),
        }
        if include_ready_backups:
            for serial in (299, 399):
                ready_distance = {
                    "route_class": "CERTIFIED",
                    "turn_delay": 0,
                    "main_actions": 0,
                    "forced_prompts": 1,
                    "projected_powerful_hand_damage": 160,
                    "witness": {
                        "template": "EXACT_READY_BACKUP",
                        "steps": [
                            {
                                "kind": "EXACT_PROMOTION",
                                "serial": serial,
                            },
                            {
                                "kind": "ATTACK_READY",
                                "attack_id": c4.POWERFUL_HAND_ATTACK,
                            },
                        ],
                        "missing_requirements": [],
                        "unsupported_reasons": [],
                    },
                }
                value["route_rows"].append(
                    {
                        "line_id": serial - 2,
                        "location": "BENCH",
                        "top_card_id": 743,
                        "top_serial": serial,
                        "stack_serials": [
                            serial - 2,
                            serial - 1,
                            serial,
                        ],
                        "stack_card_ids": [741, 742, 743],
                        "energy_units": [5],
                        "primary_distance": ready_distance,
                    }
                )
                value["line_importance_rows"].append(
                    {
                        "line_id": serial - 2,
                        "importance": "REDUNDANT",
                        "reason": "TEST_READY_BACKUP",
                        "after_removal_primary": copy.deepcopy(distance),
                    }
                )
        return value

    def exact_parent_trace(self, raw):
        main._action_parent._deck_v1.reset()
        main._action_parent._integrated.core.reset_integrated_state()
        main._action_parent._parent.ability_used_dudunsparce = False
        action = main._action_parent.agent(copy.deepcopy(raw))
        return action, copy.deepcopy(
            main._action_parent.LAST_STAGED_POLICY_TRACE
        )

    def exact_run_away_trace(self, raw):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        line = pokemon(
            743,
            70,
            owner,
            140,
            energies=(5,),
            pre_evolution=((741, 63), (742, 69)),
        )
        mine["bench"] = [line]
        distance = {
            "route_class": "CERTIFIED",
            "turn_delay": 0,
            "main_actions": 0,
            "forced_prompts": 0,
            "projected_powerful_hand_damage": 160,
            "witness": {
                "template": "EXACT_RUN_AWAY_PROMOTION",
                "steps": [
                    {
                        "kind": "EXACT_PROMOTION",
                        "serial": 70,
                    },
                    {
                        "kind": "ATTACK_READY",
                        "attack_id": c4.POWERFUL_HAND_ATTACK,
                    },
                ],
                "missing_requirements": [],
                "unsupported_reasons": [],
            },
        }
        return {
            "schema_version": 4,
            "rule_version": "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
            "metric_exception": None,
            "route_rows": [
                {
                    "line_id": 63,
                    "location": "BENCH",
                    "top_card_id": 743,
                    "top_serial": 70,
                    "stack_serials": [63, 69, 70],
                    "stack_card_ids": [741, 742, 743],
                    "energy_units": [5],
                    "primary_distance": distance,
                }
            ],
            "line_importance_rows": [
                {
                    "line_id": 63,
                    "importance": "UNIQUE",
                    "reason": "ONLY_LIVE_ALAKAZAM_LINE",
                    "after_removal_primary": {
                        "route_class": "IMPOSSIBLE",
                        "turn_delay": 99,
                    },
                }
            ],
            "best_primary_route": copy.deepcopy(distance),
        }

    def supported_repeatable_run_target(self, raw):
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["active"] = [
            pokemon(673, 320, 1 - owner, 30, energies=(6, 6))
        ]
        theirs["bench"] = [
            pokemon(674, 321, 1 - owner, 140),
            pokemon(676, 322, 1 - owner, 110),
        ]
        theirs["discard"] = [
            {
                "id": c4.PREMIUM_POWER_PRO,
                "playerIndex": 1 - owner,
                "serial": 850 + index,
            }
            for index in range(4)
        ]

    def trading_child(self, raw, source, abra, backup, owner):
        child = copy.deepcopy(raw)
        mine = child["current"]["players"][owner]
        extras = [
            copy.deepcopy(card)
            for card in mine.get("bench", [])
            if card.get("serial") == 399
        ]
        mine["active"] = []
        mine["bench"] = [
            copy.deepcopy(source),
            copy.deepcopy(abra),
            *(
                [copy.deepcopy(backup)]
                if isinstance(backup, dict)
                else []
            ),
            *extras,
        ]
        child["current"]["turnActionCount"] += 1
        child["logs"] = [
            {
                "type": 15,
                "attackId": 423,
                "serial": source["serial"],
                "playerIndex": owner,
            }
        ]
        child["select"].update(
            {
                "context": 4,
                "type": 1,
                "minCount": 1,
                "maxCount": 1,
                "effect": {
                    "attackId": 423,
                    "sourceSerial": source["serial"],
                },
                "contextCard": None,
                "option": [
                    {
                        "area": 5,
                        "index": index,
                        "playerIndex": owner,
                        "type": 3,
                    }
                    for index in range(len(mine["bench"]))
                ],
            }
        )
        return child

    def row(self, trace, kind):
        return next(
            row for row in trace["candidate_rows"] if row["kind"] == kind
        )

    def test_fixture_01_mirror_completed_threat_reusable_wall(self):
        raw, action = self.forced_raw()
        raw["opponent_label"] = "alakazam_mirror"
        trace = self.analyze(
            raw, action, trace=self.certified_environment(raw)
        )
        reusable = self.row(trace, c4.REUSABLE)
        self.assertEqual(trace["decision_point"], c4.FORCED_PROMOTION)
        self.assertEqual(reusable["certification"], "STRICT")
        self.assertEqual(trace["rejection_codes"], [])
        self.assertEqual(trace["unsupported_reasons"], [])
        self.assertEqual(trace["structural_reasons"], [])

    def test_fixture_02_nonmirror_repeatable_condition_equivalence(self):
        raw, action = self.forced_raw()
        first = self.analyze(raw, action)
        raw["opponent_label"] = "unrelated_nonmirror_name"
        second = self.analyze(raw, action)
        self.assertEqual(
            self.row(first, c4.REUSABLE)["certification"],
            self.row(second, c4.REUSABLE)["certification"],
        )
        self.assertEqual(first["pair_id"], second["pair_id"])

    def test_fixture_03_recharge_required_is_not_strict(self):
        raw, action = self.forced_raw()
        owner = raw["current"]["yourIndex"]
        c2 = self.certified_environment(raw)
        raw["current"]["players"][1 - owner]["active"] = [
            pokemon(677, 310, 1 - owner, 70, energies=(6,))
        ]
        trace = self.analyze(raw, action, trace=c2)
        row = self.row(trace, c4.REUSABLE)
        self.assertNotEqual(row["certification"], "STRICT")
        self.assertIn("RECHARGE_REQUIRED", row["rejection_codes"])

    def test_fixture_04_unique_abra_sacrifice_wall(self):
        raw, action = self.forced_raw(
            include_reusable=False,
            include_sacrifice=True,
        )
        trace = self.analyze(
            raw,
            action,
            trace=self.exact_delay_one_trading_environment(raw),
        )
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertEqual(trace["importance"], "UNIQUE")
        self.assertEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(sacrifice["wall"]["hp"], 70)
        self.assertEqual(sacrifice["wall"]["tool_card_ids"], [])
        release = sacrifice["metrics"]["safe_release"]
        self.assertEqual(release["release_target"]["attacker_serial"], 901)
        self.assertEqual(
            release["release_mode"],
            "SACRIFICE_WALL_KO_THEN_ATTACK",
        )
        self.assertTrue(release["delay_one_projection"]["wall_ko"])
        self.assertEqual(
            release["delay_one_projection"]["wall_attack_damage"], 70
        )
        self.assertEqual(
            release["delay_one_projection"]["opponent_prizes_before"], 5
        )
        self.assertEqual(
            release["delay_one_projection"]["opponent_prizes_after"], 4
        )
        self.assertEqual(
            release["delay_one_projection"]["forced_promotion_serial"], 200
        )
        self.assertEqual(
            release["delay_one_projection"]["consumed_serials"],
            [901, 902],
        )
        self.assertEqual(
            release["delay_one_projection"]["projected_hand_count"], 7
        )
        self.assertTrue(release["next_attack_certified"])
        self.assertFalse(release["backup_certified"])

    def test_delay_one_trading_release_consumes_exact_visible_resources(self):
        for missing_serial, expected_reason in (
            (901, "TRADING_DELAY_ONE_EVOLUTION_MISSING"),
            (902, "TRADING_DELAY_ONE_ENERGY_MISSING"),
        ):
            with self.subTest(missing_serial=missing_serial):
                raw, action = self.forced_raw(
                    include_reusable=False,
                    include_sacrifice=True,
                )
                c2 = self.exact_delay_one_trading_environment(raw)
                owner = raw["current"]["yourIndex"]
                mine = raw["current"]["players"][owner]
                mine["hand"] = [
                    card
                    for card in mine["hand"]
                    if card["serial"] != missing_serial
                ]
                trace = self.analyze(raw, action, trace=c2)
                sacrifice = self.row(trace, c4.SACRIFICE)
                self.assertNotEqual(sacrifice["certification"], "STRICT")
                self.assertEqual(
                    sacrifice["metrics"]["safe_release"]["reason"],
                    expected_reason,
                )

    def test_delay_one_trading_release_rejects_unsafe_completed_line(self):
        raw, action = self.forced_raw(
            include_reusable=False,
            include_sacrifice=True,
        )
        c2 = self.exact_delay_one_trading_environment(raw)
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["bench"][1] = pokemon(
            674,
            312,
            1 - owner,
            150,
            energies=(6, 6, 6),
        )
        trace = self.analyze(raw, action, trace=c2)
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(
            sacrifice["metrics"]["safe_release"]["reason"],
            "SACRIFICE_PROMOTED_ATTACKER_CAP_CONTINUITY_OR_PRIZE_UNSAFE",
        )

    def test_delay_one_attack_branch_requires_prize_promotion_and_draw(self):
        cases = (
            (
                "final_prize",
                lambda raw, c2, owner: raw["current"]["players"][
                    1 - owner
                ].update(prize=[None]),
                "TRADING_ATTACK_BRANCH_FINAL_PRIZE_DONATION",
            ),
            (
                "forced_promotion",
                lambda raw, c2, owner: raw["current"]["players"][
                    owner
                ]["bench"].append(pokemon(305, 204, owner, 70)),
                "TRADING_ATTACK_BRANCH_FORCED_PROMOTION_UNCERTIFIED",
            ),
            (
                "mandatory_draw",
                lambda raw, c2, owner: raw["current"]["players"][
                    owner
                ].update(deckCount=0),
                "TRADING_DELAY_ONE_MANDATORY_DRAW_UNCERTIFIED",
            ),
        )
        for name, mutate, expected_reason in cases:
            with self.subTest(name=name):
                raw, action = self.forced_raw(
                    include_reusable=False,
                    include_sacrifice=True,
                )
                c2 = self.exact_delay_one_trading_environment(raw)
                owner = raw["current"]["yourIndex"]
                mutate(raw, c2, owner)
                trace = self.analyze(raw, action, trace=c2)
                sacrifice = self.row(trace, c4.SACRIFICE)
                self.assertNotEqual(
                    sacrifice["certification"], "STRICT"
                )
                self.assertEqual(
                    sacrifice["metrics"]["safe_release"]["reason"],
                    expected_reason,
                )

    def test_delay_one_attack_branch_requires_complete_c2_witness(self):
        raw, action = self.forced_raw(
            include_reusable=False,
            include_sacrifice=True,
        )
        c2 = self.exact_delay_one_trading_environment(raw)
        c2["route_rows"][0]["primary_distance"]["witness"] = None
        trace = self.analyze(raw, action, trace=c2)
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        self.assertIn(
            "C2_DISTANCE_TUPLE_INVALID",
            sacrifice["rejection_codes"],
        )

    def test_fixture_05_rebuild_possible_does_not_erase_unique(self):
        raw, action = self.forced_raw()
        trace = self.analyze(
            raw,
            action,
            trace=c2_trace(
                route_class="POSSIBLE",
                delay=3,
                importance="UNIQUE",
            ),
        )
        self.assertEqual(trace["importance"], "UNIQUE")
        self.assertNotIn("IMPORTANCE_UNKNOWN", trace["rejection_codes"])

    def test_fixture_06_no_live_line_extension_is_rejected(self):
        raw, action = self.forced_raw()
        trace = self.analyze(
            raw,
            action,
            trace={
                "rule_version": "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
                "metric_exception": None,
                "route_rows": [
                    {
                        "line_id": "RECONSTRUCT",
                        "location": "VIRTUAL",
                        "primary_distance": {
                            "route_class": "IMPOSSIBLE",
                            "turn_delay": 99,
                        },
                    }
                ],
                "line_importance_rows": [],
            },
        )
        self.assertIn("NO_LIVE_PROTECTED_LINE", trace["rejection_codes"])
        self.assertNotEqual(
            self.row(trace, c4.REUSABLE)["certification"], "STRICT"
        )

    def test_fixture_07_refusal_progress_certified(self):
        raw, action = self.forced_raw(include_sacrifice=True)
        trace = self.analyze(
            raw, action, trace=self.certified_environment(raw)
        )
        self.assertEqual(
            self.row(trace, c4.REUSABLE)["metrics"]["hold_turns"], 1
        )
        self.assertEqual(
            self.row(trace, c4.REUSABLE)["metrics"]["safe_release"]["class"],
            "CERTIFIED",
        )

    def test_fixture_08_refusal_without_progress_is_rejected(self):
        raw, action = self.forced_raw()
        trace = self.analyze(
            raw,
            action,
            trace=c2_trace(route_class="POSSIBLE", delay=2),
        )
        self.assertIn(
            "PROGRESS_POSSIBLE_ONLY",
            self.row(trace, c4.REUSABLE)["rejection_codes"],
        )

    def run_away_raw(self, *, target_hp=30, opponent_bench=True):
        fixture = json.loads(
            (
                FIXTURE_88843743 / "step_022_run_away_before.json"
            ).read_text(encoding="utf-8")
        )
        raw = fixture["observation"]
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["active"] = [
            pokemon(26, 320, 1 - owner, target_hp, energies=(1, 1))
        ]
        theirs["bench"] = (
            [pokemon(26, 321, 1 - owner, 120, energies=(1, 1))]
            if opponent_bench
            else []
        )
        theirs["discard"] = []
        raw["current"]["stadium"] = []
        return raw

    def test_fixture_09_run_away_current_threat_ko_override(self):
        raw = self.run_away_raw(target_hp=30, opponent_bench=True)
        self.supported_repeatable_run_target(raw)
        c2 = self.exact_run_away_trace(raw)
        trace = self.analyze(raw, [2], trace=c2)
        run = self.row(trace, c4.RUN_AWAY)
        self.assertEqual(run["certification"], "STRICT")
        self.assertEqual(trace["rejection_codes"], [])
        self.assertEqual(trace["unsupported_reasons"], [])
        self.assertEqual(trace["structural_reasons"], [])
        self.assertEqual(
            run["metrics"]["conversion"]["conversion"],
            "CURRENT_REPEATABLE_THREAT_KO",
        )

    def test_fixture_10_run_away_unsafe_promotion_is_preserved_only(self):
        raw = self.run_away_raw(target_hp=100, opponent_bench=True)
        trace = self.analyze(raw, [2])
        run = self.row(trace, c4.RUN_AWAY)
        self.assertEqual(run["certification"], "PRESERVE_CHANCE")
        self.assertIn(
            "RUN_AWAY_NO_EXACT_TERMINAL_THREAT_KO_OR_SAFE_EXCHANGE",
            run["rejection_codes"],
        )

    def test_fixture_11_trading_places_child_is_serial_bound_and_safe(self):
        raw, _ = self.forced_raw(
            include_reusable=False, include_sacrifice=True
        )
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        source = pokemon(305, 203, owner, 70, energies=(5,))
        abra = pokemon(741, 200, owner, 50)
        mine["active"] = [source]
        mine["bench"] = [abra]
        c2 = self.exact_delay_one_trading_environment(raw)
        abra = next(
            card for card in mine["bench"] if card["serial"] == 200
        )
        raw["select"].update(
            {
                "context": 0,
                "type": 0,
                "option": [
                    {"attackId": 423, "type": 13},
                    {"type": 14},
                ],
            }
        )
        state = c4.fresh_state()
        pending = self.analyze(raw, [0], trace=c2, state=state)
        self.assertIn(
            "TRADING_PLACES_CHILD_PENDING", pending["rejection_codes"]
        )
        child = self.trading_child(raw, source, abra, None, owner)
        child_trace = self.analyze(child, [0], trace=c2, state=state)
        self.assertEqual(child_trace["decision_point"], c4.TRADING_CHILD)
        self.assertEqual(
            child_trace["protected_line"]["top_serial"], 200
        )
        sacrifice = self.row(child_trace, c4.SACRIFICE)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        refusal_release = sacrifice["metrics"]["safe_release"]
        self.assertEqual(
            refusal_release["reason"],
            "POST_RELEASE_CUMULATIVE_ATTACHMENTS_ENABLE_ATTACK:"
            "312:978:2",
        )
        self.assertEqual(
            refusal_release["delay_one_projection"]["branch"],
            c4.DELAY_ONE_REFUSAL_BRANCH,
        )
        self.assertFalse(
            refusal_release["delay_one_projection"]["wall_ko"]
        )
        self.assertEqual(
            refusal_release["delay_one_projection"][
                "projected_hand_count"
            ],
            7,
        )
        self.assertEqual(
            refusal_release["delay_one_projection"][
                "opponent_mandatory_draw_count"
            ],
            1,
        )
        self.assertEqual(
            refusal_release["delay_one_projection"][
                "prior_attachment_turns"
            ],
            1,
        )

    def test_refusal_attachment_envelope_certifies_deficit_above_turns(self):
        raw, _ = self.forced_raw(
            include_reusable=False, include_sacrifice=True
        )
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        source = pokemon(305, 203, owner, 70, energies=(5,))
        abra = pokemon(741, 200, owner, 50)
        mine["active"] = [source]
        mine["bench"] = [abra]
        c2 = self.exact_delay_one_trading_environment(raw)
        abra = next(
            card for card in mine["bench"] if card["serial"] == 200
        )
        theirs = raw["current"]["players"][1 - owner]
        for attacker in theirs["bench"]:
            if attacker["id"] == 674:
                attacker["energies"] = []
                attacker["energyCards"] = []
        raw["select"].update(
            {
                "context": 0,
                "type": 0,
                "option": [
                    {"attackId": 423, "type": 13},
                    {"type": 14},
                ],
            }
        )
        state = c4.fresh_state()
        self.analyze(raw, [0], trace=c2, state=state)
        child = self.trading_child(raw, source, abra, None, owner)
        child_trace = self.analyze(child, [0], trace=c2, state=state)
        sacrifice = self.row(child_trace, c4.SACRIFICE)
        self.assertEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(
            sacrifice["metrics"]["safe_release"][
                "delay_one_projection"
            ]["branch"],
            c4.DELAY_ONE_REFUSAL_BRANCH,
        )

    def test_trading_release_does_not_compose_a_second_same_turn_attack(self):
        raw, _ = self.forced_raw(
            include_reusable=False, include_sacrifice=True
        )
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]
        source = pokemon(305, 203, owner, 70, energies=(5,))
        abra = pokemon(741, 200, owner, 50)
        backup = pokemon(
            743,
            299,
            owner,
            140,
            energies=(5,),
            pre_evolution=((741, 297), (742, 298)),
        )
        mine["active"] = [source]
        mine["bench"] = [abra, backup]
        c2 = self.certified_environment(raw)
        c2["route_rows"][0]["primary_distance"].update(
            {
                "turn_delay": 0,
                "main_actions": 0,
                "forced_prompts": 0,
            }
        )
        theirs["active"] = [
            pokemon(674, 350, 1 - owner, 100, energies=(6, 6, 6))
        ]
        theirs["discard"] = [
            {
                "id": c4.PREMIUM_POWER_PRO,
                "playerIndex": 1 - owner,
                "serial": 880 + index,
            }
            for index in range(4)
        ]
        raw["select"].update(
            {
                "context": 0,
                "type": 0,
                "option": [
                    {"attackId": c4.TRADING_PLACES_ATTACK, "type": 13},
                    {"type": 14},
                ],
            }
        )
        state = c4.fresh_state()
        self.analyze(raw, [0], trace=c2, state=state)
        child = self.trading_child(raw, source, abra, backup, owner)
        child_trace = self.analyze(child, [0], trace=c2, state=state)
        sacrifice = self.row(child_trace, c4.SACRIFICE)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        release = sacrifice["metrics"]["safe_release"]
        self.assertEqual(
            release["release_mode"], "TRADING_PLACES_POST_ATTACK"
        )
        self.assertEqual(release["class"], "POSSIBLE")
        self.assertEqual(
            release["reason"],
            "TRADING_PROMOTED_ATTACKER_CAP_CONTINUITY_OR_PRIZE_UNSAFE",
        )

    def test_trading_timeline_rejects_current_attack_energy_effect(self):
        raw, action = self.forced_raw(
            include_reusable=False,
            include_sacrifice=True,
        )
        c2 = self.exact_delay_one_trading_environment(raw)
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["active"] = [
            pokemon(678, 350, 1 - owner, 100, energies=(6, 6))
        ]
        theirs["discard"].append(
            {
                "id": 6,
                "playerIndex": 1 - owner,
                "serial": 889,
            }
        )
        trace = self.analyze(raw, action, trace=c2)
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(
            sacrifice["metrics"]["safe_release"]["reason"],
            "FUTURE_ATTACK_ALTERS_BOARD_OR_ENERGY:982",
        )

    def test_trading_timeline_rejects_zero_energy_promoted_one_attach(self):
        raw, action = self.forced_raw(
            include_reusable=False,
            include_sacrifice=True,
        )
        c2 = self.exact_delay_one_trading_environment(raw)
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["bench"][1] = pokemon(
            678,
            312,
            1 - owner,
            160,
            energies=(),
        )
        self.assertEqual(
            c4._one_attachment_enables_attack(theirs["bench"][1]),
            (True, 982),
        )
        trace = self.analyze(raw, action, trace=c2)
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(
            sacrifice["metrics"]["safe_release"]["reason"],
            "SACRIFICE_PROMOTED_ATTACKER_CAP_CONTINUITY_OR_PRIZE_UNSAFE",
        )

    def test_fixture_12_public_certified_bench_snipe_refuses_strict(self):
        state = c4.fresh_state()
        bypass = c4._bypass_class(
            state,
            {"attack_text": "This attack does 30 damage to a Benched Pokemon."},
            True,
        )
        self.assertEqual(bypass, "UNSUPPORTED_POSSIBLE_BYPASS")
        armed = c4._bypass_class(
            state,
            {
                "status": "SUPPORTED",
                "unsupported_reasons": [],
                "attack_text": "This attack damages a Benched Pokemon.",
                "bypass_capability": "EXACT_ARMED",
            },
            True,
        )
        self.assertEqual(armed, "CERTIFIED_ARMED_BYPASS")

    def test_production_threat_scans_every_payable_attack_for_bypass(self):
        raw, action = self.forced_raw()
        c2 = self.certified_environment(raw)
        owner = raw["current"]["yourIndex"]
        attacker = raw["current"]["players"][1 - owner]["active"][0]
        attacker.update(
            id=678,
            hp=340,
            maxHp=340,
            energies=[6, 6],
            energyCards=[
                {
                    "id": 6,
                    "playerIndex": 1 - owner,
                    "serial": 930 + index,
                }
                for index in range(2)
            ],
        )
        metadata = c4.policy.card_table[678]
        with mock.patch.object(metadata, "attacks", [982, 3]):
            trace = self.analyze(raw, action, trace=c2)
        self.assertEqual(trace["threat"]["attack_id"], 982)
        self.assertEqual(
            trace["threat"]["bypass_capability"], "EXACT_ARMED"
        )
        self.assertEqual(
            [row["attack_id"] for row in trace["threat"]["bypass_attacks"]],
            [3],
        )
        reusable = self.row(trace, c4.REUSABLE)
        self.assertIn("PUBLIC_ARMED_BYPASS", reusable["rejection_codes"])
        self.assertNotEqual(reusable["certification"], "STRICT")

    def test_fixture_13_revealed_possible_boss_is_chance_only(self):
        raw, action = self.forced_raw()
        state = c4.fresh_state()
        state["boundary_fingerprint"] = "A" * 64
        state["revealed_boss"] = True
        trace = self.analyze(raw, action, state=state)
        reusable = self.row(trace, c4.REUSABLE)
        self.assertEqual(reusable["certification"], "PRESERVE_CHANCE")
        self.assertIn(
            "REVEALED_POSSIBLE_BYPASS", reusable["rejection_codes"]
        )

    def test_fixture_14_final_prize_wall_is_rejected(self):
        raw, action = self.forced_raw(opponent_prizes=1)
        trace = self.analyze(raw, action)
        self.assertIn(
            "FINAL_PRIZE_DONATION",
            self.row(trace, c4.REUSABLE)["rejection_codes"],
        )

    def test_fixture_15_wall_and_draw3_are_separate_rows(self):
        raw = self.run_away_raw(target_hp=100)
        trace = self.analyze(raw, [2])
        self.assertEqual(
            [row["kind"] for row in trace["candidate_rows"]],
            list(c4.CANDIDATE_KINDS),
        )
        self.assertEqual(trace["certified_draw_count"], 3)
        self.assertEqual(trace["certified_draw_damage_delta"], 60)
        self.assertEqual(
            self.row(trace, c4.RUN_AWAY)["metrics"][
                "drawn_card_identities"
            ],
            "POSSIBLE",
        )

    def test_fixture_16_reorder_duplicate_and_stale_pending(self):
        raw, action = self.forced_raw()
        first = self.analyze(raw, action)
        reordered = copy.deepcopy(raw)
        reordered["select"]["option"] = list(
            reversed(reordered["select"]["option"])
        )
        second = self.analyze(reordered, [len(action)])
        self.assertEqual(first["pair_id"], second["pair_id"])
        duplicate = copy.deepcopy(raw)
        duplicate["select"]["option"].append(
            copy.deepcopy(duplicate["select"]["option"][0])
        )
        dup_trace = self.analyze(duplicate, action)
        self.assertIn(
            "DUPLICATE_SEMANTIC_OPTION", dup_trace["rejection_codes"]
        )
        self.assertFalse(
            any(
                row["certification"] == "STRICT"
                for row in dup_trace["candidate_rows"]
            )
        )
        state = c4.fresh_state()
        state["boundary_fingerprint"] = "B" * 64
        state["trading_pending"] = {
            "boundary": "B" * 64,
            "turn": 1,
            "created_ordinal": 1,
        }
        raw["current"]["turn"] = 5
        stale = self.analyze(raw, action, state=state)
        self.assertNotEqual(stale["decision_point"], c4.TRADING_CHILD)

    def test_fixture_17_episode_88844273_all_actions_identity(self):
        expected = {67: [0], 98: [0], 121: [4], 148: [0]}
        for path in sorted(FIXTURE_88844273.glob("*.json")):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            main._action_parent._deck_v1.reset()
            main._action_parent._integrated.core.reset_integrated_state()
            main._action_parent._parent.ability_used_dudunsparce = False
            c4.reset()
            returned = main.agent(copy.deepcopy(fixture["observation"]))
            self.assertEqual(
                returned, expected[fixture["source_step_index"]], path.name
            )
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["rule_version"],
                c4.RULE_VERSION,
            )

    def test_fixture_18_episode_88843743_before_after_identity(self):
        for path in sorted(FIXTURE_88843743.glob("*.json")):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            main._action_parent._deck_v1.reset()
            main._action_parent._integrated.core.reset_integrated_state()
            main._action_parent._parent.ability_used_dudunsparce = False
            c4.reset()
            returned = main.agent(copy.deepcopy(fixture["observation"]))
            self.assertEqual(
                returned, fixture["expected_parent_action"], path.name
            )
            self.assertIs(
                main.LAST_STAGED_POLICY_TRACE["applied_action"], returned
            )

    def test_power_pro_physical_four_stack_and_equal_hp_rejection(self):
        raw, action = self.forced_raw()
        owner = raw["current"]["yourIndex"]
        raw["current"]["players"][1 - owner]["active"] = [
            pokemon(673, 330, 1 - owner, 80, energies=(6,))
        ]
        state = c4.fresh_state()
        state["boundary_fingerprint"] = "A" * 64
        state["power_pro_seen_serials"] = {800}
        state["family_marker_ids"] = {673, 676, 678}
        trace = self.analyze(raw, action, state=state)
        multiplicity = trace["premium_power_pro_multiplicity"]
        self.assertEqual(multiplicity["deck_limit"], 4)
        self.assertEqual(multiplicity["stack_max"], 4)
        reusable = self.row(trace, c4.REUSABLE)
        self.assertIn(
            "REUSABLE_WALL_NOT_ABOVE_FINAL_SAFETY_CAP",
            reusable["rejection_codes"],
        )

    def test_pareto_no_automatic_reusable_priority_and_unique_dominance(self):
        raw, action = self.forced_raw(include_sacrifice=True)
        trace = self.analyze(
            raw,
            action,
            trace=self.exact_delay_one_trading_environment(
                raw, include_ready_backups=True
            ),
        )
        reusable = self.row(trace, c4.REUSABLE)
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertEqual(reusable["certification"], "STRICT")
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(
            sacrifice["metrics"]["safe_release"]["reason"],
            "TRADING_ATTACK_BRANCH_FORCED_PROMOTION_UNCERTIFIED",
        )
        comparable_sacrifice = copy.deepcopy(reusable)
        comparable_sacrifice["kind"] = c4.SACRIFICE
        selected, reason = c4.pareto_arbitrate(
            [
                self.row(trace, c4.RUN_AWAY),
                reusable,
                comparable_sacrifice,
                self.row(trace, c4.NO_WALL),
            ]
        )
        self.assertEqual(
            (selected, reason),
            (c4.NO_WALL, "NO_CERTIFIED_DOMINANCE"),
        )
        comparable_sacrifice["pareto_vector"] = {
            key: value - 1
            for key, value in reusable["pareto_vector"].items()
        }
        selected, reason = c4.pareto_arbitrate(
            [
                self.row(trace, c4.RUN_AWAY),
                reusable,
                comparable_sacrifice,
                self.row(trace, c4.NO_WALL),
            ]
        )
        self.assertEqual((selected, reason), (c4.REUSABLE, "PARETO_DOMINANCE"))

    def test_nonrolling_deadline_and_strict_progress(self):
        raw = self.run_away_raw(target_hp=100)
        state = c4.fresh_state()
        state["boundary_fingerprint"] = "A" * 64
        state["holds"][79] = {
            "entry_turn": 4,
            "deadline": 6,
            "last_checked_turn": 4,
            "last_quality": (0, 2),
            "distance_progress_by_turn": [],
            "decision_id": "D",
        }
        raw["current"]["turn"] = 5
        first = self.analyze(
            raw, [2], trace=c2_trace(delay=1), state=state
        )
        self.assertEqual(first["hold_deadline"], 6)
        raw["current"]["turn"] = 6
        stalled = self.analyze(
            raw, [2], trace=c2_trace(delay=1), state=state
        )
        self.assertEqual(stalled["hold_deadline"], 6)
        self.assertIn("HOLD_PROGRESS_STALLED", stalled["rejection_codes"])
        self.assertIn("HOLD_DEADLINE_REACHED", stalled["rejection_codes"])
        self.assertNotIn(79, state["holds"])
        self.assertEqual(
            state["closed_holds"][79]["reason"], "HOLD_DEADLINE_REACHED"
        )

    def test_b_decision_has_exact_run_and_hold_options_and_fails_closed(self):
        raw = self.run_away_raw(target_hp=30)
        self.supported_repeatable_run_target(raw)
        c2 = self.exact_run_away_trace(raw)
        trace = self.analyze(raw, [3], trace=c2)
        run = self.row(trace, c4.RUN_AWAY)
        hold = self.row(trace, c4.REUSABLE)
        self.assertEqual(trace["decision_point"], c4.RUN_AWAY_POINT)
        self.assertEqual((run["legality"], run["option_index"]), ("EXACT", 2))
        self.assertEqual((hold["legality"], hold["option_index"]), ("EXACT", 3))
        malformed = copy.deepcopy(raw)
        malformed["select"]["option"][2]["index"] = 99
        rejected = self.analyze(malformed, [3], trace=c2)
        self.assertFalse(
            any(
                row["certification"] == "STRICT"
                for row in rejected["candidate_rows"]
            )
        )

    def test_partial_attack_parse_never_certifies_a_wall(self):
        raw, action = self.forced_raw()
        trace = self.analyze(raw, action)
        row = self.row(trace, c4.REUSABLE)
        self.assertNotEqual(row["certification"], "STRICT")
        self.assertTrue(row["unsupported_reasons"])

    def test_safe_release_requires_real_backup_and_strictly_above_cap(self):
        raw, action = self.forced_raw()
        c2 = self.certified_environment(raw)
        backup = next(
            card
            for card in raw["current"]["players"][
                raw["current"]["yourIndex"]
            ]["bench"]
            if card["serial"] == 299
        )
        backup["hp"] = 70
        next(
            card
            for card in raw["current"]["players"][
                raw["current"]["yourIndex"]
            ]["bench"]
            if card["serial"] == 399
        )["hp"] = 70
        ready_opponent = next(
            card
            for card in raw["current"]["players"][
                1 - raw["current"]["yourIndex"]
            ]["bench"]
            if card["serial"] == 314
        )
        ready_opponent["energies"] = [6]
        ready_opponent["energyCards"] = [
            {
                "id": 6,
                "playerIndex": 1 - raw["current"]["yourIndex"],
                "serial": 994,
            }
        ]
        equal_cap = self.analyze(raw, action, trace=c2)
        self.assertNotEqual(
            self.row(equal_cap, c4.REUSABLE)["certification"], "STRICT"
        )

        raw, action = self.forced_raw()
        c2 = self.certified_environment(raw)
        mine = raw["current"]["players"][raw["current"]["yourIndex"]]
        mine["bench"] = [
            card
            for card in mine["bench"]
            if card["serial"] not in (299, 399)
        ]
        fake_backup = self.analyze(raw, action, trace=c2)
        release = self.row(fake_backup, c4.REUSABLE)["metrics"][
            "safe_release"
        ]
        self.assertEqual(release["class"], "POSSIBLE")
        self.assertFalse(release["backup_certified"])

    def test_safe_release_uses_promoted_bench_threat_not_ko_target_cap(self):
        raw, action = self.forced_raw()
        c2 = self.certified_environment(raw)
        owner = raw["current"]["yourIndex"]
        raw["current"]["players"][1 - owner]["bench"][-1] = pokemon(
            674, 450, 1 - owner, 140, energies=(6, 6, 6)
        )
        trace = self.analyze(raw, action, trace=c2)
        row = self.row(trace, c4.REUSABLE)
        self.assertNotEqual(row["certification"], "STRICT")
        self.assertEqual(
            row["metrics"]["safe_release"]["class"], "POSSIBLE"
        )
        self.assertEqual(
            row["metrics"]["safe_release"]["reason"],
            "POST_RELEASE_PROMOTION_CAP_OR_CONTINUITY_UNSAFE",
        )

        raw, action = self.forced_raw()
        c2 = self.certified_environment(raw)
        owner = raw["current"]["yourIndex"]
        raw["current"]["players"][1 - owner]["bench"][-1] = pokemon(
            678, 990, 1 - owner, 340, energies=(6, 6)
        )
        lucario = self.analyze(raw, action, trace=c2)
        lucario_release = self.row(lucario, c4.REUSABLE)["metrics"][
            "safe_release"
        ]
        self.assertEqual(lucario_release["class"], "POSSIBLE")
        self.assertEqual(
            lucario_release["reason"],
            "POST_RELEASE_PROMOTION_CAP_OR_CONTINUITY_UNSAFE",
        )

    def test_missing_turn_or_status_fields_cannot_be_strict(self):
        cases = (
            ("turn", lambda raw, owner: raw["current"].pop("turn")),
            (
                "opponent_status",
                lambda raw, owner: raw["current"]["players"][
                    1 - owner
                ].pop("confused"),
            ),
        )
        for name, mutation in cases:
            with self.subTest(name=name):
                raw, action = self.forced_raw()
                c2 = self.certified_environment(raw)
                owner = raw["current"]["yourIndex"]
                mutation(raw, owner)
                trace = self.analyze(raw, action, trace=c2)
                self.assertFalse(
                    any(
                        row["certification"] == "STRICT"
                        for row in trace["candidate_rows"]
                    )
                )
                self.assertTrue(trace["structural_reasons"])

    def test_missing_benchmax_or_duplicate_public_serial_cannot_be_strict(self):
        cases = (
            (
                "own_benchmax",
                lambda raw, owner: raw["current"]["players"][owner].pop(
                    "benchMax"
                ),
            ),
            (
                "opponent_benchmax",
                lambda raw, owner: raw["current"]["players"][
                    1 - owner
                ].pop("benchMax"),
            ),
            (
                "duplicate_visible_serial",
                lambda raw, owner: raw["current"]["players"][
                    1 - owner
                ]["bench"][0].update(
                    serial=raw["current"]["players"][1 - owner]["active"][
                        0
                    ]["serial"]
                ),
            ),
        )
        for name, mutation in cases:
            with self.subTest(name=name):
                raw, action = self.forced_raw()
                c2 = self.certified_environment(raw)
                owner = raw["current"]["yourIndex"]
                mutation(raw, owner)
                trace = self.analyze(raw, action, trace=c2)
                self.assertFalse(
                    any(
                        row["certification"] == "STRICT"
                        for row in trace["candidate_rows"]
                    )
                )
                self.assertTrue(trace["structural_reasons"])

    def test_solrock_requires_exact_benched_lunatone(self):
        raw, action = self.forced_raw()
        c2 = self.certified_environment(raw)
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        with_lunatone = self.analyze(raw, action, trace=c2)
        self.assertEqual(
            self.row(with_lunatone, c4.REUSABLE)["certification"],
            "STRICT",
        )

        theirs["bench"] = [
            card for card in theirs["bench"] if card["id"] != 675
        ]
        missing = self.analyze(raw, action, trace=c2)
        row = self.row(missing, c4.REUSABLE)
        self.assertNotEqual(row["certification"], "STRICT")
        self.assertEqual(missing["threat"]["damage_floor"], 0)

    def test_power_pro_current_unavailable_re_evaluates_and_hidden_hand_is_ignored(self):
        raw, _ = self.forced_raw()
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["discard"] = [
            {"id": 1141, "playerIndex": 1 - owner, "serial": 801}
        ]
        state = c4.fresh_state()
        c4._update_public_evidence(raw, state)
        self.assertEqual(state["power_pro_unavailable_serials"], {801})
        theirs["discard"] = []
        theirs["hand"] = [
            {"id": 1141, "playerIndex": 1 - owner, "serial": 999}
        ]
        c4._update_public_evidence(raw, state)
        self.assertEqual(state["power_pro_unavailable_serials"], set())
        self.assertNotIn(999, state["power_pro_seen_serials"])

    def test_mega_lucario_prefers_repeatable_floor_ko_over_recharge(self):
        raw, _ = self.forced_raw()
        owner = raw["current"]["yourIndex"]
        c2 = self.certified_environment(raw)
        theirs = raw["current"]["players"][1 - owner]
        theirs["active"] = [
            pokemon(678, 310, 1 - owner, 340, energies=(6, 6))
        ]
        state = c4.fresh_state()
        state["boundary_fingerprint"] = "A" * 64
        c4._update_public_evidence(raw, state)
        defender = next(
            card
            for card in raw["current"]["players"][owner]["bench"]
            if card["serial"] == 201
        )
        threat = c4._threat_analysis(raw, defender, state)
        self.assertEqual(threat["attack_id"], 982)
        self.assertEqual(threat["continuity"], c4.REPEATABLE_READY)
        self.assertTrue(threat["floor_ko"])
        self.assertGreater(threat["final_safety_cap"], threat["damage_cap"])
        self.assertEqual(c2["route_rows"][1]["top_serial"], 299)

    def test_powerful_hand_counter_placement_does_not_apply_weakness(self):
        raw = self.run_away_raw(target_hp=170)
        owner = raw["current"]["yourIndex"]
        raw["current"]["players"][1 - owner]["active"] = [
            pokemon(673, 320, 1 - owner, 170)
        ]
        c2 = self.exact_run_away_trace(raw)
        line = raw["current"]["players"][owner]["bench"][0]
        conversion = c4._exact_attack_conversion(
            raw,
            line,
            c2["route_rows"][0]["primary_distance"],
            location="BENCH",
            hand_bonus=3,
        )
        self.assertEqual(conversion["damage"], 160)
        self.assertFalse(conversion["certified"])

    def test_powerful_hand_threat_respects_exact_public_blocker(self):
        raw, _ = self.forced_raw()
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]
        defender = next(card for card in mine["bench"] if card["serial"] == 201)
        defender["energies"] = [5]
        defender["energyCards"] = [
            {"id": c4.MIST_ENERGY, "playerIndex": owner, "serial": 991}
        ]
        theirs["active"] = [
            pokemon(743, 310, 1 - owner, 140, energies=(5,))
        ]
        theirs["handCount"] = 8
        state = c4.fresh_state()
        state["boundary_fingerprint"] = "A" * 64
        threat = c4._threat_analysis(raw, defender, state)
        self.assertEqual(threat["attack_id"], c4.POWERFUL_HAND_ATTACK)
        self.assertEqual(threat["damage_floor"], 0)
        self.assertFalse(threat["floor_ko"])

    def test_repelling_veil_blocks_run_away_powerful_hand_exactly(self):
        raw = self.run_away_raw(target_hp=100)
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        target = pokemon(431, 320, 1 - owner, 100)
        theirs["active"] = [target]
        theirs["bench"] = [pokemon(414, 321, 1 - owner, 120)]
        c2 = self.exact_run_away_trace(raw)
        blocked = self.analyze(raw, [2], trace=c2)
        run = self.row(blocked, c4.RUN_AWAY)
        self.assertNotEqual(run["certification"], "STRICT")
        self.assertFalse(run["metrics"]["conversion"]["ko"])
        self.assertIs(
            c4._powerful_hand_target_blocked(raw, target), True
        )

        theirs["bench"] = []
        clear = self.analyze(raw, [2], trace=c2)
        self.assertEqual(
            self.row(clear, c4.RUN_AWAY)["certification"], "STRICT"
        )
        self.assertIs(
            c4._powerful_hand_target_blocked(raw, target), False
        )

    def test_run_away_safe_exchange_needs_repeatable_threat_and_backup(self):
        raw = self.run_away_raw(target_hp=30)
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        theirs["active"] = [
            pokemon(677, 320, 1 - owner, 30, energies=(6,))
        ]
        theirs["bench"] = [
            pokemon(674, 321, 1 - owner, 140, energies=(6, 6, 6)),
            pokemon(676, 322, 1 - owner, 110),
        ]
        theirs["discard"] = [
            {
                "id": c4.PREMIUM_POWER_PRO,
                "playerIndex": 1 - owner,
                "serial": 860 + index,
            }
            for index in range(4)
        ]
        c2 = self.exact_run_away_trace(raw)
        trace = self.analyze(raw, [2], trace=c2)
        run = self.row(trace, c4.RUN_AWAY)
        conversion = run["metrics"]["conversion"]
        self.assertEqual(trace["continuity"], c4.RECHARGE_REQUIRED)
        self.assertNotEqual(run["certification"], "STRICT")
        self.assertFalse(conversion["safe_prize_exchange"])
        self.assertIsNone(conversion["distinct_backup_serial"])
        self.assertEqual(
            conversion["conversion"],
            "CURRENT_TARGET_KO_UNCERTIFIED_CONTINUITY",
        )

    def test_trading_child_rejects_unrelated_prompt_and_clears_pending(self):
        raw, _ = self.forced_raw(
            include_reusable=False, include_sacrifice=True
        )
        owner = raw["current"]["yourIndex"]
        source = pokemon(305, 203, owner, 70, energies=(5,))
        abra = pokemon(741, 200, owner, 50)
        backup = pokemon(
            743,
            299,
            owner,
            140,
            energies=(5,),
            pre_evolution=((741, 297), (742, 298)),
        )
        mine = raw["current"]["players"][owner]
        mine["active"] = [source]
        mine["bench"] = [abra, backup]
        c2 = self.certified_environment(raw)
        raw["select"].update(
            {
                "context": 0,
                "type": 0,
                "option": [{"attackId": 423, "type": 13}, {"type": 14}],
            }
        )
        state = c4.fresh_state()
        self.analyze(raw, [0], trace=c2, state=state)
        unrelated = self.trading_child(raw, source, abra, backup, owner)
        unrelated["logs"] = []
        unrelated["select"]["effect"] = None
        trace = self.analyze(unrelated, [0], trace=c2, state=state)
        self.assertNotEqual(trace["decision_point"], c4.TRADING_CHILD)
        self.assertIsNone(state["trading_pending"])

    def test_line_importance_is_structural_for_all_four_classes(self):
        exposed = pokemon(741, 200, 1, 50)
        unique = c4._line_from_c2(c2_trace(), exposed)
        self.assertEqual(unique["importance"], "UNIQUE")

        important_trace = c2_trace(
            importance="IMPORTANT", second_ready=True
        )
        important = c4._line_from_c2(important_trace, exposed)
        self.assertEqual(important["importance"], "IMPORTANT")

        redundant_trace = c2_trace(
            importance="REDUNDANT", second_ready=True
        )
        redundant_trace["line_importance_rows"][0][
            "after_removal_primary"
        ] = copy.deepcopy(
            redundant_trace["route_rows"][1]["primary_distance"]
        )
        redundant = c4._line_from_c2(redundant_trace, exposed)
        self.assertEqual(redundant["importance"], "REDUNDANT")

        unknown_trace = c2_trace(second_ready=True)
        unknown_trace["line_importance_rows"] = []
        unknown = c4._line_from_c2(unknown_trace, exposed)
        self.assertEqual(unknown["importance"], "UNKNOWN_IMPORTANCE")

        forged = c2_trace(importance="IMPORTANT", second_ready=True)
        forged["line_importance_rows"][0]["after_removal_primary"] = (
            copy.deepcopy(forged["route_rows"][0]["primary_distance"])
        )
        self.assertEqual(
            c4._line_from_c2(forged, exposed)["importance"],
            "UNKNOWN_IMPORTANCE",
        )

    def test_sacrifice_can_dominate_and_same_class_choice_is_deterministic(self):
        raw, action = self.forced_raw(
            include_reusable=False, include_sacrifice=True
        )
        owner = raw["current"]["yourIndex"]
        raw["current"]["players"][owner]["bench"].append(
            pokemon(305, 204, owner, 70, energies=(5,))
        )
        raw["select"]["option"].append(
            {
                "area": 5,
                "index": len(raw["select"]["option"]),
                "playerIndex": owner,
                "type": 3,
            }
        )
        trace = self.analyze(
            raw,
            action,
            trace=self.exact_delay_one_trading_environment(raw),
        )
        sacrifice = self.row(trace, c4.SACRIFICE)
        self.assertEqual(sacrifice["wall"]["serial"], 203)
        self.assertNotEqual(sacrifice["certification"], "STRICT")
        self.assertEqual(
            sacrifice["metrics"]["safe_release"]["reason"],
            "TRADING_ATTACK_BRANCH_FORCED_PROMOTION_UNCERTIFIED",
        )

        sacrifice = copy.deepcopy(sacrifice)
        sacrifice["certification"] = "STRICT"
        reusable = copy.deepcopy(sacrifice)
        reusable["kind"] = c4.REUSABLE
        reusable["pareto_vector"] = {
            key: value - 1
            for key, value in sacrifice["pareto_vector"].items()
        }
        selected, reason = c4.pareto_arbitrate(
            [
                self.row(trace, c4.RUN_AWAY),
                reusable,
                sacrifice,
                self.row(trace, c4.NO_WALL),
            ]
        )
        self.assertEqual(
            (selected, reason), (c4.SACRIFICE, "PARETO_DOMINANCE")
        )

    def test_self_damage_and_status_checkup_prevent_repeatable_ready(self):
        cases = (
            ("self_damage", 674, 50, (6, 6, 6), None),
            ("poison", 673, 10, (6,), "poisoned"),
            ("burn", 673, 20, (6,), "burned"),
        )
        for name, card_id, hp, energies, status in cases:
            with self.subTest(name=name):
                raw, action = self.forced_raw()
                c2 = self.certified_environment(raw)
                owner = raw["current"]["yourIndex"]
                theirs = raw["current"]["players"][1 - owner]
                theirs["active"] = [
                    pokemon(
                        card_id,
                        350,
                        1 - owner,
                        hp,
                        energies=energies,
                    )
                ]
                if status is not None:
                    theirs[status] = True
                theirs["discard"] = [
                    {
                        "id": c4.PREMIUM_POWER_PRO,
                        "playerIndex": 1 - owner,
                        "serial": 880 + index,
                    }
                    for index in range(4)
                ]
                trace = self.analyze(raw, action, trace=c2)
                self.assertEqual(
                    trace["threat"]["continuity"], c4.NO_READY_ATTACK
                )
                self.assertNotEqual(
                    self.row(trace, c4.REUSABLE)["certification"],
                    "STRICT",
                )

    def test_common_structure_rejects_before_trading_pending_is_saved(self):
        raw, _ = self.forced_raw(
            include_reusable=False, include_sacrifice=True
        )
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        source = pokemon(305, 203, owner, 70, energies=(5,))
        abra = pokemon(741, 200, owner, 50)
        backup = pokemon(
            743,
            299,
            owner,
            140,
            energies=(5,),
            pre_evolution=((741, 297), (742, 298)),
        )
        mine["active"] = [source]
        mine["bench"] = [abra, backup]
        c2 = self.certified_environment(raw)
        raw["select"].update(
            {
                "context": 0,
                "type": 0,
                "option": [
                    {"attackId": c4.TRADING_PLACES_ATTACK, "type": 13},
                    {"type": 14},
                ],
            }
        )
        state = c4.fresh_state()
        bench_max = mine.pop("benchMax")
        rejected = self.analyze(raw, [0], trace=c2, state=state)
        self.assertIn("OWN_BENCHMAX_INVALID", rejected["structural_reasons"])
        self.assertIsNone(state["trading_pending"])
        mine["benchMax"] = bench_max
        child = self.trading_child(raw, source, abra, backup, owner)
        carried = self.analyze(child, [0], trace=c2, state=state)
        self.assertNotEqual(carried["decision_point"], c4.TRADING_CHILD)
        self.assertIsNone(state["trading_pending"])

    def test_each_required_in_play_card_field_is_fail_closed(self):
        fields = (
            "tools",
            "preEvolution",
            "maxHp",
            "appearThisTurn",
            "energyCards",
            "energies",
        )
        for field in fields:
            with self.subTest(field=field):
                raw, action = self.forced_raw()
                c2 = self.certified_environment(raw)
                owner = raw["current"]["yourIndex"]
                reusable = next(
                    card
                    for card in raw["current"]["players"][owner]["bench"]
                    if card["serial"] == 201
                )
                reusable.pop(field)
                trace = self.analyze(raw, action, trace=c2)
                self.assertIsNone(trace["decision_point"])
                self.assertTrue(trace["structural_reasons"])
                self.assertFalse(
                    any(
                        row["certification"] == "STRICT"
                        for row in trace["candidate_rows"]
                    )
                )

    def test_common_structure_rejects_wrong_types_negatives_and_duplicates(self):
        def reusable_card(raw):
            owner = raw["current"]["yourIndex"]
            mine = raw["current"]["players"][owner]
            card = next(
                item
                for item in mine["bench"]
                if item["serial"] == 201
            )
            return owner, mine, card

        mutations = {
            "current_string": lambda raw, owner, mine, card: raw[
                "current"
            ].update(turn="4"),
            "owner_string": lambda raw, owner, mine, card: raw[
                "current"
            ].update(yourIndex=str(owner)),
            "negative_deck": lambda raw, owner, mine, card: mine.update(
                deckCount=-1
            ),
            "negative_hand": lambda raw, owner, mine, card: mine.update(
                handCount=-1
            ),
            "card_id_string": lambda raw, owner, mine, card: card.update(
                id=str(card["id"])
            ),
            "serial_float": lambda raw, owner, mine, card: card.update(
                serial=float(card["serial"])
            ),
            "owner_string_card": lambda raw, owner, mine, card: card.update(
                playerIndex=str(owner)
            ),
            "negative_hp": lambda raw, owner, mine, card: card.update(hp=-1),
            "max_hp_float": lambda raw, owner, mine, card: card.update(
                maxHp=float(card["maxHp"])
            ),
            "nested_serial_string": (
                lambda raw, owner, mine, card: card["preEvolution"][0].update(
                    serial=str(card["preEvolution"][0]["serial"])
                )
            ),
            "duplicate_in_play_serial": (
                lambda raw, owner, mine, card: next(
                    item for item in mine["bench"] if item is not card
                ).update(
                    serial=card["serial"]
                )
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                raw, action = self.forced_raw()
                c2 = self.certified_environment(raw)
                owner, mine, card = reusable_card(raw)
                mutation(raw, owner, mine, card)
                trace = self.analyze(raw, action, trace=c2)
                self.assertIsNone(trace["decision_point"])
                self.assertTrue(trace["structural_reasons"])
                self.assertFalse(
                    any(
                        row["certification"] == "STRICT"
                        for row in trace["candidate_rows"]
                    )
                )

    def test_run_away_parent_still_enumerates_exact_hold_alternative(self):
        raw = self.run_away_raw(target_hp=30, opponent_bench=True)
        self.supported_repeatable_run_target(raw)
        trace = self.analyze(
            raw, [2], trace=self.exact_run_away_trace(raw)
        )
        reusable = self.row(trace, c4.REUSABLE)
        self.assertEqual(reusable["legality"], "EXACT")
        self.assertEqual(reusable["option_index"], 3)
        self.assertEqual(
            reusable["semantic_action_key"]["type"], c4.END_TURN
        )
        self.assertNotEqual(reusable["certification"], "UNAVAILABLE")

    def test_complete_distance_tuple_detects_action_and_prompt_progress(self):
        before = c2_trace()["route_rows"][0]["primary_distance"]
        before["main_actions"] = 4
        before["forced_prompts"] = 3
        after = copy.deepcopy(before)
        after["main_actions"] = 1
        after["forced_prompts"] = 0
        self.assertLess(
            c4._distance_quality(after),
            c4._distance_quality(before),
        )
        for field in ("main_actions", "forced_prompts", "witness"):
            with self.subTest(field=field):
                incomplete = copy.deepcopy(before)
                incomplete.pop(field)
                self.assertIsNone(c4._distance_quality(incomplete))

        raw, action = self.forced_raw()
        incomplete_trace = self.certified_environment(raw)
        incomplete_trace["route_rows"][0]["primary_distance"].pop(
            "main_actions"
        )
        analyzed = self.analyze(raw, action, trace=incomplete_trace)
        self.assertFalse(
            any(
                row["certification"] == "STRICT"
                for row in analyzed["candidate_rows"]
            )
        )

    def test_projection_payloads_reconstruct_fingerprints_and_chosen_bypass(self):
        raw, action = self.forced_raw()
        trace = self.analyze(
            raw, action, trace=self.certified_environment(raw)
        )
        self.assertEqual(
            c4.fingerprint(trace["public_state_material"]),
            trace["public_state_fingerprint"],
        )
        self.assertEqual(
            c4.fingerprint(trace["expose_projection"]),
            trace["expose_state_fingerprint"],
        )
        self.assertEqual(
            c4.fingerprint(trace["wall_projection"]),
            trace["wall_state_fingerprint"],
        )
        chosen = trace["wall_projection"]["chosen"]
        self.assertIsInstance(chosen["public_board"], dict)
        self.assertIsInstance(chosen["resource_state"], dict)
        self.assertIsInstance(chosen["refusal_state"], dict)
        self.assertIsInstance(chosen["release_state"], dict)
        self.assertEqual(trace["bypass"], chosen["bypass"])

    def test_emergency_trace_keeps_full_frozen_schema(self):
        trace = c4.emergency_trace([0], RuntimeError("forced"))
        self.assertEqual(set(collector.TRACE_REQUIRED) - set(trace), set())
        self.assertEqual(
            [row["kind"] for row in trace["candidate_rows"]],
            list(c4.CANDIDATE_KINDS),
        )
        for row in trace["candidate_rows"]:
            self.assertEqual(set(collector.ROW_REQUIRED) - set(row), set())
        self.assertTrue(
            all(
                collector._row_schema_ok(
                    row, kind, trace["decision_point"]
                )
                for row, kind in zip(
                    trace["candidate_rows"], collector.CANDIDATE_KINDS
                )
            )
        )
        self.assertEqual(trace["rejection_codes"], ["METRIC_EXCEPTION"])

    def test_natural_run_away_outcome_persists_across_callbacks(self):
        before = self.run_away_raw(target_hp=30)
        self.supported_repeatable_run_target(before)
        state = c4.fresh_state()
        c2 = self.exact_run_away_trace(before)
        agreement = self.analyze(
            before, [2], trace=c2, state=state
        )
        self.assertEqual(agreement["outcome_status"], "PARENT_AGREEMENT")
        decision_id = agreement["decision_id"]

        after = json.loads(
            (
                FIXTURE_88843743 / "step_023_run_away_after.json"
            ).read_text(encoding="utf-8")
        )["observation"]
        released = self.analyze(after, [0], state=state)
        release_kinds = {
            event["event"]
            for event in released["outcome_events"]
            if event.get("decision_id") == decision_id
        }
        self.assertIn("RUN_AWAY_RELEASED", release_kinds)

        promoted = copy.deepcopy(after)
        owner = promoted["current"]["yourIndex"]
        mine = promoted["current"]["players"][owner]
        mine["active"] = [mine["bench"].pop(0)]
        promoted["select"].update(
            {
                "context": 0,
                "type": 0,
                "option": [{"type": 14}],
            }
        )
        destination = self.analyze(promoted, [0], state=state)
        outcome_kinds = {
            event["event"]
            for event in destination["outcome_events"]
            if event.get("decision_id") == decision_id
        }
        self.assertEqual(
            {
                "PARENT_AGREEMENT",
                "RUN_AWAY_RELEASED",
                "PROMOTION_DESTINATION",
            }
            - outcome_kinds,
            set(),
        )

    def test_forced_metric_exception_returns_exact_parent_object(self):
        raw, _ = self.forced_raw()
        original_parent = main._action_parent.agent
        original_trace = main._action_parent.LAST_STAGED_POLICY_TRACE
        original_analyze = main._c4_shadow.analyze
        original_rejection = main._c4_shadow.rejection_trace
        original_emergency = main._c4_shadow.emergency_trace

        def explode(*args, **kwargs):
            raise RuntimeError("forced")

        try:
            for failures in (
                ("analyze",),
                ("analyze", "rejection"),
                ("analyze", "rejection", "emergency"),
            ):
                with self.subTest(failures=failures):
                    action_object = [0]
                    main._action_parent.agent = (
                        lambda observation, action=action_object: action
                    )
                    main._action_parent.LAST_STAGED_POLICY_TRACE = c2_trace()
                    main._c4_shadow.analyze = (
                        explode
                        if "analyze" in failures
                        else original_analyze
                    )
                    main._c4_shadow.rejection_trace = (
                        explode
                        if "rejection" in failures
                        else original_rejection
                    )
                    main._c4_shadow.emergency_trace = (
                        explode
                        if "emergency" in failures
                        else original_emergency
                    )
                    returned = main.agent(raw)
                    self.assertIs(returned, action_object)
                    self.assertIs(
                        main.LAST_STAGED_POLICY_TRACE["applied_action"],
                        action_object,
                    )
                    self.assertEqual(
                        set(collector.TRACE_REQUIRED)
                        - set(main.LAST_STAGED_POLICY_TRACE),
                        set(),
                    )
                    self.assertEqual(
                        main.LAST_STAGED_POLICY_TRACE["rejection_codes"],
                        ["METRIC_EXCEPTION"],
                    )
                    self.assertNotEqual(
                        main.LAST_STAGED_POLICY_TRACE.get("outcome_status"),
                        "CANDIDATE_APPLIED",
                    )
        finally:
            main._action_parent.agent = original_parent
            main._action_parent.LAST_STAGED_POLICY_TRACE = original_trace
            main._c4_shadow.analyze = original_analyze
            main._c4_shadow.rejection_trace = original_rejection
            main._c4_shadow.emergency_trace = original_emergency


if __name__ == "__main__":
    unittest.main()
