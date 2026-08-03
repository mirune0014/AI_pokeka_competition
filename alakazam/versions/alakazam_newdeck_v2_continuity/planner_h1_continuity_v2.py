"""Single-rule fail-closed wrapper for certified Alakazam H0/H1 continuity."""
from __future__ import annotations
import copy
from itertools import combinations
from math import ceil

import planner_deck_adaptation_v1 as v1
import planner_h1_continuity_v2_model as cert
import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime

RULE=cert.RULE
V2_TRANSACTION=None
V2_DUPLICATES={}
LAST_V2_CONTINUITY_TRACE={"public_snapshot_hash":None,"context":None,"selected_action":[],
 "selected_rule":None,"stage":None,"reason_tags":["V2_BASELINE_FALLBACK"],
 "continuity_rule_hits":[],"H0_serial":None,"H1_serials":[],"Hreq":None,"Hfinal":None,
 "resource_intervals":{},"transaction_outcome":"BASELINE","transaction_abort":None,
 "irreversible_abort_fault":False}


def reset():
    global V2_TRANSACTION
    V2_TRANSACTION=None; V2_DUPLICATES.clear()


def trace(snap,context,action,stage=None,tags=(),tx=None,outcome="BASELINE",abort=None,selected=False,fault=False):
    global LAST_V2_CONTINUITY_TRACE
    tx=tx or {}
    candidate=tx.get("candidate",{})
    LAST_V2_CONTINUITY_TRACE={"public_snapshot_hash":snap,"context":context,
      "selected_action":list(action) if isinstance(action,(list,tuple)) else [],
      "selected_rule":RULE if selected else None,"stage":stage,
      "reason_tags":list(tags),"continuity_rule_hits":[RULE] if selected else [],
      "H0_serial":tx.get("h0_serial"),"H1_serials":list(candidate.get("h1_serials",())),
      "Hreq":tx.get("hreq"),"Hfinal":tx.get("hfinal"),
      "resource_intervals":copy.deepcopy(tx.get("resource_intervals") or {}),
      "transaction_outcome":outcome,"transaction_abort":abort,
      "irreversible_abort_fault":bool(fault)}


def ctx(obs):
    try:return int(obs.select.context)
    except (AttributeError,TypeError,ValueError):return None


def action_keys(parent,obs,action):
    if not model.action_is_valid(obs,action):return None
    keys=tuple(runtime.stable_option_key(parent,obs,obs.select.option[i]) for i in action)
    return None if any(k is None for k in keys) else keys


def remember(parent,obs,snap,action):
    keys=action_keys(parent,obs,action)
    if keys is not None:V2_DUPLICATES[snap]=keys


def duplicate(parent,obs,snap):
    keys=V2_DUPLICATES.get(snap)
    if keys is None:return None
    action=model.rebind_option_keys(parent,obs,keys)
    if action is None or not model.action_is_valid(obs,action):
        V2_DUPLICATES.pop(snap,None);return None
    return action


def v1_state():
    return copy.deepcopy(v1.V1_TRANSACTION),copy.deepcopy(v1.V1_DUPLICATES)


def rollback(parent,parent_pre,v1_pre):
    core.restore_parent_state(parent,parent_pre)
    v1.V1_TRANSACTION=copy.deepcopy(v1_pre[0])
    v1.V1_DUPLICATES.clear();v1.V1_DUPLICATES.update(copy.deepcopy(v1_pre[1]))


def find_top(parent,obs,owner,serial):
    rows=[]
    player=obs.current.players[owner]
    for area,group in ((parent.AreaType.ACTIVE,player.active),(parent.AreaType.BENCH,player.bench)):
        rows.extend((area,i,p) for i,p in enumerate(group) if p.serial==serial)
    return rows[0] if len(rows)==1 else None


def frozen_key(parent,obs,action):
    keys=action_keys(parent,obs,action)
    return keys[0] if keys and len(keys)==1 else None


def new_tx(mode,obs,h0,key,candidate,intervals):
    return {"mode":mode,"owner":obs.current.yourIndex,"stage":candidate["next_stage"],
      "turn":obs.current.turn,"h0_serial":h0["attacker"].serial,
      "h0_id":h0["attacker"].id,"h0_hp":h0["attacker"].hp,
      "h0_stack":tuple(c.serial for c in h0["attacker"].preEvolution),
      "h0_energy":tuple(c.serial for c in h0["attacker"].energyCards),
      "target_serial":h0["target"].serial,"target_hp":h0["target"].hp,
      "hreq":h0["Hreq"],"hfinal":candidate["Hfinal"],"h0_key":key,
      "candidate":copy.deepcopy(candidate),"resource_intervals":copy.deepcopy(intervals),
      "irreversible":True,"recovery_used":False}


def invariant(parent,obs,tx,allow_missing=False):
    if obs.current.yourIndex!=tx["owner"]:return False
    target=find_top(parent,obs,1-tx["owner"],tx["target_serial"])
    if target is None or target[2].hp!=tx["target_hp"]:return False
    h0=find_top(parent,obs,tx["owner"],tx["h0_serial"])
    if h0 is None:return allow_missing
    p=h0[2]
    return (p.id==tx["h0_id"] and p.hp==tx["h0_hp"]
      and tuple(c.serial for c in p.preEvolution)==tx["h0_stack"]
      and tuple(c.serial for c in p.energyCards)==tx["h0_energy"])


def abort(snap,context,action,tx,tag="V2_ABORT_PUBLIC_MUTATION",fault=False):
    global V2_TRANSACTION
    trace(snap,context,action,tx.get("stage"),(tag,"V2_BASELINE_FALLBACK"),tx,
          "ABORT",tag,False,fault)
    V2_TRANSACTION=None;V2_DUPLICATES.clear();return action


def bind_serial(parent,obs,serial):
    if cert.census(parent,obs) is None:return None
    matches=[]
    for i,option in enumerate(obs.select.option):
        source=cert.option_card(parent,obs,option);target=cert.target_pokemon(parent,obs,option)
        value=source if source is not None else target
        if value is not None and value.serial==serial:matches.append(i)
    return matches[0] if len(matches)==1 else None


def yes_no(parent,obs,use_draw):
    if (obs.select.context!=parent.SelectContext.ACTIVATE or int(obs.select.type)!=9
        or obs.select.minCount!=1 or obs.select.maxCount!=1 or cert.census(parent,obs) is None):return None
    wanted=parent.OptionType.YES if use_draw else parent.OptionType.NO
    rows=[i for i,o in enumerate(obs.select.option) if o.type==wanted and cert.exact_option(o,wanted)]
    return [rows[0]] if len(rows)==1 else None


def recovery_child(parent,obs,tx):
    if obs.select.context!=parent.SelectContext.TO_HAND or cert.census(parent,obs) is None:return None
    candidate=tx["candidate"]
    if cert.card_row(obs.select.effect)!=candidate["source_row"]:
        return None
    selected=[]
    if candidate.get("wanted_rows"):
        for wanted in candidate["wanted_rows"]:
            rows=[i for i,o in enumerate(obs.select.option)
                  if cert.option_card(parent,obs,o) is not None
                  and cert.card_row(cert.option_card(parent,obs,o))==wanted]
            if len(rows)!=1:return None
            selected.append(rows[0])
    else:
        for wanted_id in candidate.get("wanted_ids",()):
            rows=sorted((cert.option_card(parent,obs,o).serial,i)
                        for i,o in enumerate(obs.select.option)
                        if cert.option_card(parent,obs,o) is not None
                        and cert.option_card(parent,obs,o).id==wanted_id)
            if not rows:return None
            selected.append(rows[0][1])
    expected_area = (parent.AreaType.DECK if candidate["reason"] == "V2_H1_RECOVER_HILDA"
                     else parent.AreaType.DISCARD)
    owner = obs.current.yourIndex
    if any(obs.select.option[index].type != parent.OptionType.CARD
           or obs.select.option[index].area != expected_area
           or obs.select.option[index].playerIndex not in (None, owner)
           for index in selected):
        return None
    return selected if len(selected)==len(set(selected)) and obs.select.minCount<=len(selected)<=obs.select.maxCount else None


def retreat_payment(parent,obs):
    if obs.select.context not in (parent.SelectContext.DISCARD_ENERGY,parent.SelectContext.DISCARD_ENERGY_CARD):return None
    valid=[]
    for n in range(obs.select.minCount,obs.select.maxCount+1):
        for row in combinations(range(len(obs.select.option)),n):
            action=list(row)
            if runtime.action_is_certified(parent,obs,action):valid.append(action)
    return valid[0] if len(valid)==1 else None


def child(parent,obs,tx,v1_action,parent_pre,v1_pre,snap):
    stage=tx["stage"];candidate=tx["candidate"];action=None
    allow_h0_missing = tx["mode"] == "POST_KO"
    if stage=="await_optional_draw":
        if cert.card_row(obs.select.contextCard)!=candidate["source_row"] or not invariant(parent,obs,tx,allow_h0_missing):
            return abort(snap.sha256,ctx(obs),v1_action,tx,fault=True)
        action=yes_no(parent,obs,candidate["draw_count"]>0)
        if action is not None:tx["stage"]="await_main"
    elif stage=="await_candy":
        if not invariant(parent,obs,tx,allow_h0_missing):return abort(snap.sha256,ctx(obs),v1_action,tx,fault=True)
        if obs.select.context in (parent.SelectContext.EVOLVES_FROM,parent.SelectContext.TO_FIELD,parent.SelectContext.EVOLVE):
            wanted=candidate["target_serial"]
        else:wanted=candidate["evolution_serial"]
        index=bind_serial(parent,obs,wanted)
        if index is not None:
            action=[index]
            tx["candy_abra" if wanted==candidate["target_serial"] else "candy_ala"]=True
            if tx.get("candy_abra") and tx.get("candy_ala"):tx["stage"]="await_optional_draw"
    elif stage=="await_telepath_or_main":
        if obs.select.context==parent.SelectContext.MAIN:
            tx["stage"]="await_main";return advance_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)
        if not invariant(parent,obs,tx,allow_h0_missing):return abort(snap.sha256,ctx(obs),v1_action,tx,fault=True)
        abras=sorted((cert.option_card(parent,obs,o).serial,i) for i,o in enumerate(obs.select.option)
                     if cert.option_card(parent,obs,o) is not None and cert.option_card(parent,obs,o).id==cert.ABRA)
        if tx["resource_intervals"][cert.ABRA]["deck_lb"]>=1 and abras:action=[abras[0][1]]
        elif obs.select.minCount==0:action=[]
        if action is not None:tx["stage"]="await_main"
    elif stage=="await_recovery_child":
        action=recovery_child(parent,obs,tx)
        if action is not None:tx["stage"]="await_main"
    elif stage=="await_retreat_payment":
        action=retreat_payment(parent,obs)
        if action is not None:tx["stage"]="await_promotion_or_main"
    elif stage=="await_promotion_or_main":
        if obs.select.context==parent.SelectContext.MAIN:
            tx["stage"]="await_main";return advance_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)
        index=bind_serial(parent,obs,tx["post_h1_serial"])
        if index is not None:action=[index];tx["stage"]="await_main"
    if action is None or not runtime.action_is_certified(parent,obs,action):
        return abort(snap.sha256,ctx(obs),v1_action,tx,fault=True)
    rollback(parent,parent_pre,v1_pre);remember(parent,obs,snap.sha256,action)
    trace(snap.sha256,ctx(obs),action,stage,(candidate["reason"],),tx,"ADVANCE",selected=True)
    return action


def ready_attack(parent,obs,action):
    return cert.current_h0(parent,obs,action) is not None


def post_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap):
    global V2_TRANSACTION
    owner=tx["owner"];mine,theirs=obs.current.players[owner],obs.current.players[1-owner]
    if len(theirs.active)!=1:return abort(snap.sha256,ctx(obs),v1_action,tx)
    tx["turn"]=obs.current.turn;tx["target_serial"]=theirs.active[0].serial;tx["target_hp"]=theirs.active[0].hp
    tx["hreq"]=ceil(theirs.active[0].hp/20)
    if ready_attack(parent,obs,v1_action):
        trace(snap.sha256,ctx(obs),v1_action,"POST_KO",("V2_H1_POWERFUL_HAND",),tx,"POST_KO_ATTACK",selected=True)
        V2_TRANSACTION=None;V2_DUPLICATES.clear();return v1_action
    direct=cert.prep_candidates(parent,obs,tx["h0_serial"],tx["hreq"],allow_active=True)
    if direct:
        candidate=direct[0];tx["candidate"]=candidate;tx["stage"]=candidate["next_stage"]
        tx["hfinal"]=candidate["Hfinal"];tx["resource_intervals"]=cert.resource_intervals(obs)
        action=candidate["action"];rollback(parent,parent_pre,v1_pre);remember(parent,obs,snap.sha256,action)
        trace(snap.sha256,ctx(obs),action,"POST_KO",(candidate["reason"],),tx,"POST_KO_PREP",selected=True);return action
    ready_bench=[p for p in mine.bench if cert.ready_alakazam(parent,obs.current,p,owner)]
    retreat=[i for i,o in enumerate(obs.select.option) if o.type==parent.OptionType.RETREAT and cert.exact_option(o,parent.OptionType.RETREAT)]
    if len(ready_bench)==1 and len(retreat)==1:
        candidate={"action":[retreat[0]],"reason":"V2_H1_PROMOTE_OR_RETREAT","kind":"RETREAT",
          "score":1,"Hfinal":mine.handCount,"h1_serials":(ready_bench[0].serial,),"next_stage":"await_retreat_payment"}
        tx["candidate"]=candidate;tx["stage"]=candidate["next_stage"];tx["post_h1_serial"]=ready_bench[0].serial
        action=candidate["action"];rollback(parent,parent_pre,v1_pre);remember(parent,obs,snap.sha256,action)
        trace(snap.sha256,ctx(obs),action,"POST_KO",(candidate["reason"],),tx,"POST_KO_RETREAT",selected=True);return action
    if not tx.get("recovery_used"):
        candidate,block=cert.recovery_candidate(parent,obs,tx["hreq"])
        if candidate:
            tx["candidate"]=candidate;tx["stage"]=candidate["next_stage"];tx["hfinal"]=candidate["Hfinal"]
            tx["resource_intervals"]=cert.resource_intervals(obs);tx["recovery_used"]=True
            action=candidate["action"];rollback(parent,parent_pre,v1_pre);remember(parent,obs,snap.sha256,action)
            trace(snap.sha256,ctx(obs),action,"POST_KO",(candidate["reason"],),tx,"POST_KO_RECOVERY",selected=True);return action
    else:block="V2_H1_RESOURCE_INTERVAL_UNPROVEN"
    return abort(snap.sha256,ctx(obs),v1_action,tx,block or "V2_H1_RESOURCE_INTERVAL_UNPROVEN")


def advance_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap):
    global V2_TRANSACTION
    if (v1._main_envelope(parent,obs) is None or obs.current.turn!=tx["turn"]
        or not invariant(parent,obs,tx,tx["mode"]=="POST_KO")):
        return abort(snap.sha256,ctx(obs),v1_action,tx,fault=tx.get("irreversible",False))
    if tx["mode"]=="POST_KO":return post_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)
    if tx["mode"]=="UNSAFE_ACTIVE_743":
        if v1.LAST_V1_PACKAGE_TRACE.get("selected_rule")==v1.RULE_ALAKAZAM and frozen_key(parent,obs,v1_action)==tx["h0_key"]:
            trace(snap.sha256,ctx(obs),v1_action,"PREATTACK",("V2_UNSAFE_ACTIVE_743_BLOCKED",tx["candidate"]["reason"]),tx,"PREP_COMPLETE_DEFER_V1",selected=True)
            V2_TRANSACTION=None;V2_DUPLICATES.clear();return v1_action
        return abort(snap.sha256,ctx(obs),v1_action,tx,fault=True)
    h0=cert.current_h0(parent,obs,v1_action)
    if h0 is None or frozen_key(parent,obs,v1_action)!=tx["h0_key"]:
        return abort(snap.sha256,ctx(obs),v1_action,tx,fault=True)
    tx["stage"]="track_h0_ko";tx["attack_turn"]=obs.current.turn;tx["hfinal"]=obs.current.players[tx["owner"]].handCount
    remember(parent,obs,snap.sha256,v1_action)
    trace(snap.sha256,ctx(obs),v1_action,"PREATTACK",(tx["candidate"]["reason"],"V2_H1_POWERFUL_HAND"),tx,"H0_ATTACK_EXECUTED",selected=True)
    return v1_action


def track(parent,obs,tx,v1_action,parent_pre,v1_pre,snap):
    global V2_TRANSACTION
    if obs.current.yourIndex!=tx["owner"]:return abort(snap.sha256,ctx(obs),v1_action,tx)
    if obs.select.context!=parent.SelectContext.MAIN:
        trace(snap.sha256,ctx(obs),v1_action,"POST_KO_WAIT",("V2_BASELINE_FALLBACK",),tx,"TRACKING",selected=True);return v1_action
    if obs.current.turn<=tx["attack_turn"]:return abort(snap.sha256,ctx(obs),v1_action,tx,"V2_BASELINE_FALLBACK")
    mine=obs.current.players[tx["owner"]]
    observed=(find_top(parent,obs,tx["owner"],tx["h0_serial"]) is None
              and len([c for c in mine.discard if c.id==cert.ALAKAZAM and c.serial==tx["h0_serial"]])==1)
    if not observed:
        trace(snap.sha256,ctx(obs),v1_action,"POST_KO",("V2_BASELINE_FALLBACK",),tx,"H0_SURVIVED_OR_UNPROVEN")
        V2_TRANSACTION=None;V2_DUPLICATES.clear();return v1_action
    tx["mode"]="POST_KO";tx["stage"]="await_main";tx["turn"]=obs.current.turn
    if len(obs.current.players[1-tx["owner"]].active)!=1:return abort(snap.sha256,ctx(obs),v1_action,tx)
    target=obs.current.players[1-tx["owner"]].active[0];tx["target_serial"]=target.serial;tx["target_hp"]=target.hp
    return post_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)


def unsafe_h0(parent,obs):
    if v1.LAST_V1_PACKAGE_TRACE.get("selected_rule")!=v1.RULE_ALAKAZAM:return None
    owner=obs.current.yourIndex;mine,theirs=obs.current.players[owner],obs.current.players[1-owner]
    if (v1.V1_TRANSACTION is None or len(mine.active)!=1 or mine.active[0].id!=cert.KADABRA
        or len(theirs.active)!=1 or parent.prize_count(theirs.active[0])>=len(mine.prize) or not theirs.bench):return None
    return {"owner":owner,"attacker":mine.active[0],"target":theirs.active[0],"Hreq":ceil(theirs.active[0].hp/20)}


def agent(parent,v1_agent,raw):
    global V2_TRANSACTION
    obs=snap=None;context=None;v1_action=None
    try:
        if not isinstance(raw,dict) or raw.get("select") is None:
            reset();v1_action=v1_agent(raw);trace(None,None,v1_action,tags=("V2_BASELINE_FALLBACK",));return v1_action
        obs=parent.to_observation_class(raw);context=ctx(obs)
        if not runtime.raw_parsed_agree(raw,obs):
            reset();v1_action=v1_agent(raw);trace(None,context,v1_action,tags=("V2_ABORT_PUBLIC_MUTATION","V2_BASELINE_FALLBACK"),abort="RAW_PARSED_MISMATCH");return v1_action
        snap=runtime.public_snapshot(parent,obs)
        if snap is None or cert.census(parent,obs) is None or not cert.public_exact(parent,obs) or not cert.metadata_exact(parent):
            reset();v1_action=v1_agent(raw);trace(None if snap is None else snap.sha256,context,v1_action,tags=("V2_H1_RESOURCE_INTERVAL_UNPROVEN","V2_BASELINE_FALLBACK"),abort="AMBIGUOUS_PUBLIC_METADATA");return v1_action
        if snap.sha256 in core.INTEGRATED_DUPLICATE_CACHE or snap.sha256 in v1.V1_DUPLICATES:
            reset();v1_action=v1_agent(raw);trace(snap.sha256,context,v1_action,tags=("V2_BASELINE_FALLBACK",),outcome="DEFER_INHERITED_DUPLICATE");return v1_action
        rebound=duplicate(parent,obs,snap.sha256)
        if rebound is not None:
            trace(snap.sha256,context,rebound,V2_TRANSACTION.get("stage") if V2_TRANSACTION else None,("V2_BASELINE_FALLBACK",),V2_TRANSACTION,"V2_DUPLICATE_REBIND",selected=V2_TRANSACTION is not None);return rebound
        if V2_TRANSACTION is None:V2_DUPLICATES.clear()
        parent_pre=core.parent_state_snapshot(parent);v1_pre=v1_state()
        inherited=(core.INTEGRATED_TRANSACTION is not None or core.parent_owner_active(parent_pre) or v1_pre[0] is not None)
        v1_action=v1_agent(raw)
        if inherited:
            reset();trace(snap.sha256,context,v1_action,tags=("V2_BASELINE_FALLBACK",),outcome="DEFER_INHERITED_TRANSACTION");return v1_action
        rule=v1.LAST_V1_PACKAGE_TRACE.get("selected_rule")
        if rule==v1.RULE_BOSS:
            reset();trace(snap.sha256,context,v1_action,"PREATTACK",("V2_TERMINAL_KO_PRECEDENCE",),outcome="DEFER_V1_BOSS");return v1_action
        if rule==v1.RULE_XEROSIC:
            reset();trace(snap.sha256,context,v1_action,"PREATTACK",("V2_DEFER_V1_XEROSIC",),outcome="DEFER_V1_XEROSIC");return v1_action
        if V2_TRANSACTION is not None:
            tx=V2_TRANSACTION
            if tx["stage"]=="track_h0_ko":return track(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)
            if tx["stage"]=="await_main":return advance_main(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)
            return child(parent,obs,tx,v1_action,parent_pre,v1_pre,snap)
        intervals=cert.resource_intervals(obs)
        if v1._main_envelope(parent,obs) is None or intervals is None:
            trace(snap.sha256,context,v1_action,tags=("V2_H1_RESOURCE_INTERVAL_UNPROVEN","V2_BASELINE_FALLBACK"));return v1_action
        h0=cert.current_h0(parent,obs,v1_action)
        if h0:
            if h0["terminal"]:
                tx={"h0_serial":h0["attacker"].serial,"hreq":h0["Hreq"],"hfinal":obs.current.players[h0["owner"]].handCount,"resource_intervals":intervals}
                trace(snap.sha256,context,v1_action,"PREATTACK",("V2_TERMINAL_KO_PRECEDENCE",),tx,"TERMINAL_H0");return v1_action
            key=frozen_key(parent,obs,v1_action)
            candidates=cert.prep_candidates(parent,obs,h0["attacker"].serial,h0["Hreq"])
            certificate=cert.h1_certificate(parent,obs,h0["attacker"].serial)
            if key is not None and candidates:
                candidate=candidates[0];V2_TRANSACTION=new_tx("PREATTACK",obs,h0,key,candidate,intervals)
                action=candidate["action"];rollback(parent,parent_pre,v1_pre);remember(parent,obs,snap.sha256,action)
                trace(snap.sha256,context,action,"PREATTACK",(candidate["reason"],),V2_TRANSACTION,"PREP_STARTED",selected=True);return action
            candidate={"reason":"V2_H1_POWERFUL_HAND" if certificate else "V2_H0_FLOOR_BLOCK",
              "Hfinal":obs.current.players[h0["owner"]].handCount,"h1_serials":certificate["serials"] if certificate else (),"next_stage":"track_h0_ko"}
            if key is not None:
                V2_TRANSACTION=new_tx("PREATTACK",obs,h0,key,candidate,intervals);V2_TRANSACTION["stage"]="track_h0_ko";V2_TRANSACTION["attack_turn"]=obs.current.turn
                remember(parent,obs,snap.sha256,v1_action)
                trace(snap.sha256,context,v1_action,"PREATTACK",(candidate["reason"],"V2_H1_POWERFUL_HAND"),V2_TRANSACTION,"H0_ATTACK_TRACKED",selected=True)
            else:trace(snap.sha256,context,v1_action,tags=("V2_ABORT_PUBLIC_MUTATION","V2_BASELINE_FALLBACK"))
            return v1_action
        unsafe=unsafe_h0(parent,obs)
        if unsafe:
            h0_future_serial=v1.V1_TRANSACTION.get("card_serial")
            current=cert.h1_certificate(parent,obs,unsafe["attacker"].serial)
            if current is not None and h0_future_serial in current["serials"]:
                current=None
            candidates=[candidate for candidate in cert.prep_candidates(
                parent,obs,unsafe["attacker"].serial,unsafe["Hreq"],2)
                if h0_future_serial not in candidate["h1_serials"]]
            key=frozen_key(parent,obs,v1_action)
            if current is None and candidates and key is not None:
                candidate=candidates[0];V2_TRANSACTION=new_tx("UNSAFE_ACTIVE_743",obs,unsafe,key,candidate,intervals)
                action=candidate["action"];rollback(parent,parent_pre,v1_pre);remember(parent,obs,snap.sha256,action)
                trace(snap.sha256,context,action,"PREATTACK",("V2_UNSAFE_ACTIVE_743_BLOCKED",candidate["reason"]),V2_TRANSACTION,"UNSAFE_ACTIVE_743_PREP",selected=True);return action
        trace(snap.sha256,context,v1_action,tags=("V2_BASELINE_FALLBACK",),outcome="BASELINE");return v1_action
    except Exception as error:
        reset()
        if v1_action is None:v1_action=v1_agent(raw)
        trace(None if snap is None else snap.sha256,context,v1_action,tags=("V2_ABORT_PUBLIC_MUTATION","V2_BASELINE_FALLBACK"),outcome="EXCEPTION_FALLBACK",abort=type(error).__name__)
        return v1_action