from __future__ import annotations
import copy
import hashlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
import unittest
from unittest import mock

from cg.api import (
    AreaType,
    Card,
    EnergyType,
    Observation,
    Option,
    OptionType,
    PlayerState,
    Pokemon,
    SelectContext,
    SelectData,
    SelectType,
    State,
)
import _cumulative_parent as parent
import main
import planner_deck_adaptation_v1 as deck_v1
import planner_policy as core
import planner_public_survival_bench0 as survival
import planner_public_tactical_monotonicity as fix9
import planner_runtime_model as runtime_model

HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parents[1] / "fixtures" / "episode_88844273_public_observations" / "step_148_energized_kadabra_alakazam_in_hand_main.json"
CLEAN_PARENT = core.parent_state_snapshot(parent)

class PublicTacticalMonotonicityFix9Tests(unittest.TestCase):
    def setUp(self):
        core.restore_parent_state(parent, CLEAN_PARENT)
        core.reset_integrated_state(); deck_v1.reset(); survival.reset(); fix9.reset()
        self.base = json.loads(FIXTURE.read_text(encoding="utf-8"))["observation"]
        self.serial = 6000

    def tearDown(self):
        core.restore_parent_state(parent, CLEAN_PARENT)
        core.reset_integrated_state(); deck_v1.reset(); survival.reset(); fix9.reset()

    def pokemon(self, owner, card_id):
        hp = {741:60, 742:80, 743:140, 305:70, 66:140, 140:210}.get(card_id, 70)
        serial = self.serial; self.serial += 1
        return {"appearThisTurn":False, "energies":[], "energyCards":[], "hp":hp,
            "id":card_id, "maxHp":hp, "playerIndex":owner, "preEvolution":[],
            "serial":serial, "tools":[]}

    def set_roles(self, raw, a_count, n_count, free):
        owner = raw["current"]["yourIndex"]; mine = raw["current"]["players"][owner]
        bench_count = mine["benchMax"] - free
        roles = [741]*a_count + [305]*n_count
        active_id = roles.pop(0) if roles else 140
        mine["active"] = [self.pokemon(owner, active_id)]
        mine["bench"] = [self.pokemon(owner, cid) for cid in roles]
        while len(mine["bench"]) < bench_count: mine["bench"].append(self.pokemon(owner, 140))
        return raw

    def reconcile(self, raw):
        owner = raw["current"]["yourIndex"]; mine = raw["current"]["players"][owner]
        public = list(mine["hand"]) + list(mine["discard"])
        for pokemon in list(mine["active"]) + list(mine["bench"]):
            public.append(pokemon); public += list(pokemon["preEvolution"])+list(pokemon["energyCards"])+list(pokemon["tools"])
        hidden = sum(card is None for card in mine["prize"])
        public += [card for card in mine["prize"] if card is not None]
        public += [card for card in raw["current"]["stadium"] if card["playerIndex"] == owner]
        mine["deckCount"] = 60-len(public)-hidden
        return raw

    def main_raw(self, a_count=0, n_count=0, free=2):
        raw = self.set_roles(copy.deepcopy(self.base), a_count, n_count, free)
        owner=raw["current"]["yourIndex"]; mine=raw["current"]["players"][owner]
        mine["hand"][0] = {"id":1086,"serial":9000,"playerIndex":owner}
        raw["select"]={"type":0,"context":0,"minCount":1,"maxCount":1,
            "remainDamageCounter":0,"remainEnergyCost":0,"contextCard":None,"effect":None,"deck":None,
            "option":[{"type":7,"index":0},{"type":13,"attackId":1071},{"type":14}]}
        return self.reconcile(raw)

    def deplete_roles(self, raw):
        owner=raw["current"]["yourIndex"]; mine=raw["current"]["players"][owner]
        for card in list(mine["hand"])+list(mine["discard"]):
            if card["id"] in (741,305): card["id"]=1152
        targets=list(mine["discard"])
        for index, card in enumerate(targets[:7]): card["id"] = 741 if index < 4 else 305
        return self.reconcile(raw)

    def child_raw(self, a_count, n_count, free, cards, reorder=None):
        raw=self.set_roles(copy.deepcopy(self.base),a_count,n_count,free)
        owner=raw["current"]["yourIndex"]
        deck=[{"id":cid,"serial":9100+i,"playerIndex":owner} for i,cid in enumerate(cards)]
        options=[{"type":3,"area":1,"index":i,"playerIndex":owner} for i in range(len(deck))]
        if reorder is not None: options=[options[i] for i in reorder]
        raw["select"]={"type":1,"context":5,"minCount":0,"maxCount":2,
            "remainDamageCounter":0,"remainEnergyCost":0,"contextCard":None,
            "effect":{"id":1086,"serial":9000,"playerIndex":owner},"deck":deck,"option":options}
        return raw

    def boss_child_raw(self, targets, hand_count=12, own_prizes=6):
        own_active = Pokemon(
            743, 18000, 140, 140, False, [EnergyType.PSYCHIC],
            [Card(5, 18001, 0)], [], [Card(741, 18002, 0), Card(742, 18003, 0)],
        )
        own_hand = [Card(1152, 18100 + index, 0) for index in range(hand_count)]
        mine = PlayerState(
            [own_active], [], 5, 30, [], [None] * own_prizes, hand_count, own_hand,
            False, False, False, False, False,
        )
        theirs = PlayerState(
            [Pokemon(57, 18200, 100, 100, False, [], [], [], [])],
            targets, 5, 30, [], [None] * 6, 5, None,
            False, False, False, False, False,
        )
        state = State(6, 3, 0, 0, True, False, True, False, -1, [], None, [mine, theirs])
        options = [
            Option(OptionType.CARD, area=AreaType.BENCH, index=index, playerIndex=1)
            for index in range(len(targets))
        ]
        select = SelectData(
            SelectType.CARD, SelectContext.SWITCH, 1, 1, 0, 0,
            options, None, None, Card(1182, 18300, 0),
        )
        return json.loads(json.dumps(asdict(Observation(select, [], state))))

    def choose_poffin_then_attack(self, raw):
        owner=raw["current"]["yourIndex"]; hand=raw["current"]["players"][owner]["hand"]
        for i,opt in enumerate(raw["select"]["option"]):
            if opt.get("type")==7 and hand[opt["index"]]["id"]==1086: return [i]
        for i,opt in enumerate(raw["select"]["option"]):
            if opt.get("type")==13: return [i]
        return [0]

    def test_full_bench_defers_then_freed_slot_allows_again_and_depletion_never_returns_poffin(self):
        original=main._complete_survival_agent
        main._complete_survival_agent=self.choose_poffin_then_attack
        try:
            full=self.main_raw(a_count=0,n_count=0,free=0)
            self.assertEqual(main.agent(copy.deepcopy(full)),[1])
            self.assertEqual(main.LAST_STAGED_POLICY_TRACE["selected_rule"],"POFFIN_ONE_STEP_DEFER")
            freed=self.main_raw(a_count=0,n_count=0,free=2)
            self.assertEqual(main.agent(copy.deepcopy(freed)),[0])
            depleted=self.deplete_roles(self.main_raw(a_count=2,n_count=2,free=2))
            action=main.agent(copy.deepcopy(depleted))
            self.assertNotEqual(action,[0]); self.assertEqual(action,[1])
        finally: main._complete_survival_agent=original

    def test_full_bench_poffin_is_unchanged_when_delegate_arms_c3_transaction(self):
        original = main._complete_survival_agent
        sentinel_action = [0]
        sentinel_transaction = {"kind": "TEST_C3_TRANSACTION"}

        def armed_delegate(_raw):
            survival.C3_TRANSACTION = sentinel_transaction
            return sentinel_action

        main._complete_survival_agent = armed_delegate
        try:
            raw = self.main_raw(a_count=0, n_count=0, free=0)
            returned = main.agent(copy.deepcopy(raw))
            self.assertIs(returned, sentinel_action)
            self.assertIs(survival.C3_TRANSACTION, sentinel_transaction)
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["PARENT_TRANSACTION_IN_PROGRESS"],
            )
        finally:
            main._complete_survival_agent = original
            survival.C3_TRANSACTION = None

    def test_only_dead_poffin_fails_closed_without_exception(self):
        original = main._complete_survival_agent
        sentinel_action = [0]
        main._complete_survival_agent = lambda _raw: sentinel_action
        try:
            raw = self.main_raw(a_count=0, n_count=0, free=0)
            raw["select"]["option"] = [raw["select"]["option"][0]]
            returned = main.agent(copy.deepcopy(raw))
            self.assertIs(returned, sentinel_action)
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["selected_rule"],
                "POFFIN_DEFER_UNRESOLVED",
            )
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["NO_LEGAL_NON_POFFIN_ACTION_FAIL_CLOSED"],
            )
        finally:
            main._complete_survival_agent = original
    def test_unique_important_abra_demand_is_preserved(self):
        raw=self.main_raw(a_count=1,n_count=1,free=2); obs=parent.to_observation_class(raw)
        trace={"line_importance_rows":[{"importance":"UNIQUE"}]}
        decision=fix9._poffin_defer(parent,obs,raw,[0],trace,fix9._rows(parent,obs))
        self.assertIsNone(decision)

    def selected_ids(self, raw, action):
        return [raw["select"]["deck"][raw["select"]["option"][i]["index"]]["id"] for i in action]

    def test_poffin_child_exercises_zero_one_two_final_slot_and_no_third_dunsparce(self):
        cases=[
            (self.child_raw(2,2,2,[741,305,305]),[],[]),
            (self.child_raw(0,1,1,[305,741]),[1],[741]),
            (self.child_raw(0,0,2,[305,741]),None,[741,305]),
            (self.child_raw(2,1,2,[305,305,305]),None,[305]),
        ]
        trace={"line_importance_rows":[{"importance":"UNIQUE"}]}
        for raw, exact, ids in cases:
            obs=parent.to_observation_class(raw); result=fix9._poffin_child(parent,obs,raw,[],trace)
            self.assertIsNotNone(result); action,details=result
            if exact is not None: self.assertEqual(action,exact)
            self.assertEqual(self.selected_ids(raw,action),ids)
            self.assertEqual(details["selected_cardinality"],len(ids))
        original=self.child_raw(0,0,2,[305,741,305],reorder=[2,0,1])
        result=fix9._poffin_child(parent,parent.to_observation_class(original),original,[],trace)
        self.assertEqual(set(self.selected_ids(original,result[0])),{741,305})

    def test_poffin_child_final_slot_returns_empty_without_abra(self):
        raw = self.child_raw(0, 0, 1, [305, 305])
        trace = {"line_importance_rows": [{"importance": "REDUNDANT"}]}
        result = fix9._poffin_child(
            parent, parent.to_observation_class(raw), raw, [0], trace,
        )
        self.assertIsNotNone(result)
        action, details = result
        self.assertEqual(action, [])
        self.assertTrue(details["final_slot_abra_only"])
        self.assertEqual(details["selected_cardinality"], 0)

    def test_direct_final_slot_dunsparce_is_reranked_to_abra_by_stable_key(self):
        raw = self.main_raw(a_count=0, n_count=0, free=1)
        owner = raw["current"]["yourIndex"]
        hand = raw["current"]["players"][owner]["hand"]
        hand[0] = {"id": 305, "serial": 22000, "playerIndex": owner}
        hand[1] = {"id": 741, "serial": 22001, "playerIndex": owner}
        raw["select"]["option"] = [
            {"type": 7, "index": 0},
            {"type": 7, "index": 1},
            {"type": 14},
        ]
        raw = self.reconcile(raw)

        def choose_dunsparce_then_abra(candidate_raw):
            candidate_owner = candidate_raw["current"]["yourIndex"]
            candidate_hand = candidate_raw["current"]["players"][candidate_owner]["hand"]
            for wanted in (305, 741):
                for index, option in enumerate(candidate_raw["select"]["option"]):
                    if option.get("type") == 7 and candidate_hand[option["index"]]["id"] == wanted:
                        return [index]
            return [len(candidate_raw["select"]["option"]) - 1]

        original = main._complete_survival_agent
        main._complete_survival_agent = choose_dunsparce_then_abra
        try:
            self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
            self.assertEqual(main.LAST_STAGED_POLICY_TRACE["selected_rule"], "FINAL_SLOT_PROTECTION")
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["FINAL_SLOT_DENIES_FIRST_ALAKAZAM_LINE"],
            )
            self.assertEqual(main.LAST_STAGED_POLICY_TRACE["rerank_attempts"][0]["candidate"], [1])
        finally:
            main._complete_survival_agent = original

    def test_hand15_exact_ko_blocks_spend_and_end_hand16_allows_one_loss_only(self):
        raw=self.main_raw(); raw["select"]["option"]=[{"type":7,"index":0},{"type":13,"attackId":1072},{"type":14}]
        obs=parent.to_observation_class(raw); cert={"attack_index":1}
        with mock.patch.object(deck_v1,"_powerful_hand_ko",side_effect=lambda _p,_o,h:h>=15):
            obs.current.players[obs.current.yourIndex].handCount=15
            self.assertEqual(fix9._ko_harm(parent,obs,[0],cert),"ACTION_CROSSES_EXACT_KO_HAND_FLOOR")
            self.assertEqual(fix9._ko_harm(parent,obs,[2],cert),"END_BEFORE_EXACT_KO")
            self.assertIsNone(fix9._ko_harm(parent,obs,[1],cert))
            obs.current.players[obs.current.yourIndex].handCount=16
            self.assertIsNone(fix9._ko_harm(parent,obs,[0],cert))
            obs.current.players[obs.current.yourIndex].handCount=15
            self.assertIsNotNone(fix9._ko_harm(parent,obs,[0],cert))

    def test_rare_candy_uses_two_card_exact_ko_hand_cost(self):
        raw = self.main_raw()
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        mine["hand"] = [
            {"id": 1079, "serial": 19000, "playerIndex": owner},
            {"id": 743, "serial": 19001, "playerIndex": owner},
            *(
                {"id": 1152, "serial": 19002 + index, "playerIndex": owner}
                for index in range(14)
            ),
        ]
        mine["handCount"] = 16
        raw["select"]["option"] = [
            {"type": 7, "index": 0},
            {"type": 13, "attackId": 1072},
            {"type": 14},
        ]
        raw = self.reconcile(raw)
        obs = parent.to_observation_class(raw)
        self.assertTrue(fix9._rare_candy_cost_is_exact(parent, obs, obs.select.option[0]))
        with mock.patch.object(deck_v1, "_powerful_hand_ko", side_effect=lambda _p, _o, h: h >= 15):
            self.assertEqual(
                fix9._ko_harm(parent, obs, [0], {"attack_index": 1}),
                "ACTION_CROSSES_EXACT_KO_HAND_FLOOR",
            )

    def test_boss_target_child_rebinds_repelling_veil_target_to_damageable_target(self):
        own_active = Pokemon(
            743,
            8000,
            140,
            140,
            False,
            [EnergyType.PSYCHIC],
            [Card(5, 8001, 0)],
            [],
            [Card(741, 8002, 0), Card(742, 8003, 0)],
        )
        own_hand = [Card(1152, 8100 + index, 0) for index in range(12)]
        mine = PlayerState(
            [own_active],
            [],
            5,
            30,
            [],
            [None] * 6,
            len(own_hand),
            own_hand,
            False,
            False,
            False,
            False,
            False,
        )
        articuno = Pokemon(414, 8200, 120, 120, False, [], [], [], [])
        protected = Pokemon(431, 8201, 100, 280, False, [], [], [], [])
        damageable = Pokemon(140, 8202, 100, 210, False, [], [], [], [])
        theirs = PlayerState(
            [articuno],
            [protected, damageable],
            5,
            30,
            [],
            [None] * 6,
            5,
            None,
            False,
            False,
            False,
            False,
            False,
        )
        state = State(
            6,
            3,
            0,
            0,
            True,
            False,
            True,
            False,
            -1,
            [],
            None,
            [mine, theirs],
        )
        select = SelectData(
            SelectType.CARD,
            SelectContext.SWITCH,
            1,
            1,
            0,
            0,
            [
                Option(
                    OptionType.CARD,
                    area=AreaType.BENCH,
                    index=0,
                    playerIndex=1,
                ),
                Option(
                    OptionType.CARD,
                    area=AreaType.BENCH,
                    index=1,
                    playerIndex=1,
                ),
            ],
            None,
            None,
            Card(1182, 8300, 0),
        )
        raw = json.loads(
            json.dumps(asdict(Observation(select, [], state)))
        )
        parsed = parent.to_observation_class(copy.deepcopy(raw))
        self.assertTrue(runtime_model.raw_parsed_agree(raw, parsed))
        all_serials = [
            8000,
            8001,
            8002,
            8003,
            *(8100 + index for index in range(12)),
            8200,
            8201,
            8202,
            8300,
        ]
        self.assertEqual(len(all_serials), len(set(all_serials)))
        self.assertIsNone(core.INTEGRATED_TRANSACTION)
        self.assertIsNone(deck_v1.V1_TRANSACTION)
        self.assertIsNone(survival.C3_TRANSACTION)

        original = main._complete_survival_agent
        sentinel_action = [0]
        main._complete_survival_agent = lambda _raw: sentinel_action
        try:
            self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["selected_rule"],
                "EFFECTIVE_TARGET_SAFETY",
            )
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["TARGET_CHILD_REJECT_KNOWN_ZERO"],
            )
            targets = main.LAST_STAGED_POLICY_TRACE["effective_targets"]
            self.assertEqual(targets[0]["effective"], "KNOWN_ZERO_REPELLING_VEIL")
            self.assertEqual(targets[1]["effective"], "DAMAGEABLE")
        finally:
            main._complete_survival_agent = original
    def test_boss_child_prefers_terminal_then_higher_prize_ko_without_positive_tie_override(self):
        one_prize = Pokemon(305, 20000, 70, 70, False, [], [], [], [])
        two_prize = Pokemon(140, 20001, 100, 210, False, [], [], [], [])
        raw = self.boss_child_raw([one_prize, two_prize])
        parsed = parent.to_observation_class(copy.deepcopy(raw))
        self.assertTrue(runtime_model.raw_parsed_agree(raw, parsed))
        self.assertTrue(fix9._boss_child_envelope(parent, parsed))

        original = main._complete_survival_agent
        main._complete_survival_agent = lambda _raw: [0]
        try:
            self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["TARGET_CHILD_SELECT_HIGHER_PRIZE_KO"],
            )
            targets = main.LAST_STAGED_POLICY_TRACE["effective_targets"]
            self.assertEqual([(row["ko"], row["prizes"]) for row in targets], [(True, 1), (True, 2)])

            terminal_raw = self.boss_child_raw(
                [
                    Pokemon(305, 20100, 70, 70, False, [], [], [], []),
                    Pokemon(140, 20101, 100, 210, False, [], [], [], []),
                ],
                own_prizes=2,
            )
            self.assertEqual(main.agent(copy.deepcopy(terminal_raw)), [1])
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["TARGET_CHILD_SELECT_TERMINAL"],
            )
        finally:
            main._complete_survival_agent = original

        tied_raw = self.boss_child_raw([
            Pokemon(305, 20200, 70, 70, False, [], [], [], []),
            Pokemon(305, 20201, 60, 70, False, [], [], [], []),
        ])
        tied = parent.to_observation_class(tied_raw)
        self.assertIsNone(fix9._boss_child(parent, tied, [0]))

        malformed = copy.deepcopy(raw)
        malformed["select"]["maxCount"] = 2
        malformed_obs = parent.to_observation_class(malformed)
        self.assertFalse(fix9._boss_child_envelope(parent, malformed_obs))
        self.assertIsNone(fix9._boss_child(parent, malformed_obs, [0]))

    def test_boss_child_same_prize_ko_dominates_positive_survivor(self):
        raw = self.boss_child_raw([
            Pokemon(431, 20300, 280, 280, False, [], [], [], []),
            Pokemon(431, 20301, 200, 280, False, [], [], [], []),
        ])
        parsed = parent.to_observation_class(copy.deepcopy(raw))
        self.assertTrue(runtime_model.raw_parsed_agree(raw, parsed))
        original = main._complete_survival_agent
        main._complete_survival_agent = lambda _raw: [0]
        try:
            self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["TARGET_CHILD_SELECT_KO_DOMINANCE"],
            )
            targets = main.LAST_STAGED_POLICY_TRACE["effective_targets"]
            self.assertEqual(
                [(row["damage"], row["ko"], row["prizes"]) for row in targets],
                [(240, False, 2), (240, True, 2)],
            )
        finally:
            main._complete_survival_agent = original

        lower_prize_ko = self.boss_child_raw([
            Pokemon(431, 20400, 280, 280, False, [], [], [], []),
            Pokemon(305, 20401, 70, 70, False, [], [], [], []),
        ])
        lower_obs = parent.to_observation_class(lower_prize_ko)
        self.assertIsNone(fix9._boss_child(parent, lower_obs, [0]))

    def test_mist_and_matching_rock_are_known_zero_but_wrong_type_rock_is_damageable(self):
        mist = Pokemon(
            305, 21000, 70, 70, False, [EnergyType.COLORLESS],
            [Card(11, 21001, 1)], [], [],
        )
        clear = Pokemon(305, 21002, 70, 70, False, [], [], [], [])
        raw = self.boss_child_raw([mist, clear])
        original = main._complete_survival_agent
        main._complete_survival_agent = lambda _raw: [0]
        try:
            self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["reason_tags"],
                ["TARGET_CHILD_REJECT_KNOWN_ZERO"],
            )
            targets = main.LAST_STAGED_POLICY_TRACE["effective_targets"]
            self.assertEqual(targets[0]["effective"], "KNOWN_ZERO_MIST_ENERGY")
            self.assertEqual(targets[1]["effective"], "DAMAGEABLE")
        finally:
            main._complete_survival_agent = original

        rock_raw = self.boss_child_raw([
            Pokemon(
                22, 21100, 90, 90, False, [EnergyType.FIGHTING],
                [Card(20, 21101, 1)], [], [],
            ),
            Pokemon(
                140, 21102, 210, 210, False, [EnergyType.FIGHTING],
                [Card(20, 21103, 1)], [], [],
            ),
        ])
        rock_obs = parent.to_observation_class(rock_raw)
        opponent = rock_obs.current.players[1]
        matching = fix9._projection(parent, rock_obs, opponent.bench[0], 1, 12)
        wrong_type = fix9._projection(parent, rock_obs, opponent.bench[1], 1, 12)
        self.assertEqual(matching["effective"], "KNOWN_ZERO_ROCK_FIGHTING_ENERGY")
        self.assertEqual(matching["damage"], 0)
        self.assertEqual(wrong_type["effective"], "DAMAGEABLE")
        self.assertEqual(wrong_type["damage"], 240)

    def test_certified_higher_prize_boss_nonfire_and_repelling_zero_rejected(self):
        current={"damage":300,"ko":True,"prizes":1}
        higher={"damage":300,"ko":True,"prizes":2,"terminal":False}
        with mock.patch.object(fix9,"_current_projection",return_value=current), mock.patch.object(fix9,"_boss_targets",return_value=[higher]):
            allowed,_,reason=fix9._boss_admissible(parent,object())
            self.assertTrue(allowed); self.assertEqual(reason,"CERTIFIED_HIGHER_PRIZE_BOSS_KO")
        for effective in (
            "KNOWN_ZERO_REPELLING_VEIL",
            "KNOWN_ZERO_MIST_ENERGY",
            "KNOWN_ZERO_ROCK_FIGHTING_ENERGY",
        ):
            zero={"damage":0,"ko":False,"prizes":1,"terminal":False,"effective":effective}
            with mock.patch.object(fix9,"_current_projection",return_value={"damage":200,"ko":False,"prizes":1}), mock.patch.object(fix9,"_boss_targets",return_value=[zero]):
                allowed,_,reason=fix9._boss_admissible(parent,object())
                self.assertFalse(allowed); self.assertEqual(reason,"BOSS_REPLACES_POSITIVE_WITH_KNOWN_ZERO")
        self.assertFalse(fix9._is_known_zero({"effective": "UNKNOWN"}))
        safe={"damage":200,"ko":False,"prizes":1,"terminal":False,"effective":"DAMAGEABLE"}
        with mock.patch.object(fix9,"_current_projection",return_value={"damage":200,"ko":False,"prizes":1}), mock.patch.object(fix9,"_boss_targets",return_value=[safe]):
            allowed,_,reason=fix9._boss_admissible(parent,object())
            self.assertTrue(allowed); self.assertIsNone(reason)

    def alakazam_raw(self, energy_id):
        raw=self.main_raw(); owner=raw["current"]["yourIndex"]; mine=raw["current"]["players"][owner]
        active=self.pokemon(owner,743); active["preEvolution"]=[{"id":741,"serial":9701,"playerIndex":owner},{"id":742,"serial":9702,"playerIndex":owner}]
        active["energyCards"]=[{"id":energy_id,"serial":9703,"playerIndex":owner}]; active["energies"]=[5 if energy_id in (5,19) else 6]
        mine["active"]=[active]; mine["bench"]=[]; mine["benchMax"]=5
        return self.reconcile(raw)

    def test_closure_is_stable_across_source_and_packaged_logical_files(self):
        runtime_payload = (HERE / "runtime" / "main.py").read_bytes()
        self.assertEqual(len(runtime_payload), fix9._RUNTIME_MAIN_SIZE)
        self.assertEqual(
            hashlib.sha256(runtime_payload).hexdigest().upper(),
            fix9._RUNTIME_MAIN_SHA256,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            packaged = root / "packaged"
            (source / "runtime").mkdir(parents=True)
            packaged.mkdir()
            policy_payload = b"exact-policy-main\n"
            shared_payload = b"shared-module\n"
            deck_payload = b"741\n" * 60
            (source / "main.py").write_bytes(policy_payload)
            (source / "planner_shared.py").write_bytes(shared_payload)
            (source / "runtime" / "main.py").write_bytes(runtime_payload)
            (source / "deck.csv").write_bytes(deck_payload)
            (packaged / "main.py").write_bytes(b"package-wrapper\n")
            (packaged / "_policy_main.py").write_bytes(policy_payload)
            (packaged / "planner_shared.py").write_bytes(shared_payload)
            (packaged / "deck.csv").write_bytes(deck_payload)

            with mock.patch.object(fix9, "__file__", str(source / "planner_fix9.py")):
                source_closure = fix9._closure()
            with mock.patch.object(fix9, "__file__", str(packaged / "planner_fix9.py")):
                packaged_closure = fix9._closure()
            self.assertIsNotNone(source_closure)
            self.assertEqual(packaged_closure, source_closure)

            (packaged / "main.py").write_bytes(b"different-wrapper\n")
            with mock.patch.object(fix9, "__file__", str(packaged / "planner_fix9.py")):
                self.assertEqual(fix9._closure(), source_closure)
            (packaged / "_policy_main.py").write_bytes(b"different-policy\n")
            with mock.patch.object(fix9, "__file__", str(packaged / "planner_fix9.py")):
                self.assertNotEqual(fix9._closure(), source_closure)

            (source / "runtime" / "main.py").write_bytes(b"invalid-runtime\n")
            with mock.patch.object(fix9, "__file__", str(source / "planner_fix9.py")):
                self.assertIsNone(fix9._closure())

    def test_wrong_energy_readiness_nonfire_nonko_stays_parent_and_no_persistent_state(self):
        psychic=parent.to_observation_class(self.alakazam_raw(5)); wrong=parent.to_observation_class(self.alakazam_raw(6))
        self.assertTrue(fix9._ready(parent,psychic)); self.assertFalse(fix9._ready(parent,wrong))
        raw=self.main_raw(); obs=parent.to_observation_class(raw)
        with mock.patch.object(deck_v1,"_attack_index",return_value=1), mock.patch.object(deck_v1,"_powerful_hand_ko",return_value=False):
            self.assertIsNone(fix9._ko_certificate(parent,obs))
        source=Path(fix9.__file__).read_text(encoding="utf-8")
        self.assertNotIn("PERSISTENT_"+"HOLD",source); self.assertNotIn("POFFIN_ZERO_DEMAND_LATCH",source)

if __name__ == "__main__": unittest.main()

