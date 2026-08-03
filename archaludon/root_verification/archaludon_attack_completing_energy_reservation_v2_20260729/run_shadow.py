from __future__ import annotations

import collections
import copy
import csv
import hashlib
import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_attack_completing_energy_reservation_v2"
)
PARENT = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
FROZEN_MANIFEST = (
    ROOT
    / "archaludon"
    / "implementation"
    / "archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2"
    / "shadow_source_manifest.csv"
)
CORPUS = (
    ROOT
    / "archaludon"
    / "live"
    / "55070349"
    / "refresh_20260729_1241"
    / "shadow_corpus_196_prior_plus_11_new"
)
EXPECTED_MANIFEST_SHA256 = (
    "A252E906160A83A36DA916593C31766F4586481F1995E6E9C05210A697685EC3"
)
EXPECTED_FILES = 207
EXPECTED_CALLBACKS = 11473


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(CANDIDATE))
CAND = load_module("h6_shadow_candidate", CANDIDATE / "main.py")
PARENT_MOD = load_module("h6_shadow_parent", PARENT / "main.py")


def reset_modules() -> None:
    CAND._h6_reset()
    CAND._opp_last_attack_id = None
    CAND._cur_turn_logs.clear()
    PARENT_MOD._opp_last_attack_id = None
    PARENT_MOD._cur_turn_logs.clear()


def action(module, obs_dict, candidate: bool):
    observation = module.to_observation_class(obs_dict)
    module._update_opp_attack_tracking(observation)
    if not observation.select.option:
        if candidate:
            module._h6_reset()
        return []
    return module.choose_options(observation)


def valid(obs_dict, selected) -> bool:
    select = obs_dict["select"]
    return (
        isinstance(selected, list)
        and select["minCount"] <= len(selected) <= select["maxCount"]
        and len(selected) == len(set(selected))
        and all(
            isinstance(position, int)
            and 0 <= position < len(select["option"])
            for position in selected
        )
    )


def semantics(module, obs_dict, selected):
    observation = module.to_observation_class(copy.deepcopy(obs_dict))
    output = []
    for position in selected:
        option = observation.select.option[position]
        card = module.option_card(observation, option)
        target = module.option_target(observation, option)
        output.append(
            {
                "position": position,
                "type": int(option.type),
                "context": int(observation.select.context),
                "card_id": getattr(card, "id", None),
                "serial": getattr(card, "serial", None),
                "target_id": getattr(target, "id", None),
                "target_serial": getattr(target, "serial", None),
                "attack_id": option.attackId,
            }
        )
    return output


def position_free(items):
    return [
        {key: value for key, value in item.items() if key != "position"}
        for item in items
    ]


def write_csv(name, rows, fields):
    path = HERE / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def main() -> None:
    if sha256(FROZEN_MANIFEST) != EXPECTED_MANIFEST_SHA256:
        raise AssertionError("frozen manifest hash changed")
    with FROZEN_MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    if len(manifest) != EXPECTED_FILES:
        raise AssertionError(len(manifest))

    callbacks = 0
    differences = []
    rollbacks = []
    per_file = []
    source_checks = {}
    action_errors = 0
    exceptions = 0
    external_differences = 0
    stale_transactions = 0
    correct_seats = collections.Counter()

    for source in manifest:
        episode = int(source["episode"])
        seat = int(source["seat"])
        path = CORPUS / source["filename"]
        if (
            not path.is_file()
            or sha256(path) != source["sha256"]
            or path.stat().st_size != int(source["bytes"])
        ):
            raise AssertionError(("source mismatch", source))
        replay = json.loads(path.read_text(encoding="utf-8"))
        if int(replay["info"]["EpisodeId"]) != episode:
            raise AssertionError(("episode mismatch", source))
        reset_modules()
        correct_seats[seat] += 1
        file_callbacks = 0
        file_differences = 0
        file_rollbacks = 0

        for row, step in enumerate(replay["steps"]):
            record = step[seat]
            obs = record.get("observation")
            if (
                record.get("status") != "ACTIVE"
                or not obs
                or not obs.get("select")
            ):
                continue
            if (
                not obs["select"].get("option")
                and obs["select"].get("minCount", 0) > 0
            ):
                continue
            callbacks += 1
            file_callbacks += 1
            before = copy.deepcopy(CAND._h6_transaction)
            try:
                parent_action = action(
                    PARENT_MOD, copy.deepcopy(obs), False
                )
                candidate_action = action(
                    CAND, copy.deepcopy(obs), True
                )
            except Exception:
                exceptions += 1
                raise
            after = copy.deepcopy(CAND._h6_transaction)
            if not valid(obs, parent_action) or not valid(
                obs, candidate_action
            ):
                action_errors += 1
                raise AssertionError(
                    (episode, row, parent_action, candidate_action)
                )
            parent_semantic = semantics(
                PARENT_MOD, obs, parent_action
            )
            candidate_semantic = semantics(
                CAND, obs, candidate_action
            )
            equal = position_free(parent_semantic) == position_free(
                candidate_semantic
            )

            if episode == 88584180 and row in {
                90,
                91,
                92,
                93,
                111,
                112,
                113,
                114,
                142,
                143,
            }:
                source_checks[str(row)] = {
                    "seat": seat,
                    "parent": parent_semantic,
                    "candidate": candidate_semantic,
                    "stage_before": None if before is None else before["stage"],
                    "stage_after": None if after is None else after["stage"],
                }

            if before is not None and after is None:
                file_rollbacks += 1
                rollbacks.append(
                    {
                        "episode": episode,
                        "row": row,
                        "seat": seat,
                        "stage_before": before["stage"],
                        "semantic_equal": equal,
                    }
                )
                if not equal:
                    raise AssertionError(
                        ("rollback changed action", episode, row)
                    )
            if equal:
                continue

            file_differences += 1
            if after is None:
                external_differences += 1
                raise AssertionError(
                    ("unowned difference", episode, row)
                )
            reserved = after["energy_serial"]
            parent_cards = {
                (item["card_id"], item["serial"])
                for item in parent_semantic
            }
            candidate_cards = {
                (item["card_id"], item["serial"])
                for item in candidate_semantic
            }
            classification = (
                after["stage"] == "SAFE_EFFECT"
                and (CAND.METAL_ENERGY, reserved) in parent_cards
                and (CAND.METAL_ENERGY, reserved) not in candidate_cards
                and len(parent_cards) == len(candidate_cards)
            )
            if not classification:
                raise AssertionError(
                    (
                        "unclassified difference",
                        episode,
                        row,
                        parent_semantic,
                        candidate_semantic,
                        after,
                    )
                )
            differences.append(
                {
                    "episode": episode,
                    "row": row,
                    "seat": seat,
                    "turn": obs["current"]["turn"],
                    "turn_action_count": obs["current"]["turnActionCount"],
                    "stage": after["stage"],
                    "reserved_energy_serial": reserved,
                    "active_serial": after["active_serial"],
                    "target_serial": after["target_serial"],
                    "damage": after["damage"],
                    "parent_semantic": json.dumps(
                        parent_semantic,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "candidate_semantic": json.dumps(
                        candidate_semantic,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "classification": (
                        "H6_RESERVED_METAL_EXCLUDED_FROM_SAFE_MANDATORY_DISCARD"
                    ),
                }
            )

        if CAND._h6_transaction is not None:
            stale_transactions += 1
            CAND._h6_reset()
        per_file.append(
            {
                "episode": episode,
                "seat": seat,
                "callbacks": file_callbacks,
                "differences": file_differences,
                "rollbacks": file_rollbacks,
            }
        )

    if callbacks != EXPECTED_CALLBACKS:
        raise AssertionError((callbacks, EXPECTED_CALLBACKS))
    if action_errors or exceptions or external_differences or stale_transactions:
        raise AssertionError(
            {
                "action_errors": action_errors,
                "exceptions": exceptions,
                "external_differences": external_differences,
                "stale_transactions": stale_transactions,
            }
        )
    required_equal = {"90", "92", "93", "111", "112", "113", "114", "142", "143"}
    if set(source_checks) != required_equal | {"91"}:
        raise AssertionError(source_checks)
    for row in required_equal:
        check = source_checks[row]
        if position_free(check["parent"]) != position_free(
            check["candidate"]
        ):
            raise AssertionError((row, check))
    row91 = source_checks["91"]
    if {
        (item["card_id"], item["serial"]) for item in row91["candidate"]
    } != {(1097, 90), (1147, 94)}:
        raise AssertionError(row91)

    difference_path = write_csv(
        "shadow_differences.csv",
        differences,
        [
            "episode",
            "row",
            "seat",
            "turn",
            "turn_action_count",
            "stage",
            "reserved_energy_serial",
            "active_serial",
            "target_serial",
            "damage",
            "parent_semantic",
            "candidate_semantic",
            "classification",
        ],
    )
    rollback_path = write_csv(
        "shadow_rollbacks.csv",
        rollbacks,
        ["episode", "row", "seat", "stage_before", "semantic_equal"],
    )
    per_file_path = write_csv(
        "shadow_per_file.csv",
        per_file,
        ["episode", "seat", "callbacks", "differences", "rollbacks"],
    )
    manifest_copy = HERE / "shadow_source_manifest.csv"
    manifest_copy.write_bytes(FROZEN_MANIFEST.read_bytes())

    summary = {
        "frozen_manifest": str(FROZEN_MANIFEST.relative_to(ROOT).as_posix()),
        "source_manifest_sha256": sha256(manifest_copy),
        "source_file_count": len(manifest),
        "callback_total": callbacks,
        "correct_seat_counts": dict(sorted(correct_seats.items())),
        "action_differences": len(differences),
        "classified_action_differences": len(differences),
        "files_with_differences": len(
            {row["episode"] for row in differences}
        ),
        "certificate_external_differences": external_differences,
        "rollbacks": len(rollbacks),
        "action_errors": action_errors,
        "exceptions": exceptions,
        "stale_transactions": stale_transactions,
        "max_step_hits": 0,
        "source_checks": source_checks,
        "outputs": {
            path.name: sha256(path)
            for path in (
                difference_path,
                rollback_path,
                per_file_path,
                manifest_copy,
            )
        },
    }
    output = HERE / "shadow_summary.json"
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
