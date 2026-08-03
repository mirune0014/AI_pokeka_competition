from __future__ import annotations
from dataclasses import asdict
import copy
import json
import unittest

from cg.api import (AreaType, Card, EnergyType, Observation, Option, OptionType,
                    PlayerState, Pokemon, SelectContext, SelectData, SelectType, State)

import _cumulative_parent as policy
import planner_deck_adaptation_v1 as v1
import planner_h1_continuity_v2 as v2
import planner_h1_continuity_v2_model as cert
import planner_policy as core
import planner_runtime_model as runtime
import main as entrypoint


class V2ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.parent=core.parent_state_snapshot(policy)
        self.core_tx=core.INTEGRATED_TRANSACTION
        self.core_dup=copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE)
        self.core_latest=core.INTEGRATED_LATEST_TRACE
        core.INTEGRATED_TRANSACTION=None;core.INTEGRATED_DUPLICATE_CACHE.clear()
        v1.reset();v2.reset();v1.LAST_V1_PACKAGE_TRACE={"selected_rule":None,"reason_tags":[]};self.serial=200
    def tearDown(self):
        core.restore_parent_state(policy,self.parent)
        core.INTEGRATED_TRANSACTION=self.core_tx
        core.INTEGRATED_DUPLICATE_CACHE.clear();core.INTEGRATED_DUPLICATE_CACHE.update(self.core_dup)
        core.INTEGRATED_LATEST_TRACE=self.core_latest
        v1.reset();v2.reset()
    def card(self,card_id,owner=0,serial=None):
        if serial is None:self.serial+=1;serial=self.serial
        return Card(card_id,serial,owner)
    def abra(self,serial=40,appear=False,energy=False):
        cards=[self.card(5,0,serial+1)] if energy else []
        return Pokemon(741,serial,60,60,appear,[EnergyType.PSYCHIC]*len(cards),cards,[],[])
    def kadabra(self,serial=30,appear=False,energy=True):
        cards=[self.card(5,0,serial+1)] if energy else []
        return Pokemon(742,serial,80,80,appear,[EnergyType.PSYCHIC]*len(cards),cards,[],[self.card(741,0,serial+2)])
    def alakazam(self,serial=10,energy=True):
        cards=[self.card(5,0,serial+1)] if energy else []
        return Pokemon(743,serial,140,140,False,[EnergyType.PSYCHIC]*len(cards),cards,[],
                       [self.card(741,0,serial+2),self.card(742,0,serial+3)])
    def target(self,hp=100,serial=90):
        return Pokemon(140,serial,hp,210,False,[],[],[],[])
    def player(self,active,bench=(),hand=(),discard=(),prizes=5,deck=30):
        count=5 if hand is None else len(hand)
        result=PlayerState(list(active),list(bench),5,deck,list(discard),[],count,
                           None if hand is None else list(hand),False,False,False,False,False)
        result.prize=[None]*prizes
        return result
    def obs(self,*,active=None,bench=(),hand_ids=(),hand_cards=None,target_hp=100,
            opponent_bench=1,options=(),prizes=5,discard=(),deck=30):
        active=active or self.alakazam()
        hand=list(hand_cards) if hand_cards is not None else [self.card(i) for i in hand_ids]
        mine=self.player([active],bench,hand,discard,prizes,deck)
        their_bench=[Pokemon(305,100+i,60,60,False,[],[],[],[]) for i in range(opponent_bench)]
        theirs=self.player([self.target(target_hp)],their_bench,None,(),5,30)
        state=State(4,2,0,0,False,False,False,False,-1,[],None,[mine,theirs])
        opts=[]
        for row in options:
            kind=row[0]
            if kind=='play':
                index=next(i for i,c in enumerate(hand) if c.id==row[1] and (len(row)<3 or c.serial==row[2]))
                opts.append(Option(OptionType.PLAY,index=index))
            elif kind=='attack':opts.append(Option(OptionType.ATTACK,attackId=1072))
            elif kind=='end':opts.append(Option(OptionType.END))
            elif kind=='evolve_active':
                index=next(i for i,c in enumerate(hand) if c.serial==row[1])
                opts.append(Option(OptionType.EVOLVE,area=AreaType.HAND,index=index,inPlayArea=AreaType.ACTIVE,inPlayIndex=0))
            elif kind=='evolve_bench':
                index=next(i for i,c in enumerate(hand) if c.serial==row[1])
                opts.append(Option(OptionType.EVOLVE,area=AreaType.HAND,index=index,inPlayArea=AreaType.BENCH,inPlayIndex=row[2]))
            elif kind=='attach_bench':
                index=next(i for i,c in enumerate(hand) if c.serial==row[1])
                opts.append(Option(OptionType.ATTACH,area=AreaType.HAND,index=index,inPlayArea=AreaType.BENCH,inPlayIndex=row[2]))
        select=SelectData(SelectType.MAIN,SelectContext.MAIN,1,1,0,0,opts,None,None,None)
        return Observation(select,[],state),hand
    def raw(self,obs):return json.loads(json.dumps(asdict(obs)))
    def wrapper(self,obs,baseline):
        calls=[]
        action=v2.agent(policy,lambda raw:calls.append(raw) or baseline,self.raw(obs))
        return action,calls

    def test_resource_interval_formula_and_enriching_excluded(self):
        obs,_=self.obs(hand_ids=[741,1079,743,5,19,13],options=(('end',),))
        intervals=cert.resource_intervals(obs)
        self.assertEqual(set(intervals),{741,742,743,1079,5,19})
        for card_id,total in cert.TOTALS.items():
            row=intervals[card_id];self.assertEqual(row['U'],total-row['V'])
            self.assertEqual(row['deck_lb'],max(0,row['U']-row['P']))
            self.assertEqual(row['prize_ub'],min(row['U'],row['P']))

    def test_hfloor_boundary_blocks_and_plus_one_preps(self):
        for extra,expected in ((0,[1]),(1,[0])):
            v2.reset();v1.reset()
            ids=[741,1079,743,5,1152]+[1152]*extra
            obs,_=self.obs(hand_ids=ids,options=(('play',741),('attack',),('end',)))
            action,calls=self.wrapper(obs,[1])
            self.assertEqual(action,expected);self.assertEqual(len(calls),1)
            if extra:
                self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_H1_PREP_ABRA'])
                self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['Hfinal'],5)
            else:
                self.assertIn('V2_H0_FLOOR_BLOCK',v2.LAST_V2_CONTINUITY_TRACE['reason_tags'])

    def test_terminal_board_out_is_identical(self):
        obs,_=self.obs(hand_ids=[741,1079,743,5,1152,1152],opponent_bench=0,
                       options=(('play',741),('attack',),('end',)))
        before=core.parent_state_snapshot(policy)
        action,calls=self.wrapper(obs,[1])
        self.assertEqual(action,[1]);self.assertEqual(len(calls),1)
        self.assertEqual(core.parent_state_snapshot(policy),before)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_TERMINAL_KO_PRECEDENCE'])
        self.assertIsNone(v2.V2_TRANSACTION)

    def test_xerosic_prefix_deferred_exactly(self):
        obs,_=self.obs(hand_ids=[1197,1152,1152,1152,1152,1152],target_hp=100,
                       options=(('play',1197),('attack',),('end',)))
        raw=self.raw(obs);calls=[]
        action=v2.agent(policy,lambda value:calls.append(value) or v1.agent(policy,lambda _: [2],value),raw)
        self.assertEqual(action,[0]);self.assertEqual(len(calls),1)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'],v1.RULE_XEROSIC)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_DEFER_V1_XEROSIC'])
        self.assertEqual(v1.V1_TRANSACTION['stage'],'await_xerosic_verify')

    def test_boss_terminal_prefix_deferred_exactly(self):
        obs,hand=self.obs(hand_ids=[1182,1152,1152,1152,1152,1152],target_hp=200,
                          opponent_bench=0,options=(('play',1182),('attack',),('end',)),prizes=1)
        obs.current.players[1].bench=[Pokemon(140,91,100,210,False,[],[],[],[])]
        raw=self.raw(obs);calls=[]
        action=v2.agent(policy,lambda value:calls.append(value) or v1.agent(policy,lambda _: [2],value),raw)
        self.assertEqual(action,[0]);self.assertEqual(len(calls),1)
        self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'],v1.RULE_BOSS)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_TERMINAL_KO_PRECEDENCE'])

    def test_unsafe_active_743_blocked_by_distinct_bench_prep(self):
        active=self.kadabra(30,False,True)
        future=self.card(743,0,900);basic=self.card(741,0,901);candy=self.card(1079,0,902)
        extra_ala=self.card(743,0,800);energy=self.card(5,0,903);filler=self.card(1152,0,904)
        obs,_=self.obs(active=active,hand_cards=[future,basic,candy,extra_ala,energy,filler],target_hp=120,
                       options=(('evolve_active',900),('play',741,901),('end',)))
        raw=self.raw(obs);calls=[]
        action=v2.agent(policy,lambda value:calls.append(value) or v1.agent(policy,lambda _: [2],value),raw)
        self.assertEqual(action,[1]);self.assertEqual(len(calls),1)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['selected_rule'],cert.RULE)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],
                         ['V2_UNSAFE_ACTIVE_743_BLOCKED','V2_H1_PREP_ABRA'])
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertEqual(v2.V2_TRANSACTION['mode'],'UNSAFE_ACTIVE_743')
        self.assertNotIn(900,v2.V2_TRANSACTION['candidate']['h1_serials'])

    def test_unsafe_active_ready_certificate_falls_back_v1(self):
        active=self.kadabra(30,False,True);future=self.card(743,0,900)
        ready=self.alakazam(50,True)
        obs,_=self.obs(active=active,bench=[ready],hand_cards=[future,self.card(1152),self.card(1152),self.card(1152)],
                       target_hp=120,options=(('evolve_active',900),('end',)))
        raw=self.raw(obs)
        action=v2.agent(policy,lambda value:v1.agent(policy,lambda _:[1],value),raw)
        self.assertEqual(action,[0]);self.assertEqual(v1.LAST_V1_PACKAGE_TRACE['selected_rule'],v1.RULE_ALAKAZAM)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_BASELINE_FALLBACK'])

    def test_bench_evolve_and_psychic_prep_candidates(self):
        active=self.alakazam();bench_k=self.kadabra(50,False,False)
        ala=self.card(743,0,801);energy=self.card(5,0,802)
        obs,_=self.obs(active=active,bench=[bench_k],hand_cards=[ala,energy]+[self.card(1152) for _ in range(5)],
                       target_hp=100,options=(('evolve_bench',801,0),('attach_bench',802,0),('attack',),('end',)))
        rows=cert.prep_candidates(policy,obs,active.serial,5)
        self.assertTrue(any(r['reason']=='V2_H1_PREP_EVOLVE' for r in rows))
        self.assertTrue(any(r['reason']=='V2_H1_PREP_PSYCHIC' for r in rows))
        for _ in range(3):
            again=cert.prep_candidates(policy,obs,active.serial,5)
            self.assertEqual([(r['action'],r['h1_serials'],r['Hfinal']) for r in rows],
                             [(r['action'],r['h1_serials'],r['Hfinal']) for r in again])

    def test_recovery_stretcher_lana_hilda_and_blocks(self):
        active=self.kadabra(30,False,True);discard_ala=self.card(743,0,700)
        obs,_=self.obs(active=active,hand_ids=[1097,1152,1152,1152],discard=[discard_ala],target_hp=80,
                       options=(('play',1097),('end',)),prizes=1)
        row,block=cert.recovery_candidate(policy,obs,4)
        self.assertEqual(row['reason'],'V2_H1_RECOVER_STRETCHER');self.assertIsNone(block)
        active2=self.kadabra(40,False,False);ala=self.card(743,0,710);psy=self.card(5,0,711)
        obs,_=self.obs(active=active2,hand_ids=[1184,1152,1152],discard=[ala,psy],target_hp=80,
                       options=(('play',1184),('end',)),prizes=1)
        row,_=cert.recovery_candidate(policy,obs,4)
        self.assertEqual(row['reason'],'V2_H1_RECOVER_LANA');self.assertEqual(len(row['wanted_rows']),2)
        active3=self.kadabra(50,False,False)
        obs,_=self.obs(active=active3,hand_ids=[1225,1152,1152],target_hp=80,
                       options=(('play',1225),('end',)),prizes=1,deck=30)
        row,_=cert.recovery_candidate(policy,obs,4)
        self.assertEqual(row['reason'],'V2_H1_RECOVER_HILDA')
        obs.current.players[0].deckCount=3
        row,block=cert.recovery_candidate(policy,obs,4)
        self.assertIsNone(row);self.assertEqual(block,'V2_H1_DECK_CLOCK_BLOCK')
        obs,_=self.obs(active=active3,hand_ids=[1225,1152,1152],target_hp=80,
                       options=(('play',1225),('end',)),prizes=6,deck=30)
        row,block=cert.recovery_candidate(policy,obs,4)
        self.assertIsNone(row);self.assertEqual(block,'V2_H1_RESOURCE_INTERVAL_UNPROVEN')

    def test_option_reorder_duplicate_rebind_calls_delegate_once(self):
        obs,_=self.obs(hand_ids=[741,1079,743,5,1152,1152],options=(('play',741),('attack',),('end',)))
        raw=self.raw(obs);calls=[]
        first=v2.agent(policy,lambda value:calls.append(value) or [1],raw)
        self.assertEqual(first,[0]);self.assertEqual(len(calls),1)
        obs.select.option=[obs.select.option[2],obs.select.option[1],obs.select.option[0]]
        second=v2.agent(policy,lambda value:calls.append(value) or [1],self.raw(obs))
        self.assertEqual(second,[2]);self.assertEqual(len(calls),1)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['transaction_outcome'],'V2_DUPLICATE_REBIND')

    def test_raw_mismatch_and_option_duplicate_fail_closed(self):
        obs,_=self.obs(hand_ids=[741,1079,743,5,1152,1152],options=(('play',741),('attack',),('end',)))
        raw=self.raw(obs);calls=[];original=runtime.raw_parsed_agree
        runtime.raw_parsed_agree=lambda raw,parsed:False
        try:self.assertEqual(v2.agent(policy,lambda value:calls.append(value) or [1],raw),[1])
        finally:runtime.raw_parsed_agree=original
        self.assertEqual(len(calls),1);self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['transaction_abort'],'RAW_PARSED_MISMATCH')
        v2.reset();obs.select.option.insert(1,copy.deepcopy(obs.select.option[0]));calls=[]
        self.assertEqual(v2.agent(policy,lambda value:calls.append(value) or [2],self.raw(obs)),[2])
        self.assertEqual(len(calls),1);self.assertIsNone(v2.V2_TRANSACTION)

    def test_nonfire_action_trace_and_parent_state_exact(self):
        obs,_=self.obs(hand_ids=[1152,1152,1152,1152],target_hp=200,options=(('end',),))
        sentinel={'classification':'SENTINEL'};v1.LAST_V1_PACKAGE_TRACE=sentinel
        before=core.parent_state_snapshot(policy);fallback=[0]
        action,calls=self.wrapper(obs,fallback)
        self.assertIs(action,fallback);self.assertEqual(len(calls),1)
        self.assertEqual(core.parent_state_snapshot(policy),before)
        self.assertIs(v1.LAST_V1_PACKAGE_TRACE,sentinel)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_BASELINE_FALLBACK'])


    def test_post_ko_active_evolution_is_separate_from_preattack(self):
        active=self.kadabra(30,False,True);ala=self.card(743,0,801)
        obs,_=self.obs(active=active,hand_cards=[ala]+[self.card(1152) for _ in range(4)],
                       target_hp=100,options=(('evolve_active',801),('end',)),prizes=1)
        self.assertEqual(cert.prep_candidates(policy,obs,999,5),[])
        rows=cert.prep_candidates(policy,obs,999,5,allow_active=True)
        self.assertEqual(rows[0]['reason'],'V2_H1_PREP_EVOLVE')
        self.assertEqual(rows[0]['target_serial'],active.serial)

    def test_trace_surface_and_threefold_determinism(self):
        required={'context','selected_action','selected_rule','stage','reason_tags',
                  'continuity_rule_hits','H0_serial','H1_serials','Hreq','Hfinal',
                  'resource_intervals','transaction_outcome','transaction_abort',
                  'irreversible_abort_fault'}
        obs,_=self.obs(hand_ids=[741,1079,743,5,1152,1152],
                       options=(('play',741),('attack',),('end',)))
        observed=[]
        for _ in range(3):
            v1.reset();v2.reset();v1.LAST_V1_PACKAGE_TRACE={'selected_rule':None}
            action,_=self.wrapper(obs,[1])
            observed.append((action,copy.deepcopy(v2.LAST_V2_CONTINUITY_TRACE)))
        self.assertEqual(observed[0],observed[1]);self.assertEqual(observed[1],observed[2])
        self.assertTrue(required.issubset(observed[0][1]))
        self.assertFalse(observed[0][1]['irreversible_abort_fault'])


    def test_post_ko_tracked_stretcher_route_starts_exactly(self):
        h0_discard=self.card(743,0,700);active=self.kadabra(30,False,True)
        obs,_=self.obs(active=active,hand_ids=[1097,1152,1152,1152],discard=[h0_discard],
                       target_hp=80,options=(('play',1097),('end',)),prizes=1)
        v2.V2_TRANSACTION={'mode':'PREATTACK','owner':0,'stage':'track_h0_ko','turn':2,
            'attack_turn':2,'h0_serial':700,'target_serial':90,'target_hp':80,'hreq':4,
            'hfinal':4,'candidate':{'h1_serials':(),'reason':'V2_H0_FLOOR_BLOCK'},
            'resource_intervals':cert.resource_intervals(obs),'recovery_used':False}
        action,calls=self.wrapper(obs,[1])
        self.assertEqual(action,[0]);self.assertEqual(len(calls),1)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['reason_tags'],['V2_H1_RECOVER_STRETCHER'])
        self.assertEqual(v2.V2_TRANSACTION['stage'],'await_recovery_child')

    def test_public_serial_collision_fails_closed(self):
        collision=self.card(1152,0,11)
        obs,_=self.obs(hand_cards=[collision],target_hp=200,options=(('end',),))
        action,calls=self.wrapper(obs,[0])
        self.assertEqual(action,[0]);self.assertEqual(len(calls),1)
        self.assertIsNone(v2.V2_TRANSACTION)
        self.assertEqual(v2.LAST_V2_CONTINUITY_TRACE['transaction_abort'],'AMBIGUOUS_PUBLIC_METADATA')

    def test_main_and_runtime_trace_surface(self):
        sentinel={'context':0,'selected_action':[0],'selected_rule':cert.RULE,'stage':'PREATTACK',
                  'reason_tags':['V2_H1_PREP_ABRA'],'continuity_rule_hits':[cert.RULE],
                  'H0_serial':10,'H1_serials':[20],'Hreq':5,'Hfinal':5,
                  'resource_intervals':{},'transaction_outcome':'TEST','transaction_abort':None,
                  'irreversible_abort_fault':False}
        original=entrypoint._continuity_v2.agent
        entrypoint._continuity_v2.agent=lambda parent,delegate,raw:(setattr(entrypoint._continuity_v2,'LAST_V2_CONTINUITY_TRACE',sentinel) or [0])
        try:self.assertEqual(entrypoint.agent({'select':{}}),[0])
        finally:entrypoint._continuity_v2.agent=original
        self.assertEqual(entrypoint.LAST_V2_CONTINUITY_TRACE,sentinel)


if __name__=='__main__':unittest.main()