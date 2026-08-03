"""Focused Task 7 exact-terminal Supporter arbitration fixtures."""
from __future__ import annotations

import copy
import importlib.util
import itertools
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "archaludon"
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_complete_supporter_purpose_arbitration_t7_v1"
)
REPLAY = (
    AUTO
    / "live/55155015/analysis_20260802/refresh"
    / "episode_89292594_replay.json"
)
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "infrastructure" / "tools")]

from ptcg_common import read_deck  # noqa: E402
from research.rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "task7_supporter_candidate", CANDIDATE / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = load_module()
RAW = json.loads(REPLAY.read_text(encoding="utf-8"))
SEAT = target_seat_for_deck(RAW, read_deck(CANDIDATE / "deck.csv"))
ANCHOR = next(
    copy.deepcopy(obs)
    for step, obs, _ in replay_decisions(RAW, SEAT)
    if step == 120
)
RESULTS = []


def record(name, condition, **evidence):
    assert condition, (name, evidence)
    RESULTS.append({"name": name, "status": "PASS", **evidence})


def mine(obs):
    return obs["current"]["players"][obs["current"]["yourIndex"]]


def opponent(obs):
    return obs["current"]["players"][1 - obs["current"]["yourIndex"]]


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


def for_seat(seat):
    return copy.deepcopy(ANCHOR) if SEAT == seat else mirror(ANCHOR)


def parsed(obs):
    return M.to_observation_class(copy.deepcopy(obs))


def semantic(obs, action):
    return M._cum_action_semantic(parsed(obs), action)


def valid(obs, action):
    return M._cum_valid_action(parsed(obs), action)


def card_option_position(obs, card_id):
    view = parsed(obs)
    rows = [
        position
        for position, option in enumerate(view.select.option)
        if M._pcrd_get(M.option_card(view, option), "id") == card_id
    ]
    assert rows
    return rows[0]


def clear_runtime():
    global_owner = getattr(M, "_t7_transaction", None)
    if global_owner is not None:
        M._t7_abort([], "fixture_reset")
    if M._pfgear_transaction is not None:
        M._pfgear_reset_active("fixture_reset")
    for name in M._PRACTICE_OWNER_GLOBALS:
        if hasattr(M, name):
            setattr(M, name, None)
    M._t7_transaction = None
    M._pfgear_transaction = None
    M._pfgear_veto_watch = None
    M._cum_active_transaction_owner = None
    M._cum_owner_meta = None
    if isinstance(M._public_boss_ledger, dict):
        M._public_boss_ledger["transaction"] = None


def call_agent(obs, parent_action, side_effect=None):
    calls = {"count": 0}

    def parent(_):
        calls["count"] += 1
        if side_effect is not None:
            side_effect()
        return list(parent_action)

    old = M._t7_parent_agent
    M._t7_parent_agent = parent
    try:
        action = M.agent(copy.deepcopy(obs))
    finally:
        M._t7_parent_agent = old
    assert calls["count"] == 1
    assert valid(obs, action)
    return action


def switch_prompt(start, certificate, *, reverse=False):
    obs = copy.deepcopy(start)
    seat = obs["current"]["yourIndex"]
    player = mine(obs)
    player["hand"] = [
        card for card in player["hand"]
        if not (
            card.get("id") == M.BOSS
            and card.get("serial") == certificate["supporter_serial"]
        )
    ]
    player["handCount"] = len(player["hand"])
    obs["current"]["supporterPlayed"] = True
    obs["current"]["turnActionCount"] += 1
    bench = list(opponent(obs)["bench"])
    options = [
        {
            "type": int(M.OptionType.CARD),
            "area": int(M.AreaType.BENCH),
            "index": index,
            "playerIndex": 1 - seat,
        }
        for index, card in enumerate(bench)
        if card is not None
    ]
    if reverse:
        options.reverse()
    obs["select"] = {
        "type": 0,
        "context": int(M.SelectContext.SWITCH),
        "contextCard": None,
        "effect": {
            "id": M.BOSS,
            "serial": certificate["supporter_serial"],
            "playerIndex": seat,
        },
        "minCount": 1,
        "maxCount": 1,
        "option": options,
        "deck": None,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
    }
    return obs


def post_gust_main(target_prompt, certificate, boss_from_gear=False):
    obs = copy.deepcopy(target_prompt)
    seat = obs["current"]["yourIndex"]
    other = opponent(obs)
    position = next(
        index for index, card in enumerate(other["bench"])
        if card is not None and card["serial"] == certificate["target_serial"]
    )
    old_active = other["active"][0]
    other["active"] = [other["bench"][position]]
    other["bench"][position] = old_active
    player = mine(obs)
    player["discard"].append({
        "id": M.BOSS,
        "serial": certificate["supporter_serial"],
        "playerIndex": seat,
    })
    obs["current"]["turnActionCount"] += 1
    obs["current"]["looking"] = None
    obs["select"] = {
        "type": 0,
        "context": int(M.SelectContext.MAIN),
        "contextCard": None,
        "effect": None,
        "minCount": 1,
        "maxCount": 1,
        "option": [{
            "type": int(M.OptionType.ATTACK),
            "attackId": certificate["attack_id"],
        }],
        "deck": None,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
    }
    return obs


def complete_direct(seat, *, reverse_start=False, reverse_target=False):
    clear_runtime()
    start = for_seat(seat)
    if reverse_start:
        start["select"]["option"].reverse()
    parent = [card_option_position(start, M.EXPLORER)]
    action = call_agent(start, parent)
    certificate = copy.deepcopy(M._t7_transaction["certificate"])
    record(
        f"anchor_seat{seat}_boss",
        semantic(start, action)[0][12][0] == M.BOSS,
        action=action,
        target_serial=certificate["target_serial"],
    )
    repeated = call_agent(start, parent)
    record(
        f"anchor_seat{seat}_boss_retry",
        semantic(start, repeated) == semantic(start, action),
    )
    target = switch_prompt(start, certificate, reverse=reverse_target)
    target_action = call_agent(target, [0])
    selected = M.option_card(parsed(target), parsed(target).select.option[target_action[0]])
    record(
        f"anchor_seat{seat}_canonical_target",
        M._pcrd_serial(selected) == certificate["target_serial"],
        target_serial=M._pcrd_serial(selected),
        tie_break=certificate["tie_break_key"],
    )
    target_retry = call_agent(target, [0])
    record(
        f"anchor_seat{seat}_target_retry",
        M._pcrd_serial(M.option_card(
            parsed(target), parsed(target).select.option[target_retry[0]]
        )) == certificate["target_serial"],
    )
    attack_obs = post_gust_main(target, certificate)
    attack = call_agent(attack_obs, [0])
    chosen = parsed(attack_obs).select.option[attack[0]]
    record(
        f"anchor_seat{seat}_metal_defender",
        M._pcrd_int(chosen.attackId) == M.METAL_DEFENDER,
    )
    completed = copy.deepcopy(attack_obs)
    completed["logs"].append({
        "type": int(M.LogType.ATTACK),
        "playerIndex": seat,
        "serial": certificate["attacker_serial"],
        "cardId": certificate["attacker_id"],
        "attackId": certificate["attack_id"],
    })
    call_agent(completed, [0])
    record(
        f"anchor_seat{seat}_complete",
        M._t7_transaction is None and M._t7_conservation()["holds"],
        conservation=M._t7_conservation(),
    )


def direct_controls(seat):
    # Exactly one HP beyond Metal Defender and no alternate Bench target.
    clear_runtime()
    hp221 = for_seat(seat)
    target = copy.deepcopy(opponent(hp221)["bench"][2])
    target["hp"] = target["maxHp"] = 221
    opponent(hp221)["bench"] = [target]
    parent = [card_option_position(hp221, M.EXPLORER)]
    returned = call_agent(hp221, parent)
    record(
        f"hp221_seat{seat}_parent",
        semantic(hp221, returned) == semantic(hp221, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    current = for_seat(seat)
    opponent(current)["active"][0]["hp"] = 220
    parent = [card_option_position(current, M.EXPLORER)]
    returned = call_agent(current, parent)
    record(
        f"current_terminal_seat{seat}_parent",
        semantic(current, returned) == semantic(current, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    used = for_seat(seat)
    used["current"]["supporterPlayed"] = True
    parent = [card_option_position(used, M.EXPLORER)]
    returned = call_agent(used, parent)
    record(
        f"supporter_used_seat{seat}_parent",
        semantic(used, returned) == semantic(used, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    illegal = for_seat(seat)
    view = parsed(illegal)
    boss_positions = {
        position
        for position, option in enumerate(view.select.option)
        if M._pcrd_get(M.option_card(view, option), "id") == M.BOSS
    }
    illegal["select"]["option"] = [
        option for position, option in enumerate(illegal["select"]["option"])
        if position not in boss_positions
    ]
    parent = [card_option_position(illegal, M.EXPLORER)]
    returned = call_agent(illegal, parent)
    record(
        f"boss_illegal_seat{seat}_parent",
        semantic(illegal, returned) == semantic(illegal, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    insufficient = for_seat(seat)
    mine(insufficient)["prize"].append(None)
    parent = [card_option_position(insufficient, M.EXPLORER)]
    returned = call_agent(insufficient, parent)
    record(
        f"prize_insufficient_seat{seat}_parent",
        semantic(insufficient, returned) == semantic(insufficient, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    no_bench = for_seat(seat)
    opponent(no_bench)["bench"] = []
    parent = [card_option_position(no_bench, M.EXPLORER)]
    returned = call_agent(no_bench, parent)
    record(
        f"no_bench_seat{seat}_parent",
        semantic(no_bench, returned) == semantic(no_bench, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    mixed = for_seat(seat)
    opponent(mixed)["bench"] = [
        copy.deepcopy(opponent(mixed)["bench"][0]),
        copy.deepcopy(opponent(mixed)["bench"][1]),
    ]
    certificate, reason = M._t7_complete_supporter_certificate(
        parsed(mixed), "DIRECT_HAND"
    )
    record(
        f"lunar_cycle_plus_exact_seat{seat}",
        certificate is not None
        and certificate["target_rejections"] == ()
        and certificate["target_serial"]
        == opponent(mixed)["bench"][1]["serial"],
        reason=reason,
    )

    clear_runtime()
    unknown = for_seat(seat)
    opponent(unknown)["bench"] = [
        copy.deepcopy(opponent(unknown)["bench"][0])
    ]
    parent = [card_option_position(unknown, M.EXPLORER)]
    old_hash = M._T7_LUNAR_CYCLE_TEXT_HASH
    M._T7_LUNAR_CYCLE_TEXT_HASH = "0" * 64
    try:
        returned = call_agent(unknown, parent)
    finally:
        M._T7_LUNAR_CYCLE_TEXT_HASH = old_hash
    record(
        f"all_target_metadata_unknown_seat{seat}_parent",
        semantic(unknown, returned) == semantic(unknown, parent)
        and M._t7_transaction is None,
    )

    clear_runtime()
    lunar = for_seat(seat)
    lunar_target = opponent(lunar)["bench"][0]
    lunar_view = parsed(lunar)
    projected = M._pfgear_project_gust(
        lunar_view, lunar_target["serial"]
    )
    source = M.active_pokemon(projected)
    target = M.opp_active_pokemon(projected)
    maps_before = (
        copy.deepcopy(M._PCRD_SUPPORTED_SKILLS),
        copy.deepcopy(M._PCRD_IN_PLAY_SKILL_CLASSIFICATIONS),
    )
    with_lunar = M._t7_scoped_attack_certificate(
        projected, source, M.METAL_DEFENDER, target
    )
    maps_after = (
        M._PCRD_SUPPORTED_SKILLS,
        M._PCRD_IN_PLAY_SKILL_CLASSIFICATIONS,
    )
    data = M.CARD_DB[M._T7_LUNAR_CYCLE_CARD_ID]
    saved_skills = list(data.skills)
    data.skills[:] = []
    try:
        without_lunar = M._pfgear_attack_certificate(
            projected, source, M.METAL_DEFENDER, target
        )
    finally:
        data.skills[:] = saved_skills
    record(
        f"lunar_cycle_combat_invariance_seat{seat}",
        with_lunar is not None
        and without_lunar is not None
        and tuple(
            with_lunar[key] for key in ("final_damage", "ko", "prize_yield")
        ) == tuple(
            without_lunar[key]
            for key in ("final_damage", "ko", "prize_yield")
        ),
    )
    record(
        f"lunar_cycle_global_scope_restored_seat{seat}",
        maps_before == maps_after,
    )
    original_skill = data.skills[0]
    data.skills[0] = type(original_skill)(
        name=original_skill.name,
        text=original_skill.text + "x",
    )
    try:
        mismatched = M._t7_scoped_attack_certificate(
            projected, source, M.METAL_DEFENDER, target
        )
    finally:
        data.skills[0] = original_skill
    record(
        f"lunar_cycle_one_char_mismatch_unknown_seat{seat}",
        mismatched is None
        and maps_before == (
            M._PCRD_SUPPORTED_SKILLS,
            M._PCRD_IN_PLAY_SKILL_CLASSIFICATIONS,
        ),
    )

    clear_runtime()
    owner = for_seat(seat)
    parent = [card_option_position(owner, M.EXPLORER)]
    returned = call_agent(
        owner,
        parent,
        side_effect=lambda: setattr(
            M, "_cum_active_transaction_owner", "FIXTURE_OWNER"
        ),
    )
    record(
        f"owner_collision_seat{seat}_parent",
        semantic(owner, returned) == semantic(owner, parent)
        and M._t7_transaction is None,
    )
    M._cum_active_transaction_owner = None

    clear_runtime()
    hidden_a = for_seat(seat)
    hidden_b = copy.deepcopy(hidden_a)
    opponent(hidden_a)["hand"] = [{
        "id": M.EXPLORER, "serial": 8001, "playerIndex": 1 - seat,
    }]
    opponent(hidden_b)["hand"] = [{
        "id": M.LILLIE, "serial": 8002, "playerIndex": 1 - seat,
    }]
    cert_a, _ = M._t7_complete_supporter_certificate(
        parsed(hidden_a), "DIRECT_HAND"
    )
    cert_b, _ = M._t7_complete_supporter_certificate(
        parsed(hidden_b), "DIRECT_HAND"
    )
    record(
        f"hidden_hand_invariance_seat{seat}",
        cert_a is not None
        and cert_b is not None
        and cert_a["public_input_hash"] == cert_b["public_input_hash"]
        and cert_a["tie_break_key"] == cert_b["tie_break_key"],
    )


def gear_start(seat):
    obs = for_seat(seat)
    player = mine(obs)
    boss = next(card for card in player["hand"] if card["id"] == M.BOSS)
    boss_index = player["hand"].index(boss)
    boss_position = next(
        position
        for position, option in enumerate(obs["select"]["option"])
        if option.get("type") == int(M.OptionType.PLAY)
        and option.get("index") == boss_index
    )
    boss["id"] = M.POKEGEAR
    obs["select"]["option"][boss_position]["index"] = boss_index
    return obs


def reveal_prompt(
    start,
    certificate,
    subset,
    *,
    reverse=False,
    duplicate=False,
    option_only_reverse=False,
):
    obs = copy.deepcopy(start)
    seat = obs["current"]["yourIndex"]
    player = mine(obs)
    gear = next(
        card for card in player["hand"]
        if card["id"] == M.POKEGEAR
        and card["serial"] == certificate["gear_serial"]
    )
    player["hand"].remove(gear)
    player["handCount"] = len(player["hand"])
    player["deckCount"] -= certificate["gear_reveal_count"]
    cards = []
    serial = 3000 + seat * 100
    for card_id in subset:
        cards.append({"id": card_id, "serial": serial, "playerIndex": seat})
        serial += 1
    if duplicate and M.BOSS in subset:
        cards.append({"id": M.BOSS, "serial": serial, "playerIndex": seat})
        serial += 1
    while len(cards) < certificate["gear_reveal_count"]:
        cards.append({
            "id": M.METAL_ENERGY,
            "serial": serial,
            "playerIndex": seat,
        })
        serial += 1
    if reverse:
        cards.reverse()
    obs["current"]["looking"] = cards
    obs["current"]["turnActionCount"] += 1
    options = [
        {
            "type": int(M.OptionType.CARD),
            "area": int(M.AreaType.LOOKING),
            "index": index,
            "playerIndex": seat,
        }
        for index, card in enumerate(cards)
        if card["id"] in {M.BOSS, M.EXPLORER, M.LILLIE}
    ]
    if reverse or option_only_reverse:
        options.reverse()
    obs["select"] = {
        "type": 0,
        "context": int(M.SelectContext.TO_HAND),
        "contextCard": None,
        "effect": copy.deepcopy(gear),
        "minCount": 0,
        "maxCount": 1,
        "option": options,
        "deck": None,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
    }
    return obs


def miss_main(start, certificate):
    obs = copy.deepcopy(start)
    seat = obs["current"]["yourIndex"]
    player = mine(obs)
    gear = next(
        card for card in player["hand"]
        if card["id"] == M.POKEGEAR
        and card["serial"] == certificate["gear_serial"]
    )
    player["hand"].remove(gear)
    player["handCount"] = len(player["hand"])
    player["discard"].append(copy.deepcopy(gear))
    obs["current"]["turnActionCount"] += 2
    obs["current"]["looking"] = None
    obs["select"] = {
        "type": 0,
        "context": int(M.SelectContext.MAIN),
        "contextCard": None,
        "effect": None,
        "minCount": 1,
        "maxCount": 1,
        "option": [{
            "type": int(M.OptionType.ATTACK),
            "attackId": certificate["attack_id"],
        }],
        "deck": None,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
    }
    return obs


def acquired_main(start, certificate, selected_boss):
    obs = copy.deepcopy(start)
    seat = obs["current"]["yourIndex"]
    player = mine(obs)
    gear = next(
        card for card in player["hand"]
        if card["id"] == M.POKEGEAR
        and card["serial"] == certificate["gear_serial"]
    )
    player["hand"].remove(gear)
    player["hand"].append(copy.deepcopy(selected_boss))
    player["handCount"] = len(player["hand"])
    player["discard"].append(copy.deepcopy(gear))
    player["deckCount"] -= 1
    obs["current"]["turnActionCount"] += 2
    obs["current"]["looking"] = None
    boss_index = len(player["hand"]) - 1
    obs["select"] = {
        "type": 0,
        "context": int(M.SelectContext.MAIN),
        "contextCard": None,
        "effect": None,
        "minCount": 1,
        "maxCount": 1,
        "option": [
            {"type": int(M.OptionType.PLAY), "index": boss_index},
            {
                "type": int(M.OptionType.ATTACK),
                "attackId": certificate["attack_id"],
            },
        ],
        "deck": None,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
    }
    return obs


def gear_hit_complete(seat):
    clear_runtime()
    start = gear_start(seat)
    certificate, reason = M._t7_complete_supporter_certificate(
        parsed(start), "POKEGEAR"
    )
    assert certificate is not None, reason
    first = M._pfgear_begin(parsed(start), certificate)
    assert first is not None
    reveal = reveal_prompt(
        start, certificate, (M.BOSS, M.EXPLORER, M.LILLIE), reverse=True
    )
    reveal_action = M._pfgear_resume(parsed(reveal), [])
    selected_boss = copy.deepcopy(M.option_card(
        parsed(reveal), parsed(reveal).select.option[reveal_action[0]]
    ).__dict__)
    bound_certificate = copy.deepcopy(M._pfgear_transaction["certificate"])
    main = acquired_main(start, bound_certificate, selected_boss)
    boss_action = M._pfgear_resume(parsed(main), [1])
    record(
        f"gear_hit_seat{seat}_boss_play",
        M._pcrd_get(M.option_card(
            parsed(main), parsed(main).select.option[boss_action[0]]
        ), "id") == M.BOSS,
    )
    target = switch_prompt(main, bound_certificate, reverse=bool(seat))
    target_action = M._pfgear_resume(parsed(target), [0])
    chosen_target = M.option_card(
        parsed(target), parsed(target).select.option[target_action[0]]
    )
    record(
        f"gear_hit_seat{seat}_canonical_target",
        M._pcrd_serial(chosen_target) == bound_certificate["target_serial"],
    )
    attack_obs = post_gust_main(target, bound_certificate)
    attack = M._pfgear_resume(parsed(attack_obs), [0])
    record(
        f"gear_hit_seat{seat}_metal_defender",
        parsed(attack_obs).select.option[attack[0]].attackId
        == M.METAL_DEFENDER,
    )
    completed = copy.deepcopy(attack_obs)
    completed["logs"].append({
        "type": int(M.LogType.ATTACK),
        "playerIndex": seat,
        "serial": bound_certificate["attacker_serial"],
        "cardId": bound_certificate["attacker_id"],
        "attackId": bound_certificate["attack_id"],
    })
    M._pfgear_resume(parsed(completed), [0])
    record(
        f"gear_hit_seat{seat}_complete",
        M._pfgear_transaction is None
        and M._pfgear_conservation()["positive"]["holds"],
        conservation=M._pfgear_conservation()["positive"],
    )


def gear_subsets(seat):
    ids = (M.BOSS, M.EXPLORER, M.LILLIE)
    for bits in itertools.product((False, True), repeat=3):
        clear_runtime()
        subset = tuple(card_id for card_id, keep in zip(ids, bits) if keep)
        start = gear_start(seat)
        certificate, reason = M._t7_complete_supporter_certificate(
            parsed(start), "POKEGEAR"
        )
        assert certificate is not None, reason
        started = M._pfgear_begin(parsed(start), certificate)
        assert started is not None
        reveal = reveal_prompt(
            start,
            certificate,
            subset,
            reverse=bool(sum(bits) % 2),
        )
        action = M._pfgear_resume(parsed(reveal), [])
        has_boss = M.BOSS in subset
        if has_boss:
            selected = M.option_card(
                parsed(reveal), parsed(reveal).select.option[action[0]]
            )
            condition = (
                M._pcrd_get(selected, "id") == M.BOSS
                and M._pfgear_transaction["stage"] == "GEAR_HIT_EMITTED"
            )
        else:
            condition = (
                action == []
                and M._pfgear_transaction["stage"] == "MISS_EMPTY_EMITTED"
                and M._pfgear_transaction["certificate"]["selected_route"]
                is None
            )
        label = "".join("BEL"[index] for index, bit in enumerate(bits) if bit)
        record(
            f"gear_subset_{label or 'empty'}_seat{seat}",
            condition,
            subset=subset,
            action=action,
        )
        retry = M._pfgear_resume(parsed(reveal), [])
        record(
            f"gear_subset_{label or 'empty'}_retry_seat{seat}",
            retry == action,
        )
        if not has_boss:
            returned = M._pfgear_resume(
                parsed(miss_main(start, certificate)), [0]
            )
            record(
                f"gear_subset_{label or 'empty'}_miss_clear_seat{seat}",
                returned == [0] and M._pfgear_transaction is None,
            )

    clear_runtime()
    start = gear_start(seat)
    certificate, reason = M._t7_complete_supporter_certificate(
        parsed(start), "POKEGEAR"
    )
    assert certificate is not None, reason
    M._pfgear_begin(parsed(start), certificate)
    reveal = reveal_prompt(
        start,
        certificate,
        (M.BOSS, M.EXPLORER, M.LILLIE),
        reverse=True,
        duplicate=True,
    )
    action = M._pfgear_resume(parsed(reveal), [])
    selected = M.option_card(
        parsed(reveal), parsed(reveal).select.option[action[0]]
    )
    bosses = sorted(
        card["serial"] for card in reveal["current"]["looking"]
        if card["id"] == M.BOSS
    )
    record(
        f"gear_duplicate_boss_min_serial_seat{seat}",
        M._pcrd_serial(selected) == bosses[0],
        selected=M._pcrd_serial(selected),
        bosses=bosses,
    )


def gear_option_order_certificate(seat):
    variants = []
    for option_only_reverse in (False, True):
        clear_runtime()
        start = gear_start(seat)
        certificate, reason = M._t7_complete_supporter_certificate(
            parsed(start), "POKEGEAR"
        )
        assert certificate is not None, reason
        assert M._pfgear_begin(parsed(start), certificate) is not None
        reveal = reveal_prompt(
            start,
            certificate,
            (M.BOSS, M.EXPLORER, M.LILLIE),
            duplicate=True,
            option_only_reverse=option_only_reverse,
        )
        action = M._pfgear_resume(parsed(reveal), [])
        selected = M.option_card(
            parsed(reveal), parsed(reveal).select.option[action[0]]
        )
        emitted = copy.deepcopy(M._pfgear_transaction["certificate"])
        last_fingerprint = M._pfgear_transaction["last_fingerprint"]
        last_roles = tuple(M._pfgear_transaction["last_roles"])
        retry = M._pfgear_resume(parsed(reveal), [])
        retried = copy.deepcopy(M._pfgear_transaction["certificate"])
        variants.append({
            "looking": copy.deepcopy(reveal["current"]["looking"]),
            "options": copy.deepcopy(reveal["select"]["option"]),
            "action": action,
            "retry": retry,
            "selected_boss": M._pfgear_card_ref(selected),
            "emitted": emitted,
            "retried": retried,
            "last_fingerprint": last_fingerprint,
            "last_roles": last_roles,
        })

    normal, reversed_options = variants
    record(
        f"gear_option_only_reversal_shape_seat{seat}",
        normal["looking"] == reversed_options["looking"]
        and normal["options"] == list(reversed(reversed_options["options"])),
    )
    record(
        f"gear_option_only_reversal_certificate_seat{seat}",
        normal["selected_boss"] == reversed_options["selected_boss"]
        and normal["emitted"]["selected_route"]
        == reversed_options["emitted"]["selected_route"]
        and normal["emitted"]["certificate_hash"]
        == reversed_options["emitted"]["certificate_hash"]
        and normal["emitted"]["reveal_option_hash"]
        == reversed_options["emitted"]["reveal_option_hash"]
        and normal["emitted"]["per_supporter_rejection"]
        == reversed_options["emitted"]["per_supporter_rejection"]
        and all(
            variant["emitted"]["callback_fingerprint"]
            == variant["last_fingerprint"]
            and tuple(variant["emitted"]["callback_roles"])
            == variant["last_roles"]
            and len(variant["last_roles"]) == 1
            for variant in variants
        ),
        selected_boss=normal["selected_boss"],
        certificate_hash=normal["emitted"]["certificate_hash"],
    )
    record(
        f"gear_option_only_reversal_duplicate_seat{seat}",
        normal["retry"] == normal["action"]
        and reversed_options["retry"] == reversed_options["action"]
        and normal["retried"]["duplicate_count"] == 1
        and reversed_options["retried"]["duplicate_count"] == 1
        and normal["retried"]["certificate_hash"]
        == reversed_options["retried"]["certificate_hash"],
        certificate_hash=normal["retried"]["certificate_hash"],
    )


for checked_seat in (0, 1):
    complete_direct(
        checked_seat,
        reverse_start=bool(checked_seat),
        reverse_target=not bool(checked_seat),
    )
    direct_controls(checked_seat)
    gear_subsets(checked_seat)
    gear_option_order_certificate(checked_seat)
    gear_hit_complete(checked_seat)

clear_runtime()
summary = {
    "fixture_count": len(RESULTS),
    "passed": len(RESULTS),
    "failed": 0,
    "anchor_replay": str(REPLAY),
    "anchor_seat": SEAT,
    "results": RESULTS,
    "t7_counters": dict(M._t7_counters),
    "t7_conservation": M._t7_conservation(),
    "pfgear_conservation": M._pfgear_conservation(),
}
assert summary["t7_conservation"]["holds"]
Path(__file__).with_name("focused_fixture_results.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    key: summary[key] for key in ("fixture_count", "passed", "failed")
}, sort_keys=True))
