"""Focused hard-ordering, lifecycle, determinism and fail-closed Task 9 gate."""
from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
CANDIDATE = AUTO / "candidates/archaludon_public_prize_race_threat_control_t9_v1"
CURRENT = AUTO / "live/55155015/analysis_20260802/refresh"
HISTORICAL = AUTO / "live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new"
OUTPUT = Path(__file__).with_name("focused_fixture_results.json")
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "tools")]

from rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402
from cg.api import Card, SelectData  # noqa: E402


def load():
    spec = importlib.util.spec_from_file_location("task9_focused", CANDIDATE / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load()
RESULTS = []


def record(name, condition, **evidence):
    assert condition, (name, evidence)
    RESULTS.append({"name": name, "status": "PASS", **evidence})


def observations(path, seat=0):
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {step: copy.deepcopy(obs) for step, obs, _ in replay_decisions(raw, seat)}


def parsed(obs):
    return M.to_observation_class(copy.deepcopy(obs))


def reset():
    M._t9_transaction = None
    if M._t8_is_transaction():
        M._t8_abort([], "focused_reset")
    M._t7_transaction = None
    M._pfgear_reset_active("focused_reset")
    M._pcrd_clear("focused_reset")
    M._pfc_clear("focused_reset")
    M._cum_reset_runtime("focused_reset")
    M._dper_reset_runtime("focused_reset")


def remap_player_indexes(value):
    if isinstance(value, dict):
        for key, item in tuple(value.items()):
            if key == "playerIndex" and item in (0, 1):
                value[key] = 1 - item
            else:
                remap_player_indexes(item)
    elif isinstance(value, list):
        for item in value:
            remap_player_indexes(item)


def mirror(obs):
    changed = copy.deepcopy(obs)
    changed["current"]["players"].reverse()
    remap_player_indexes(changed)
    changed["current"]["yourIndex"] = 1 - obs["current"]["yourIndex"]
    first = changed["current"].get("firstPlayer")
    if first in (0, 1):
        changed["current"]["firstPlayer"] = 1 - first
    return changed


def build_counterfactual_boss_callbacks(start, certificate):
    """Construct the exact public Boss target and post-gust MAIN callbacks."""
    target_callback = copy.deepcopy(start)
    mine = M.my_state(target_callback)
    opponent = M.opp_state(target_callback)
    boss_serial = certificate["supporter_serial"]
    bosses = [card for card in tuple(mine.hand or ()) if card.serial == boss_serial]
    assert len(bosses) == 1
    boss = bosses[0]
    mine.hand[:] = [
        card for card in tuple(mine.hand or ()) if card.serial != boss_serial
    ]
    mine.handCount = len(mine.hand)
    target_callback.current.turnActionCount += 1
    target_callback.current.supporterPlayed = True
    target_callback.select = SelectData(
        type=start.select.type,
        context=M.SelectContext.SWITCH,
        minCount=1,
        maxCount=1,
        remainDamageCounter=0,
        remainEnergyCost=0,
        option=[
            M.Option(
                type=M.OptionType.CARD,
                area=M.AreaType.BENCH,
                index=index,
                playerIndex=1 - target_callback.current.yourIndex,
            )
            for index, card in enumerate(tuple(opponent.bench or ()))
            if card is not None
        ],
        deck=None,
        contextCard=None,
        effect=Card(M.BOSS, boss_serial, target_callback.current.yourIndex),
    )

    post_gust = copy.deepcopy(target_callback)
    post_mine = M.my_state(post_gust)
    post_opponent = M.opp_state(post_gust)
    target_positions = [
        index for index, card in enumerate(tuple(post_opponent.bench or ()))
        if card is not None and card.serial == certificate["target_serial"]
    ]
    assert len(target_positions) == 1 and len(tuple(post_opponent.active or ())) == 1
    position = target_positions[0]
    original_active = post_opponent.active[0]
    selected_target = post_opponent.bench[position]
    post_opponent.active[:] = [selected_target]
    post_opponent.bench[position] = original_active
    post_mine.discard.append(boss)
    post_gust.current.turnActionCount += 1

    # Rebind the original ordinary-MAIN options after the physical Boss card
    # left hand. Keeping all remaining legal setup options is essential: this
    # is what catches a lower owner attempting to start before T9's attack.
    rebound_options = []
    for option in tuple(start.select.option or ()):
        rebound = copy.deepcopy(option)
        card = M.option_card(start, option)
        if (
            card is not None
            and option.index is not None
            and (
                option.area == M.AreaType.HAND
                or option.type == M.OptionType.PLAY
            )
        ):
            positions = [
                index for index, row in enumerate(tuple(post_mine.hand or ()))
                if row is not None and row.serial == card.serial
            ]
            if len(positions) != 1:
                continue
            rebound.index = positions[0]
        rebound_options.append(rebound)
    post_gust.select = copy.deepcopy(start.select)
    post_gust.select.context = M.SelectContext.MAIN
    post_gust.select.option = rebound_options
    post_gust.select.deck = None
    post_gust.select.contextCard = None
    post_gust.select.effect = None
    return asdict(target_callback), asdict(post_gust)


def safe_reply(*, terminal=0, wipe=0, requirement=None):
    losing = bool(terminal or wipe)
    return {
        "terminal_routes": tuple(("terminal", index) for index in range(terminal)),
        "wipe_routes": tuple(("wipe", index) for index in range(wipe)),
        "terminal_count": terminal,
        "wipe_count": wipe,
        "exact_loss_next_turn": losing,
        "exact_loss_horizon": 1 if losing else None,
        "opponent_resource_requirement": requirement,
        "exact_route_signatures": (),
        "effect_inventory": {"status": "EXACT"},
        "unsupported_text": (),
    }


def plan(seed, **changes):
    row = copy.deepcopy(seed)
    row.update(changes)
    return row


# A real, exact, non-Adrena Boss sequence exercises the strict transaction.
boss_path = CURRENT / "episode_89279601_replay.json"
boss_obs = observations(boss_path)
start = parsed(boss_obs[112])
attack_plans, attack_reason = M._t9_attack_plans(start)
boss_plans, boss_reason = M._t9_boss_plans(start, attack_plans)
record("boss_fixture_inventory_exact", attack_reason is None and boss_reason is None and len(boss_plans) == 1)
boss_plan = boss_plans[0]
dummy_relation = {
    "purpose": "NONTERMINAL_BOSS_PRIZE_CONVERSION",
    "hard_layer": 3,
    "reason": "focused_exact_lifecycle",
}

for seat in (0, 1):
    reset()
    local_start = start
    local_attack_plans = attack_plans
    local_boss_plans = boss_plans
    local_target = parsed(boss_obs[113])
    local_attack = parsed(boss_obs[114])
    if seat == 1:
        local_start = parsed(mirror(boss_obs[112]))
        local_target = parsed(mirror(boss_obs[113]))
        local_attack = parsed(mirror(boss_obs[114]))
        local_attack_plans, local_reason = M._t9_attack_plans(local_start)
        local_boss_plans, local_boss_reason = M._t9_boss_plans(
            local_start, local_attack_plans
        )
        record(
            "boss_mirrored_inventory_exact",
            local_reason is None and local_boss_reason is None
            and len(local_boss_plans) == 1,
        )
    local_plan = local_boss_plans[0]
    action0 = M._t9_begin_boss(
        local_start, local_plan, dummy_relation,
        tuple(local_attack_plans) + tuple(local_boss_plans),
    )
    record(f"boss_begin_valid_seat{seat}", M._cum_valid_action(local_start, action0), action=action0)
    duplicate0 = M._t9_resume(local_start, action0)
    record(f"boss_begin_duplicate_seat{seat}", duplicate0 == action0)
    action1 = M._t9_resume(local_target, [0])
    record(f"boss_target_bound_seat{seat}", M._cum_valid_action(local_target, action1), action=action1)
    duplicate1 = M._t9_resume(local_target, action1)
    record(f"boss_target_duplicate_seat{seat}", duplicate1 == action1)
    action2 = M._t9_resume(local_attack, [0])
    record(f"boss_attack_bound_seat{seat}", M._cum_valid_action(local_attack, action2), action=action2)
    record(f"boss_conservation_seat{seat}", M._t9_conservation()["holds"] and M._t9_transaction is None)

# The final wrapper must call the accepted Task 8 parent at every callback
# without allowing PCRD/Pokégear or another inherited owner to start between
# Boss play, target, and the bound attack. Exercise both seats and both attacks.
wrapper_cases = (
    (
        "turbo_flare",
        observations(CURRENT / "episode_89277462_replay.json")[45],
        M._PCRD_TURBO_FLARE,
        observations(CURRENT / "episode_89277462_replay.json")[46],
    ),
    (
        "metal_defender",
        boss_obs[112],
        M.METAL_DEFENDER,
        None,
    ),
)
for label, factual_start, attack_id, aftereffect in wrapper_cases:
    for seat in (0, 1):
        reset()
        start_raw = copy.deepcopy(factual_start)
        if seat == 1:
            start_raw = mirror(start_raw)
        start_view = parsed(start_raw)
        play_action = M.agent(copy.deepcopy(start_raw))
        record(
            f"wrapper_{label}_boss_play_seat{seat}",
            M._cum_valid_action(start_view, play_action)
            and M._t9_transaction is not None
            and M._t9_transaction["stage"] == "BOSS_PLAY_EMITTED"
            and M._practice_owner_fingerprint()
            and tuple(row[0] for row in M._practice_owner_fingerprint())
            == ("_t9_transaction",),
            action=play_action,
            owners=M._practice_owner_fingerprint(),
        )
        certificate = copy.deepcopy(M._t9_transaction["certificate"])
        target_raw, post_gust_raw = build_counterfactual_boss_callbacks(
            start_view, certificate
        )
        target_view = parsed(target_raw)
        target_action = M.agent(copy.deepcopy(target_raw))
        record(
            f"wrapper_{label}_boss_target_seat{seat}",
            M._cum_valid_action(target_view, target_action)
            and M._t9_transaction is not None
            and M._t9_transaction["stage"] == "BOSS_TARGET_EMITTED"
            and tuple(row[0] for row in M._practice_owner_fingerprint())
            == ("_t9_transaction",)
            and M._pcrd_transaction is None
            and M._pfgear_transaction is None
            and M._dper_active_callback is None,
            action=target_action,
            owners=M._practice_owner_fingerprint(),
        )
        post_gust_view = parsed(post_gust_raw)
        attack_action = M.agent(copy.deepcopy(post_gust_raw))
        selected_options = (
            tuple(post_gust_view.select.option[index] for index in attack_action)
            if M._cum_valid_action(post_gust_view, attack_action)
            else ()
        )
        record(
            f"wrapper_{label}_bound_attack_and_release_seat{seat}",
            len(selected_options) == 1
            and selected_options[0].type == M.OptionType.ATTACK
            and selected_options[0].attackId == attack_id
            and M._t9_transaction is None
            and not M._practice_owner_fingerprint()
            and M._t9_last_certificate.get("completion_reason")
            == "attack_emitted_owner_released",
            action=attack_action,
            owners=M._practice_owner_fingerprint(),
        )
        if aftereffect is not None:
            callback_raw = copy.deepcopy(aftereffect)
            if seat == 1:
                callback_raw = mirror(callback_raw)
            callback_view = parsed(callback_raw)
            callback_action = M.agent(copy.deepcopy(callback_raw))
            record(
                f"wrapper_{label}_aftereffect_owner_seat{seat}",
                M._cum_valid_action(callback_view, callback_action)
                and M._t9_transaction is None
                and M._dper_active_callback is not None
                and M._dper_active_callback.get("effect_id") == "TURBO_FLARE"
                and tuple(row[0] for row in M._practice_owner_fingerprint())
                == ("_dper_active_callback",),
                action=callback_action,
                owners=M._practice_owner_fingerprint(),
            )

# Option order changes indices, never selected semantics.
permuted_raw = copy.deepcopy(boss_obs[112])
permuted_raw["select"]["option"].reverse()
permuted = parsed(permuted_raw)
role = boss_plan["execution"]["boss_role"]
original_action = M._t9_bind_roles(start, (role,))
permuted_action = M._t9_bind_roles(permuted, (role,))
record(
    "boss_option_order_semantic_invariance",
    M._cum_action_semantic(start, original_action)
    == M._cum_action_semantic(permuted, permuted_action),
    original=original_action, permuted=permuted_action,
)

# Stale target and owner collision both fail closed and settle ownership.
reset()
M._t9_begin_boss(start, boss_plan, dummy_relation, boss_plans)
stale_raw = copy.deepcopy(boss_obs[113])
stale_raw["select"]["effect"]["serial"] += 1000
stale = parsed(stale_raw)
fallback = [0]
record("stale_boss_target_aborts", M._t9_resume(stale, fallback) == fallback and M._t9_transaction is None)
reset()
M._t9_begin_boss(start, boss_plan, dummy_relation, boss_plans)
M._t7_transaction = {"rule_id": M._T7_RULE_ID}
record("boss_owner_collision_aborts", M._t9_resume(parsed(boss_obs[113]), fallback) == fallback and M._t9_transaction is None)
M._t7_transaction = None

# Task 7 terminal Boss remains above Task 9.
reset()
terminal_raw = observations(CURRENT / "episode_89292594_replay.json")[49]
parent_terminal = M._t9_parent_agent(copy.deepcopy(terminal_raw))
reset()
candidate_terminal = M.agent(copy.deepcopy(terminal_raw))
record(
    "terminal_boss_parent_invariance",
    M._cum_action_semantic(parsed(terminal_raw), parent_terminal)
    == M._cum_action_semantic(parsed(terminal_raw), candidate_terminal)
    and M._t9_transaction is None,
)

# Use a complete real plan as the structural seed for all hard-order tests.
seed = copy.deepcopy(attack_plans[0])
seed.update({
    "semantic_key": ("SEED",), "physical_key": (("SEED",),),
    "family": "CURRENT_ATTACK", "target_serial": 100,
    "current_ko": False, "current_prizes": 0,
    "resettable_nonlethal": False, "durable_damage": 20,
    "comeback_outs": 1, "self_deckout_risk": 0,
    "consumed_refs": (), "post_attack_readiness": {"payable": True},
    "reply": safe_reply(),
})

harm_parent = plan(seed, semantic_key=("HARM_PARENT",), current_ko=True, reply=safe_reply(terminal=1, requirement=1))
harm_alt = plan(seed, semantic_key=("HARM_ALT",), family="END", reply=safe_reply())
record("harmful_ko_positive", M._t9_relation(harm_alt, harm_parent, all_losing=False)["purpose"] == "HARMFUL_KO_VETO")
record("harmful_ko_negative_safe_trade", M._t9_relation(harm_alt, plan(harm_parent, reply=safe_reply()), all_losing=False) is None)

reset_parent = plan(seed, semantic_key=("RESET_PARENT",), resettable_nonlethal=True, durable_damage=0)
one_shot = plan(seed, semantic_key=("ONE_SHOT",), current_ko=True, current_prizes=1)
record("reset_wall_one_shot", M._t9_relation(one_shot, reset_parent, all_losing=False)["purpose"] == "RESET_WALL_ONE_SHOT_OR_BYPASS")
bypass = plan(one_shot, semantic_key=("BYPASS",), family="BOSS_ATTACK", target_serial=200)
record("reset_wall_boss_bypass", M._t9_relation(bypass, reset_parent, all_losing=False)["purpose"] == "RESET_WALL_ONE_SHOT_OR_BYPASS")
fallback_wall = plan(seed, semantic_key=("FALLBACK_WALL",), durable_damage=30)
record("reset_wall_fallback_parent", M._t9_relation(fallback_wall, reset_parent, all_losing=False) is None)
record("lone_dudunsparce_not_reset_wall", M._t9_relation(one_shot, plan(reset_parent, resettable_nonlethal=False), all_losing=False) is None)

wipe_parent = plan(seed, semantic_key=("WIPE_PARENT",), reply=safe_reply(wipe=1, requirement=1))
wipe_avoid = plan(seed, semantic_key=("WIPE_AVOID",), family="PCRD_SETUP_ATTACK", comeback_outs=2)
record("bench_damage_wipe_avoidance", M._t9_relation(wipe_avoid, wipe_parent, all_losing=False)["purpose"] == "EXACT_LOSS_AVOIDANCE")

boss_convert = plan(seed, semantic_key=("BOSS_CONVERT",), family="BOSS_ATTACK", target_serial=201, current_ko=True, current_prizes=3)
record("three_prize_boss_conversion", M._t9_relation(boss_convert, seed, all_losing=False)["purpose"] == "NONTERMINAL_BOSS_PRIZE_CONVERSION")
record("boss_conversion_rejects_worse_reply", M._t9_relation(plan(boss_convert, reply=safe_reply(terminal=1)), seed, all_losing=False) is None)

threat_parent = plan(seed, semantic_key=("THREAT_PARENT",), current_ko=False, current_prizes=1, reply=safe_reply(terminal=2, requirement=1))
threat_parent["reply"]["exact_route_signatures"] = ((
    "READY", (), 169, 333, 224, 190, 100, True, True, 2, 300, (333,),
),)
threat_boss = plan(seed, semantic_key=("THREAT_BOSS",), family="BOSS_ATTACK", target_serial=333, current_ko=True, current_prizes=1, reply=safe_reply(terminal=1, requirement=2))
record("ready_threat_removal_positive", M._t9_relation(threat_boss, threat_parent, all_losing=False)["purpose"] == "READY_THREAT_OR_ENGINE_REMOVAL")
record("ready_threat_removal_negative_unbound", M._t9_relation(plan(threat_boss, target_serial=444), threat_parent, all_losing=False) is None)

# Serial references are schema-bound exact integers. Attack ids and decimal
# substrings must never masquerade as Pokemon/evolution/engine serials.
collision_route = {
    "source_serial": 13,
    "sequence": (
        ("ATTACK", 253, "VISIBLE_PREVIOUS_EVOLUTION", 13, 39),
        ("EVOLVE_KNOWN", 39, 13),
        ("ADRENA_BRAIN", 13, 39, 30, 3, "ACTIVE"),
    ),
    "public_resource": {
        "source_serial": 39,
        "legal_target_serials": (13, 30),
    },
    "certificate": {
        "saved_callback_transaction": {
            "source_serial": 39,
            "legal_target_serials": (13, 30),
        },
        "attack_id": 253,
        "final_damage": 130,
    },
}
collision_refs = M._t9_route_serial_references(collision_route)
record(
    "structured_serial_references_positive",
    set(collision_refs) == {13, 30, 39},
    references=collision_refs,
)
for serial in (3, 253, 139):
    record(
        f"structured_serial_collision_negative_{serial}",
        serial not in collision_refs,
        references=collision_refs,
    )

losing_parent = plan(seed, semantic_key=("LOSE_PARENT",), reply=safe_reply(terminal=1, requirement=1), comeback_outs=1)
losing_alt = plan(seed, semantic_key=("LOSE_ALT",), reply=safe_reply(terminal=1, requirement=2), comeback_outs=2)
record("all_losing_comeback_order", M._t9_relation(losing_alt, losing_parent, all_losing=True)["purpose"] == "COMEBACK_RESOURCE_REQUIREMENT")

# Actual unknown public effect inventory must return the exact parent.
unknown_obs = observations(CURRENT / "episode_89273226_replay.json")[26]
reset()
unknown_parent = M._t9_parent_agent(copy.deepcopy(unknown_obs))
unknown_selected = M.agent(copy.deepcopy(unknown_obs))
record(
    "unknown_effect_fail_closed",
    M._cum_action_semantic(parsed(unknown_obs), unknown_parent)
    == M._cum_action_semantic(parsed(unknown_obs), unknown_selected)
    and "unknown" in str((M._t9_last_telemetry or {}).get("rejection_reason")),
    reason=(M._t9_last_telemetry or {}).get("rejection_reason"),
)

# One-step successor plans are complete PCRD transactions, not a loose score.
attach_obs = observations(CURRENT / "episode_89273146_replay.json")[32]
attach_view = parsed(attach_obs)
attach_attacks, _ = M._t9_attack_plans(attach_view)
attach_plans, attach_reason = M._t9_successor_plans(attach_view, attach_attacks)
record(
    "bench_metal_successor_complete_plans",
    attach_reason is None and len(attach_plans) == 2
    and all(row["actions"][0]["kind"] == "MANUAL_METAL" for row in attach_plans),
)
evolve_obs = observations(CURRENT / "episode_89275349_replay.json")[88]
evolve_view = parsed(evolve_obs)
evolve_attacks, _ = M._t9_attack_plans(evolve_view)
evolve_plans, evolve_reason = M._t9_successor_plans(evolve_view, evolve_attacks)
ex_plans = [
    row for row in tuple(evolve_plans or ())
    if row["actions"][0].get("card_id") == M.ARCHALUDON_EX
]
record(
    "bench_evolve_alloy_successor_complete_plans",
    evolve_reason is None and len(ex_plans) == 2
    and all(row["actions"][1]["kind"] == "ASSEMBLE_ALLOY" for row in ex_plans),
)
reset()
handoff_action = M._pcrd_begin_transaction(evolve_view, ex_plans[0]["execution"]["plan"])
record(
    "bench_evolve_pcrd_handoff_valid",
    M._cum_valid_action(evolve_view, handoff_action)
    and M._pcrd_transaction is not None,
    action=handoff_action,
)
M._pcrd_clear("focused_handoff_complete")

result = {
    "candidate_main_sha256": hashlib.sha256((CANDIDATE / "main.py").read_bytes()).hexdigest().upper(),
    "fixture_count": len(RESULTS),
    "passed": len(RESULTS),
    "failed": 0,
    "results": RESULTS,
    "t9_conservation": M._t9_conservation(),
}
OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({"fixture_count": len(RESULTS), "status": "PASS"}, indent=2))
