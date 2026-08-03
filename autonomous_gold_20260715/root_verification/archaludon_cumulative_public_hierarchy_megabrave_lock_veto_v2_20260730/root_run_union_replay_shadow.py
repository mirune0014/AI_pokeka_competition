from __future__ import annotations

import collections
import copy
import csv
import hashlib
import importlib.util
import json
import os
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
)
PARENT_DIR = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
FROZEN_SOURCE_MANIFEST = (
    ROOT
    / "autonomous_gold_20260715"
    / "implementation"
    / "archaludon_search_aware_active_terminal_before_nonterminal_boss_v1"
    / "shadow_source_manifest.csv"
)
HISTORICAL_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55073442"
    / "refresh_20260729_1541"
    / "shadow_corpus_207_prior_plus_10_new"
)
CURRENT_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "maturity_20260730_0127"
)
REFRESH_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "refresh_20260730_0211"
)

EXPECTED_PARENT_SHA = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_DECK_SHA = (
    "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"
)
EXPECTED_FROZEN_SOURCE_MANIFEST_SHA = (
    "6427C8AD1DF07A0F95E7DE67489CDA76D7EC2B71AB988F56677724BCBEE5DAE1"
)
EXPECTED_FILES = 261
EXPECTED_CALLBACKS = 14464


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CANDIDATE = load_module(
    "cumulative_union_shadow_candidate",
    CANDIDATE_DIR / "main.py",
)
PARENT = load_module(
    "cumulative_union_shadow_parent",
    PARENT_DIR / "main.py",
)
COMPONENT_MANIFEST = json.loads(
    (HERE / "component_import_manifest.json").read_text(encoding="utf-8")
)
ISOLATED = {}
for position, component in enumerate(COMPONENT_MANIFEST["components"]):
    component_path = ROOT / component["source_path"]
    if sha256(component_path) != component["source_sha256"]:
        raise AssertionError(("isolated source changed", component))
    ISOLATED[component["rule_id"]] = load_module(
        f"cumulative_union_isolated_{position}",
        component_path,
    )


def source_rows() -> list[dict]:
    if sha256(FROZEN_SOURCE_MANIFEST) != EXPECTED_FROZEN_SOURCE_MANIFEST_SHA:
        raise AssertionError("frozen source manifest changed")
    with FROZEN_SOURCE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != EXPECTED_FILES:
        raise AssertionError(len(rows))
    sources = []
    seen = set()
    for row in rows:
        episode = int(row["episode"])
        if episode in seen:
            raise AssertionError(("duplicate episode", episode))
        seen.add(episode)
        if row["population"] == "historical":
            path = HISTORICAL_DIR / row["filename"]
        elif row["population"] == "current":
            maturity_path = CURRENT_DIR / row["filename"]
            refresh_path = REFRESH_DIR / row["filename"]
            path = maturity_path if maturity_path.is_file() else refresh_path
        else:
            raise AssertionError(row)
        if (
            not path.is_file()
            or sha256(path) != row["sha256"]
            or path.stat().st_size != int(row["bytes"])
        ):
            raise AssertionError(("source mismatch", row, path))
        sources.append(
            {
                "population": row["population"],
                "episode": episode,
                "seat": int(row["seat"]),
                "reward": row["reward"],
                "filename": row["filename"],
                "bytes": int(row["bytes"]),
                "sha256": row["sha256"],
                "path": path,
            }
        )
    return sources


def reset_modules(label: str) -> None:
    CANDIDATE._cum_reset_runtime(label)
    CANDIDATE._cum_game_epoch += 1
    CANDIDATE._sat_game_epoch += 1
    CANDIDATE._hero_game_epoch += 1
    CANDIDATE._opp_last_attack_id = None
    CANDIDATE._cur_turn_logs.clear()
    for name in (
        "_h2_last_seat",
        "_h2_last_turn",
        "_h1_last_seat",
        "_h1_last_turn",
        "_h3_last_seat",
        "_h3_last_turn",
    ):
        setattr(CANDIDATE, name, None)
    CANDIDATE.drain_cumulative_telemetry()
    PARENT._opp_last_attack_id = None
    PARENT._cur_turn_logs.clear()
    old_cwd = pathlib.Path.cwd()
    try:
        for module in ISOLATED.values():
            os.chdir(pathlib.Path(module.__file__).resolve().parent)
            isolated_deck = module.agent(
                {
                    "select": None,
                    "logs": [],
                    "current": None,
                    "search_begin_input": None,
                }
            )
            if len(isolated_deck) != 60:
                raise AssertionError(("isolated deck request", module.__file__))
    finally:
        os.chdir(old_cwd)


def valid(observation, selected) -> bool:
    return (
        isinstance(selected, list)
        and observation.select.minCount <= len(selected)
        <= observation.select.maxCount
        and len(selected) == len(set(selected))
        and all(
            isinstance(position, int)
            and 0 <= position < len(observation.select.option)
            for position in selected
        )
    )


def semantic(module, observation, selected):
    result = []
    for position in selected:
        option = observation.select.option[position]
        card = module.option_card(observation, option)
        target = module.option_target(observation, option)
        result.append(
            {
                "type": int(option.type),
                "context": int(observation.select.context),
                "card_id": getattr(card, "id", None),
                "serial": getattr(card, "serial", None),
                "target_id": getattr(target, "id", None),
                "target_serial": getattr(target, "serial", None),
                "attack_id": getattr(option, "attackId", None),
            }
        )
    return result


def write_csv(path: pathlib.Path, rows, fields) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if sha256(PARENT_DIR / "main.py") != EXPECTED_PARENT_SHA:
        raise AssertionError("parent changed")
    if sha256(CANDIDATE_DIR / "deck.csv") != EXPECTED_DECK_SHA:
        raise AssertionError("deck changed")

    sources = source_rows()
    callbacks = collections.Counter()
    seat_counts = collections.Counter()
    attribution_counts = collections.Counter()
    collision_size_counts = collections.Counter()
    rollback_counts = collections.Counter()
    differences = []
    first_differences = []
    per_file = []
    source_manifest = []
    action_errors = 0
    outer_exceptions = 0
    caught_component_exceptions = 0
    emergency_fallbacks = 0
    unknown_collision_rollbacks = 0
    two_owner_states = 0
    stale_owners = 0
    starts = 0
    clears = 0
    owner_switches = 0
    eof_boundary_clears = 0
    eof_boundary_owners = collections.Counter()
    retry_checks = 0
    retry_parent_call_errors = 0
    telemetry_rows = 0
    isolated_comparisons = collections.Counter()
    isolated_mismatches = 0

    for source in sources:
        source_manifest.append(
            {
                "population": source["population"],
                "episode": source["episode"],
                "seat": source["seat"],
                "reward": source["reward"],
                "filename": source["filename"],
                "bytes": source["bytes"],
                "sha256": source["sha256"],
                "path": str(source["path"].relative_to(ROOT)),
            }
        )
        replay = json.loads(source["path"].read_text(encoding="utf-8"))
        if int(replay["info"]["EpisodeId"]) != source["episode"]:
            raise AssertionError(source)
        reset_modules(f"union_shadow_{source['episode']}")
        seat_counts[(source["population"], source["seat"])] += 1
        file_callbacks = 0
        file_differences = 0
        file_starts = 0
        file_clears = 0
        file_rollbacks = 0
        first_difference = None

        for row_index, step in enumerate(replay["steps"]):
            record = step[source["seat"]]
            raw = record.get("observation")
            if (
                record.get("status") != "ACTIVE"
                or not raw
                or not raw.get("select")
            ):
                continue
            if (
                not raw["select"].get("option")
                and raw["select"].get("minCount", 0) > 0
            ):
                continue

            callbacks[source["population"]] += 1
            file_callbacks += 1
            owner_before = CANDIDATE._cum_active_transaction_owner
            try:
                parent_action = PARENT.agent(copy.deepcopy(raw))
                candidate_action = CANDIDATE.agent(copy.deepcopy(raw))
            except Exception:
                outer_exceptions += 1
                raise
            owner_after = CANDIDATE._cum_active_transaction_owner
            telemetry = copy.deepcopy(CANDIDATE._cum_last_telemetry)
            pending = CANDIDATE.drain_cumulative_telemetry()
            if len(pending) != 1 or telemetry != pending[0]:
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        "callback telemetry",
                        len(pending),
                    )
                )
            telemetry_rows += 1

            candidate_obs = CANDIDATE.to_observation_class(copy.deepcopy(raw))
            parent_obs = PARENT.to_observation_class(copy.deepcopy(raw))
            if not valid(parent_obs, parent_action) or not valid(
                candidate_obs, candidate_action
            ):
                action_errors += 1
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        parent_action,
                        candidate_action,
                    )
                )
            parent_semantic = semantic(PARENT, parent_obs, parent_action)
            candidate_semantic = semantic(
                CANDIDATE,
                candidate_obs,
                candidate_action,
            )
            parent_key = CANDIDATE._cum_jsonable(
                CANDIDATE._cum_action_semantic(candidate_obs, parent_action)
            )
            if telemetry["exact_parent_action"] != parent_key:
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        "parent cache mismatch",
                        telemetry["exact_parent_action"],
                        parent_key,
                    )
                )
            final_key = CANDIDATE._cum_jsonable(
                CANDIDATE._cum_action_semantic(
                    candidate_obs,
                    candidate_action,
                )
            )
            if telemetry["final_action"] != final_key:
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        "final action mismatch",
                    )
                )

            proposal_ids = [entry["rule_id"] for entry in telemetry["proposals"]]
            if proposal_ids and proposal_ids != list(CANDIDATE._CUM_RULE_ORDER):
                raise AssertionError(
                    (source["episode"], row_index, proposal_ids)
                )
            for proposal_row in telemetry["proposals"]:
                rule = CANDIDATE._CUM_RULE_BY_ID[proposal_row["rule_id"]]
                if (
                    proposal_row["source_hash"] != rule["source_hash"]
                    or proposal_row["contract_hash"] != rule["contract_hash"]
                ):
                    raise AssertionError(proposal_row)
                if proposal_row["caught_exception"] is not None:
                    caught_component_exceptions += 1

            integrated_proposals = {
                entry["rule_id"]: entry for entry in telemetry["proposals"]
            }
            for rule in CANDIDATE._CUM_RULES:
                rule_id = rule["rule_id"]
                isolated = ISOLATED[rule_id]
                isolated_action = isolated.agent(copy.deepcopy(raw))
                if not valid(candidate_obs, isolated_action):
                    isolated_mismatches += 1
                    raise AssertionError(
                        (
                            source["episode"],
                            row_index,
                            rule_id,
                            "invalid isolated action",
                            isolated_action,
                        )
                    )
                if not integrated_proposals:
                    # Rank-0 empty-option callbacks have no rule proposal.
                    if isolated_action != []:
                        isolated_mismatches += 1
                        raise AssertionError(
                            (
                                source["episode"],
                                row_index,
                                rule_id,
                                "rank0 isolated mismatch",
                                isolated_action,
                            )
                        )
                    continue
                isolated_semantic = CANDIDATE._cum_jsonable(
                    CANDIDATE._cum_action_semantic(
                        candidate_obs,
                        isolated_action,
                    )
                )
                isolated_transaction = copy.deepcopy(
                    getattr(isolated, rule["transaction"])
                )
                isolated_eligible = (
                    isolated_transaction is not None
                    or isolated_semantic != parent_key
                )
                integrated = integrated_proposals[rule_id]
                digest_transaction = copy.deepcopy(isolated_transaction)
                if (
                    digest_transaction is not None
                    and "game_epoch" in digest_transaction
                ):
                    isolated_epoch = digest_transaction["game_epoch"]
                    if rule_id == (
                        "SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_NONTERMINAL_BOSS_V1"
                    ):
                        integrated_epoch = CANDIDATE._sat_game_epoch
                    elif rule_id == (
                        "HERO_CAPE_CURRENT_PAYABLE_SAME_ATTACK_SURVIVAL"
                    ):
                        integrated_epoch = CANDIDATE._hero_game_epoch
                    else:
                        integrated_epoch = isolated_epoch
                    digest_transaction["game_epoch"] = integrated_epoch
                    snapshot = digest_transaction.get("snapshot_id")
                    if (
                        isinstance(snapshot, str)
                        and snapshot.startswith(f"{isolated_epoch}:")
                    ):
                        digest_transaction["snapshot_id"] = (
                            f"{integrated_epoch}:"
                            f"{snapshot.split(':', 1)[1]}"
                        )
                isolated_digest = (
                    None
                    if digest_transaction is None
                    else CANDIDATE._cum_digest(digest_transaction)
                )
                isolated_comparisons[rule_id] += 1
                if (
                    integrated["eligible"] != isolated_eligible
                    or (
                        isolated_eligible
                        and integrated["desired_action"]
                        != isolated_semantic
                    )
                    or (
                        isolated_eligible
                        and integrated["certificate_digest"]
                        != isolated_digest
                    )
                ):
                    isolated_mismatches += 1
                    raise AssertionError(
                        {
                            "episode": source["episode"],
                            "row": row_index,
                            "rule_id": rule_id,
                            "parent": parent_key,
                            "isolated_action": isolated_semantic,
                            "isolated_eligible": isolated_eligible,
                            "isolated_digest": isolated_digest,
                            "isolated_transaction": isolated_transaction,
                            "integrated_proposal": integrated,
                        }
                    )
            if telemetry["caught_exceptions"]:
                caught_component_exceptions += len(
                    telemetry["caught_exceptions"]
                )
            if telemetry["invalid_or_emergency_fallback"]:
                emergency_fallbacks += 1
            if (
                telemetry["rollback_reason"]
                and "unknown" in telemetry["rollback_reason"]
            ):
                unknown_collision_rollbacks += 1
            if telemetry["rollback_reason"]:
                rollback_counts[telemetry["rollback_reason"]] += 1
                file_rollbacks += 1

            active_transactions = CANDIDATE._cum_nonclear_rules()
            if len(active_transactions) > 1:
                two_owner_states += 1
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        active_transactions,
                    )
                )
            if active_transactions and active_transactions != [owner_after]:
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        active_transactions,
                        owner_after,
                    )
                )
            if owner_before is None and owner_after is not None:
                starts += 1
                file_starts += 1
            elif owner_before is not None and owner_after is None:
                clears += 1
                file_clears += 1
            elif (
                owner_before is not None
                and owner_after is not None
                and owner_before != owner_after
            ):
                owner_switches += 1
                raise AssertionError(
                    (
                        source["episode"],
                        row_index,
                        owner_before,
                        owner_after,
                    )
                )

            attribution = telemetry["attribution_owner"]
            attribution_counts[attribution] += 1
            collision_size_counts[len(telemetry["collision_set"])] += 1
            equal = parent_semantic == candidate_semantic
            if not equal:
                if attribution in (
                    "exact_historical_silver",
                    "engine_emergency",
                    "engine_empty_options",
                ):
                    raise AssertionError(
                        (
                            source["episode"],
                            row_index,
                            attribution,
                            parent_semantic,
                            candidate_semantic,
                        )
                    )
                file_differences += 1
                if first_difference is None:
                    first_difference = row_index
                    first_differences.append(
                        {
                            "population": source["population"],
                            "episode": source["episode"],
                            "row": row_index,
                            "seat": source["seat"],
                            "winning_rule_id": telemetry["winning_rule_id"],
                            "attribution_owner": attribution,
                            "parent_semantic": json.dumps(
                                parent_semantic,
                                sort_keys=True,
                            ),
                            "candidate_semantic": json.dumps(
                                candidate_semantic,
                                sort_keys=True,
                            ),
                        }
                    )
                differences.append(
                    {
                        "population": source["population"],
                        "episode": source["episode"],
                        "row": row_index,
                        "seat": source["seat"],
                        "turn": raw["current"]["turn"],
                        "turn_action_count": raw["current"][
                            "turnActionCount"
                        ],
                        "winning_rule_id": telemetry["winning_rule_id"],
                        "attribution_owner": attribution,
                        "active_owner_before": owner_before,
                        "active_owner_after": owner_after,
                        "collision_set": json.dumps(
                            telemetry["collision_set"],
                            sort_keys=True,
                        ),
                        "suppressed_rule_ids": json.dumps(
                            telemetry["suppressed_rule_ids"],
                            sort_keys=True,
                        ),
                        "precedence_reason": telemetry["precedence_reason"],
                        "rollback_reason": telemetry["rollback_reason"],
                        "parent_semantic": json.dumps(
                            parent_semantic,
                            sort_keys=True,
                        ),
                        "candidate_semantic": json.dumps(
                            candidate_semantic,
                            sort_keys=True,
                        ),
                        "snapshot_id": telemetry["snapshot_id"],
                    }
                )

            if owner_after is not None:
                retry_checks += 1
                original_parent = CANDIDATE._cum_parent_choose_options
                parent_calls = {"count": 0}

                def counted_parent(obs):
                    parent_calls["count"] += 1
                    return original_parent(obs)

                CANDIDATE._cum_parent_choose_options = counted_parent
                try:
                    retry_action = CANDIDATE.agent(copy.deepcopy(raw))
                finally:
                    CANDIDATE._cum_parent_choose_options = original_parent
                retry_pending = CANDIDATE.drain_cumulative_telemetry()
                retry_row = copy.deepcopy(CANDIDATE._cum_last_telemetry)
                retry_obs = CANDIDATE.to_observation_class(copy.deepcopy(raw))
                if (
                    len(retry_pending) != 1
                    or semantic(CANDIDATE, retry_obs, retry_action)
                    != candidate_semantic
                    or parent_calls["count"] != 0
                    or retry_row["duplicate_or_reset_state"]
                    != "IDENTICAL_RETRY"
                    or retry_row["precedence_reason"]
                    != "rank2_identical_retry_cached_without_parent_call"
                ):
                    retry_parent_call_errors += 1
                    raise AssertionError(
                        (
                            source["episode"],
                            row_index,
                            retry_pending,
                            retry_action,
                            parent_calls,
                            retry_row,
                        )
                    )
                telemetry_rows += 1

        if CANDIDATE._cum_active_transaction_owner is not None:
            # A recorded parent replay can end immediately after the
            # counterfactual candidate arms.  Execute the actual next-game
            # deck-request boundary and require callback-complete reset
            # telemetry; do not silently mutate state in the harness.
            eof_owner = CANDIDATE._cum_active_transaction_owner
            active_at_eof = CANDIDATE._cum_nonclear_rules()
            if active_at_eof != [eof_owner]:
                stale_owners += 1
                raise AssertionError(
                    (
                        source["episode"],
                        "inconsistent owner at EOF",
                        eof_owner,
                        active_at_eof,
                    )
            )
            eof_boundary_clears += 1
            eof_boundary_owners[eof_owner] += 1
            old_cwd = pathlib.Path.cwd()
            try:
                os.chdir(CANDIDATE_DIR)
                deck = CANDIDATE.agent(
                    {
                        "select": None,
                        "logs": [],
                        "current": None,
                        "search_begin_input": None,
                    }
                )
            finally:
                os.chdir(old_cwd)
            boundary_pending = CANDIDATE.drain_cumulative_telemetry()
            boundary_row = copy.deepcopy(CANDIDATE._cum_last_telemetry)
            if (
                len(deck) != 60
                or len(boundary_pending) != 1
                or boundary_row != boundary_pending[0]
                or boundary_row["duplicate_or_reset_state"] != "DECK_REQUEST"
                or boundary_row["active_owner_before"] != eof_owner
                or boundary_row["active_owner_after"] is not None
                or boundary_row["state_clear_result"] != "ALL_CLEAR"
                or CANDIDATE._cum_active_transaction_owner is not None
                or CANDIDATE._cum_nonclear_rules()
            ):
                stale_owners += 1
                raise AssertionError(
                    (source["episode"], "EOF boundary reset failed")
                )
        elif CANDIDATE._cum_nonclear_rules():
            stale_owners += 1
            raise AssertionError(
                (
                    source["episode"],
                    "ownerless component at EOF",
                    CANDIDATE._cum_nonclear_rules(),
                )
            )
        per_file.append(
            {
                "population": source["population"],
                "episode": source["episode"],
                "seat": source["seat"],
                "callbacks": file_callbacks,
                "differences": file_differences,
                "starts": file_starts,
                "clears": file_clears,
                "rollbacks": file_rollbacks,
                "first_difference": first_difference,
            }
        )

    if sum(callbacks.values()) != EXPECTED_CALLBACKS:
        raise AssertionError(callbacks)
    if (
        action_errors
        or outer_exceptions
        or caught_component_exceptions
        or emergency_fallbacks
        or unknown_collision_rollbacks
        or two_owner_states
        or stale_owners
        or owner_switches
        or retry_parent_call_errors
        or isolated_mismatches
    ):
        raise AssertionError(
            {
                "action_errors": action_errors,
                "outer_exceptions": outer_exceptions,
                "caught_component_exceptions": caught_component_exceptions,
                "emergency_fallbacks": emergency_fallbacks,
                "unknown_collision_rollbacks": unknown_collision_rollbacks,
                "two_owner_states": two_owner_states,
                "stale_owners": stale_owners,
                "owner_switches": owner_switches,
                "retry_parent_call_errors": retry_parent_call_errors,
                "isolated_mismatches": isolated_mismatches,
            }
        )

    source_path = HERE / "union_shadow_source_manifest.csv"
    differences_path = HERE / "union_shadow_differences.csv"
    first_path = HERE / "union_shadow_first_differences.csv"
    per_file_path = HERE / "union_shadow_per_file.csv"
    write_csv(
        source_path,
        source_manifest,
        [
            "population",
            "episode",
            "seat",
            "reward",
            "filename",
            "bytes",
            "sha256",
            "path",
        ],
    )
    difference_fields = [
        "population",
        "episode",
        "row",
        "seat",
        "turn",
        "turn_action_count",
        "winning_rule_id",
        "attribution_owner",
        "active_owner_before",
        "active_owner_after",
        "collision_set",
        "suppressed_rule_ids",
        "precedence_reason",
        "rollback_reason",
        "parent_semantic",
        "candidate_semantic",
        "snapshot_id",
    ]
    write_csv(differences_path, differences, difference_fields)
    write_csv(
        first_path,
        first_differences,
        [
            "population",
            "episode",
            "row",
            "seat",
            "winning_rule_id",
            "attribution_owner",
            "parent_semantic",
            "candidate_semantic",
        ],
    )
    write_csv(
        per_file_path,
        per_file,
        [
            "population",
            "episode",
            "seat",
            "callbacks",
            "differences",
            "starts",
            "clears",
            "rollbacks",
            "first_difference",
        ],
    )
    summary = {
        "rule_id": CANDIDATE._CUM_RULE_ID,
        "candidate_main_sha256": sha256(CANDIDATE_DIR / "main.py"),
        "parent_main_sha256": EXPECTED_PARENT_SHA,
        "deck_sha256": EXPECTED_DECK_SHA,
        "source_file_count": len(sources),
        "callback_total": sum(callbacks.values()),
        "callbacks": dict(sorted(callbacks.items())),
        "telemetry_rows_including_identical_retries": telemetry_rows,
        "retry_checks": retry_checks,
        "seat_file_counts": {
            f"{population}:seat{seat}": count
            for (population, seat), count in sorted(seat_counts.items())
        },
        "action_differences": len(differences),
        "files_with_differences": len(first_differences),
        "attribution_counts": dict(sorted(attribution_counts.items())),
        "collision_size_counts": {
            str(size): count
            for size, count in sorted(collision_size_counts.items())
        },
        "rollback_counts": dict(sorted(rollback_counts.items())),
        "transaction_starts": starts,
        "transaction_clears": clears,
        "eof_boundary_clears": eof_boundary_clears,
        "eof_boundary_owners": dict(sorted(eof_boundary_owners.items())),
        "owner_switches": owner_switches,
        "action_errors": action_errors,
        "outer_exceptions": outer_exceptions,
        "caught_component_exceptions": caught_component_exceptions,
        "emergency_fallbacks": emergency_fallbacks,
        "unknown_collision_rollbacks": unknown_collision_rollbacks,
        "two_owner_states": two_owner_states,
        "stale_owners": stale_owners,
        "retry_parent_call_errors": retry_parent_call_errors,
        "isolated_comparisons": dict(sorted(isolated_comparisons.items())),
        "isolated_mismatches": isolated_mismatches,
        "max_step_hits": 0,
        "source_hashes": {
            "frozen_input_manifest": EXPECTED_FROZEN_SOURCE_MANIFEST_SHA,
            "owned_union_manifest": sha256(source_path),
        },
        "outputs": {
            source_path.name: sha256(source_path),
            differences_path.name: sha256(differences_path),
            first_path.name: sha256(first_path),
            per_file_path.name: sha256(per_file_path),
        },
    }
    summary_path = HERE / "union_shadow_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
