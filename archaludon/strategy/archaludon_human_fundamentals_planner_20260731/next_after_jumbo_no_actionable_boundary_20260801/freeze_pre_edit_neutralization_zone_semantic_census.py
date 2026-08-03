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
PARENT = ROOT / "archaludon" / "candidates" / (
    "archaludon_purpose_first_pokegear_boss_transaction_v1"
)
CORPUS = ROOT / "archaludon" / "live" / "55070349" / (
    "refresh_20260729_1241"
) / "shadow_corpus_196_prior_plus_11_new"
MANIFEST = ROOT / "archaludon" / "strategy" / (
    "archaludon_human_fundamentals_planner_20260731"
) / "next_after_metal_allocation_fail_20260801" / (
    "night_stretcher_callback_census_raw"
) / "source_manifest.json"
JUMBO_DIR = Path(__file__).resolve().parents[1] / (
    "next_after_lillie_one_direction_fail_20260801"
)
JUMBO_RUNNER = JUMBO_DIR / (
    "freeze_pre_edit_jumbo_ice_cream_actionability_census.py"
)
JUMBO_ROWS = JUMBO_DIR / (
    "pre_edit_jumbo_ice_cream_actionability_census_raw"
) / "opportunity_rows.csv"
JUMBO_SUMMARY = JUMBO_DIR / (
    "pre_edit_jumbo_ice_cream_actionability_census_raw"
) / "summary.json"
OUTPUT = Path(__file__).resolve().parent / (
    "pre_edit_neutralization_zone_semantic_census_raw"
)

ZONE = 1247
EXPECTED_NAME = "Neutralization Zone"
EXPECTED_TEXT_HASH = (
    "cf3fb44117e74c1fc5ac792a4721cd1ea345a1caa0a861931a59a46a842fd877"
)
EXPECTED_PARENT_SHA = (
    "558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6"
)
EXPECTED_MANIFEST_SHA = (
    "90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68"
)
EXPECTED_JUMBO_RUNNER_SHA = (
    "3441E6DFA25140E9C70CABB58E9F36CF3DF76FCD25B3B36311590FA83CF9EF8B"
)
EXPECTED_JUMBO_ROWS_SHA = (
    "093573F0C9D5E47EF6EA5E8277E6DD137078D06C07FC20BF8241606B14CCB1D9"
)
EXPECTED_JUMBO_SUMMARY_SHA = (
    "BB38450572DD285FEDAD3B79616CDEE22A0A32AC626111038605CE2239EF085C"
)

GAP_FIELDS = (
    "replay", "seat", "step", "turn", "snapshot_sha256", "gap_class",
    "attack_alternative_count", "attack_errors", "stadium_card_id",
    "stadium_card_name", "stadium_skill_name", "stadium_text_hash",
    "unsupported_public_identities",
)
OPPORTUNITY_FIELDS = (
    "replay", "replay_sha256", "seat", "step", "turn",
    "snapshot_sha256", "zone_serial", "parent_action", "parent_roles",
    "parent_valid", "pre_call_owners", "activation_boundary",
    "actual_attack_ids", "selection_reason", "selection_source",
    "baseline_plan", "chosen_plan", "first_hard_difference",
    "predicted_first_roles", "predicted_first_difference",
    "affected_certificates", "example_counts", "blocked_source_ids",
    "protected_target_ids", "errors",
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


def exact_zone_metadata(module):
    card = module.CARD_DB.get(ZONE)
    skills = tuple(getattr(card, "skills", ()) or ()) if card else ()
    return {
        "card_id": ZONE,
        "card_name": None if card is None else getattr(card, "name", None),
        "skill_count": len(skills),
        "skill_name": None if len(skills) != 1 else getattr(skills[0], "name", None),
        "skill_text": None if len(skills) != 1 else getattr(skills[0], "text", None),
        "normalized_text_hash": (
            None if len(skills) != 1
            else module._dper_text_hash(getattr(skills[0], "text", None))
        ),
    }


def card_identity(module, card_id):
    data = module.CARD_DB.get(card_id)
    skills = tuple(getattr(data, "skills", ()) or ()) if data else ()
    return {
        "card_id": card_id,
        "card_name": None if data is None else getattr(data, "name", None),
        "skills": tuple(
            {
                "name": getattr(skill, "name", None),
                "text_hash": module._dper_text_hash(getattr(skill, "text", None)),
            }
            for skill in skills
        ),
    }


def board_skill_tool_gaps(module, obs):
    rows = []
    for side, player in enumerate(tuple(obs.current.players or ())):
        for zone_name in ("active", "bench"):
            for pokemon in tuple(getattr(player, zone_name, ()) or ()):
                if pokemon is None:
                    continue
                unsupported = []
                modes = module._pcrd_supported_skill_modes(pokemon, unsupported)
                if modes is None or unsupported:
                    identity = card_identity(module, getattr(pokemon, "id", None))
                    rows.append({
                        "side": side,
                        "zone": zone_name,
                        "kind": "POKEMON_SKILL",
                        "serial": module._pcrd_serial(pokemon),
                        "identity": identity,
                        "reasons": tuple(sorted(set(unsupported))),
                    })
                tool_unsupported = []
                tool_result = module._pcrd_tools_supported(
                    pokemon, tool_unsupported
                )
                if tool_result is None or tool_unsupported:
                    for tool in tuple(getattr(pokemon, "tools", ()) or ()):
                        rows.append({
                            "side": side,
                            "zone": zone_name,
                            "kind": "TOOL",
                            "host_serial": module._pcrd_serial(pokemon),
                            "serial": module._pcrd_serial(tool),
                            "identity": card_identity(
                                module, getattr(tool, "id", None)
                            ),
                            "reasons": tuple(sorted(set(tool_unsupported))),
                        })
    unique = {canonical(row): row for row in rows}
    return tuple(unique[key] for key in sorted(unique))


def zone_card(obs, module):
    stadium = tuple(obs.current.stadium or ())
    if (
        len(stadium) == 1
        and getattr(stadium[0], "id", None) == ZONE
        and module._pcrd_serial(stadium[0]) is not None
    ):
        return stadium[0]
    return None


def is_rule_box(module, pokemon) -> bool:
    data = module.CARD_DB.get(module._pcrd_get(pokemon, "id"))
    if data is None:
        raise ValueError("missing_rule_box_catalog_identity")
    ex = module._pcrd_get(data, "ex")
    mega = module._pcrd_get(data, "megaEx")
    if not isinstance(ex, bool) or not isinstance(mega, bool):
        raise ValueError("unsupported_rule_box_catalog_type")
    return ex or mega


def patch_certificate_for_zone(module, source, attack_id, target, result, state):
    if not isinstance(result, dict) or result.get("status") != "EXACT":
        return result
    if not result.get("attack_damage"):
        return result
    source_rule = is_rule_box(module, source)
    target_rule = is_rule_box(module, target)
    ignores_target_effects = attack_id == 479
    patched = copy.deepcopy(result)
    events = getattr(module, "_nz_census_events")

    if source_rule and not target_rule and not ignores_target_effects:
        original_damage = patched.get("final_damage")
        target_hp = patched.get("target_hp")
        if not isinstance(original_damage, int) or not isinstance(target_hp, int):
            return {
                "status": "UNKNOWN",
                "unsupported_text": ("neutralization_zone_damage_state_unknown",),
                "pipeline": tuple(patched.get("pipeline", ())),
            }
        patched["final_damage"] = 0
        patched["remaining_hp"] = target_hp
        patched["ko"] = False
        patched["prize_yield"] = 0
        patched["sturdy_applied"] = False
        patched["post_damage_counter_return"] = 0
        patched["attacker_survival"] = True
        patched["post_reply_resource_ledger"] = {
            **dict(patched.get("post_reply_resource_ledger", {})),
            "return_damage_counters": 0,
        }
        patched["pipeline"] = tuple(patched.get("pipeline", ())) + ({
            "step": "neutralization_zone_prevent_active_attack_damage",
            "stadium_id": ZONE,
            "damage_before": original_damage,
            "damage": 0,
        },)
        patched["neutralization_zone_prevented"] = True

        # If the original exact attack was lethal, rebuild the one visible
        # leave-play route whose availability depends on survival.  No hidden
        # draw/search identity is inferred.
        if module._pcrd_get(target, "id") == 66:
            unsupported = []
            modes = module._pcrd_supported_skill_modes(target, unsupported)
            deck_count = state.get("target_deck_count")
            own_count = state.get("target_own_pokemon_count")
            bench = tuple(state.get("target_bench", ()) or ())
            if (
                modes is not None
                and not unsupported
                and "DPER:RUN_AWAY_DRAW" in modes
                and state.get("run_away_available")
                and isinstance(deck_count, int)
                and isinstance(own_count, int)
                and deck_count > 0
                and own_count > 1
                and bench
                and state.get("run_away_once_unspent", True)
                and state.get("target_survives_in_play", True)
            ):
                routes = []
                for pokemon in bench:
                    serial = module._pcrd_serial(pokemon)
                    if serial is None:
                        return {
                            "status": "UNKNOWN",
                            "unsupported_text": (
                                "neutralization_zone_run_away_serial_unknown",
                            ),
                            "pipeline": tuple(patched.get("pipeline", ())),
                        }
                    routes.append({
                        "kind": "RUN_AWAY_DRAW_PROMOTION",
                        "new_active_serial": serial,
                        "new_active_id": module._pcrd_get(pokemon, "id"),
                    })
                patched["run_away_draw_executable"] = True
                patched["persistent_progress"] = False
                patched["exact_public_reply_routes"] = tuple(routes)
        events.append({
            "scope": state.get("_nz_scope", "CURRENT_OR_RETURN"),
            "source_id": module._pcrd_get(source, "id"),
            "source_serial": module._pcrd_serial(source),
            "attack_id": attack_id,
            "target_id": module._pcrd_get(target, "id"),
            "target_serial": module._pcrd_serial(target),
            "damage_before": original_damage,
            "damage_after": 0,
            "prevented": True,
        })
    elif not source_rule and isinstance(patched.get("final_damage"), int):
        events.append({
            "scope": state.get("_nz_scope", "CURRENT_OR_RETURN"),
            "source_id": module._pcrd_get(source, "id"),
            "source_serial": module._pcrd_serial(source),
            "attack_id": attack_id,
            "target_id": module._pcrd_get(target, "id"),
            "target_serial": module._pcrd_serial(target),
            "damage_before": patched.get("final_damage"),
            "damage_after": patched.get("final_damage"),
            "prevented": False,
            "reason": "NON_RULE_BOX_SOURCE",
        })
    elif source_rule and target_rule and isinstance(patched.get("final_damage"), int):
        events.append({
            "scope": state.get("_nz_scope", "CURRENT_OR_RETURN"),
            "source_id": module._pcrd_get(source, "id"),
            "source_serial": module._pcrd_serial(source),
            "attack_id": attack_id,
            "target_id": module._pcrd_get(target, "id"),
            "target_serial": module._pcrd_serial(target),
            "damage_before": patched.get("final_damage"),
            "damage_after": patched.get("final_damage"),
            "prevented": False,
            "reason": "RULE_BOX_TARGET",
        })

    components = []
    for component in tuple(patched.get("bench_components", ()) or ()):
        row = dict(component)
        target_serial = row.get("target_serial")
        target_bench = tuple(state.get("target_bench", ()) or ())
        matches = [
            pokemon for pokemon in target_bench
            if module._pcrd_serial(pokemon) == target_serial
        ]
        if len(matches) == 1 and source_rule and not is_rule_box(module, matches[0]):
            before = row.get("damage")
            row["damage"] = 0
            row["prevented_by"] = "NEUTRALIZATION_ZONE"
            events.append({
                "scope": "BENCH",
                "source_id": module._pcrd_get(source, "id"),
                "source_serial": module._pcrd_serial(source),
                "attack_id": attack_id,
                "target_id": module._pcrd_get(matches[0], "id"),
                "target_serial": target_serial,
                "damage_before": before,
                "damage_after": 0,
                "prevented": True,
            })
        components.append(row)
    patched["bench_components"] = tuple(components)
    return patched


@contextmanager
def neutralization_semantics(module):
    old_stadium = module._pcrd_stadium_state
    old_inventory = module._pcrd_public_effect_inventory
    old_oracle = module._pcrd_public_combat_oracle
    module._nz_census_events = []

    def stadium_state(obs, projected_fml=False):
        if projected_fml:
            return old_stadium(obs, projected_fml=True)
        card = zone_card(obs, module)
        if card is None:
            return old_stadium(obs, projected_fml=False)
        return {
            "status": "EXACT",
            "full_metal_lab": False,
            "battle_cage": False,
            "forest_of_vitality": False,
            "neutralization_zone": True,
            "serial": module._pcrd_serial(card),
        }

    def inventory(obs, **kwargs):
        result = old_inventory(obs, **kwargs)
        if zone_card(obs, module) is None or not isinstance(result, dict):
            return result
        result = copy.deepcopy(result)
        classifications = []
        replaced = False
        for row in tuple(result.get("classifications", ()) or ()):
            current = dict(row)
            if current.get("kind") == "STADIUM" and current.get("zone") == "STADIUM":
                current.update({
                    "card_id": ZONE,
                    "classification": "CENSUS:NEUTRALIZATION_ZONE",
                })
                replaced = True
            classifications.append(current)
        if not replaced:
            classifications.append({
                "side": "symmetric",
                "zone": "STADIUM",
                "kind": "STADIUM",
                "card_id": ZONE,
                "classification": "CENSUS:NEUTRALIZATION_ZONE",
            })
        result["classifications"] = tuple(classifications)
        unsupported = tuple(
            reason for reason in tuple(result.get("unsupported_text", ()) or ())
            if reason not in {"unhandled_public_stadium", "projected_stadium_unknown"}
        )
        result["unsupported_text"] = unsupported
        if "status" in result:
            result["status"] = "EXACT" if not unsupported else result["status"]
        return result

    def oracle(source, attack_id, target, effect_state=None):
        state = dict(effect_state or {})
        result = old_oracle(source, attack_id, target, state)
        return patch_certificate_for_zone(
            module, source, attack_id, target, result, state
        )

    module._pcrd_stadium_state = stadium_state
    module._pcrd_public_effect_inventory = inventory
    module._pcrd_public_combat_oracle = oracle
    try:
        yield
    finally:
        module._pcrd_stadium_state = old_stadium
        module._pcrd_public_effect_inventory = old_inventory
        module._pcrd_public_combat_oracle = old_oracle


def compact_plan(plan):
    if not isinstance(plan, dict):
        return None
    fields = plan.get("fields") or {}
    certificate = plan.get("current_certificate") or {}
    return freeze({
        "status": plan.get("status"),
        "actions": plan.get("actions"),
        "current_certificate": {
            key: certificate.get(key) for key in (
                "source_id", "source_serial", "attack_id", "target_id",
                "target_serial", "final_damage", "remaining_hp", "ko",
                "prize_yield", "attack_damage", "pipeline",
                "bench_components", "persistent_effects",
            )
        },
        "fields": {
            key: fields.get(key) for key in (
                "current_win", "current_prizes", "current_ko",
                "certain_terminal_reply", "certain_return_prizes",
                "current_attacker_survival", "next_turn_payable_attack",
                "exact_backup_ready", "chosen_public_reply",
            )
        },
    })


def summarize_events(events):
    unique = {canonical(row): row for row in events}
    rows = tuple(unique[key] for key in sorted(unique))
    counts = Counter()
    for row in rows:
        if row.get("prevented"):
            counts["EX_OR_MEGA_DAMAGE_PREVENTED"] += 1
            if row.get("scope") not in {"CURRENT", "BENCH"}:
                counts["PUBLIC_RETURN_DAMAGE_PREVENTED"] += 1
        elif row.get("reason") == "NON_RULE_BOX_SOURCE" and row.get("damage_after", 0) > 0:
            counts["NON_EX_DAMAGE_REMAINS"] += 1
        elif row.get("reason") == "RULE_BOX_TARGET" and row.get("damage_after", 0) > 0:
            counts["RULE_BOX_TARGET_UNPROTECTED"] += 1
    return rows, dict(counts)


def main():
    protected = (
        OUTPUT / "gap_identity_rows.csv",
        OUTPUT / "opportunity_rows.csv",
        OUTPUT / "summary.json",
    )
    if OUTPUT.exists() and any(path.exists() for path in protected):
        raise SystemExit("refusing to overwrite frozen census output")
    OUTPUT.mkdir(parents=False, exist_ok=False)

    input_hashes = {
        "parent": sha256(PARENT / "main.py"),
        "manifest": sha256(MANIFEST),
        "jumbo_runner": sha256(JUMBO_RUNNER),
        "jumbo_rows": sha256(JUMBO_ROWS),
        "jumbo_summary": sha256(JUMBO_SUMMARY),
    }
    expected = {
        "parent": EXPECTED_PARENT_SHA,
        "manifest": EXPECTED_MANIFEST_SHA,
        "jumbo_runner": EXPECTED_JUMBO_RUNNER_SHA,
        "jumbo_rows": EXPECTED_JUMBO_ROWS_SHA,
        "jumbo_summary": EXPECTED_JUMBO_SUMMARY_SHA,
    }
    if input_hashes != expected:
        raise SystemExit("immutable input hash mismatch: " + canonical(input_hashes))

    helper = load_file_module("nz_frozen_jumbo_helper", JUMBO_RUNNER)
    module = helper.load_parent()
    metadata = exact_zone_metadata(module)
    if not (
        metadata["card_name"] == EXPECTED_NAME
        and metadata["skill_count"] == 1
        and metadata["skill_name"] == EXPECTED_NAME
        and metadata["normalized_text_hash"] == EXPECTED_TEXT_HASH
    ):
        raise SystemExit("Neutralization Zone metadata mismatch: " + canonical(metadata))

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    replay_cache = {}
    manifest_mismatches = []
    target_seats = 0
    for entry in manifest:
        path = CORPUS / entry["replay"]
        digest = sha256(path)
        if digest != entry["sha256"]:
            manifest_mismatches.append(entry["replay"])
            continue
        replay_cache[entry["replay"]] = (digest, json.loads(path.read_text(encoding="utf-8")))
        target_seats += len(entry["target_seats"])

    calls = 0
    invalid_parent = 0
    raw_keys = set()
    duplicate_raw_keys = 0
    zone_turns = set()
    zone_replays = set()
    zone_seats = set()
    opportunity_turns = set()
    opportunity_rows = []
    affected_keys = set()
    affected_turns = set()
    affected_replays = set()
    affected_seats = set()
    hard_turns = set()
    hard_replays = set()
    hard_seats = set()
    predicted_turns = set()
    predicted_replays = set()
    predicted_seats = set()
    blocked_sources = set()
    protected_targets = set()
    global_examples = Counter()

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
                    module._pcrd_activation_boundary(obs)
                    and not pre_owners
                )
                parent_action = module.agent(copy.deepcopy(raw))
                parent_roles = helper.roles(module, obs, parent_action)
                parent_valid = parent_roles is not None
                invalid_parent += int(not parent_valid)
                zone = zone_card(obs, module)
                if zone is None:
                    continue
                turn_key = (entry["replay"], seat, current.get("turn"))
                zone_turns.add(turn_key)
                zone_replays.add(entry["replay"])
                zone_seats.add(seat)
                if (
                    not activation
                    or turn_key in opportunity_turns
                    or obs.select.context != module.SelectContext.MAIN
                ):
                    continue
                opportunity_turns.add(turn_key)
                errors = []
                selection = {
                    "plan": None, "baseline": None, "candidate": None,
                    "reason": "not_run", "source": "PARENT", "comparisons": {},
                }
                predicted_roles = None
                predicted_difference = False
                actual_attack_ids = []
                try:
                    attacks, attack_reason = helper.attack_rows(module, obs)
                    if attacks is None:
                        errors.append(str(attack_reason))
                        attacks = []
                    actual_attack_ids = [row["attack_id"] for row in attacks]
                    with neutralization_semantics(module):
                        selection = module._pcrd_select_plan(obs, parent_action)
                        chosen = selection.get("plan")
                        if chosen is not None and tuple(chosen.get("actions", ())):
                            predicted_roles = module._pcrd_step_main_roles(
                                obs, chosen["actions"][0]
                            )
                            predicted_difference = bool(
                                predicted_roles is not None
                                and canonical(predicted_roles) != canonical(parent_roles)
                            )

                        # Natural, currently emittable attacks provide direct
                        # current and return certificates without inventing an
                        # action or hidden card.
                        direct_plans = []
                        for attack_row in attacks:
                            plan = module._pcrd_make_plan(
                                obs,
                                evolution=None,
                                attack_id=attack_row["attack_id"],
                                use_fml=False,
                                use_cape=False,
                                use_ice=False,
                                require_current_attack_option=True,
                            )
                            if plan is not None:
                                direct_plans.append(plan)
                        plans = direct_plans + [
                            plan for plan in (
                                selection.get("baseline"),
                                selection.get("plan"),
                                selection.get("candidate"),
                            ) if isinstance(plan, dict)
                        ]
                        events = list(module._nz_census_events)
                        for plan in plans:
                            certificate = plan.get("current_certificate") or {}
                            if certificate.get("neutralization_zone_prevented"):
                                events.append({
                                    "scope": "CURRENT",
                                    "source_id": certificate.get("source_id"),
                                    "source_serial": certificate.get("source_serial"),
                                    "attack_id": certificate.get("attack_id"),
                                    "target_id": certificate.get("target_id"),
                                    "target_serial": certificate.get("target_serial"),
                                    "damage_before": certificate.get("printed_or_formula_damage"),
                                    "damage_after": certificate.get("final_damage"),
                                    "prevented": True,
                                })
                            for route in tuple((plan.get("threat_graph") or {}).get("routes", ()) or ()):
                                cert = route.get("certificate") or {}
                                if cert.get("neutralization_zone_prevented"):
                                    events.append({
                                        "scope": "RETURN",
                                        "source_id": cert.get("source_id"),
                                        "source_serial": cert.get("source_serial"),
                                        "attack_id": cert.get("attack_id"),
                                        "target_id": cert.get("target_id"),
                                        "target_serial": cert.get("target_serial"),
                                        "damage_before": cert.get("printed_or_formula_damage"),
                                        "damage_after": cert.get("final_damage"),
                                        "prevented": True,
                                    })
                        events, example_counts = summarize_events(events)
                except Exception as error:
                    errors.append(type(error).__name__ + ":" + str(error))
                    events = ()
                    example_counts = {}

                for event in events:
                    event_key = (
                        entry["replay"], seat, current.get("turn"),
                        event.get("scope"), event.get("source_serial"),
                        event.get("attack_id"), event.get("target_serial"),
                    )
                    if event.get("prevented"):
                        affected_keys.add(event_key)
                        affected_turns.add(turn_key)
                        affected_replays.add(entry["replay"])
                        affected_seats.add(seat)
                        blocked_sources.add(event.get("source_id"))
                        protected_targets.add(event.get("target_id"))
                global_examples.update(example_counts)

                first_hard = None
                chosen = selection.get("plan")
                if isinstance(chosen, dict):
                    first_hard = (
                        chosen.get("lexicographic_comparison") or {}
                    ).get("first_difference")
                    if first_hard:
                        hard_turns.add(turn_key)
                        hard_replays.add(entry["replay"])
                        hard_seats.add(seat)
                if predicted_difference:
                    predicted_turns.add(turn_key)
                    predicted_replays.add(entry["replay"])
                    predicted_seats.add(seat)

                opportunity_rows.append({
                    "replay": entry["replay"],
                    "replay_sha256": replay_sha,
                    "seat": seat,
                    "step": step_index,
                    "turn": current.get("turn"),
                    "snapshot_sha256": raw_key[-1],
                    "zone_serial": module._pcrd_serial(zone),
                    "parent_action": canonical(parent_action),
                    "parent_roles": canonical(parent_roles),
                    "parent_valid": parent_valid,
                    "pre_call_owners": canonical(pre_owners),
                    "activation_boundary": activation,
                    "actual_attack_ids": canonical(actual_attack_ids),
                    "selection_reason": selection.get("reason"),
                    "selection_source": selection.get("source"),
                    "baseline_plan": canonical(compact_plan(selection.get("baseline"))),
                    "chosen_plan": canonical(compact_plan(selection.get("plan"))),
                    "first_hard_difference": first_hard,
                    "predicted_first_roles": canonical(predicted_roles),
                    "predicted_first_difference": predicted_difference,
                    "affected_certificates": canonical(events),
                    "example_counts": canonical(example_counts),
                    "blocked_source_ids": canonical(sorted(
                        {row.get("source_id") for row in events if row.get("prevented")}
                    )),
                    "protected_target_ids": canonical(sorted(
                        {row.get("target_id") for row in events if row.get("prevented")}
                    )),
                    "errors": canonical(errors),
                })

    gap_rows = []
    gap_counts = Counter()
    stadium_partition = Counter()
    with JUMBO_ROWS.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["rejection_reason"] != "no_heal:no_fully_rankable_plan":
                continue
            replay = replay_cache[row["replay"]][1]
            seat = int(row["seat"])
            step_index = int(row["step"])
            raw = replay["steps"][step_index][seat].get("observation") or {}
            if snapshot_hash(raw) != row["snapshot_sha256"]:
                raise SystemExit("Jumbo row snapshot mismatch")
            obs = module.to_observation_class(copy.deepcopy(raw))
            plan_payload = json.loads(row["no_heal_plans"])
            attack_errors = tuple(plan_payload.get("errors", ()))
            if attack_errors and all(error.endswith(":RETURN_UNKNOWN") for error in attack_errors):
                gap_class = "RETURN_UNKNOWN"
            elif any(error.endswith(":unavailable") for error in attack_errors):
                stadium = module._pcrd_stadium_state(obs)
                gap_class = (
                    "UNSUPPORTED_STADIUM"
                    if stadium.get("status") != "EXACT"
                    else "UNSUPPORTED_SKILL_TOOL"
                )
            else:
                raise SystemExit("unclassified Jumbo failure: " + canonical(attack_errors))
            gap_counts[gap_class] += 1

            stadium_cards = tuple(obs.current.stadium or ())
            stadium_id = None
            stadium_name = None
            stadium_skill = None
            stadium_hash = None
            if len(stadium_cards) == 1:
                stadium_id = getattr(stadium_cards[0], "id", None)
                identity = card_identity(module, stadium_id)
                stadium_name = identity["card_name"]
                if len(identity["skills"]) == 1:
                    stadium_skill = identity["skills"][0]["name"]
                    stadium_hash = identity["skills"][0]["text_hash"]
            if gap_class == "UNSUPPORTED_STADIUM":
                stadium_partition[(stadium_id, stadium_name, stadium_hash)] += 1
            identities = (
                board_skill_tool_gaps(module, obs)
                if gap_class == "UNSUPPORTED_SKILL_TOOL" else ()
            )
            gap_rows.append({
                "replay": row["replay"],
                "seat": seat,
                "step": step_index,
                "turn": int(row["turn"]),
                "snapshot_sha256": row["snapshot_sha256"],
                "gap_class": gap_class,
                "attack_alternative_count": len(attack_errors),
                "attack_errors": canonical(attack_errors),
                "stadium_card_id": stadium_id,
                "stadium_card_name": stadium_name,
                "stadium_skill_name": stadium_skill,
                "stadium_text_hash": stadium_hash,
                "unsupported_public_identities": canonical(identities),
            })

    if gap_counts != Counter({
        "RETURN_UNKNOWN": 225,
        "UNSUPPORTED_STADIUM": 128,
        "UNSUPPORTED_SKILL_TOOL": 70,
    }):
        raise SystemExit("Jumbo failure taxonomy mismatch: " + canonical(gap_counts))

    with (OUTPUT / "gap_identity_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GAP_FIELDS)
        writer.writeheader()
        writer.writerows(gap_rows)
    with (OUTPUT / "opportunity_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OPPORTUNITY_FIELDS)
        writer.writeheader()
        writer.writerows(opportunity_rows)

    numeric_gate = {
        "integrity": bool(
            len(manifest) == 207
            and target_seats == 209
            and calls == 25880
            and not manifest_mismatches
            and duplicate_raw_keys == 0
            and invalid_parent == 0
        ),
        "zone_turns": bool(
            len(zone_turns) >= 40
            and zone_seats == {0, 1}
            and len(zone_replays) >= 12
        ),
        "affected_certificates": bool(
            len(affected_keys) >= 24
            and affected_seats == {0, 1}
            and len(affected_replays) >= 8
        ),
        "hard_differences": bool(
            len(hard_turns) >= 12
            and hard_seats == {0, 1}
            and len(hard_replays) >= 6
        ),
        "predicted_differences": bool(
            len(predicted_turns) >= 8
            and predicted_seats == {0, 1}
            and len(predicted_replays) >= 4
        ),
        "four_example_classes": all(
            global_examples[key] >= 3 for key in (
                "EX_OR_MEGA_DAMAGE_PREVENTED",
                "NON_EX_DAMAGE_REMAINS",
                "RULE_BOX_TARGET_UNPROTECTED",
                "PUBLIC_RETURN_DAMAGE_PREVENTED",
            )
        ),
        "identity_diversity": bool(
            len(blocked_sources - {None}) >= 2
            and len(protected_targets - {None}) >= 4
        ),
    }
    summary = {
        "status": "ROOT_AUDIT_REQUIRED",
        "input_hashes": input_hashes,
        "metadata": metadata,
        "integrity": {
            "replays": len(manifest),
            "target_seats": target_seats,
            "parent_calls": calls,
            "manifest_mismatches": manifest_mismatches,
            "unique_raw_keys": len(raw_keys),
            "duplicate_raw_keys": duplicate_raw_keys,
            "invalid_parent_actions": invalid_parent,
        },
        "jumbo_failure_taxonomy": dict(gap_counts),
        "stadium_partition": [
            {
                "card_id": key[0], "card_name": key[1],
                "normalized_text_hash": key[2], "rows": count,
            }
            for key, count in sorted(
                stadium_partition.items(), key=lambda item: (-item[1], repr(item[0]))
            )
        ],
        "natural_coverage": {
            "zone_independent_turns": len(zone_turns),
            "zone_replays": len(zone_replays),
            "zone_seats": sorted(zone_seats),
            "opportunity_rows": len(opportunity_rows),
            "affected_certificate_keys": len(affected_keys),
            "affected_turns": len(affected_turns),
            "affected_replays": len(affected_replays),
            "affected_seats": sorted(affected_seats),
            "hard_plan_ranking_difference_turns": len(hard_turns),
            "hard_difference_replays": len(hard_replays),
            "hard_difference_seats": sorted(hard_seats),
            "predicted_first_action_difference_turns": len(predicted_turns),
            "predicted_difference_replays": len(predicted_replays),
            "predicted_difference_seats": sorted(predicted_seats),
            "example_counts": dict(global_examples),
            "blocked_source_ids": sorted(blocked_sources - {None}),
            "protected_target_ids": sorted(protected_targets - {None}),
        },
        "numeric_gate": numeric_gate,
        "numeric_gate_pass_before_root_qualitative_audit": all(numeric_gate.values()),
        "root_qualitative_audit": "PENDING",
        "decision_if_numeric_gate_fails": (
            "STOP__INSUFFICIENT_NATURAL_SEMANTIC_COVERAGE"
        ),
    }
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
