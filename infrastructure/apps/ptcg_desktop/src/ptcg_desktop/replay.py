from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .artifacts import sha256_file
from .config import (
    APP_VERSION,
    HUMAN_VIEW_SCHEMA_VERSION,
    MAX_REPLAY_MEMBER_BYTES,
    MAX_REPLAY_TOTAL_BYTES,
    PROTOCOL_VERSION,
    REPLAY_SCHEMA_VERSION,
)


class ReplayError(RuntimeError):
    pass


LEGACY_REPLAY_MEMBERS = {
    "manifest.json",
    "artifact.json",
    "settings.json",
    "decks.json",
    "frames.jsonl",
    "public_log.jsonl",
    "result.json",
    "diagnostics.json",
}
VISUALIZER_MEMBER = "visualizer.json"
REPLAY_MEMBERS = LEGACY_REPLAY_MEMBERS | {VISUALIZER_MEMBER}

OPTION_FIELDS = {
    "type",
    "number",
    "area",
    "index",
    "playerIndex",
    "toolIndex",
    "energyIndex",
    "count",
    "inPlayArea",
    "inPlayIndex",
    "attackId",
    "cardId",
    "serial",
    "specialConditionType",
}

LOG_FIELDS = {
    "type",
    "playerIndex",
    "hasBasicPokemon",
    "cardId",
    "serial",
    "fromArea",
    "toArea",
    "cardIdActive",
    "serialActive",
    "cardIdBench",
    "serialBench",
    "cardIdBefore",
    "serialBefore",
    "cardIdAfter",
    "serialAfter",
    "cardIdTarget",
    "serialTarget",
    "attackId",
    "value",
    "putDamageCounter",
    "isRecover",
    "head",
    "result",
    "reason",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest().upper()


def _scalar(value: Any, field: str, allowed: tuple[type, ...], *, nullable: bool = False) -> Any:
    if nullable and value is None:
        return None
    if type(value) not in allowed:
        raise ReplayError(f"{field} has invalid type")
    return value


def _card(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ReplayError(f"{field} must be a card object")
    output = {
        "id": _scalar(value.get("id"), f"{field}.id", (int,)),
        "serial": _scalar(value.get("serial"), f"{field}.serial", (int,)),
    }
    if value.get("playerIndex") is not None:
        output["player_index"] = _scalar(value.get("playerIndex"), f"{field}.playerIndex", (int,))
    if value.get("name") is not None:
        output["name"] = _scalar(value.get("name"), f"{field}.name", (str,))
    return output


def _cards(value: Any, field: str) -> list[dict[str, Any] | None]:
    if not isinstance(value, list):
        raise ReplayError(f"{field} must be a list")
    return [_card(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _pokemon(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ReplayError(f"{field} must be a pokemon object")
    base = _card(value, field)
    assert base is not None
    energies = value.get("energies", [])
    if not isinstance(energies, list) or not all(type(item) in (int, str) for item in energies):
        raise ReplayError(f"{field}.energies is invalid")
    return {
        **base,
        "hp": _scalar(value.get("hp"), f"{field}.hp", (int,)),
        "max_hp": _scalar(value.get("maxHp"), f"{field}.maxHp", (int,)),
        "appear_this_turn": _scalar(value.get("appearThisTurn"), f"{field}.appearThisTurn", (bool,)),
        "energies": list(energies),
        "energy_cards": _cards(value.get("energyCards", []), f"{field}.energyCards"),
        "tools": _cards(value.get("tools", []), f"{field}.tools"),
        "pre_evolution": _cards(value.get("preEvolution", []), f"{field}.preEvolution"),
    }


def _pokemon_list(value: Any, field: str) -> list[dict[str, Any] | None]:
    if not isinstance(value, list):
        raise ReplayError(f"{field} must be a list")
    return [_pokemon(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _player(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReplayError(f"{field} must be a player object")
    return {
        "active": _pokemon_list(value.get("active", []), f"{field}.active"),
        "bench": _pokemon_list(value.get("bench", []), f"{field}.bench"),
        "bench_max": _scalar(value.get("benchMax"), f"{field}.benchMax", (int,)),
        "deck_count": _scalar(value.get("deckCount"), f"{field}.deckCount", (int,)),
        "discard": _cards(value.get("discard", []), f"{field}.discard"),
        "prize": _cards(value.get("prize", []), f"{field}.prize"),
        "hand_count": _scalar(value.get("handCount"), f"{field}.handCount", (int,)),
        "hand": _cards(value.get("hand", []), f"{field}.hand"),
        "deck": _cards(value.get("deck", []), f"{field}.deck"),
        "conditions": {
            "poisoned": _scalar(value.get("poisoned", False), f"{field}.poisoned", (bool,)),
            "burned": _scalar(value.get("burned", False), f"{field}.burned", (bool,)),
            "asleep": _scalar(value.get("asleep", False), f"{field}.asleep", (bool,)),
            "paralyzed": _scalar(value.get("paralyzed", False), f"{field}.paralyzed", (bool,)),
            "confused": _scalar(value.get("confused", False), f"{field}.confused", (bool,)),
        },
    }


def _select(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ReplayError("select must be an object")
    options = value.get("option", [])
    if not isinstance(options, list) or not all(isinstance(option, dict) for option in options):
        raise ReplayError("select.option must be a list")
    return {
        "type": _scalar(value.get("type"), "select.type", (int, str)),
        "context": _scalar(value.get("context"), "select.context", (int, str)),
        "min_count": _scalar(value.get("minCount"), "select.minCount", (int,)),
        "max_count": _scalar(value.get("maxCount"), "select.maxCount", (int,)),
        "remain_damage_counter": _scalar(value.get("remainDamageCounter", 0), "select.remainDamageCounter", (int,)),
        "remain_energy_cost": _scalar(value.get("remainEnergyCost", 0), "select.remainEnergyCost", (int,)),
        "options": [{key: option[key] for key in OPTION_FIELDS if key in option} for option in options],
        "deck": None if value.get("deck") is None else _cards(value["deck"], "select.deck"),
        "context_card": _card(value.get("contextCard"), "select.contextCard"),
        "effect": _card(value.get("effect"), "select.effect"),
    }


def _logs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(log, dict) for log in value):
        raise ReplayError("logs must be a list")
    return [{key: log[key] for key in LOG_FIELDS if key in log} for log in value]


def normalize_full_frame(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ReplayError("visualizer frame must be an object")
    current = raw.get("current")
    if not isinstance(current, dict):
        raise ReplayError("visualizer frame has no current state")
    players = current.get("players")
    if not isinstance(players, list) or len(players) != 2:
        raise ReplayError("visualizer frame must contain two players")
    selected = raw.get("selected")
    if selected is not None and (not isinstance(selected, list) or not all(type(index) is int for index in selected)):
        raise ReplayError("selected must be null or list[int]")
    looking = current.get("looking")
    return {
        "select": _select(raw.get("select")),
        "logs": _logs(raw.get("logs", [])),
        "current": {
            "turn": _scalar(current.get("turn"), "current.turn", (int,)),
            "turn_action_count": _scalar(current.get("turnActionCount"), "current.turnActionCount", (int,)),
            "acting_seat": _scalar(current.get("yourIndex"), "current.yourIndex", (int,)),
            "first_player": _scalar(current.get("firstPlayer"), "current.firstPlayer", (int,)),
            "supporter_played": _scalar(current.get("supporterPlayed"), "current.supporterPlayed", (bool,)),
            "stadium_played": _scalar(current.get("stadiumPlayed"), "current.stadiumPlayed", (bool,)),
            "energy_attached": _scalar(current.get("energyAttached"), "current.energyAttached", (bool,)),
            "retreated": _scalar(current.get("retreated"), "current.retreated", (bool,)),
            "result": _scalar(current.get("result"), "current.result", (int,)),
            "stadium": _cards(current.get("stadium", []), "current.stadium"),
            "looking": None if looking is None else _cards(looking, "current.looking"),
            "players": [_player(player, f"current.players[{index}]") for index, player in enumerate(players)],
        },
        "selected": None if selected is None else list(selected),
    }


def _raw_card(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    output = {"id": value["id"], "serial": value["serial"]}
    if "player_index" in value:
        output["playerIndex"] = value["player_index"]
    if "name" in value:
        output["name"] = value["name"]
    return output


def _raw_cards(value: Iterable[Any]) -> list[dict[str, Any] | None]:
    return [_raw_card(item) for item in value]


def _raw_pokemon(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    base = _raw_card(value)
    assert base is not None
    return {
        **base,
        "hp": value["hp"],
        "maxHp": value["max_hp"],
        "appearThisTurn": value["appear_this_turn"],
        "energies": list(value.get("energies", [])),
        "energyCards": _raw_cards(value.get("energy_cards", [])),
        "tools": _raw_cards(value.get("tools", [])),
        "preEvolution": _raw_cards(value.get("pre_evolution", [])),
    }


def _raw_player(value: dict[str, Any]) -> dict[str, Any]:
    conditions = value.get("conditions", {})
    return {
        "active": [_raw_pokemon(item) for item in value.get("active", [])],
        "bench": [_raw_pokemon(item) for item in value.get("bench", [])],
        "benchMax": value["bench_max"],
        "deckCount": value["deck_count"],
        "discard": _raw_cards(value.get("discard", [])),
        "prize": _raw_cards(value.get("prize", [])),
        "handCount": value["hand_count"],
        "hand": _raw_cards(value.get("hand", [])),
        "deck": _raw_cards(value.get("deck", [])),
        "poisoned": bool(conditions.get("poisoned", False)),
        "burned": bool(conditions.get("burned", False)),
        "asleep": bool(conditions.get("asleep", False)),
        "paralyzed": bool(conditions.get("paralyzed", False)),
        "confused": bool(conditions.get("confused", False)),
    }


def _raw_select(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "type": value["type"],
        "context": value["context"],
        "minCount": value["min_count"],
        "maxCount": value["max_count"],
        "remainDamageCounter": value.get("remain_damage_counter", 0),
        "remainEnergyCost": value.get("remain_energy_cost", 0),
        "option": [dict(option) for option in value.get("options", [])],
        "deck": None if value.get("deck") is None else _raw_cards(value["deck"]),
        "contextCard": _raw_card(value.get("context_card")),
        "effect": _raw_card(value.get("effect")),
    }


def denormalize_full_frame(normalized: dict[str, Any]) -> dict[str, Any]:
    """Rebuild cg.visualize_data-compatible JSON from a verified replay frame."""

    current = normalized["current"]
    looking = current.get("looking")
    return {
        "select": _raw_select(normalized.get("select")),
        "logs": [dict(item) for item in normalized.get("logs", [])],
        "current": {
            "turn": current["turn"],
            "turnActionCount": current["turn_action_count"],
            "yourIndex": current["acting_seat"],
            "firstPlayer": current["first_player"],
            "supporterPlayed": current["supporter_played"],
            "stadiumPlayed": current["stadium_played"],
            "energyAttached": current["energy_attached"],
            "retreated": current["retreated"],
            "result": current["result"],
            "stadium": _raw_cards(current.get("stadium", [])),
            "lookingCount": 0 if looking is None else len(looking),
            "looking": None if looking is None else _raw_cards(looking),
            "players": [_raw_player(player) for player in current["players"]],
        },
        "selected": None if normalized.get("selected") is None else list(normalized["selected"]),
    }


@dataclass
class ReplayBuilder:
    match_id: str

    def __post_init__(self) -> None:
        self.frames: list[dict[str, Any]] = []
        self._source_hashes: list[str] = []
        self._visualizer_frames: list[dict[str, Any]] = []
        self._visualizer_source_hashes: list[str] = []

    def ingest_visualizer(self, payload: str | list[dict[str, Any]], *, revision: int, captured_after: str) -> int:
        try:
            raw_frames = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError as exc:
            raise ReplayError("visualize_data returned invalid JSON") from exc
        if not isinstance(raw_frames, list):
            raise ReplayError("visualize_data must be a list")
        normalized = [normalize_full_frame(frame) for frame in raw_frames]
        hashes = [sha256_json(frame) for frame in normalized]
        try:
            visualizer_hashes = [sha256_json(frame) for frame in raw_frames]
        except (TypeError, ValueError) as exc:
            raise ReplayError("visualize_data contains unsupported JSON values") from exc
        if hashes[: len(self._source_hashes)] != self._source_hashes:
            raise ReplayError("visualizer history prefix changed")
        if visualizer_hashes[: len(self._visualizer_source_hashes)] != self._visualizer_source_hashes:
            raise ReplayError("raw visualizer history prefix changed")
        if captured_after == "battle_start":
            if self._source_hashes or len(normalized) != 1:
                raise ReplayError("battle_start must contribute exactly one initial frame")
        elif captured_after == "battle_select":
            if len(normalized) != len(self._source_hashes) + 1:
                raise ReplayError("battle_select must contribute exactly one replay frame")
        else:
            raise ReplayError("unsupported replay capture point")
        previous_hash = self.frames[-1]["frame_hash"] if self.frames else "0" * 64
        for index in range(len(self.frames), len(normalized)):
            body = {
                "schema_version": REPLAY_SCHEMA_VERSION,
                "frame_index": index,
                "revision": revision,
                "captured_after": captured_after,
                "payload": normalized[index],
                "previous_hash": previous_hash,
            }
            frame_hash = sha256_json(body)
            frame = {**body, "frame_hash": frame_hash}
            self.frames.append(frame)
            previous_hash = frame_hash
        self._source_hashes = hashes
        self._visualizer_frames = copy.deepcopy(raw_frames)
        self._visualizer_source_hashes = visualizer_hashes
        return len(normalized)

    def seal(
        self,
        destination: str | Path,
        *,
        artifact: dict[str, Any],
        settings: dict[str, Any],
        decks: dict[str, Any],
        public_log: Iterable[dict[str, Any]],
        result: dict[str, Any],
        diagnostics: dict[str, Any],
    ) -> tuple[Path, str]:
        if not self.frames:
            raise ReplayError("cannot seal a replay without frames")
        if len(self._visualizer_frames) != len(self.frames):
            raise ReplayError("visualizer frame count does not match replay frames")
        if diagnostics.get("complete") is True:
            steps = diagnostics.get("steps")
            if type(steps) is not int or steps < 0 or len(self.frames) != steps + 1:
                raise ReplayError("complete replay frame count does not match battle_select steps")
        target = Path(destination).resolve()
        if target.suffix.lower() != ".ptcgmatch":
            target = target.with_suffix(".ptcgmatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        members: dict[str, bytes] = {
            "artifact.json": canonical_json(artifact),
            "settings.json": canonical_json(settings),
            "decks.json": canonical_json(decks),
            "frames.jsonl": b"".join(canonical_json(frame) + b"\n" for frame in self.frames),
            VISUALIZER_MEMBER: canonical_json(self._visualizer_frames),
            "public_log.jsonl": b"".join(canonical_json(item) + b"\n" for item in public_log),
            "result.json": canonical_json(result),
            "diagnostics.json": canonical_json(diagnostics),
        }
        member_metadata = {
            name: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest().upper()}
            for name, data in members.items()
        }
        final_current = self.frames[-1].get("payload", {}).get("current", {})
        first_player = final_current.get("first_player") if isinstance(final_current, dict) else None
        human_seat = settings.get("human_seat")
        complete = diagnostics.get("complete") is True
        manifest = {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "replay_schema_version": REPLAY_SCHEMA_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "human_view_schema_version": HUMAN_VIEW_SCHEMA_VERSION,
            "match_id": self.match_id,
            "app_version": APP_VERSION,
            "submission_id": artifact.get("submission_id"),
            "artifact_manifest_id": artifact.get("artifact_manifest_id"),
            "used_file_hashes": artifact.get("files", {}),
            "human_deck_original_sha256": settings.get("human_deck_source_sha256"),
            "human_deck_normalized_sha256": decks.get("human_sha256"),
            "human_seat": human_seat,
            "first_player": first_player,
            "human_went_first": (
                human_seat == first_player if human_seat in (0, 1) and first_player in (0, 1) else None
            ),
            "started_at_utc": diagnostics.get("started_at_utc") or settings.get("started_at_utc"),
            "finished_at_utc": diagnostics.get("finished_at_utc"),
            "winner_seat": result.get("winner_seat"),
            "result_category": result.get("classification"),
            "termination_reason": result.get("reason_code"),
            "frame_count": len(self.frames),
            "complete": complete,
            "last_frame_hash": self.frames[-1]["frame_hash"],
            "visualizer_format": "cg.visualize_data",
            "visualizer_contains_full_information": True,
            "members": member_metadata,
            "content_sha256": hashlib.sha256(canonical_json(member_metadata)).hexdigest().upper(),
        }
        members["manifest.json"] = canonical_json(manifest)
        if any(len(data) > MAX_REPLAY_MEMBER_BYTES for data in members.values()):
            raise ReplayError("replay member is too large")
        if sum(len(data) for data in members.values()) > MAX_REPLAY_TOTAL_BYTES:
            raise ReplayError("replay expanded size is too large")
        temporary = target.with_name(target.name + f".{os.getpid()}.tmp")
        try:
            with temporary.open("wb") as raw:
                with zipfile.ZipFile(raw, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                    for name in sorted(members):
                        archive.writestr(name, members[name])
                raw.flush()
                os.fsync(raw.fileno())
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target, sha256_file(target)


@dataclass(frozen=True)
class ReplayData:
    path: Path
    manifest: dict[str, Any]
    frames: tuple[dict[str, Any], ...]
    public_log: tuple[dict[str, Any], ...]
    artifact: dict[str, Any]
    settings: dict[str, Any]
    decks: dict[str, Any]
    result: dict[str, Any]
    diagnostics: dict[str, Any]
    visualizer: tuple[dict[str, Any], ...]
    visualizer_exact: bool


def _json_object(data: bytes, member: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"invalid JSON in {member}") from exc
    if not isinstance(value, dict):
        raise ReplayError(f"{member} must contain an object")
    return value


def _json_lines(data: bytes, member: str) -> tuple[dict[str, Any], ...]:
    output: list[dict[str, Any]] = []
    for number, line in enumerate(data.splitlines(), 1):
        value = _json_object(line, f"{member}:{number}")
        output.append(value)
    return tuple(output)


def _json_object_array(data: bytes, member: str) -> tuple[dict[str, Any], ...]:
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReplayError(f"invalid JSON in {member}") from exc
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ReplayError(f"{member} must contain an object array")
    return tuple(value)


def export_visualizer_json(replay: ReplayData, destination: str | Path | None = None) -> tuple[Path, str]:
    """Write a single cg.visualize_data-compatible JSON beside a verified replay."""

    if not replay.visualizer:
        raise ReplayError("replay has no visualizer frames")
    target = Path(destination).resolve() if destination is not None else replay.path.with_suffix(".visualizer.json")
    if target.suffix.lower() != ".json":
        target = target.with_suffix(".json")
    encoded = canonical_json(list(replay.visualizer))
    if len(encoded) > MAX_REPLAY_MEMBER_BYTES:
        raise ReplayError("visualizer JSON is too large")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return target, sha256_file(target)


def load_replay(path: str | Path) -> ReplayData:
    source = Path(path).resolve()
    try:
        with zipfile.ZipFile(source, mode="r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            member_set = set(names)
            allowed_member_sets = {frozenset(LEGACY_REPLAY_MEMBERS), frozenset(REPLAY_MEMBERS)}
            if len(names) != len(member_set) or frozenset(member_set) not in allowed_member_sets:
                raise ReplayError("replay member set is invalid")
            if any(info.is_dir() or info.file_size > MAX_REPLAY_MEMBER_BYTES for info in infos):
                raise ReplayError("replay member size is invalid")
            if sum(info.file_size for info in infos) > MAX_REPLAY_TOTAL_BYTES:
                raise ReplayError("replay expanded size is too large")
            data = {name: archive.read(name) for name in names}
    except (OSError, zipfile.BadZipFile) as exc:
        raise ReplayError("could not open replay") from exc
    manifest = _json_object(data["manifest.json"], "manifest.json")
    if (
        manifest.get("schema_version") != REPLAY_SCHEMA_VERSION
        or manifest.get("replay_schema_version") != REPLAY_SCHEMA_VERSION
        or manifest.get("protocol_version") != PROTOCOL_VERSION
        or manifest.get("human_view_schema_version") != HUMAN_VIEW_SCHEMA_VERSION
        or manifest.get("app_version") != APP_VERSION
    ):
        raise ReplayError("unsupported replay schema")
    required_manifest_fields = {
        "match_id",
        "submission_id",
        "artifact_manifest_id",
        "used_file_hashes",
        "human_deck_original_sha256",
        "human_deck_normalized_sha256",
        "human_seat",
        "first_player",
        "human_went_first",
        "started_at_utc",
        "finished_at_utc",
        "winner_seat",
        "result_category",
        "termination_reason",
        "frame_count",
        "complete",
        "last_frame_hash",
        "members",
        "content_sha256",
    }
    if not required_manifest_fields <= set(manifest):
        raise ReplayError("replay manifest is incomplete")
    expected_members = manifest.get("members")
    if not isinstance(expected_members, dict) or set(expected_members) != member_set - {"manifest.json"}:
        raise ReplayError("replay manifest member map is invalid")
    if manifest.get("content_sha256") != hashlib.sha256(canonical_json(expected_members)).hexdigest().upper():
        raise ReplayError("replay content checksum is invalid")
    for name, expected in expected_members.items():
        if not isinstance(expected, dict):
            raise ReplayError("invalid member metadata")
        actual_hash = hashlib.sha256(data[name]).hexdigest().upper()
        if expected.get("size") != len(data[name]) or expected.get("sha256") != actual_hash:
            raise ReplayError(f"replay member integrity failed: {name}")
    frames = _json_lines(data["frames.jsonl"], "frames.jsonl")
    previous = "0" * 64
    for index, frame in enumerate(frames):
        if frame.get("frame_index") != index or frame.get("previous_hash") != previous:
            raise ReplayError("frame chain is invalid")
        claimed = frame.get("frame_hash")
        body = {key: value for key, value in frame.items() if key != "frame_hash"}
        if claimed != sha256_json(body):
            raise ReplayError("frame hash is invalid")
        previous = claimed
    if manifest.get("frame_count") != len(frames) or manifest.get("last_frame_hash") != previous:
        raise ReplayError("replay frame summary is invalid")
    visualizer_exact = VISUALIZER_MEMBER in data
    if visualizer_exact:
        visualizer = _json_object_array(data[VISUALIZER_MEMBER], VISUALIZER_MEMBER)
        if len(visualizer) != len(frames):
            raise ReplayError("visualizer frame count is invalid")
        for index, raw in enumerate(visualizer):
            if normalize_full_frame(raw) != frames[index].get("payload"):
                raise ReplayError("visualizer frame disagrees with normalized replay")
    else:
        visualizer = tuple(denormalize_full_frame(frame["payload"]) for frame in frames)
    return ReplayData(
        source,
        manifest,
        frames,
        _json_lines(data["public_log.jsonl"], "public_log.jsonl"),
        _json_object(data["artifact.json"], "artifact.json"),
        _json_object(data["settings.json"], "settings.json"),
        _json_object(data["decks.json"], "decks.json"),
        _json_object(data["result.json"], "result.json"),
        _json_object(data["diagnostics.json"], "diagnostics.json"),
        visualizer,
        visualizer_exact,
    )
