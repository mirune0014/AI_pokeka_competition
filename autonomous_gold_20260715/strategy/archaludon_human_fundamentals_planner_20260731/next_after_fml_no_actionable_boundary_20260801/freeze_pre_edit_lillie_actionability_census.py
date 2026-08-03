from __future__ import annotations

import copy
import csv
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
PARENT = ROOT / "autonomous_gold_20260715" / "candidates" / (
    "archaludon_purpose_first_pokegear_boss_transaction_v1"
)
CORPUS = ROOT / "autonomous_gold_20260715" / "live" / "55070349" / (
    "refresh_20260729_1241"
) / "shadow_corpus_196_prior_plus_11_new"
SOURCE_MANIFEST = ROOT / "autonomous_gold_20260715" / "strategy" / (
    "archaludon_human_fundamentals_planner_20260731"
) / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw"
) / "source_manifest.json"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "pre_edit_lillie_actionability_census_raw"

LILLIE = 1227
EXPECTED_LILLIE_NAME = "Lillie's Determination"
EXPECTED_LILLIE_TEXT = (
    "Shuffle your hand into your deck. Then, draw 6 cards. If you have "
    "exactly 6 Prize cards remaining, draw 8 cards instead."
)

FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "snapshot_sha256", "parent_action", "parent_roles", "parent_valid",
    "owner_state", "lillie_roles", "lillie_serials",
    "historical_lillie_play", "prize_count", "hand_count", "deck_count",
    "draw_count", "shuffle_count", "post_hand_count", "post_deck_count",
    "deckout_horizon_before", "deckout_horizon_after",
    "attack_rows", "current_combat", "hand_resources",
    "boss_explorer_conflict", "backup_certificate",
    "hand_size_return_effects", "strict_plan", "protected_route",
    "purpose", "direction", "candidate_first_role",
    "alternative_action_queue", "first_hard_difference",
    "uniquely_emittable", "predicted_first_difference",
    "rejection_reason",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def freeze(value):
    if isinstance(value, dict):
        return {str(key): freeze(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [freeze(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((freeze(item) for item in value), key=repr)
    if hasattr(value, "value") and isinstance(value.value, int):
        return int(value.value)
    if hasattr(value, "__dict__"):
        return {"__class__": type(value).__name__, **freeze(vars(value))}
    return value


def canonical(value) -> str:
    return json.dumps(freeze(value), ensure_ascii=False, sort_keys=True)


def snapshot_hash(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest().upper()


def load_parent():
    sys.path.insert(0, str(PARENT))
    spec = importlib.util.spec_from_file_location(
        "lillie_pre_edit_parent", PARENT / "main.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(PARENT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset(module) -> None:
    for function, reason in (
        ("_pfgear_reset_active", "lillie_census_reset"),
        ("_pcrd_clear", "lillie_census_reset"),
        ("_pfc_clear", "lillie_census_reset"),
        ("_cum_reset_runtime", "lillie_census_reset"),
        ("_dper_reset_runtime", "lillie_census_reset"),
    ):
        if hasattr(module, function):
            getattr(module, function)(reason)
    for name in (
        "_h2_transaction", "_h6_transaction", "_pfgear_transaction",
        "_pfgear_veto_watch", "_cum_active_transaction_owner",
        "_cum_owner_meta", "_pcrd_transaction", "_pfc_transaction",
    ):
        if hasattr(module, name):
            setattr(module, name, None)


def action_roles(module, obs, action):
    try:
        if not module._cum_valid_action(obs, action):
            return None
        return module._pcrd_action_roles(obs, action)
    except Exception as error:
        return ("ERROR", type(error).__name__, str(error))


def live_owners(module):
    result = {}
    for name in (
        "_h2_transaction", "_h6_transaction", "_pfgear_transaction",
        "_pfgear_veto_watch", "_cum_active_transaction_owner",
        "_cum_owner_meta", "_pcrd_transaction", "_pfc_transaction",
    ):
        value = getattr(module, name, None)
        if value is not None:
            result[name] = freeze(value)
    return result


def metadata(module):
    card = module.CARD_DB.get(LILLIE)
    if card is None:
        return None
    skills = []
    for skill in tuple(getattr(card, "skills", None) or ()):
        skills.append({
            "name": getattr(skill, "name", None),
            "text": getattr(skill, "text", None),
        })
    result = {
        "card_id": LILLIE,
        "name": getattr(card, "name", None),
        "skills": skills,
    }
    exact = bool(
        result["name"] == EXPECTED_LILLIE_NAME
        and len(skills) == 1
        and skills[0]["text"] == EXPECTED_LILLIE_TEXT
    )
    return {"exact": exact, **result}


def option_rows(module, obs, *, card_id=None, option_type=None):
    rows = []
    for position, option in enumerate(obs.select.option):
        card = module.option_card(obs, option)
        if option_type is not None and option.type != option_type:
            continue
        if card_id is not None and getattr(card, "id", None) != card_id:
            continue
        rows.append({
            "position": position,
            "role": module._pcrd_option_role(obs, option),
            "card_id": getattr(card, "id", None),
            "card_serial": module._pcrd_serial(card),
            "target_id": getattr(module.option_target(obs, option), "id", None),
            "target_serial": module._pcrd_serial(module.option_target(obs, option)),
            "option_type": int(option.type),
            "attack_id": getattr(option, "attackId", None),
        })
    return rows


def current_attack_rows(module, obs):
    try:
        rows, reason = module._pfgear_current_attack_rows(
            obs, allow_duplicate_ui=True
        )
    except Exception as error:
        return None, "exception:" + type(error).__name__
    if rows is None:
        return None, reason
    result = []
    for row in rows:
        result.append({
            "attack_id": row["attack_id"],
            "role": row["role"],
            "payment": freeze(row["payment"]),
            "certificate": freeze(row["certificate"]),
            "threat_graph": freeze(row["threat_graph"]),
        })
    return result, reason


def exact_plans(module, obs):
    try:
        plans = module._pcrd_generate_plans(obs)
    except Exception as error:
        return (), "exception:" + type(error).__name__
    if plans is None:
        return (), "plan_generation_unknown"
    exact = tuple(plan for plan in plans if plan.get("status") == "EXACT")
    if not exact:
        return (), "no_exact_plan"
    try:
        plan = module._pcrd_unique_nondominated(exact)
    except Exception as error:
        return (), "selection_exception:" + type(error).__name__
    if plan is None:
        return (), "no_unique_nondominated_plan"
    return (plan,), None


def first_plan_role(module, obs, plan):
    actions = tuple(plan.get("actions") or ())
    if not actions:
        return None, "empty_plan"
    first = actions[0]
    kind = first.get("kind")
    matches = []
    for row in option_rows(module, obs):
        if kind == "ATTACK":
            match = (
                row["option_type"] == int(module.OptionType.ATTACK)
                and row["attack_id"] == first.get("attack_id")
            )
        else:
            serial = first.get("card_serial", first.get("evolution_serial"))
            target = first.get("target_serial")
            match = row["card_serial"] == serial
            if target is not None:
                match = match and row["target_serial"] == target
        if match:
            matches.append(row)
    roles = {canonical(row["role"]): row["role"] for row in matches}
    if len(roles) != 1:
        return None, "first_role_not_unique"
    return next(iter(roles.values())), None


def protected_plan_route(module, obs, plan):
    first_role, reason = first_plan_role(module, obs, plan)
    if first_role is None:
        return None, reason
    actions = tuple(plan.get("actions") or ())
    first_kind = actions[0].get("kind")
    fields = plan.get("fields") or {}
    if first_kind == "ATTACK":
        if not fields.get("current_win"):
            return None, "current_attack_not_displaced_by_lillie"
        protected = "CURRENT_ATTACK"
        hard = {
            "layer": 2,
            "reason": "exact_win_now",
            "current_prizes": fields.get("current_prizes"),
        }
    elif first_kind in {"EVOLVE", "MANUAL_METAL"}:
        protected = "ATTACHMENT_EVOLUTION"
        hard = {
            "layer": 4,
            "reason": "hand_serial_completes_exact_attack_plan",
            "current_prizes": fields.get("current_prizes"),
            "current_ko": fields.get("current_ko"),
        }
    elif first_kind in {"HERO_CAPE", "JUMBO_ICE_CREAM"}:
        protected = "CURRENT_ATTACK"
        hard = {
            "layer": 5,
            "reason": "hand_serial_preserves_exact_survival_or_attack_plan",
            "survival": fields.get("current_attacker_survival"),
        }
    elif first_kind == "FULL_METAL_LAB":
        protected = "CURRENT_ATTACK"
        hard = {
            "layer": 5,
            "reason": "stadium_serial_preserves_exact_combat_plan",
            "survival": fields.get("current_attacker_survival"),
        }
    else:
        return None, "unsupported_plan_first_kind"
    serials = set()
    for action in actions:
        for key in ("card_serial", "evolution_serial", "energy_serial"):
            value = action.get(key)
            if isinstance(value, int):
                serials.add(value)
        for allocation in tuple(action.get("allocations") or ()):
            value = allocation.get("energy_serial")
            if isinstance(value, int):
                serials.add(value)
    return {
        "protected_role": protected,
        "protected_serials": sorted(serials),
        "first_role": first_role,
        "queue": freeze(actions),
        "hard_difference": hard,
    }, None


def boss_route(module, obs, attacks):
    boss_rows = option_rows(
        module, obs, card_id=module.BOSS, option_type=module.OptionType.PLAY
    )
    if len({canonical(row["role"]) for row in boss_rows}) != 1:
        return None, "boss_first_role_not_unique"
    if not boss_rows or not attacks:
        return None, "boss_or_attack_absent"
    remaining = len(tuple(module.my_state(obs).prize or ()))
    current_best = max(
        (row["certificate"].get("prize_yield", 0) for row in attacks),
        default=0,
    )
    candidates = []
    for target in tuple(module.opp_state(obs).bench or ()):
        if target is None:
            continue
        for attack in attacks:
            source_row = {
                "attack_id": attack["attack_id"],
                "payment": tuple(tuple(row) for row in attack["payment"]),
            }
            try:
                line = module._pfgear_candidate_line(obs, source_row, target)
            except Exception:
                line = None
            if line is None:
                continue
            certificate = line.get("certificate") or {}
            prize = certificate.get("prize_yield", 0) if certificate.get("ko") else 0
            terminal = bool(certificate.get("ko") and prize >= remaining)
            if terminal or prize > current_best:
                candidates.append({
                    "target_id": getattr(target, "id", None),
                    "target_serial": module._pcrd_serial(target),
                    "attack_id": attack["attack_id"],
                    "certificate": freeze(certificate),
                    "terminal": terminal,
                    "prize": prize,
                })
    best = [row for row in candidates if row["terminal"]]
    if not best and candidates:
        max_prize = max(row["prize"] for row in candidates)
        best = [row for row in candidates if row["prize"] == max_prize]
    unique = {canonical(row): row for row in best}
    if len(unique) != 1:
        return None, "boss_route_not_unique"
    chosen = next(iter(unique.values()))
    boss = boss_rows[0]
    return {
        "protected_role": "BOSS",
        "protected_serials": [boss["card_serial"]],
        "first_role": boss["role"],
        "queue": [
            {"kind": "PLAY_BOSS", "card_serial": boss["card_serial"]},
            {"kind": "SELECT_BOSS_TARGET", "target_serial": chosen["target_serial"]},
            {"kind": "ATTACK", "attack_id": chosen["attack_id"]},
        ],
        "hard_difference": {
            "layer": 2 if chosen["terminal"] else 4,
            "reason": "exact_boss_terminal_or_prize_route",
            "certificate": chosen["certificate"],
        },
    }, None


def ready_backup_route(module, obs):
    active = module.active_pokemon(obs)
    target = module.opp_active_pokemon(obs)
    if active is None or target is None:
        return None, "missing_active"
    candidates = []
    for row in option_rows(module, obs):
        if row["card_id"] != module.METAL_ENERGY:
            continue
        target_pokemon = module.option_target(obs, obs.select.option[row["position"]])
        if target_pokemon not in tuple(module.my_state(obs).bench or ()):
            continue
        projected = module._pcrd_project_pokemon(target_pokemon)
        hand_card = module.option_card(obs, obs.select.option[row["position"]])
        projected = module._pcrd_add_energy_projection(projected, hand_card)
        if projected is None:
            continue
        data = module.CARD_DB.get(projected["id"])
        if data is None:
            continue
        ready = []
        for attack_id in tuple(data.attacks or ()):
            attack = module.ALL_ATTACKS.get(attack_id)
            if attack is not None and module._pcrd_attack_payment(projected, attack) is not None:
                ready.append(attack_id)
        before_ready = []
        original_data = module.CARD_DB.get(target_pokemon.id)
        for attack_id in tuple(getattr(original_data, "attacks", None) or ()):
            attack = module.ALL_ATTACKS.get(attack_id)
            if attack is not None and module._pcrd_attack_payment(target_pokemon, attack) is not None:
                before_ready.append(attack_id)
        if ready and not before_ready:
            candidates.append({"row": row, "ready_attacks": sorted(ready)})
    unique = {canonical(row["row"]["role"]): row for row in candidates}
    if len(unique) != 1:
        return None, "ready_backup_attach_not_unique"
    chosen = next(iter(unique.values()))
    row = chosen["row"]
    return {
        "protected_role": "READY_BACKUP",
        "protected_serials": [row["card_serial"]],
        "first_role": row["role"],
        "queue": [{
            "kind": "ATTACH_READY_BACKUP",
            "card_serial": row["card_serial"],
            "target_serial": row["target_serial"],
            "ready_attacks": chosen["ready_attacks"],
        }],
        "hard_difference": {
            "layer": 5,
            "reason": "manual_attachment_creates_exact_ready_backup",
        },
    }, None


def backup_formation_route(module, obs):
    board = [
        pokemon for pokemon in
        tuple(module.my_state(obs).active or ()) + tuple(module.my_state(obs).bench or ())
        if pokemon is not None
    ]
    if len(board) > 1:
        return None, "backup_already_present"
    candidates = [
        row for row in option_rows(module, obs)
        if row["option_type"] == int(module.OptionType.PLAY)
        and row["card_id"] in {module.DURALUDON, module.CINDERACE}
    ]
    unique = {canonical(row["role"]): row for row in candidates}
    if len(unique) != 1:
        return None, "backup_play_not_unique"
    row = next(iter(unique.values()))
    return {
        "protected_role": "READY_BACKUP",
        "protected_serials": [row["card_serial"]],
        "first_role": row["role"],
        "queue": [{
            "kind": "PLAY_ONLY_BACKUP",
            "card_id": row["card_id"],
            "card_serial": row["card_serial"],
        }],
        "hard_difference": {
            "layer": 5,
            "reason": "prevent_single_pokemon_board",
        },
    }, None


def _enum_int(value):
    value = getattr(value, "value", value)
    return value if isinstance(value, int) else None


def apply_damage_modifiers(module, obs, source, target, raw):
    source_data = module.CARD_DB.get(getattr(source, "id", None))
    target_data = module.CARD_DB.get(getattr(target, "id", None))
    if source_data is None or target_data is None:
        return None
    damage = raw
    source_type = _enum_int(getattr(source_data, "energyType", None))
    weakness = _enum_int(getattr(target_data, "weakness", None))
    resistance = _enum_int(getattr(target_data, "resistance", None))
    if source_type is not None and source_type == weakness:
        damage *= 2
    if source_type is not None and source_type == resistance:
        damage = max(0, damage - 30)
    if (
        obs.current.stadium
        and obs.current.stadium[0].id == module.FULL_METAL_LAB
        and _enum_int(getattr(target_data, "energyType", None))
        == module.METAL_ENERGY
    ):
        damage = max(0, damage - 30)
    return damage


def hand_size_return_effects(module, obs, before_count, after_count):
    source = module.opp_active_pokemon(obs)
    target = module.active_pokemon(obs)
    if source is None or target is None:
        return [], None
    data = module.CARD_DB.get(source.id)
    if data is None:
        return [], "opponent_active_metadata_unknown"
    rows = []
    unsupported = []
    source_hand = getattr(module.opp_state(obs), "handCount", None)
    for attack_id in tuple(getattr(data, "attacks", None) or ()):
        attack = module.ALL_ATTACKS.get(attack_id)
        if attack is None or module._pcrd_attack_payment(source, attack) is None:
            continue
        text = (getattr(attack, "text", "") or "").replace("’", "'").lower()
        if "opponent's hand" not in text:
            continue
        raw_before = raw_after = None
        if attack_id == 123:
            raw_before, raw_after = 30 * before_count, 30 * after_count
        elif attack_id == 1240:
            raw_before, raw_after = 50 * before_count, 50 * after_count
        elif attack_id == 771:
            base = int(getattr(attack, "damage", 0) or 0)
            raw_before = base + (120 if before_count <= 3 else 0)
            raw_after = base + (120 if after_count <= 3 else 0)
        elif attack_id == 857 and isinstance(source_hand, int):
            base = int(getattr(attack, "damage", 0) or 0)
            raw_before = base + (90 if source_hand == before_count else 0)
            raw_after = base + (90 if source_hand == after_count else 0)
        else:
            unsupported.append(attack_id)
            continue
        before = apply_damage_modifiers(module, obs, source, target, raw_before)
        after = apply_damage_modifiers(module, obs, source, target, raw_after)
        if before is None or after is None:
            unsupported.append(attack_id)
            continue
        rows.append({
            "attack_id": attack_id,
            "before_damage": before,
            "after_damage": after,
            "target_hp": target.hp,
            "before_ko": before >= target.hp,
            "after_ko": after >= target.hp,
        })
    if unsupported:
        return rows, "unsupported_relevant_hand_effect:" + ",".join(
            str(value) for value in sorted(set(unsupported))
        )
    return rows, None


def card_role(module, card_id):
    mapping = {
        module.DURALUDON: "DURALUDON_LINE",
        module.ARCHALUDON_EX: "ARCHALUDON_EX_LINE",
        module.ARCHALUDON: "ARCHALUDON_NONEX_LINE",
        module.CINDERACE: "CINDERACE_SETUP",
        module.METAL_ENERGY: "METAL_ATTACHMENT",
        module.BOSS: "BOSS_SUPPORTER",
        module.EXPLORER: "EXPLORER_SUPPORTER",
        module.LILLIE: "LILLIE_SUPPORTER",
        module.NIGHT_STRETCHER: "RECOVERY",
        module.ULTRA_BALL: "POKEMON_SEARCH",
        module.POKE_PAD: "POKEMON_SEARCH",
        module.POKEGEAR: "SUPPORTER_SEARCH",
        module.JUMBO_ICE_CREAM: "HEALING",
        module.HERO_CAPE: "SURVIVAL_TOOL",
        module.FULL_METAL_LAB: "STADIUM",
    }
    return mapping.get(card_id)


def hand_resource_rows(module, obs, protected_route):
    hand = tuple(module.my_state(obs).hand or ())
    protected = defaultdict(list)
    if protected_route:
        for serial in protected_route.get("protected_serials", ()):
            protected[serial].append(protected_route["protected_role"])
    legal = defaultdict(list)
    for row in option_rows(module, obs):
        if isinstance(row["card_serial"], int):
            legal[row["card_serial"]].append(row["role"])
    rows = []
    unknown = []
    seen = set()
    for card in hand:
        serial = module._pcrd_serial(card)
        role = card_role(module, card.id)
        if serial is None or serial in seen:
            unknown.append("hand_serial_unknown_or_duplicate")
        seen.add(serial)
        if role is None:
            unknown.append("unknown_card_role:" + str(card.id))
        rows.append({
            "card_id": card.id,
            "serial": serial,
            "role": role,
            "legal_roles": freeze(legal.get(serial, ())),
            "protected_reason": sorted(protected.get(serial, ())),
            "post_lillie_location": (
                "DISCARD" if card.id == LILLIE else "DECK_UNKNOWN"
            ),
        })
    return rows, sorted(set(unknown))


def role_equal(left, right):
    return canonical(left) == canonical(right)


def main() -> dict:
    if OUTPUT.exists():
        protected = (OUTPUT / "opportunity_rows.csv", OUTPUT / "summary.json")
        if any(path.exists() for path in protected):
            raise SystemExit("refusing to overwrite frozen census output")
    else:
        OUTPUT.mkdir(parents=False)

    module = load_parent()
    effect_metadata = metadata(module)
    if effect_metadata is None or not effect_metadata["exact"]:
        raise SystemExit("Lillie metadata mismatch")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    replay_cache = {}
    historical = set()
    manifest_mismatches = []
    for entry in manifest:
        replay_path = CORPUS / entry["replay"]
        replay_sha = sha256(replay_path)
        if replay_sha != entry["sha256"]:
            manifest_mismatches.append(entry["replay"])
            continue
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        replay_cache[entry["replay"]] = (replay_sha, replay)
        for seat in entry["target_seats"]:
            for step in replay["steps"]:
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat:
                    continue
                for log in raw.get("logs") or ():
                    if (
                        log.get("type") == int(module.LogType.PLAY)
                        and log.get("playerIndex") == seat
                        and log.get("cardId") == LILLIE
                    ):
                        historical.add((entry["replay"], seat, current.get("turn")))

    rows_path = OUTPUT / "opportunity_rows.csv"
    counts = Counter()
    global_calls = 0
    invalid_parent = 0
    row_keys = set()
    duplicate_row_keys = 0
    classified_turns = set()
    classified_replays = set()
    classified_seats = set()
    actionable_turns = set()
    actionable_replays = set()
    actionable_seats = set()
    predicted_turns = set()
    predicted_replays = set()
    predicted_seats = set()
    direction_turns = defaultdict(set)
    hold_roles = set()

    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for entry in manifest:
            cached = replay_cache.get(entry["replay"])
            if cached is None:
                continue
            replay_sha, replay = cached
            for seat in entry["target_seats"]:
                reset(module)
                for step_index, step in enumerate(replay["steps"]):
                    raw = step[seat].get("observation") or {}
                    current = raw.get("current") or {}
                    if current.get("yourIndex") != seat or raw.get("select") is None:
                        continue
                    global_calls += 1
                    parent_action = module.agent(copy.deepcopy(raw))
                    obs = module.to_observation_class(copy.deepcopy(raw))
                    parent_roles = action_roles(module, obs, parent_action)
                    parent_valid = parent_roles is not None
                    invalid_parent += int(not parent_valid)
                    if obs.select.context != module.SelectContext.MAIN:
                        continue
                    lillie = option_rows(
                        module, obs, card_id=LILLIE,
                        option_type=module.OptionType.PLAY,
                    )
                    if not lillie:
                        continue
                    row_key = (
                        entry["replay"], seat, step_index,
                        current.get("turn"), snapshot_hash(raw),
                    )
                    duplicate_row_keys += int(row_key in row_keys)
                    row_keys.add(row_key)
                    turn_key = (entry["replay"], seat, current.get("turn"))
                    owner = live_owners(module)
                    role_map = {canonical(row["role"]): row["role"] for row in lillie}
                    unique_lillie_role = (
                        next(iter(role_map.values())) if len(role_map) == 1 else None
                    )
                    parent_is_lillie = bool(
                        unique_lillie_role is not None
                        and parent_roles is not None
                        and len(parent_roles) == 1
                        and role_equal(parent_roles[0], unique_lillie_role)
                    )
                    mine = module.my_state(obs)
                    prize_count = len(tuple(mine.prize or ()))
                    hand_count = mine.handCount
                    deck_count = mine.deckCount
                    draw_count = 8 if prize_count == 6 else 6
                    shuffle_count = (
                        hand_count - 1 if isinstance(hand_count, int) else None
                    )
                    post_hand = draw_count
                    post_deck = (
                        deck_count + shuffle_count - draw_count
                        if isinstance(deck_count, int)
                        and isinstance(shuffle_count, int)
                        else None
                    )
                    attacks, attack_reason = current_attack_rows(module, obs)
                    plans, plan_reason = exact_plans(module, obs)
                    strict_plan = plans[0] if plans else None
                    plan_route = None
                    plan_route_reason = plan_reason
                    if strict_plan is not None:
                        plan_route, plan_route_reason = protected_plan_route(
                            module, obs, strict_plan
                        )
                    exact_boss, boss_reason = boss_route(module, obs, attacks or [])
                    ready_backup, ready_reason = ready_backup_route(module, obs)
                    formation, formation_reason = backup_formation_route(module, obs)
                    route = None
                    route_reasons = {
                        "plan": plan_route_reason,
                        "boss": boss_reason,
                        "ready_backup": ready_reason,
                        "backup_formation": formation_reason,
                    }
                    for candidate in (plan_route, exact_boss, ready_backup, formation):
                        if candidate is not None:
                            route = candidate
                            break
                    return_effects, return_error = hand_size_return_effects(
                        module, obs, hand_count, post_hand
                    )
                    resources, resource_errors = hand_resource_rows(
                        module, obs, route
                    )
                    supporter_conflict = {
                        "boss_in_hand": any(row["card_id"] == module.BOSS for row in resources),
                        "explorer_in_hand": any(row["card_id"] == module.EXPLORER for row in resources),
                        "boss_exact_route": exact_boss is not None,
                        "supporter_already_played": obs.current.supporterPlayed,
                    }
                    purpose = None
                    direction = "EQUAL"
                    candidate_first = None
                    alternative = []
                    first_difference = None
                    uniquely_emittable = False
                    predicted = False
                    rejection = None

                    if not effect_metadata["exact"]:
                        rejection = "lillie_metadata_unknown"
                    elif unique_lillie_role is None:
                        rejection = "lillie_first_role_not_unique"
                    elif owner:
                        rejection = "live_owner_collision"
                    elif resource_errors:
                        rejection = ";".join(resource_errors)
                    elif return_error:
                        rejection = return_error
                    elif (
                        not isinstance(hand_count, int) or hand_count != len(resources)
                        or not isinstance(deck_count, int) or deck_count < 0
                        or shuffle_count is None or shuffle_count < 0
                        or post_deck is None or post_deck < 0
                    ):
                        rejection = "count_transform_not_exact_or_insufficient_deck"
                    else:
                        harmful_return = any(
                            row["after_ko"] and not row["before_ko"]
                            for row in return_effects
                        )
                        beneficial_return = any(
                            row["before_ko"] and not row["after_ko"]
                            for row in return_effects
                        )
                        if parent_is_lillie and route is not None:
                            purpose = "PROTECTED_" + route["protected_role"]
                            direction = "HOLD_LILLIE"
                            candidate_first = route["first_role"]
                            alternative = route["queue"]
                            first_difference = route["hard_difference"]
                            uniquely_emittable = candidate_first is not None
                            predicted = bool(
                                uniquely_emittable
                                and not role_equal(candidate_first, unique_lillie_role)
                            )
                            hold_roles.add(route["protected_role"])
                        elif parent_is_lillie and harmful_return and attacks:
                            attack_roles = {
                                canonical(row["role"]): row["role"] for row in attacks
                            }
                            if len(attack_roles) == 1:
                                candidate_first = next(iter(attack_roles.values()))
                                purpose = "PRESERVE_RETURN_SURVIVAL"
                                direction = "HOLD_LILLIE"
                                alternative = [{"kind": "ATTACK", "role": candidate_first}]
                                first_difference = {
                                    "layer": 5,
                                    "reason": "lillie_crosses_public_return_ko",
                                    "return_effects": return_effects,
                                }
                                uniquely_emittable = True
                                predicted = True
                                hold_roles.add("CURRENT_ATTACK")
                            else:
                                rejection = "harmful_return_no_unique_attack_alternative"
                        else:
                            hand_renewal = post_hand > hand_count
                            deck_margin = post_deck > deck_count
                            protected_serials = [
                                row for row in resources if row["protected_reason"]
                            ]
                            if protected_serials:
                                if parent_is_lillie:
                                    rejection = "protected_serial_without_complete_alternative"
                            elif hand_renewal or deck_margin or beneficial_return:
                                purpose = (
                                    "RETURN_SURVIVAL" if beneficial_return
                                    else "HAND_RENEWAL" if hand_renewal
                                    else "DECKOUT_MARGIN"
                                )
                                direction = (
                                    "APPROVE_PARENT_LILLIE"
                                    if parent_is_lillie else "PLAY_LILLIE"
                                )
                                candidate_first = unique_lillie_role
                                alternative = [{
                                    "kind": "PLAY_LILLIE",
                                    "card_serial": min(row["card_serial"] for row in lillie),
                                    "draw_count": draw_count,
                                    "post_hand_count": post_hand,
                                    "post_deck_count": post_deck,
                                }]
                                first_difference = {
                                    "layer": 5 if beneficial_return else 7,
                                    "reason": purpose,
                                    "hand_before": hand_count,
                                    "hand_after": post_hand,
                                    "deck_before": deck_count,
                                    "deck_after": post_deck,
                                }
                                uniquely_emittable = True
                                predicted = direction == "PLAY_LILLIE"

                    if rejection:
                        direction = "REJECT"
                        uniquely_emittable = False
                        predicted = False
                    if direction in {
                        "PLAY_LILLIE", "HOLD_LILLIE", "APPROVE_PARENT_LILLIE"
                    }:
                        classified_turns.add(turn_key)
                        classified_replays.add(entry["replay"])
                        classified_seats.add(seat)
                    if direction in {"PLAY_LILLIE", "HOLD_LILLIE"} and uniquely_emittable:
                        actionable_turns.add(turn_key)
                        actionable_replays.add(entry["replay"])
                        actionable_seats.add(seat)
                        direction_turns[direction].add(turn_key)
                    if predicted:
                        predicted_turns.add(turn_key)
                        predicted_replays.add(entry["replay"])
                        predicted_seats.add(seat)
                    counts["rows"] += 1
                    counts["direction:" + direction] += 1
                    if rejection:
                        counts["rejection:" + rejection] += 1

                    writer.writerow({
                        "replay": entry["replay"],
                        "replay_sha256": replay_sha,
                        "seat": seat,
                        "step": step_index,
                        "turn": current.get("turn"),
                        "snapshot_sha256": row_key[-1],
                        "parent_action": canonical(parent_action),
                        "parent_roles": canonical(parent_roles),
                        "parent_valid": parent_valid,
                        "owner_state": canonical(owner),
                        "lillie_roles": canonical([row["role"] for row in lillie]),
                        "lillie_serials": canonical([row["card_serial"] for row in lillie]),
                        "historical_lillie_play": turn_key in historical,
                        "prize_count": prize_count,
                        "hand_count": hand_count,
                        "deck_count": deck_count,
                        "draw_count": draw_count,
                        "shuffle_count": shuffle_count,
                        "post_hand_count": post_hand,
                        "post_deck_count": post_deck,
                        "deckout_horizon_before": deck_count,
                        "deckout_horizon_after": post_deck,
                        "attack_rows": canonical({
                            "rows": attacks, "reason": attack_reason,
                        }),
                        "current_combat": canonical(
                            [] if not attacks else [row["certificate"] for row in attacks]
                        ),
                        "hand_resources": canonical(resources),
                        "boss_explorer_conflict": canonical(supporter_conflict),
                        "backup_certificate": canonical({
                            "ready": ready_backup,
                            "formation": formation,
                            "reasons": {"ready": ready_reason, "formation": formation_reason},
                        }),
                        "hand_size_return_effects": canonical({
                            "rows": return_effects, "error": return_error,
                        }),
                        "strict_plan": canonical({
                            "plan": strict_plan,
                            "reason": plan_reason,
                        }),
                        "protected_route": canonical({
                            "route": route, "reasons": route_reasons,
                        }),
                        "purpose": purpose,
                        "direction": direction,
                        "candidate_first_role": canonical(candidate_first),
                        "alternative_action_queue": canonical(alternative),
                        "first_hard_difference": canonical(first_difference),
                        "uniquely_emittable": uniquely_emittable,
                        "predicted_first_difference": predicted,
                        "rejection_reason": rejection,
                    })

    summary = {
        "parent_main_sha256": sha256(PARENT / "main.py"),
        "deck_sha256": sha256(PARENT / "deck.csv"),
        "source_manifest_sha256": sha256(SOURCE_MANIFEST),
        "runner_sha256": sha256(Path(__file__)),
        "row_csv_sha256": sha256(rows_path),
        "lillie_metadata": effect_metadata,
        "lillie_metadata_sha256": hashlib.sha256(
            canonical(effect_metadata).encode("utf-8")
        ).hexdigest().upper(),
        "manifest_entries": len(manifest),
        "manifest_mismatches": manifest_mismatches,
        "target_seats": sum(len(entry["target_seats"]) for entry in manifest),
        "global_parent_calls": global_calls,
        "invalid_parent_actions": invalid_parent,
        "historical_lillie_play_turns": len(historical),
        "historical_lillie_play_replays": len({row[0] for row in historical}),
        "historical_lillie_play_seats": sorted({row[1] for row in historical}),
        "row_count": len(row_keys),
        "duplicate_row_keys": duplicate_row_keys,
        "strict_purpose_turns": len(classified_turns),
        "strict_purpose_replays": len(classified_replays),
        "strict_purpose_seats": sorted(classified_seats),
        "actionable_turns": len(actionable_turns),
        "actionable_replays": len(actionable_replays),
        "actionable_seats": sorted(actionable_seats),
        "predicted_first_difference_turns": len(predicted_turns),
        "predicted_first_difference_replays": len(predicted_replays),
        "predicted_first_difference_seats": sorted(predicted_seats),
        "direction_unique_turns": {
            key: len(value) for key, value in sorted(direction_turns.items())
        },
        "direction_seats": {
            key: sorted({row[1] for row in value})
            for key, value in sorted(direction_turns.items())
        },
        "hold_protected_roles": sorted(hold_roles),
        "counts": dict(sorted(counts.items())),
    }
    summary_path = OUTPUT / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if manifest_mismatches or invalid_parent or duplicate_row_keys:
        raise SystemExit(1)
    return summary


if __name__ == "__main__":
    main()
