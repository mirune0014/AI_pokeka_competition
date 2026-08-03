from __future__ import annotations

import copy
import csv
from collections import Counter, defaultdict
from contextlib import contextmanager
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
PLANNER = Path(__file__).resolve().parents[1]
MANIFEST = PLANNER / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw/source_manifest.json"
)
JUMBO_DIR = PLANNER / "next_after_lillie_one_direction_fail_20260801"
JUMBO_RUNNER = JUMBO_DIR / (
    "freeze_pre_edit_jumbo_ice_cream_actionability_census.py"
)
JUMBO_ROWS = JUMBO_DIR / (
    "pre_edit_jumbo_ice_cream_actionability_census_raw/opportunity_rows.csv"
)
JUMBO_AUDIT = JUMBO_DIR / "JUMBO_ICE_NUMERICAL_AUDIT_SOL_ULTRA.md"
NZ_DIR = PLANNER / "next_after_jumbo_no_actionable_boundary_20260801"
NZ_ROOT = NZ_DIR / "ROOT_PRE_EDIT_NEUTRALIZATION_ZONE_VERIFICATION.md"
NZ_AUDIT = NZ_DIR / "NEUTRALIZATION_ZONE_NUMERICAL_AUDIT_SOL_ULTRA.md"
OUTPUT = Path(__file__).resolve().parent / (
    "pre_edit_return_relevance_cause_census_raw"
)

EXPECTED_HASHES = {
    "parent": "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6",
    "manifest": "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68",
    "jumbo_rows": "093573F0C9D5E47EF6EA5E8277E6DD137078D06C07FC20BF8241606B14CCB1D9",
    "jumbo_audit": "1AD2E6036CCD988D478E2D6138E323D41712978FF5E564B158FAB6FEAF52C48D",
    "neutralization_root": "6BCC21DEB44E78A8ACF6E3495047DD6A62CE83C0C5C7D7822A930AAEB8462734",
    "neutralization_audit": "0335738B6EF85238143E834BFF62BFA66ABEE1072DFD413742E913FCC7941C39",
}

CAUSE_FIELDS = (
    "replay", "seat", "step", "turn", "snapshot_sha256", "attack_id",
    "blocker_index", "blocker", "cause_class", "matched_event_count",
    "matched_route_provenance", "source_zone", "source_id",
    "source_serial", "source_metadata", "route_tier", "route_sequence",
    "ready_attack_ids", "one_attach_attack_ids",
    "one_attach_energy_types", "skill_modes", "tool_status",
    "suppression_eligible", "suppression_reason",
)
SHADOW_FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "snapshot_sha256", "attack_id", "parent_action", "parent_roles",
    "parent_valid", "pre_call_owners", "baseline_status",
    "baseline_unsupported", "baseline_fields", "shadow_status",
    "shadow_unsupported", "shadow_fields", "suppressed_routes",
    "became_exact", "selection_reason", "selection_source",
    "first_hard_difference", "predicted_first_roles",
    "predicted_first_difference", "predicted_role_emittable", "errors",
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


def load_file_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata(module, card_id):
    data = module.CARD_DB.get(card_id)
    if data is None:
        return None
    attacks = []
    for attack_id in tuple(getattr(data, "attacks", ()) or ()):
        attack = module.ALL_ATTACKS.get(attack_id)
        if attack is None:
            return None
        attacks.append({
            "attack_id": attack_id,
            "name": getattr(attack, "name", None),
            "text_hash": module._dper_text_hash(getattr(attack, "text", None)),
            "energies": tuple(getattr(attack, "energies", ()) or ()),
        })
    return {
        "card_id": card_id,
        "name": getattr(data, "name", None),
        "basic": getattr(data, "basic", None),
        "stage1": getattr(data, "stage1", None),
        "stage2": getattr(data, "stage2", None),
        "ex": getattr(data, "ex", None),
        "mega_ex": getattr(data, "megaEx", None),
        "retreat_cost": getattr(data, "retreatCost", None),
        "skills": tuple({
            "name": getattr(skill, "name", None),
            "text_hash": module._dper_text_hash(getattr(skill, "text", None)),
        } for skill in tuple(getattr(data, "skills", ()) or ())),
        "attacks": tuple(attacks),
    }


def board_zone(module, obs, serial):
    opponent = module.opp_state(obs)
    for zone_name in ("active", "bench"):
        for pokemon in tuple(getattr(opponent, zone_name, ()) or ()):
            if pokemon is not None and module._pcrd_serial(pokemon) == serial:
                return "OPPONENT_" + zone_name.upper()
    return "PROJECTED_OR_UNKNOWN"


def one_attach_types(module, source, attack):
    result = []
    for energy_type in range(1, 10):
        projected = module._pcrd_project_pokemon(source)
        if projected is None:
            return None
        energies = list(module._pcrd_get(projected, "energies", ()) or ())
        cards = list(
            module._pcrd_get(projected, "energyCards", None)
            or module._pcrd_get(projected, "energy_cards", ())
            or ()
        )
        energies.append(energy_type)
        cards.append({"id": energy_type, "serial": -1000 - energy_type})
        projected["energies"] = energies
        projected["energyCards"] = cards
        if module._pcrd_attack_payment(projected, attack) is not None:
            result.append(energy_type)
    return tuple(result)


def route_analysis(module, source, target, tier, sequence, effect_state):
    state = module._dper_augment_effect_state(source, target, effect_state)
    access_state = dict(state)
    access_state["require_payable"] = False
    access = module._dper_memory_dive_access(source, access_state)
    if access.get("status") != "EXACT":
        return {
            "exact": False,
            "reason": "attack_access_unknown",
            "ready": (), "one_attach": (), "one_attach_types": {},
            "skill_modes": None, "tool_status": None,
            "safe_local_scope": False,
        }
    ready = []
    one_attach = []
    attach_types = {}
    for attack_row in tuple(access["after"].get("attack_rows", ()) or ()):
        attack_id = attack_row[0]
        attack = module.ALL_ATTACKS.get(attack_id)
        if attack is None:
            return {
                "exact": False,
                "reason": "attack_catalog_missing",
                "ready": (), "one_attach": (), "one_attach_types": {},
                "skill_modes": None, "tool_status": None,
                "safe_local_scope": False,
            }
        payment = module._pcrd_attack_payment(source, attack)
        missing = module._pcrd_missing_energy_count(source, attack)
        if payment is not None:
            ready.append(attack_id)
        if payment is None and missing == 1:
            types = one_attach_types(module, source, attack)
            if types is None:
                return {
                    "exact": False,
                    "reason": "one_attach_type_projection_unknown",
                    "ready": tuple(ready), "one_attach": tuple(one_attach),
                    "one_attach_types": attach_types,
                    "skill_modes": None, "tool_status": None,
                    "safe_local_scope": False,
                }
            if types:
                one_attach.append(attack_id)
                attach_types[str(attack_id)] = types

    skill_unsupported = []
    skill_modes = module._pcrd_supported_skill_modes(source, skill_unsupported)
    tool_unsupported = []
    tool_status = module._pcrd_tools_supported(source, tool_unsupported)
    safe_skill_modes = {
        "RESOLVED_EVOLUTION_TRIGGER", "RESOLVED_SETUP_ONLY",
        "LEGACY:RESOLVED_EVOLUTION_TRIGGER", "LEGACY:RESOLVED_SETUP_ONLY",
    }
    normalized_modes = tuple(skill_modes or ())
    safe_local_scope = bool(
        skill_modes is not None
        and not skill_unsupported
        and all(mode in safe_skill_modes for mode in normalized_modes)
        and tool_status is not None
        and not tool_unsupported
    )
    if not tuple(getattr(module.CARD_DB.get(module._pcrd_get(source, "id")), "skills", ()) or ()):
        safe_local_scope = bool(
            tool_status is not None and not tool_unsupported
        )

    if tier in {module._PCRD_READY_NOW, module._PCRD_KNOWN_PUBLIC_RESOURCE}:
        relevant = tuple(ready)
        route_class = "REACHABLE_READY_NOW"
    elif tier == module._PCRD_ONE_ATTACH:
        relevant = tuple(one_attach)
        route_class = "REACHABLE_AFTER_ONE_ATTACHMENT"
    else:
        relevant = tuple(sorted(set(ready + one_attach)))
        route_class = "REACHABLE_PUBLIC_ROUTE"
    return {
        "exact": True,
        "reason": None,
        "ready": tuple(ready),
        "one_attach": tuple(one_attach),
        "one_attach_types": attach_types,
        "skill_modes": normalized_modes,
        "skill_unsupported": tuple(skill_unsupported),
        "tool_status": tool_status,
        "tool_unsupported": tuple(tool_unsupported),
        "safe_local_scope": safe_local_scope,
        "relevant": relevant,
        "route_class": route_class,
        "source_zone": board_zone(module, module._rrc_obs, module._pcrd_serial(source)),
        "sequence": tuple(sequence),
    }


@contextmanager
def instrument_routes(module, obs, suppress_local_no_route):
    old = module._pcrd_attack_routes_for_source
    module._rrc_obs = obs
    module._rrc_route_events = []

    def wrapper(
            source, target, *, tier, sequence, effect_state,
            opponent_prizes, public_resource=None):
        analysis = route_analysis(
            module, source, target, tier, sequence, effect_state
        )
        original = old(
            source, target, tier=tier, sequence=sequence,
            effect_state=effect_state, opponent_prizes=opponent_prizes,
            public_resource=public_resource,
        )
        eligible = bool(
            original is None
            and analysis.get("exact")
            and not analysis.get("relevant")
            and analysis.get("safe_local_scope")
        )
        event = {
            "source_id": module._pcrd_get(source, "id"),
            "source_serial": module._pcrd_serial(source),
            "target_id": module._pcrd_get(target, "id"),
            "target_serial": module._pcrd_serial(target),
            "tier": tier,
            "sequence": tuple(sequence),
            "original_none": original is None,
            "analysis": analysis,
            "suppression_eligible": eligible,
            "suppressed": bool(eligible and suppress_local_no_route),
        }
        module._rrc_route_events.append(event)
        return () if eligible and suppress_local_no_route else original

    module._pcrd_attack_routes_for_source = wrapper
    try:
        yield
    finally:
        module._pcrd_attack_routes_for_source = old


def compact_fields(plan):
    if not isinstance(plan, dict):
        return None
    fields = plan.get("fields") or {}
    return freeze({
        "status": plan.get("status"),
        "current_certificate": {
            key: (plan.get("current_certificate") or {}).get(key)
            for key in (
                "attack_id", "final_damage", "ko", "prize_yield",
                "remaining_hp",
            )
        },
        "fields": {
            key: fields.get(key) for key in (
                "current_win", "certain_terminal_reply", "current_prizes",
                "current_ko", "certain_return_prizes",
                "current_attacker_survival", "next_turn_payable_attack",
                "exact_backup_ready", "exact_backup_next_prizes",
                "exact_turns_to_next_prize", "chosen_public_reply",
            )
        },
    })


def cause_class(blocker, event):
    if event is not None:
        analysis = event["analysis"]
        if event.get("suppression_eligible"):
            return "EXACT_LOCAL_NO_ROUTE"
        if analysis.get("relevant"):
            if event.get("tier") == "ONE_ORDINARY_ATTACH":
                return "REACHABLE_AFTER_ONE_ATTACHMENT"
            sequence = canonical(event.get("sequence"))
            if "RETREAT" in sequence or "FREE_PROMOTION" in sequence:
                return "REACHABLE_FREE_PROMOTION_OR_RETREAT"
            if "EVOLVE" in sequence or "RUN_AWAY" in sequence:
                return "REACHABLE_PUBLIC_EVOLUTION_OR_SWITCH"
            return "REACHABLE_READY_NOW"
        if not analysis.get("safe_local_scope"):
            return "GLOBAL_TARGET_OR_UNCERTAIN_EFFECT_SCOPE"
    if blocker.startswith("dper:") or "callback" in blocker or "post_action" in blocker:
        return "POST_ACTION_PROJECTION_OR_CALLBACK"
    if "backup" in blocker or "non_unique" in blocker or "reply" in blocker:
        return "BACKUP_OR_NONUNIQUE_REPLY_FAILURE"
    if "known_evolution" in blocker or "switch" in blocker:
        return "REACHABLE_PUBLIC_EVOLUTION_OR_SWITCH"
    return "GLOBAL_TARGET_OR_UNCERTAIN_EFFECT_SCOPE"


def match_events(module, blocker, events):
    source_id = None
    if ":" in blocker:
        try:
            source_id = int(blocker.rsplit(":", 1)[1])
        except ValueError:
            source_id = None
    candidates = [
        event for event in events
        if event.get("original_none")
        and (source_id is None or event.get("source_id") == source_id)
    ]
    if "one_attach" in blocker:
        candidates = [
            event for event in candidates
            if event.get("tier") == module._PCRD_ONE_ATTACH
        ]
    elif "retreat_attacker" in blocker:
        candidates = [
            event for event in candidates
            if "RETREAT" in canonical(event.get("sequence"))
        ]
    elif "visible_attacker" in blocker:
        candidates = [
            event for event in candidates
            if event.get("tier") == module._PCRD_READY_NOW
            and "RETREAT" not in canonical(event.get("sequence"))
        ]
    return tuple(sorted(
        candidates,
        key=lambda event: (
            event.get("source_serial") or 0,
            canonical(event.get("sequence")),
        ),
    ))


def main():
    protected = (
        OUTPUT / "cause_rows.csv",
        OUTPUT / "shadow_plan_rows.csv",
        OUTPUT / "summary.json",
    )
    if OUTPUT.exists() and any(path.exists() for path in protected):
        raise SystemExit("refusing to overwrite frozen return census")
    OUTPUT.mkdir(parents=False, exist_ok=False)

    actual_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "manifest": sha256(MANIFEST),
        "jumbo_rows": sha256(JUMBO_ROWS),
        "jumbo_audit": sha256(JUMBO_AUDIT),
        "neutralization_root": sha256(NZ_ROOT),
        "neutralization_audit": sha256(NZ_AUDIT),
    }
    if actual_hashes != EXPECTED_HASHES:
        raise SystemExit("immutable input mismatch: " + canonical(actual_hashes))

    helper = load_file_module("return_relevance_jumbo_helper", JUMBO_RUNNER)
    module = helper.load_parent()
    targets = {}
    with JUMBO_ROWS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if (
                row["rejection_reason"] == "no_heal:no_fully_rankable_plan"
                and all(
                    error.endswith(":RETURN_UNKNOWN")
                    for error in json.loads(row["no_heal_plans"])["errors"]
                )
            ):
                key = (row["replay"], int(row["seat"]), int(row["step"]))
                if key in targets:
                    raise SystemExit("duplicate frozen target key")
                targets[key] = row
    expected_alternatives = sum(
        len(json.loads(row["no_heal_plans"])["errors"])
        for row in targets.values()
    )
    if len(targets) != 225 or expected_alternatives != 254:
        raise SystemExit("frozen target count mismatch")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    replay_cache = {}
    manifest_mismatches = []
    target_seat_count = 0
    for entry in manifest:
        path = CORPUS / entry["replay"]
        digest = sha256(path)
        if digest != entry["sha256"]:
            manifest_mismatches.append(entry["replay"])
            continue
        replay_cache[entry["replay"]] = (
            digest, json.loads(path.read_text(encoding="utf-8"))
        )
        target_seat_count += len(entry["target_seats"])

    calls = 0
    invalid_parent = 0
    raw_keys = set()
    duplicate_raw_keys = 0
    seen_targets = set()
    seen_alternatives = set()
    cause_rows = []
    expected_blocker_rows = 0
    unmatched_blocker_rows = 0
    ambiguous_blocker_rows = 0
    allowed_cause_classes = {
        "REACHABLE_READY_NOW",
        "REACHABLE_AFTER_ONE_ATTACHMENT",
        "REACHABLE_FREE_PROMOTION_OR_RETREAT",
        "REACHABLE_PUBLIC_EVOLUTION_OR_SWITCH",
        "GLOBAL_TARGET_OR_UNCERTAIN_EFFECT_SCOPE",
        "EXACT_LOCAL_NO_ROUTE",
        "POST_ACTION_PROJECTION_OR_CALLBACK",
        "BACKUP_OR_NONUNIQUE_REPLY_FAILURE",
    }
    shadow_rows = []
    cause_turns = defaultdict(set)
    cause_replays = defaultdict(set)
    cause_seats = defaultdict(set)
    exact_turns = set()
    exact_replays = set()
    exact_seats = set()
    hard_turns = set()
    hard_replays = set()
    hard_seats = set()
    predicted_turns = set()
    predicted_replays = set()
    predicted_seats = set()
    layer_counts = Counter()
    selection_done = set()

    for entry in manifest:
        cached = replay_cache.get(entry["replay"])
        if cached is None:
            continue
        replay_sha, replay = cached
        for seat in entry["target_seats"]:
            helper.reset(module)
            for step_index, step in enumerate(replay["steps"]):
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat or raw.get("select") is None:
                    continue
                calls += 1
                raw_key = (
                    entry["replay"], seat, step_index,
                    current.get("turn"), snapshot_hash(raw),
                )
                duplicate_raw_keys += int(raw_key in raw_keys)
                raw_keys.add(raw_key)
                obs = module.to_observation_class(copy.deepcopy(raw))
                pre_owners = helper.owners(module)
                activation = bool(
                    module._pcrd_activation_boundary(obs) and not pre_owners
                )
                parent_action = module.agent(copy.deepcopy(raw))
                parent_roles = helper.roles(module, obs, parent_action)
                parent_valid = parent_roles is not None
                invalid_parent += int(not parent_valid)

                target_key = (entry["replay"], seat, step_index)
                frozen = targets.get(target_key)
                if frozen is None:
                    continue
                if raw_key[-1] != frozen["snapshot_sha256"]:
                    raise SystemExit("target snapshot mismatch")
                seen_targets.add(target_key)
                attacks, attack_reason = helper.attack_rows(module, obs)
                if attacks is None:
                    raise SystemExit("target attack rows unavailable: " + str(attack_reason))
                expected_ids = tuple(
                    int(error.split(":", 1)[0])
                    for error in json.loads(frozen["no_heal_plans"])["errors"]
                )
                actual_ids = tuple(row["attack_id"] for row in attacks)
                if actual_ids != expected_ids:
                    raise SystemExit("target attack alternative mismatch")

                selection = None
                predicted_roles = None
                predicted_difference = False
                first_hard = None
                turn_key = (entry["replay"], seat, current.get("turn"))

                for attack_row in attacks:
                    attack_id = attack_row["attack_id"]
                    alt_key = target_key + (attack_id,)
                    if alt_key in seen_alternatives:
                        raise SystemExit("duplicate target attack alternative")
                    seen_alternatives.add(alt_key)
                    errors = []
                    with instrument_routes(module, obs, False):
                        baseline = module._pcrd_make_plan(
                            obs, evolution=None, attack_id=attack_id,
                            use_fml=False, use_cape=False, use_ice=False,
                            require_current_attack_option=True,
                        )
                        baseline_events = copy.deepcopy(module._rrc_route_events)
                    if baseline is None or baseline.get("status") != "RETURN_UNKNOWN":
                        raise SystemExit("baseline return status mismatch")
                    blockers = tuple(
                        (baseline.get("threat_graph") or {}).get(
                            "unsupported_text", ()
                        ) or ()
                    )
                    if not blockers:
                        raise SystemExit("return unknown without blocker")
                    expected_blocker_rows += len(blockers)

                    with instrument_routes(module, obs, True):
                        shadow = module._pcrd_make_plan(
                            obs, evolution=None, attack_id=attack_id,
                            use_fml=False, use_cape=False, use_ice=False,
                            require_current_attack_option=True,
                        )
                        shadow_events = copy.deepcopy(module._rrc_route_events)
                    suppressed = tuple(
                        event for event in shadow_events if event.get("suppressed")
                    )
                    became_exact = bool(
                        shadow is not None and shadow.get("status") == "EXACT"
                    )
                    if became_exact:
                        exact_turns.add(turn_key)
                        exact_replays.add(entry["replay"])
                        exact_seats.add(seat)

                    for blocker_index, blocker in enumerate(blockers):
                        matched = match_events(module, blocker, baseline_events)
                        event_classes = {
                            cause_class(blocker, candidate)
                            for candidate in matched
                        }
                        if len(event_classes) == 1:
                            classification = next(iter(event_classes))
                        elif not matched:
                            classification = cause_class(blocker, None)
                        else:
                            classification = (
                                "GLOBAL_TARGET_OR_UNCERTAIN_EFFECT_SCOPE"
                            )
                        event = matched[0] if len(matched) == 1 else None
                        unmatched_blocker_rows += int(not matched)
                        ambiguous_blocker_rows += int(len(matched) > 1)
                        if classification not in allowed_cause_classes:
                            raise SystemExit(
                                "unclassified blocker cause: " + classification
                            )
                        cause_turns[classification].add(turn_key)
                        cause_replays[classification].add(entry["replay"])
                        cause_seats[classification].add(seat)
                        analysis = {} if event is None else event["analysis"]
                        source_id = None if event is None else event.get("source_id")
                        cause_rows.append({
                            "replay": entry["replay"],
                            "seat": seat,
                            "step": step_index,
                            "turn": current.get("turn"),
                            "snapshot_sha256": raw_key[-1],
                            "attack_id": attack_id,
                            "blocker_index": blocker_index,
                            "blocker": blocker,
                            "cause_class": classification,
                            "matched_event_count": len(matched),
                            "matched_route_provenance": canonical(tuple({
                                "source_id": candidate.get("source_id"),
                                "source_serial": candidate.get("source_serial"),
                                "tier": candidate.get("tier"),
                                "sequence": candidate.get("sequence"),
                                "suppression_eligible": candidate.get(
                                    "suppression_eligible"
                                ),
                                "analysis_reason": candidate[
                                    "analysis"
                                ].get("reason"),
                                "route_class": candidate[
                                    "analysis"
                                ].get("route_class"),
                            } for candidate in matched)),
                            "source_zone": None if event is None else analysis.get("source_zone"),
                            "source_id": source_id,
                            "source_serial": None if event is None else event.get("source_serial"),
                            "source_metadata": canonical(metadata(module, source_id)),
                            "route_tier": None if event is None else event.get("tier"),
                            "route_sequence": canonical(None if event is None else event.get("sequence")),
                            "ready_attack_ids": canonical(analysis.get("ready", ())),
                            "one_attach_attack_ids": canonical(analysis.get("one_attach", ())),
                            "one_attach_energy_types": canonical(analysis.get("one_attach_types", {})),
                            "skill_modes": canonical(analysis.get("skill_modes")),
                            "tool_status": canonical(analysis.get("tool_status")),
                            "suppression_eligible": bool(
                                event is not None and event.get("suppression_eligible")
                            ),
                            "suppression_reason": (
                                "NO_RELEVANT_ATTACK_AND_EXACT_LOCAL_SCOPE"
                                if event is not None and event.get("suppression_eligible")
                                else analysis.get("reason")
                            ),
                        })

                    # Selection is turn-level.  Evaluate only the earliest
                    # activation-boundary target callback for that turn.
                    if (
                        selection is None
                        and activation
                        and turn_key not in selection_done
                    ):
                        selection_done.add(turn_key)
                        with instrument_routes(module, obs, True):
                            selection = module._pcrd_select_plan(
                                obs, parent_action
                            )
                        chosen = selection.get("plan")
                        if isinstance(chosen, dict):
                            first_hard = (
                                chosen.get("lexicographic_comparison") or {}
                            ).get("first_difference")
                            if first_hard:
                                hard_turns.add(turn_key)
                                hard_replays.add(entry["replay"])
                                hard_seats.add(seat)
                                layer_counts[first_hard] += 1
                            if tuple(chosen.get("actions", ())):
                                predicted_roles = module._pcrd_step_main_roles(
                                    obs, chosen["actions"][0]
                                )
                                predicted_difference = bool(
                                    predicted_roles is not None
                                    and canonical(predicted_roles)
                                    != canonical(parent_roles)
                                )
                                if predicted_difference:
                                    predicted_turns.add(turn_key)
                                    predicted_replays.add(entry["replay"])
                                    predicted_seats.add(seat)

                    shadow_rows.append({
                        "replay": entry["replay"],
                        "replay_sha256": replay_sha,
                        "seat": seat,
                        "step": step_index,
                        "turn": current.get("turn"),
                        "snapshot_sha256": raw_key[-1],
                        "attack_id": attack_id,
                        "parent_action": canonical(parent_action),
                        "parent_roles": canonical(parent_roles),
                        "parent_valid": parent_valid,
                        "pre_call_owners": canonical(pre_owners),
                        "baseline_status": baseline.get("status"),
                        "baseline_unsupported": canonical(blockers),
                        "baseline_fields": canonical(compact_fields(baseline)),
                        "shadow_status": None if shadow is None else shadow.get("status"),
                        "shadow_unsupported": canonical(
                            () if shadow is None else (
                                shadow.get("threat_graph") or {}
                            ).get("unsupported_text", ())
                        ),
                        "shadow_fields": canonical(compact_fields(shadow)),
                        "suppressed_routes": canonical(suppressed),
                        "became_exact": became_exact,
                        "selection_reason": None if selection is None else selection.get("reason"),
                        "selection_source": None if selection is None else selection.get("source"),
                        "first_hard_difference": first_hard,
                        "predicted_first_roles": canonical(predicted_roles),
                        "predicted_first_difference": predicted_difference,
                        "predicted_role_emittable": bool(
                            predicted_roles is not None
                            and module._pcrd_bind_roles(obs, predicted_roles) is not None
                        ),
                        "errors": canonical(errors),
                    })

    if set(targets) != seen_targets or len(seen_alternatives) != 254:
        raise SystemExit("target execution coverage mismatch")

    with (OUTPUT / "cause_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAUSE_FIELDS)
        writer.writeheader()
        writer.writerows(cause_rows)
    with (OUTPUT / "shadow_plan_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHADOW_FIELDS)
        writer.writeheader()
        writer.writerows(shadow_rows)

    bounded = "EXACT_LOCAL_NO_ROUTE"
    cause_coverage = {
        key: {
            "turns": len(cause_turns[key]),
            "replays": len(cause_replays[key]),
            "seats": sorted(cause_seats[key]),
        }
        for key in sorted(cause_turns)
    }
    gate = {
        "integrity": bool(
            len(manifest) == 207
            and target_seat_count == 209
            and calls == 25880
            and not manifest_mismatches
            and duplicate_raw_keys == 0
            and invalid_parent == 0
            and len(seen_targets) == 225
            and len(seen_alternatives) == 254
        ),
        "blocker_assignment": bool(
            len(cause_rows) == expected_blocker_rows
            and expected_blocker_rows > 0
            and all(
                row["cause_class"] in allowed_cause_classes
                for row in cause_rows
            )
        ),
        "bounded_cause_coverage": bool(
            len(cause_turns[bounded]) >= 40
            and cause_seats[bounded] == {0, 1}
            and len(cause_replays[bounded]) >= 15
        ),
        "fully_exact": bool(
            len(exact_turns) >= 24
            and exact_seats == {0, 1}
            and len(exact_replays) >= 12
        ),
        "hard_differences": bool(
            len(hard_turns) >= 12
            and hard_seats == {0, 1}
            and len(hard_replays) >= 8
        ),
        "predicted_differences": bool(
            len(predicted_turns) >= 8
            and predicted_seats == {0, 1}
            and len(predicted_replays) >= 6
        ),
        "two_layer_classes": sum(
            count >= 3 for name, count in layer_counts.items()
            if name in {
                "CURRENT_PRIZE_KO",
                "EXACT_TERMINAL_LOSS_AVOIDANCE",
                "PUBLIC_RETURN_SURVIVAL_CONTINUITY",
                "EXACT_READY_BACKUP_CONVERSION",
            }
        ) >= 2,
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": actual_hashes,
        "integrity": {
            "replays": len(manifest),
            "target_seats": target_seat_count,
            "parent_calls": calls,
            "unique_raw_keys": len(raw_keys),
            "duplicate_raw_keys": duplicate_raw_keys,
            "invalid_parent_actions": invalid_parent,
            "manifest_mismatches": manifest_mismatches,
            "return_unknown_rows": len(seen_targets),
            "attack_alternatives": len(seen_alternatives),
            "expected_blocker_rows": expected_blocker_rows,
            "cause_rows": len(cause_rows),
            "unmatched_blocker_rows": unmatched_blocker_rows,
            "ambiguous_blocker_rows": ambiguous_blocker_rows,
            "shadow_plan_rows": len(shadow_rows),
        },
        "cause_coverage": cause_coverage,
        "shadow": {
            "fully_exact_turns": len(exact_turns),
            "fully_exact_replays": len(exact_replays),
            "fully_exact_seats": sorted(exact_seats),
            "hard_difference_turns": len(hard_turns),
            "hard_difference_replays": len(hard_replays),
            "hard_difference_seats": sorted(hard_seats),
            "predicted_difference_turns": len(predicted_turns),
            "predicted_difference_replays": len(predicted_replays),
            "predicted_difference_seats": sorted(predicted_seats),
            "first_hard_layers": dict(layer_counts),
        },
        "numeric_gate": gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(gate.values()),
        "root_qualitative_audit": "PENDING",
        "decision_if_gate_fails": (
            "STOP__RETURN_UNKNOWN_NOT_ONE_ACTIONABLE_BOUNDED_CAUSE"
        ),
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
