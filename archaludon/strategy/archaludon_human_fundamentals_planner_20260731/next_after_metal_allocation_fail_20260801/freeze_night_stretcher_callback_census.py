from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PARENT = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_purpose_first_pokegear_boss_transaction_v1"
)
CORPUS = (
    ROOT
    / "archaludon"
    / "live"
    / "55070349"
    / "refresh_20260729_1241"
    / "shadow_corpus_196_prior_plus_11_new"
)
RAW = HERE / "night_stretcher_callback_census_raw"
STRETCHER = 1097


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_parent():
    sys.path.insert(0, str(PARENT))
    spec = importlib.util.spec_from_file_location(
        "night_stretcher_census_parent", PARENT / "main.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(PARENT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset(module) -> None:
    if hasattr(module, "_pfgear_reset_active"):
        module._pfgear_reset_active("census_reset")
    if hasattr(module, "_pcrd_clear"):
        module._pcrd_clear("census_reset")
    if hasattr(module, "_pfc_clear"):
        module._pfc_clear("census_reset")
    if hasattr(module, "_cum_reset_runtime"):
        module._cum_reset_runtime("census_reset")
    if hasattr(module, "_dper_reset_runtime"):
        module._dper_reset_runtime("census_reset")
    for name in (
        "_h2_transaction",
        "_h6_transaction",
        "_pfgear_transaction",
        "_pfgear_veto_watch",
        "_cum_active_transaction_owner",
        "_cum_owner_meta",
    ):
        if hasattr(module, name):
            setattr(module, name, None)


def target_seats(replay: dict) -> tuple[int, ...]:
    names = tuple(replay.get("info", {}).get("TeamNames", ()))
    if names == ("rurumi", "rurumi"):
        return (0, 1)
    return tuple(i for i, name in enumerate(names) if name == "rurumi")


def freeze(value):
    if isinstance(value, dict):
        return {str(key): freeze(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [freeze(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((freeze(item) for item in value), key=repr)
    if hasattr(value, "value") and isinstance(value.value, int):
        return int(value.value)
    return value


def canonical(value) -> str:
    return json.dumps(freeze(value), ensure_ascii=False, sort_keys=True)


def owner_snapshot(module) -> dict:
    snapshot = {
        "h2": getattr(module, "_h2_transaction", None) is not None,
        "h6": getattr(module, "_h6_transaction", None) is not None,
        "pfgear_transaction": (
            getattr(module, "_pfgear_transaction", None) is not None
        ),
        "pfgear_veto": getattr(module, "_pfgear_veto_watch", None) is not None,
        "cum_owner": getattr(module, "_cum_active_transaction_owner", None),
    }
    try:
        snapshot["inherited_owner_active"] = bool(
            module._pfgear_inherited_owner_active()
        )
    except Exception as error:
        snapshot["inherited_owner_active"] = (
            "ERROR:" + type(error).__name__
        )
    return snapshot


def option_rows(module, obs) -> list[dict]:
    rows = []
    for position, option in enumerate(obs.select.option):
        card = module.option_card(obs, option)
        rows.append(
            {
                "position": position,
                "role": module._pcrd_option_role(obs, option),
                "card_id": getattr(card, "id", None),
                "card_serial": getattr(card, "serial", None),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    if "--reaggregate" in sys.argv:
        csv_path = RAW / "callback_rows.csv"
        summary_path = RAW / "summary.json"
        with csv_path.open(newline="", encoding="utf-8") as handle:
            frozen_rows = list(csv.DictReader(handle))
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["unique_play_turns"] = len(
            {
                (row["replay"], int(row["seat"]), int(row["turn"]))
                for row in frozen_rows
            }
        )
        expected = {
            "files": 207,
            "target_seats": 209,
            "callbacks": 186,
            "callback_replays": 123,
            "callback_seats": [0, 1],
            "empty_historical_actions": 0,
            "all_min_max_one": True,
            "historical_invalid": 0,
            "parent_invalid": 0,
            "unique_play_turns": 168,
        }
        summary["expected"] = expected
        summary["expected_mismatches"] = {
            key: {"expected": value, "actual": summary.get(key)}
            for key, value in expected.items()
            if summary.get(key) != value
        }
        summary["valid"] = not summary["expected_mismatches"]
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        if not summary["valid"]:
            raise SystemExit(1)
        return
    module = load_parent()
    files = sorted(CORPUS.glob("episode_*_replay.json"))
    manifest = []
    rows = []
    play_keys = set()
    play_turns = set()
    target_seat_count = 0
    for replay_path in files:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        seats = target_seats(replay)
        target_seat_count += len(seats)
        manifest.append(
            {
                "replay": replay_path.name,
                "sha256": sha256(replay_path),
                "target_seats": list(seats),
                "steps": len(replay["steps"]),
            }
        )
        for seat in seats:
            reset(module)
            seen_logs = set()
            for step_index, step in enumerate(replay["steps"]):
                raw = step[seat].get("observation") or {}
                current = raw.get("current") or {}
                if current.get("yourIndex") != seat or raw.get("select") is None:
                    continue
                for log in raw.get("logs", ()):
                    if (
                        log.get("type") == 10
                        and log.get("playerIndex") == seat
                        and log.get("cardId") == STRETCHER
                    ):
                        key = (
                            replay_path.name,
                            seat,
                            current.get("turn"),
                            log.get("serial"),
                        )
                        if key not in seen_logs:
                            seen_logs.add(key)
                            play_keys.add(key)
                            play_turns.add(key[:3])
                before_owner = owner_snapshot(module)
                parent_action = module.agent(copy.deepcopy(raw))
                after_owner = owner_snapshot(module)
                select = raw.get("select") or {}
                effect = select.get("effect") or {}
                if effect.get("id") != STRETCHER:
                    continue
                if step_index + 1 >= len(replay["steps"]):
                    raise AssertionError((replay_path.name, seat, step_index))
                historical_action = (
                    replay["steps"][step_index + 1][seat].get("action")
                )
                obs = module.to_observation_class(copy.deepcopy(raw))
                historical_valid = module._cum_valid_action(
                    obs, historical_action
                )
                parent_valid = module._cum_valid_action(obs, parent_action)
                historical_roles = (
                    module._pcrd_action_roles(obs, historical_action)
                    if historical_valid
                    else None
                )
                parent_roles = (
                    module._pcrd_action_roles(obs, parent_action)
                    if parent_valid
                    else None
                )
                option_inventory = option_rows(module, obs)
                selected_ids = [
                    row["card_id"]
                    for row in option_inventory
                    if historical_action is not None
                    and row["position"] in historical_action
                ]
                rows.append(
                    {
                        "replay": replay_path.name,
                        "replay_sha256": sha256(replay_path),
                        "seat": seat,
                        "turn": current.get("turn"),
                        "step": step_index,
                        "snapshot_sha256": sha256_bytes(
                            canonical(raw).encode("utf-8")
                        ),
                        "effect_serial": effect.get("serial"),
                        "context": select.get("context"),
                        "min_count": select.get("minCount"),
                        "max_count": select.get("maxCount"),
                        "option_count": len(option_inventory),
                        "option_rows": canonical(option_inventory),
                        "historical_action_storage": "NEXT_REPLAY_ROW",
                        "historical_action": canonical(historical_action),
                        "historical_action_valid": historical_valid,
                        "historical_roles": canonical(historical_roles),
                        "historical_selected_ids": canonical(selected_ids),
                        "parent_action": canonical(parent_action),
                        "parent_action_valid": parent_valid,
                        "parent_roles": canonical(parent_roles),
                        "owner_before": canonical(before_owner),
                        "owner_after_parent": canonical(after_owner),
                    }
                )
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    manifest_path = RAW / "source_manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    csv_path = RAW / "callback_rows.csv"
    write_csv(csv_path, rows)
    counts = {}
    for row in rows:
        for card_id in json.loads(row["historical_selected_ids"]):
            counts[str(card_id)] = counts.get(str(card_id), 0) + 1
    summary = {
        "parent_main_sha256": sha256(PARENT / "main.py"),
        "parent_deck_sha256": sha256(PARENT / "deck.csv"),
        "files": len(files),
        "target_seats": target_seat_count,
        "callbacks": len(rows),
        "callback_replays": len({row["replay"] for row in rows}),
        "callback_seats": sorted({row["seat"] for row in rows}),
        "unique_play_keys": len(play_keys),
        "unique_play_turns": len(play_turns),
        "historical_target_id_counts": counts,
        "empty_historical_actions": sum(
            json.loads(row["historical_action"]) == [] for row in rows
        ),
        "all_min_max_one": all(
            row["min_count"] == row["max_count"] == 1 for row in rows
        ),
        "historical_invalid": sum(
            not row["historical_action_valid"] for row in rows
        ),
        "parent_invalid": sum(not row["parent_action_valid"] for row in rows),
        "source_manifest_sha256": sha256_bytes(manifest_bytes),
        "callback_rows_sha256": sha256(csv_path),
        "action_alignment": (
            "The action stored on replay row i+1 responds to observation row i."
        ),
    }
    expected = {
        "files": 207,
        "target_seats": 209,
        "callbacks": 186,
        "callback_replays": 123,
        "callback_seats": [0, 1],
        "empty_historical_actions": 0,
        "all_min_max_one": True,
        "historical_invalid": 0,
        "parent_invalid": 0,
        "unique_play_turns": 168,
    }
    mismatches = {
        key: {"expected": value, "actual": summary.get(key)}
        for key, value in expected.items()
        if summary.get(key) != value
    }
    summary["expected_mismatches"] = mismatches
    summary["expected"] = expected
    summary["valid"] = not mismatches
    summary_path = RAW / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
