"""Focused Task 7 regression plus Task 8 Lillie arbitration fixtures."""
from __future__ import annotations

import copy
import importlib.util
import itertools
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1"
)
REPLAY = (
    AUTO
    / "live/55155015/analysis_20260802/refresh"
    / "episode_89292594_replay.json"
)
HISTORICAL_REPLAY_DIR = AUTO / (
    "live/55070349/refresh_20260729_1241/"
    "shadow_corpus_196_prior_plus_11_new"
)
CURRENT_REPLAY_DIR = AUTO / "live/55155015/analysis_20260802/refresh"
EXACT_REJECTIONS = (
    (
        HISTORICAL_REPLAY_DIR / "episode_88035562_replay.json",
        30,
        [6],
        "EXACT_EVOLUTION_ROUTE",
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88357830_replay.json",
        69,
        [2],
        "EXACT_EVOLUTION_ROUTE",
    ),
    (
        CURRENT_REPLAY_DIR / "episode_89289898_replay.json",
        31,
        [0],
        "PARENT_DECLARED_SUPPORTER",
    ),
)
EXACT_ICE_REJECTIONS = (
    (CURRENT_REPLAY_DIR / "episode_89288811_replay.json", 78, [0]),
    (CURRENT_REPLAY_DIR / "episode_89286075_replay.json", 123, [2]),
    (CURRENT_REPLAY_DIR / "episode_89308835_replay.json", 107, [0]),
    (HISTORICAL_REPLAY_DIR / "episode_88397927_replay.json", 119, [2]),
    (HISTORICAL_REPLAY_DIR / "episode_88482123_replay.json", 54, [4]),
    (HISTORICAL_REPLAY_DIR / "episode_88579549_replay.json", 128, [0]),
)
EXACT_DUPLICATE_SUPPORTER_REJECTION = (
    HISTORICAL_REPLAY_DIR / "episode_87868636_replay.json",
    49,
    51,
)
EXACT_GEAR_REVEAL_SUPPORTER_REJECTIONS = (
    (
        CURRENT_REPLAY_DIR / "episode_89291523_replay.json",
        17, [1], 1185,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_87672938_replay.json",
        77, [0], 1182,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88197270_replay.json",
        13, [1], 1185,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88338429_replay.json",
        17, [0], 1182,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88507294_replay.json",
        86, [1], 1185,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88589778_replay.json",
        96, [0], 1185,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88660007_replay.json",
        30, [0], 1185,
    ),
    (
        HISTORICAL_REPLAY_DIR / "episode_88682711_replay.json",
        77, [3], 1185,
    ),
)
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "tools")]

from ptcg_common import read_deck  # noqa: E402
from rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "task8_lillie_candidate", CANDIDATE / "main.py"
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


def t8_main_options(obs, *, attack=True, end=True, extra=()):
    options = list(extra)
    if attack:
        options.append({
            "type": int(M.OptionType.ATTACK),
            "attackId": M.METAL_DEFENDER,
        })
    if end:
        options.append({"type": int(M.OptionType.END)})
    obs["select"] = {
        "type": 0,
        "context": int(M.SelectContext.MAIN),
        "contextCard": None,
        "effect": None,
        "minCount": 1,
        "maxCount": 1,
        "option": options,
        "deck": None,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
    }


def t8_base(seat, card_ids, *, prizes=5, deck_count=30, bench=None):
    obs = for_seat(seat)
    player = mine(obs)
    player["hand"] = [
        {"id": card_id, "serial": 6000 + seat * 100 + index, "playerIndex": seat}
        for index, card_id in enumerate(card_ids)
    ]
    player["handCount"] = len(player["hand"])
    player["deckCount"] = deck_count
    player["prize"] = [None] * prizes
    player["discard"] = []
    if bench is not None:
        player["bench"] = copy.deepcopy(bench)
    obs["current"]["supporterPlayed"] = False
    obs["current"]["energyAttached"] = False
    obs["current"]["result"] = -1
    obs["current"]["looking"] = None
    extras = [
        {"type": int(M.OptionType.PLAY), "index": index}
        for index, card in enumerate(player["hand"])
        if card["id"] in {
            M.LILLIE, M.POKEGEAR, M.DURALUDON, M.POKE_PAD,
            M.ULTRA_BALL, M.NIGHT_STRETCHER, M.JUMBO_ICE_CREAM,
            M.HERO_CAPE,
            M.FULL_METAL_LAB, M.BOSS, M.EXPLORER,
        }
    ]
    t8_main_options(obs, extra=extras)
    return obs


def t8_position(obs, *, card_id=None, option_type=None, serial=None):
    view = parsed(obs)
    rows = []
    for position, option in enumerate(view.select.option):
        card = M.option_card(view, option)
        if option_type is not None and option.type != option_type:
            continue
        if card_id is not None and M._pcrd_get(card, "id") != card_id:
            continue
        if serial is not None and M._pcrd_serial(card) != serial:
            continue
        rows.append(position)
    assert rows, (card_id, option_type, serial, obs["select"]["option"])
    return rows[0]


def call_t8_agent(obs, parent_action, side_effect=None):
    calls = {"count": 0}

    def parent(_):
        calls["count"] += 1
        if side_effect is not None:
            side_effect()
        return list(parent_action)

    old = M._t8_parent_agent
    M._t8_parent_agent = parent
    try:
        action = M.agent(copy.deepcopy(obs))
    finally:
        M._t8_parent_agent = old
    assert calls["count"] == 1
    assert valid(obs, action)
    return action


def t8_lillie_post(start, certificate, *, redraw_ids=None):
    obs = copy.deepcopy(start)
    seat = obs["current"]["yourIndex"]
    player = mine(obs)
    lillie = next(
        card for card in player["hand"]
        if card["id"] == M.LILLIE
        and card["serial"] == certificate["supporter_serial"]
    )
    player["discard"].append(copy.deepcopy(lillie))
    draw_n = certificate["transform"]["post_hand_count"]
    ids = list(redraw_ids or ([M.CINDERACE] * draw_n))
    assert len(ids) == draw_n
    player["hand"] = [
        {"id": card_id, "serial": 9000 + index, "playerIndex": seat}
        for index, card_id in enumerate(ids)
    ]
    player["handCount"] = draw_n
    player["deckCount"] = certificate["transform"]["post_deck_count"]
    obs["current"]["supporterPlayed"] = True
    obs["current"]["turnActionCount"] += 1
    t8_main_options(obs, attack=False)
    return obs


def t8_direct_play_and_counts(seat, prizes):
    clear_runtime()
    start = t8_base(seat, (M.LILLIE, M.CINDERACE), prizes=prizes)
    parent = [t8_position(start, card_id=M.LILLIE)]
    action = call_t8_agent(start, parent)
    certificate = copy.deepcopy(M._pfgear_transaction["certificate"])
    draw_n = 8 if prizes == 6 else 6
    record(
        f"t8_direct_play_draw{draw_n}_seat{seat}",
        M._t8_last_telemetry["direction"] == "PLAY_LILLIE"
        and semantic(start, action)[0][12][0] == M.LILLIE
        and certificate["transform"]["draw_n"] == draw_n
        and certificate["transform"]["shuffle_count"] == 1
        and certificate["transform"]["post_deck_count"] == 31 - draw_n
        and not certificate["unknown_redraw_identity_assumed"],
        transform=certificate["transform"],
    )
    retry = M._pfgear_resume(parsed(start), parent)
    record(
        f"t8_direct_retry_seat{seat}_prizes{prizes}",
        semantic(start, retry) == semantic(start, action)
        and M._pfgear_transaction["certificate"]["duplicate_count"] == 1,
    )
    post = t8_lillie_post(start, certificate)
    M._pfgear_resume(parsed(post), [0])
    record(
        f"t8_direct_complete_seat{seat}_prizes{prizes}",
        M._pfgear_transaction is None and M._t8_conservation()["holds"],
        conservation=M._t8_conservation(),
    )


def t8_hidden_redraw_invariance(seat):
    variants = []
    for redraw_ids in (
        [M.CINDERACE] * 6,
        [M.DURALUDON, M.ARCHALUDON, M.METAL_ENERGY,
         M.BOSS, M.EXPLORER, M.LILLIE],
    ):
        clear_runtime()
        start = t8_base(seat, (M.LILLIE, M.CINDERACE), prizes=5)
        parent = [t8_position(start, card_id=M.LILLIE)]
        action = call_t8_agent(start, parent)
        certificate = copy.deepcopy(M._pfgear_transaction["certificate"])
        post = t8_lillie_post(start, certificate, redraw_ids=redraw_ids)
        M._pfgear_resume(parsed(post), [0])
        variants.append((semantic(start, action), certificate["certificate_hash"]))
    record(
        f"t8_hidden_redraw_identity_invariance_seat{seat}",
        variants[0] == variants[1] and M._pfgear_transaction is None,
        variants=variants,
    )


def t8_zero_bench_materialize(seat):
    clear_runtime()
    start = t8_base(
        seat, (M.LILLIE, M.DURALUDON), prizes=5, bench=[]
    )
    parent = [t8_position(start, card_id=M.LILLIE)]
    action = call_t8_agent(start, parent)
    chosen = M.option_card(parsed(start), parsed(start).select.option[action[0]])
    certificate = copy.deepcopy(M._pfgear_transaction["certificate"])
    materializer = copy.deepcopy(M._pfgear_transaction["materializer"])
    record(
        f"t8_zero_bench_materialize_seat{seat}",
        M._t8_last_telemetry["direction"] == "MATERIALIZE_THEN_REEVALUATE"
        and M._pcrd_get(chosen, "id") == M.DURALUDON
        and materializer["route"]["reason"] == "ZERO_BENCH_BASIC",
        required_refs=certificate["physical_routes"]["required_refs"],
    )
    post = copy.deepcopy(start)
    player = mine(post)
    basic = next(card for card in player["hand"] if card["id"] == M.DURALUDON)
    player["hand"].remove(basic)
    player["handCount"] -= 1
    player["bench"].append({
        **copy.deepcopy(basic),
        "hp": M.CARD_DB[M.DURALUDON].hp,
        "maxHp": M.CARD_DB[M.DURALUDON].hp,
        "appearThisTurn": True,
        "energies": [],
        "energyCards": [],
        "tools": [],
        "preEvolution": [],
    })
    post["current"]["turnActionCount"] += 1
    t8_main_options(post, attack=True)
    M._pfgear_resume(parsed(post), [0])
    record(
        f"t8_zero_bench_materializer_complete_seat{seat}",
        M._pfgear_transaction is None and M._t8_conservation()["holds"],
    )


def t8_one_metal_materialize(seat):
    clear_runtime()
    start = t8_base(seat, (M.LILLIE, M.METAL_ENERGY), prizes=5)
    player = mine(start)
    active = player["active"][0]
    active["energyCards"] = active["energyCards"][:2]
    active["energies"] = active["energies"][:2]
    metal_index = next(
        index for index, card in enumerate(player["hand"])
        if card["id"] == M.METAL_ENERGY
    )
    extra = [
        {"type": int(M.OptionType.PLAY), "index": 0},
        {
            "type": int(M.OptionType.ATTACH),
            "area": int(M.AreaType.HAND),
            "index": metal_index,
            "inPlayArea": int(M.AreaType.ACTIVE),
            "inPlayIndex": 0,
        },
    ]
    t8_main_options(start, attack=False, extra=extra)
    parent = [t8_position(start, card_id=M.LILLIE)]
    action = call_t8_agent(start, parent)
    selected = parsed(start).select.option[action[0]]
    record(
        f"t8_one_metal_materialize_seat{seat}",
        M._t8_last_telemetry["direction"] == "MATERIALIZE_THEN_REEVALUATE"
        and selected.type == M.OptionType.ATTACH
        and M._pfgear_transaction["materializer"]["route"]["reason"]
        in {"CURRENT_ATTACK_MANUAL_METAL", "TURBO_COMPLETION_MANUAL_METAL"},
    )
    M._t8_abort([], "fixture_settle_one_metal")


def t8_exact_evolution_materialize(seat):
    clear_runtime()
    start = t8_base(seat, (M.LILLIE, M.ARCHALUDON), prizes=5)
    player = mine(start)
    duraludon = copy.deepcopy(player["bench"][0])
    duraludon["appearThisTurn"] = False
    duraludon["energyCards"] = copy.deepcopy(player["active"][0]["energyCards"])
    duraludon["energies"] = list(player["active"][0]["energies"])
    player["active"] = [duraludon]
    player["bench"] = []
    extra = [
        {"type": int(M.OptionType.PLAY), "index": 0},
        {
            "type": int(M.OptionType.EVOLVE),
            "area": int(M.AreaType.HAND),
            "index": 1,
            "inPlayArea": int(M.AreaType.ACTIVE),
            "inPlayIndex": 0,
        },
    ]
    t8_main_options(start, attack=False, extra=extra)
    parent = [t8_position(start, card_id=M.LILLIE)]
    action = call_t8_agent(start, parent)
    selected = parsed(start).select.option[action[0]]
    record(
        f"t8_exact_evolution_materialize_seat{seat}",
        M._t8_last_telemetry["direction"] == "MATERIALIZE_THEN_REEVALUATE"
        and selected.type == M.OptionType.EVOLVE
        and M._pfgear_transaction["materializer"]["route"]["reason"]
        == "EXACT_EVOLUTION_ROUTE",
        materializer=M._pfgear_transaction["materializer"],
    )
    M._t8_abort([], "fixture_settle_exact_evolution")


def t8_protected_route_holds(seat):
    cases = []

    recovery = t8_base(
        seat, (M.LILLIE, M.NIGHT_STRETCHER), prizes=5
    )
    mine(recovery)["discard"].append({
        "id": M.DURALUDON,
        "serial": 8600 + seat,
        "playerIndex": seat,
    })
    cases.append((
        "recovery",
        recovery,
        "NIGHT_STRETCHER_RECOVERY_ROUTE",
    ))

    backup = t8_base(seat, (M.LILLIE, M.METAL_ENERGY), prizes=5)
    backup["current"]["energyAttached"] = True
    bench = mine(backup)["bench"][0]
    bench["id"] = M.ARCHALUDON
    bench["hp"] = bench["maxHp"] = M.CARD_DB[M.ARCHALUDON].hp
    bench["energyCards"] = [
        {"id": M.METAL_ENERGY, "serial": 8700 + seat * 10 + index,
         "playerIndex": seat}
        for index in range(2)
    ]
    bench["energies"] = [M.METAL_ENERGY, M.METAL_ENERGY]
    cases.append((
        "ready_backup",
        backup,
        "CERTIFIED_NEXT_ATTACKER_METAL",
    ))

    declared_boss = t8_base(
        seat, (M.LILLIE, M.BOSS), prizes=5
    )
    boss_active = copy.deepcopy(opponent(declared_boss)["active"][0])
    boss_active.update({
        "id": M.DURALUDON,
        "hp": M.CARD_DB[M.DURALUDON].hp,
        "maxHp": M.CARD_DB[M.DURALUDON].hp,
        "energyCards": [],
        "energies": [],
        "tools": [],
        "preEvolution": [],
        "appearThisTurn": False,
    })
    boss_target = copy.deepcopy(opponent(declared_boss)["bench"][0])
    boss_target.update({
        "id": M.ARCHALUDON_EX,
        "hp": 220,
        "maxHp": M.CARD_DB[M.ARCHALUDON_EX].hp,
        "energyCards": [],
        "energies": [],
        "tools": [],
        "preEvolution": [],
        "appearThisTurn": False,
    })
    opponent(declared_boss)["active"] = [boss_active]
    opponent(declared_boss)["bench"] = [boss_target]
    cases.append((
        "declared_boss",
        declared_boss,
        "CONCRETE_BOSS_TARGET_ROUTE",
    ))

    for label, start, expected_reason in cases:
        clear_runtime()
        parent = [t8_position(start, card_id=M.LILLIE)]
        action = call_t8_agent(start, parent)
        certificate = M._t8_last_certificate
        reasons = tuple(
            route["reason"]
            for route in certificate["physical_routes"]["held"]
        ) if certificate is not None else ()
        record(
            f"t8_{label}_physical_hold_seat{seat}",
            M._t8_last_telemetry["direction"] == "HOLD_LILLIE"
            and parsed(start).select.option[action[0]].type
            == M.OptionType.ATTACK
            and expected_reason in reasons,
            reasons=reasons,
            rejection=M._t8_last_telemetry["rejection_reason"],
        )


def t8_direct_precedes_gear(seat):
    clear_runtime()
    start = t8_base(
        seat, (M.LILLIE, M.POKEGEAR, M.CINDERACE), prizes=5
    )
    gear_common, gear_reason = M._t8_gear_common(parsed(start))
    parent = [t8_position(start, card_id=M.POKEGEAR)]
    action = call_t8_agent(start, parent)
    selected = M.option_card(parsed(start), parsed(start).select.option[action[0]])
    record(
        f"t8_direct_lillie_precedes_gear_seat{seat}",
        gear_common is None
        and gear_reason == "direct_lillie_has_priority"
        and M._pcrd_get(selected, "id") == M.LILLIE
        and M._t8_last_telemetry["direction"] == "PLAY_LILLIE",
        gear_reason=gear_reason,
    )
    M._t8_abort([], "fixture_settle_direct_precedence")


def t8_future_hold_and_duplicates(seat):
    clear_runtime()
    start = t8_base(
        seat,
        (M.LILLIE, M.ARCHALUDON, M.ARCHALUDON),
        prizes=5,
    )
    player = mine(start)
    target = copy.deepcopy(player["bench"][0])
    target["appearThisTurn"] = True
    target["energyCards"] = [
        {
            **copy.deepcopy(card),
            "serial": 8100 + seat * 10 + index,
        }
        for index, card in enumerate(player["active"][0]["energyCards"])
    ]
    target["energies"] = list(player["active"][0]["energies"])
    player["bench"] = [target]
    t8_main_options(start, extra=[
        {"type": int(M.OptionType.PLAY), "index": 0},
    ])
    parent = [t8_position(start, card_id=M.LILLIE)]
    action = call_t8_agent(start, parent)
    certificate = copy.deepcopy(M._t8_last_certificate)
    future = tuple(
        route for route in certificate["physical_routes"]["held"]
        if route["reason"] == "FUTURE_EVOLUTION_ATTACK_ROUTE"
    )
    record(
        f"t8_future_evolution_hold_seat{seat}",
        M._t8_last_telemetry["direction"] == "HOLD_LILLIE"
        and parsed(start).select.option[action[0]].type == M.OptionType.ATTACK
        and future
        and all(route["available_copy_count"] == 2 for route in future)
        and len({route["serial"] for route in future}) == len(future),
        required_refs=certificate["physical_routes"]["required_refs"],
        direction=M._t8_last_telemetry["direction"],
        rejection=M._t8_last_telemetry["rejection_reason"],
        hand=mine(start)["hand"],
        routes=certificate["physical_routes"],
        action=action,
    )

    clear_runtime()
    duplicate = t8_base(
        seat, (M.LILLIE, M.DURALUDON, M.DURALUDON), prizes=5, bench=[]
    )
    parent = [t8_position(duplicate, card_id=M.LILLIE)]
    action = call_t8_agent(duplicate, parent)
    selected = M.option_card(parsed(duplicate), parsed(duplicate).select.option[action[0]])
    duraludon_serials = sorted(
        card["serial"] for card in mine(duplicate)["hand"]
        if card["id"] == M.DURALUDON
    )
    record(
        f"t8_duplicate_minimum_only_seat{seat}",
        M._pcrd_serial(selected) == duraludon_serials[0]
        and M._pfgear_transaction["materializer"]["route"]["available_copy_count"] == 2,
        selected=M._pcrd_serial(selected),
        copies=duraludon_serials,
    )
    M._t8_abort([], "fixture_settle_duplicate")


def t8_negative_counts(seat):
    for label, cards, deck_count, expected_reason in (
        (
            "neutral_count",
            (M.LILLIE,) + (M.CINDERACE,) * 5,
            30,
            "NO_PUBLIC_COUNT_BENEFIT",
        ),
        (
            "post_deck_zero",
            (M.LILLIE,) + (M.CINDERACE,) * 5,
            1,
            "POST_LILLIE_DECK_BELOW_ONE",
        ),
    ):
        clear_runtime()
        start = t8_base(seat, cards, prizes=5, deck_count=deck_count)
        parent = [t8_position(start, card_id=M.LILLIE)]
        action = call_t8_agent(start, parent)
        cert = M._t8_last_certificate
        record(
            f"t8_{label}_hold_seat{seat}",
            M._t8_last_telemetry["direction"] == "HOLD_LILLIE"
            and parsed(start).select.option[action[0]].type == M.OptionType.ATTACK
            and expected_reason in tuple(cert["completion_reason"]),
            transform=cert["transform"],
        )


def t8_mind_ruler_boundaries(seat):
    for label, hand_count, hp, expected_direction in (
        ("survival", 8, 400, "PLAY_LILLIE"),
        ("worsening", 3, 300, "HOLD_LILLIE"),
    ):
        clear_runtime()
        cards = (M.LILLIE,) + (M.CINDERACE,) * (hand_count - 1)
        start = t8_base(seat, cards, prizes=5)
        target = mine(start)["active"][0]
        target["hp"] = target["maxHp"] = hp
        fire = {
            "id": 2, "serial": 7700 + seat, "playerIndex": 1 - seat,
        }
        chandelure = opponent(start)["active"][0]
        chandelure.update({
            "id": 98,
            "hp": 130,
            "maxHp": 130,
            "energyCards": [fire],
            "energies": [2],
            "tools": [],
            "preEvolution": [],
            "appearThisTurn": False,
        })
        start["current"]["stadium"] = None
        parent = [t8_position(start, card_id=M.LILLIE)]
        action = call_t8_agent(start, parent)
        cert = (
            M._pfgear_transaction["certificate"]
            if M._pfgear_transaction is not None else M._t8_last_certificate
        )
        record(
            f"t8_mind_ruler_{label}_seat{seat}",
            M._t8_last_telemetry["direction"] == expected_direction
            and cert["transform"]["survival"] is not None
            and (
                "RETURN_SURVIVAL_EXACT_HAND_COUNT"
                in cert["transform"]["benefits"]
            ) == (label == "survival")
            and (
                "HAND_SIZE_ATTACK_WORSENS_TO_CERTAIN_KO"
                in cert["transform"]["negatives"]
            ) == (label == "worsening"),
            transform=cert["transform"],
            action=action,
            direction=M._t8_last_telemetry["direction"],
            rejection=M._t8_last_telemetry["rejection_reason"],
        )
        if M._t8_is_transaction():
            M._t8_abort([], "fixture_settle_mind_ruler")


def t8_owner_handoffs(seat):
    for label, owner_name, card_id in (
        ("pad", "_pfc_transaction", M.POKE_PAD),
        ("ultra", "_pfc_transaction", M.ULTRA_BALL),
        ("stretcher", "_pfc_transaction", M.NIGHT_STRETCHER),
        ("tool", "_hero_transaction", M.HERO_CAPE),
        ("stadium", "_cum_active_transaction_owner", M.FULL_METAL_LAB),
    ):
        clear_runtime()
        start = t8_base(seat, (M.LILLIE, card_id), prizes=5)
        parent = [t8_position(start, card_id=card_id)]
        marker = {"rule": "FIXTURE_" + label}
        action = call_t8_agent(
            start,
            parent,
            side_effect=lambda name=owner_name, value=marker: setattr(M, name, value),
        )
        record(
            f"t8_existing_{label}_owner_handoff_seat{seat}",
            semantic(start, action) == semantic(start, parent)
            and M._t8_last_telemetry["rejection_reason"]
            == "pre_or_post_parent_owner_handoff"
            and not M._t8_is_transaction(),
        )
        setattr(M, owner_name, None)


def t8_fail_close_controls(seat):
    clear_runtime()
    start = t8_base(seat, (M.LILLIE, M.CINDERACE), prizes=5)
    parent = [t8_position(start, card_id=M.LILLIE)]
    old_hash = M._T8_LILLIE_TEXT_HASH
    M._T8_LILLIE_TEXT_HASH = "0" * 64
    try:
        action = call_t8_agent(start, parent)
    finally:
        M._T8_LILLIE_TEXT_HASH = old_hash
    record(
        f"t8_metadata_mismatch_fail_close_seat{seat}",
        semantic(start, action) == semantic(start, parent)
        and not M._t8_is_transaction(),
    )

    clear_runtime()
    old_bindings = M._pfc_task6_route_bindings
    M._pfc_task6_route_bindings = lambda *args, **kwargs: None
    try:
        action = call_t8_agent(start, parent)
    finally:
        M._pfc_task6_route_bindings = old_bindings
    record(
        f"t8_incomplete_route_fail_close_seat{seat}",
        semantic(start, action) == semantic(start, parent)
        and not M._t8_is_transaction(),
    )


def t8_gear_start(seat):
    return t8_base(seat, (M.POKEGEAR, M.CINDERACE), prizes=5)


def t8_gear_certificate(start):
    common, reason = M._t8_gear_common(parsed(start))
    assert common is not None, reason
    return M._t8_certificate(common, "GEAR_LILLIE")


def t8_gear_whiff_main(start, certificate):
    obs = copy.deepcopy(start)
    player = mine(obs)
    gear = next(
        card for card in player["hand"]
        if card["id"] == M.POKEGEAR
        and card["serial"] == certificate["gear_serial"]
    )
    player["hand"].remove(gear)
    player["handCount"] -= 1
    player["discard"].append(copy.deepcopy(gear))
    player["deckCount"] = certificate["deck_counts"][0]
    obs["current"]["looking"] = None
    obs["current"]["turnActionCount"] += 2
    t8_main_options(obs)
    return obs


def t8_gear_acquired_main(start, certificate, selected_lillie):
    obs = copy.deepcopy(start)
    player = mine(obs)
    gear = next(card for card in player["hand"] if card["id"] == M.POKEGEAR)
    player["hand"].remove(gear)
    player["discard"].append(copy.deepcopy(gear))
    player["hand"].append(copy.deepcopy(selected_lillie))
    player["handCount"] = len(player["hand"])
    player["deckCount"] = certificate["deck_counts"][0] - 1
    obs["current"]["looking"] = None
    obs["current"]["turnActionCount"] += 2
    t8_main_options(obs, extra=[
        {"type": int(M.OptionType.PLAY), "index": len(player["hand"]) - 1},
    ])
    return obs


def t8_gear_lillie_post(acquired, certificate):
    obs = copy.deepcopy(acquired)
    player = mine(obs)
    lillie = next(
        card for card in player["hand"]
        if card["id"] == M.LILLIE
        and card["serial"] == certificate["supporter_serial"]
    )
    player["discard"].append(copy.deepcopy(lillie))
    draw_n = certificate["transform"]["draw_n"]
    player["hand"] = [
        {"id": M.CINDERACE, "serial": 9800 + index,
         "playerIndex": obs["current"]["yourIndex"]}
        for index in range(draw_n)
    ]
    player["handCount"] = draw_n
    player["deckCount"] = certificate["transform"]["post_deck_count"]
    obs["current"]["supporterPlayed"] = True
    obs["current"]["turnActionCount"] += 1
    t8_main_options(obs, attack=False)
    return obs


def t8_gear_subsets_and_lifecycle(seat):
    supporters = (M.BOSS, M.EXPLORER, M.LILLIE)
    for size in range(4):
        for subset in itertools.combinations(supporters, size):
            clear_runtime()
            start = t8_gear_start(seat)
            certificate = t8_gear_certificate(start)
            assert M._pfgear_begin(parsed(start), certificate) is not None
            reveal = reveal_prompt(start, certificate, subset)
            action = M._pfgear_resume(parsed(reveal), [])
            selected_id = None
            if action:
                selected_id = M._pcrd_get(M.option_card(
                    parsed(reveal), parsed(reveal).select.option[action[0]]
                ), "id")
            record(
                f"t8_gear_subset_{''.join(map(str, subset)) or 'empty'}_seat{seat}",
                selected_id == (M.LILLIE if M.LILLIE in subset else None),
                action=action,
                selected_id=selected_id,
            )
            if M.LILLIE not in subset:
                whiff = t8_gear_whiff_main(start, certificate)
                M._pfgear_resume(parsed(whiff), [0])
                record(
                    f"t8_gear_whiff_clear_{''.join(map(str, subset)) or 'empty'}_seat{seat}",
                    M._pfgear_transaction is None and M._t8_conservation()["holds"],
                )
            else:
                selected = copy.deepcopy(M.option_card(
                    parsed(reveal), parsed(reveal).select.option[action[0]]
                ).__dict__)
                acquired = t8_gear_acquired_main(
                    start, M._pfgear_transaction["certificate"], selected
                )
                lillie_action = M._pfgear_resume(parsed(acquired), [0])
                bound = copy.deepcopy(M._pfgear_transaction["certificate"])
                record(
                    f"t8_gear_lillie_play_{''.join(map(str, subset))}_seat{seat}",
                    M._pcrd_get(M.option_card(
                        parsed(acquired), parsed(acquired).select.option[lillie_action[0]]
                    ), "id") == M.LILLIE,
                )
                post = t8_gear_lillie_post(acquired, bound)
                M._pfgear_resume(parsed(post), [0])
                record(
                    f"t8_gear_lillie_complete_{''.join(map(str, subset))}_seat{seat}",
                    M._pfgear_transaction is None and M._t8_conservation()["holds"],
                )


def t8_gear_duplicate_and_order(seat):
    variants = []
    for reverse in (False, True):
        clear_runtime()
        start = t8_gear_start(seat)
        certificate = t8_gear_certificate(start)
        assert M._pfgear_begin(parsed(start), certificate) is not None
        reveal = reveal_prompt(
            start, certificate, (M.LILLIE, M.EXPLORER),
            reverse=reverse, duplicate=False,
        )
        extra = {
            "id": M.LILLIE,
            "serial": 2999,
            "playerIndex": seat,
        }
        reveal["current"]["looking"].append(extra)
        reveal["select"]["option"].append({
            "type": int(M.OptionType.CARD),
            "area": int(M.AreaType.LOOKING),
            "index": len(reveal["current"]["looking"]) - 1,
            "playerIndex": seat,
        })
        # Keep the fixed seven-card reveal by replacing one filler.
        filler_index = next(
            index for index, card in enumerate(reveal["current"]["looking"][:-1])
            if card["id"] == M.METAL_ENERGY
        )
        reveal["current"]["looking"].pop(filler_index)
        for option in reveal["select"]["option"]:
            if option.get("index", -1) > filler_index:
                option["index"] -= 1
        if reverse:
            reveal["select"]["option"].reverse()
        action = M._pfgear_resume(parsed(reveal), [])
        selected = M.option_card(
            parsed(reveal), parsed(reveal).select.option[action[0]]
        )
        emitted = copy.deepcopy(M._pfgear_transaction["certificate"])
        retry = M._pfgear_resume(parsed(reveal), [])
        variants.append((
            M._pcrd_serial(selected),
            emitted["reveal_option_hash"],
            emitted["per_supporter_rejection"],
            retry == action,
            M._pfgear_transaction["certificate"]["duplicate_count"],
        ))
        M._t8_abort([], "fixture_settle_gear_order")
    record(
        f"t8_gear_duplicate_min_order_retry_seat{seat}",
        variants[0] == variants[1]
        and variants[0][0] == 2999
        and variants[0][3]
        and variants[0][4] == 1,
        variants=variants,
    )


def exact_reject_regressions():
    deck = read_deck(CANDIDATE / "deck.csv")
    for replay_path, target_step, expected_action, route_reason in EXACT_REJECTIONS:
        raw = json.loads(replay_path.read_text(encoding="utf-8"))
        seat = target_seat_for_deck(raw, deck)
        decisions = tuple(replay_decisions(raw, seat))
        clear_runtime()
        target_obs = None
        preceding_obs = None
        action = None
        for index, (step, obs, _recorded) in enumerate(decisions):
            action = M.agent(copy.deepcopy(obs))
            if step == target_step:
                target_obs = copy.deepcopy(obs)
                preceding_obs = (
                    None if index == 0 else copy.deepcopy(decisions[index - 1][1])
                )
                break
        assert target_obs is not None
        record(
            f"t8_exact_reject_{replay_path.stem}_step{target_step}",
            action == expected_action,
            seat=seat,
            action=action,
            expected_action=expected_action,
            direction=(M._t8_last_telemetry or {}).get("direction"),
            rejection=(M._t8_last_telemetry or {}).get("rejection_reason"),
        )

        if route_reason == "EXACT_EVOLUTION_ROUTE":
            for mirrored in (False, True):
                reversed_options = False
                clear_runtime()
                variant = mirror(target_obs) if mirrored else copy.deepcopy(target_obs)
                if reversed_options:
                    variant["select"]["option"].reverse()
                variant_action = M.agent(copy.deepcopy(variant))
                view = parsed(variant)
                chosen = view.select.option[variant_action[0]]
                transaction = copy.deepcopy(M._pfgear_transaction)
                route = (
                    None if transaction is None
                    else transaction.get("materializer", {}).get("route", {})
                )
                telemetry = copy.deepcopy(M._t8_last_telemetry)
                record(
                    f"t8_exact_reject_{replay_path.stem}_seat{1-seat if mirrored else seat}_reverse{int(reversed_options)}",
                    chosen.type == M.OptionType.EVOLVE
                    and (
                        route.get("reason") == route_reason
                        or telemetry.get("rejection_reason")
                        == "complete_parent_route_precedes_lillie"
                    ),
                    action=variant_action,
                    chosen_card=M._pcrd_get(M.option_card(view, chosen), "id"),
                    route=route,
                    telemetry=telemetry,
                )
                M._t8_abort([], "exact_reject_fixture_settle")
            continue

        assert preceding_obs is not None
        preceding_step = next(
            decisions[index - 1][0]
            for index in range(1, len(decisions))
            if decisions[index][0] == target_step
        )
        for mirrored, reversed_options in itertools.product((False, True), repeat=2):
            clear_runtime()
            start_action = None
            reveal_action = None
            reveal = None
            for step, obs, _recorded in decisions:
                variant = mirror(obs) if mirrored else copy.deepcopy(obs)
                if reversed_options and step in {preceding_step, target_step}:
                    variant["select"]["option"].reverse()
                emitted = M.agent(copy.deepcopy(variant))
                if step == preceding_step:
                    start_action = emitted
                if step == target_step:
                    reveal_action = emitted
                    reveal = variant
                    break
            assert reveal is not None and reveal_action is not None
            view = parsed(reveal)
            chosen = view.select.option[reveal_action[0]]
            certificate = copy.deepcopy(M._t8_last_certificate)
            protected = certificate.get("inherited_protected_supporter", {})
            task8_certificate = certificate.get("rule") == M._T8_RULE_ID
            telemetry = copy.deepcopy(M._t8_last_telemetry)
            record(
                f"t8_exact_reject_{replay_path.stem}_seat{1-seat if mirrored else seat}_reverse{int(reversed_options)}",
                M._pcrd_get(M.option_card(view, chosen), "id") == M.EXPLORER
                and not M._t8_is_transaction()
                and (
                    (
                        telemetry.get("selected_source") == "DIRECT_PARENT"
                        and telemetry.get("direction") is None
                    )
                    or (
                        protected.get("reason") == route_reason
                        and protected.get("card_id") == M.EXPLORER
                        and certificate.get("rollback_reason")
                        == "parent_declared_supporter_minimum_precedes_gear_lillie"
                    )
                ),
                start_action=start_action,
                reveal_action=reveal_action,
                protected=protected,
                rollback=certificate.get("rollback_reason"),
                task8_certificate=task8_certificate,
                telemetry=telemetry,
            )


def exact_ice_regressions():
    deck = read_deck(CANDIDATE / "deck.csv")
    for replay_path, target_step, expected_action in EXACT_ICE_REJECTIONS:
        raw = json.loads(replay_path.read_text(encoding="utf-8"))
        seat = target_seat_for_deck(raw, deck)
        decisions = tuple(replay_decisions(raw, seat))
        for mirrored, reversed_options in itertools.product((False, True), repeat=2):
            clear_runtime()
            action = None
            target_obs = None
            for step, obs, _recorded in decisions:
                variant = mirror(obs) if mirrored else copy.deepcopy(obs)
                if reversed_options and step == target_step:
                    variant["select"]["option"].reverse()
                action = M.agent(copy.deepcopy(variant))
                if step == target_step:
                    target_obs = variant
                    break
            assert target_obs is not None and action is not None
            view = parsed(target_obs)
            chosen = view.select.option[action[0]]
            chosen_card = M.option_card(view, chosen)
            route = M._t8_jumbo_ice_route(view, action)
            exact_original = not mirrored and not reversed_options
            record(
                f"t8_exact_ice_{replay_path.stem}_seat{1-seat if mirrored else seat}_reverse{int(reversed_options)}",
                (not exact_original or action == expected_action)
                and M._pcrd_get(chosen_card, "id") == M.JUMBO_ICE_CREAM
                and route is not None
                and route["serial"] == M._pcrd_serial(chosen_card)
                and tuple(route["required_ref"])
                == (M.JUMBO_ICE_CREAM, M._pcrd_serial(chosen_card))
                and route["exact_healing"] > 0
                and not M._t8_is_transaction(),
                action=action,
                expected_action=(expected_action if exact_original else None),
                route=route,
                telemetry=copy.deepcopy(M._t8_last_telemetry),
            )


def exact_duplicate_supporter_regressions():
    replay_path, gear_step, explorer_step = EXACT_DUPLICATE_SUPPORTER_REJECTION
    raw = json.loads(replay_path.read_text(encoding="utf-8"))
    deck = read_deck(CANDIDATE / "deck.csv")
    seat = target_seat_for_deck(raw, deck)
    decisions = tuple(replay_decisions(raw, seat))
    for mirrored, reversed_options in itertools.product((False, True), repeat=2):
        clear_runtime()
        gear_action = None
        explorer_action = None
        gear_view = None
        explorer_view = None
        supporter_routes = None
        supporter_reason = None
        for step, obs, _recorded in decisions:
            variant = mirror(obs) if mirrored else copy.deepcopy(obs)
            if reversed_options and step in {gear_step, gear_step + 1, explorer_step}:
                variant["select"]["option"].reverse()
            if step == gear_step:
                gear_view = parsed(variant)
                gear_serials = sorted(
                    M._pcrd_serial(M.option_card(gear_view, option))
                    for option in gear_view.select.option
                    if M._pcrd_get(M.option_card(gear_view, option), "id")
                    == M.POKEGEAR
                )
                assert len(gear_serials) == 1
                supporter_routes, supporter_reason = (
                    M._t8_same_family_supporter_routes(
                        gear_view, gear_serials[0]
                    )
                )
            emitted = M.agent(copy.deepcopy(variant))
            if step == gear_step:
                gear_action = emitted
            if step == explorer_step:
                explorer_action = emitted
                explorer_view = parsed(variant)
                break
        assert all(value is not None for value in (
            gear_action, explorer_action, gear_view, explorer_view,
            supporter_routes,
        ))
        gear_card = M.option_card(
            gear_view, gear_view.select.option[gear_action[0]]
        )
        explorer_card = M.option_card(
            explorer_view, explorer_view.select.option[explorer_action[0]]
        )
        route = supporter_routes[0]
        exact_original = not mirrored and not reversed_options
        record(
            f"t8_exact_duplicate_explorer_{replay_path.stem}_seat{1-seat if mirrored else seat}_reverse{int(reversed_options)}",
            (not exact_original or gear_action == [1])
            and (not exact_original or explorer_action == [0])
            and M._pcrd_get(gear_card, "id") == M.POKEGEAR
            and M._pcrd_get(explorer_card, "id") == M.EXPLORER
            and supporter_reason is None
            and route["reason"] == "PARENT_DECLARED_SUPPORTER"
            and route["card_id"] == M.EXPLORER
            and route["minimum_count"] == 1
            and route["canonical_serial"] == 43
            and route["declared_family_count"] == 2
            and not M._t8_is_transaction(),
            gear_action=gear_action,
            explorer_action=explorer_action,
            route=route,
            telemetry=copy.deepcopy(M._t8_last_telemetry),
        )


def exact_gear_reveal_supporter_regressions():
    deck = read_deck(CANDIDATE / "deck.csv")
    reveal_kinds = set()
    for replay_path, target_step, expected_action, expected_card_id in (
        EXACT_GEAR_REVEAL_SUPPORTER_REJECTIONS
    ):
        raw = json.loads(replay_path.read_text(encoding="utf-8"))
        seat = target_seat_for_deck(raw, deck)
        decisions = tuple(replay_decisions(raw, seat))
        for mirrored, reversed_options in itertools.product(
            (False, True), repeat=2
        ):
            clear_runtime()
            action = None
            parent_action = None
            target_obs = None
            for step, obs, _recorded in decisions:
                variant = mirror(obs) if mirrored else copy.deepcopy(obs)
                if reversed_options and step == target_step:
                    variant["select"]["option"].reverse()
                captured = {}
                exact_parent = M._t8_parent_agent

                def capture_parent(value):
                    selected = exact_parent(value)
                    captured["action"] = copy.deepcopy(selected)
                    return selected

                M._t8_parent_agent = capture_parent
                try:
                    action = M.agent(copy.deepcopy(variant))
                finally:
                    M._t8_parent_agent = exact_parent
                assert "action" in captured
                if step == target_step:
                    parent_action = captured["action"]
                    target_obs = variant
                    break
            assert all(value is not None for value in (
                action, parent_action, target_obs,
            ))
            view = parsed(target_obs)
            chosen = view.select.option[action[0]]
            chosen_card = M.option_card(view, chosen)
            family_serials = sorted(
                M._pcrd_serial(M.option_card(view, option))
                for option in view.select.option
                if (
                    option.type == M.OptionType.CARD
                    and M._pcrd_get(M.option_card(view, option), "id")
                    == expected_card_id
                )
            )
            contains_lillie = any(
                M._pcrd_get(M.option_card(view, option), "id") == M.LILLIE
                for option in view.select.option
            )
            reveal_kinds.add(contains_lillie)
            protected = copy.deepcopy(M._t8_last_certificate).get(
                "inherited_protected_supporter", {}
            )
            exact_original = not mirrored and not reversed_options
            record(
                f"t8_exact_gear_reveal_parent_{replay_path.stem}_seat{1-seat if mirrored else seat}_reverse{int(reversed_options)}",
                (not exact_original or action == expected_action)
                and action == parent_action
                and action != []
                and view.select.context == M.SelectContext.TO_HAND
                and chosen.type == M.OptionType.CARD
                and M._pcrd_get(chosen_card, "id") == expected_card_id
                and M._pcrd_get(chosen_card, "id")
                in {M.BOSS, M.EXPLORER}
                and protected.get("reason")
                == "PARENT_DECLARED_SUPPORTER"
                and protected.get("card_id") == expected_card_id
                and protected.get("canonical_serial") == family_serials[0]
                and protected.get("minimum_count") == 1
                and protected.get("declared_family_count")
                == len(family_serials)
                and protected.get("semantic_context")
                == int(M.SelectContext.TO_HAND)
                and protected.get("semantic_option_type")
                == int(M.OptionType.CARD)
                and M._t8_last_certificate.get("rollback_reason")
                == "parent_declared_supporter_minimum_precedes_gear_lillie"
                and not M._t8_is_transaction(),
                action=action,
                parent_action=parent_action,
                expected_action=(expected_action if exact_original else None),
                contains_lillie=contains_lillie,
                protected=protected,
            )
    record(
        "t8_exact_gear_reveal_with_and_without_lillie_covered",
        reveal_kinds == {False, True},
        reveal_kinds=sorted(reveal_kinds),
    )


def t8_gear_acquired_parent_supporter_fail_close(seat):
    for reverse in (False, True):
        clear_runtime()
        start = t8_base(
            seat,
            (M.POKEGEAR, M.EXPLORER, M.EXPLORER, M.CINDERACE),
            prizes=5,
        )
        old_routes = M._t8_same_family_supporter_routes
        M._t8_same_family_supporter_routes = lambda *_: ((), None)
        try:
            certificate = t8_gear_certificate(start)
        finally:
            M._t8_same_family_supporter_routes = old_routes
        assert M._pfgear_begin(parsed(start), certificate) is not None
        reveal = reveal_prompt(start, certificate, (M.LILLIE,))
        selected_action = M._pfgear_resume(parsed(reveal), [0])
        selected = copy.deepcopy(M.option_card(
            parsed(reveal), parsed(reveal).select.option[selected_action[0]]
        ).__dict__)
        acquired = t8_gear_acquired_main(
            start, M._pfgear_transaction["certificate"], selected
        )
        player = mine(acquired)
        extras = [
            {"type": int(M.OptionType.PLAY), "index": index}
            for index, card in enumerate(player["hand"])
            if card["id"] in {M.LILLIE, M.EXPLORER}
        ]
        t8_main_options(acquired, extra=extras)
        if reverse:
            acquired["select"]["option"].reverse()
        parent = [t8_position(acquired, card_id=M.EXPLORER)]
        canonical = min(
            card["serial"] for card in player["hand"]
            if card["id"] == M.EXPLORER
        )
        action = M._pfgear_resume(parsed(acquired), parent)
        protected = copy.deepcopy(M._t8_last_certificate).get(
            "inherited_protected_supporter", {}
        )
        record(
            f"t8_gear_acquired_parent_explorer_fail_close_seat{seat}_reverse{int(reverse)}",
            action == parent
            and protected.get("reason") == "PARENT_DECLARED_SUPPORTER"
            and protected.get("card_id") == M.EXPLORER
            and protected.get("canonical_serial") == canonical
            and protected.get("minimum_count") == 1
            and protected.get("declared_family_count") == 2
            and M._t8_last_certificate.get("rollback_reason")
            == "parent_declared_supporter_minimum_precedes_gear_lillie"
            and not M._t8_is_transaction()
            and M._t8_conservation()["holds"],
            action=action,
            parent=parent,
            protected=protected,
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

for checked_seat in (0, 1):
    t8_direct_play_and_counts(checked_seat, 5)
    t8_direct_play_and_counts(checked_seat, 6)
    t8_hidden_redraw_invariance(checked_seat)
    t8_zero_bench_materialize(checked_seat)
    t8_one_metal_materialize(checked_seat)
    t8_exact_evolution_materialize(checked_seat)
    t8_protected_route_holds(checked_seat)
    t8_direct_precedes_gear(checked_seat)
    t8_future_hold_and_duplicates(checked_seat)
    t8_negative_counts(checked_seat)
    t8_mind_ruler_boundaries(checked_seat)
    t8_owner_handoffs(checked_seat)
    t8_fail_close_controls(checked_seat)
    t8_gear_subsets_and_lifecycle(checked_seat)
    t8_gear_duplicate_and_order(checked_seat)
    t8_gear_acquired_parent_supporter_fail_close(checked_seat)

exact_reject_regressions()
exact_ice_regressions()
exact_duplicate_supporter_regressions()
exact_gear_reveal_supporter_regressions()
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
    "t8_counters": dict(M._t8_counters),
    "t8_conservation": M._t8_conservation(),
}
assert summary["t7_conservation"]["holds"]
assert summary["t8_conservation"]["holds"]
Path(__file__).with_name("focused_fixture_results.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    key: summary[key] for key in ("fixture_count", "passed", "failed")
}, sort_keys=True))
