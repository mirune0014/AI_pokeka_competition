from __future__ import annotations

import json
import math
import re
import uuid
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any, Iterable

from .config import MAX_IPC_BYTES, PROTOCOL_VERSION


MESSAGE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MESSAGE_TYPE_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
ENVELOPE_KEYS = {
    "protocol_version",
    "message_id",
    "message_type",
    "match_id",
    "request_id",
    "state_revision",
    "step_id",
    "payload",
}


class ProtocolError(RuntimeError):
    pass


class FrameTooLarge(ProtocolError):
    pass


class DuplicateMessage(ProtocolError):
    pass


def _reject_constant(value: str) -> None:
    raise ProtocolError(f"non-finite JSON number is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ProtocolError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def _check_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > 64:
        raise ProtocolError("JSON nesting is too deep")
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        if abs(value) > 2**53:
            raise ProtocolError("integer is outside the interoperable JSON range")
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ProtocolError("non-finite float is forbidden")
        return
    if isinstance(value, list):
        for item in value:
            _check_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProtocolError("JSON object keys must be strings")
            _check_json_value(item, depth=depth + 1)
        return
    raise ProtocolError(f"not a JSON value: {type(value).__name__}")


def encode_json(value: dict[str, Any], *, max_bytes: int = MAX_IPC_BYTES) -> bytes:
    _check_json_value(value)
    try:
        data = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ProtocolError(str(exc)) from exc
    if len(data) > max_bytes:
        raise FrameTooLarge(f"JSON frame is {len(data)} bytes; limit is {max_bytes}")
    return data


def decode_json(data: bytes, *, max_bytes: int = MAX_IPC_BYTES) -> dict[str, Any]:
    if len(data) > max_bytes:
        raise FrameTooLarge(f"JSON frame is {len(data)} bytes; limit is {max_bytes}")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except ProtocolError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(str(exc)) from exc
    if not isinstance(value, dict):
        raise ProtocolError("top-level JSON value must be an object")
    _check_json_value(value)
    return value


def _metadata_from_payload(payload: dict[str, Any]) -> tuple[str | None, int | None, int | None]:
    request_id = payload.get("request_id")
    state_revision = payload.get("state_revision")
    step_id = payload.get("step_id")
    for nested_key in ("decision", "state"):
        nested = payload.get(nested_key)
        if not isinstance(nested, dict):
            continue
        if request_id is None:
            request_id = nested.get("request_id")
        if state_revision is None:
            state_revision = nested.get("state_revision", nested.get("revision"))
        if step_id is None:
            step_id = nested.get("step_id")
    if step_id is None:
        step_id = state_revision
    return (
        request_id if isinstance(request_id, str) else None,
        state_revision if type(state_revision) is int else None,
        step_id if type(step_id) is int else None,
    )


def make_envelope(
    message_type: str,
    match_id: str,
    payload: dict[str, Any],
    *,
    message_id: str | None = None,
    request_id: str | None = None,
    state_revision: int | None = None,
    step_id: int | None = None,
) -> dict[str, Any]:
    inferred_request, inferred_revision, inferred_step = _metadata_from_payload(payload)
    envelope = {
        "protocol_version": PROTOCOL_VERSION,
        "message_id": message_id or str(uuid.uuid4()),
        "message_type": message_type,
        "match_id": match_id,
        "request_id": request_id if request_id is not None else inferred_request,
        "state_revision": state_revision if state_revision is not None else inferred_revision,
        "step_id": step_id if step_id is not None else inferred_step,
        "payload": payload,
    }
    validate_envelope(envelope)
    return envelope


def validate_envelope(value: dict[str, Any], *, allowed_ops: Iterable[str] | None = None) -> None:
    if set(value) != ENVELOPE_KEYS:
        raise ProtocolError(f"invalid envelope keys: {sorted(set(value) ^ ENVELOPE_KEYS)}")
    if type(value["protocol_version"]) is not int or value["protocol_version"] != PROTOCOL_VERSION:
        raise ProtocolError("unsupported protocol version")
    if not isinstance(value["message_id"], str) or not MESSAGE_ID_RE.fullmatch(value["message_id"]):
        raise ProtocolError("invalid message id")
    message_type = value["message_type"]
    if not isinstance(message_type, str) or not MESSAGE_TYPE_RE.fullmatch(message_type):
        raise ProtocolError("invalid message type")
    if allowed_ops is not None and message_type not in set(allowed_ops):
        raise ProtocolError(f"message type is not allowed here: {message_type}")
    if not isinstance(value["match_id"], str) or not MESSAGE_ID_RE.fullmatch(value["match_id"]):
        raise ProtocolError("invalid match id")
    request_id = value["request_id"]
    if request_id is not None and (not isinstance(request_id, str) or not MESSAGE_ID_RE.fullmatch(request_id)):
        raise ProtocolError("invalid request id")
    for field in ("state_revision", "step_id"):
        item = value[field]
        if item is not None and (type(item) is not int or not 0 <= item <= 2**53):
            raise ProtocolError(f"invalid {field}")
    if not isinstance(value["payload"], dict):
        raise ProtocolError("payload must be an object")


def send_message(connection: Connection, value: dict[str, Any], *, max_bytes: int = MAX_IPC_BYTES) -> None:
    validate_envelope(value)
    connection.send_bytes(encode_json(value, max_bytes=max_bytes))


def receive_message(
    connection: Connection,
    *,
    max_bytes: int = MAX_IPC_BYTES,
    allowed_ops: Iterable[str] | None = None,
) -> dict[str, Any]:
    try:
        data = connection.recv_bytes(maxlength=max_bytes)
    except OSError as exc:
        message = str(exc).lower()
        if "bad message length" in message or "too long" in message:
            raise FrameTooLarge(str(exc)) from exc
        raise ProtocolError(str(exc)) from exc
    value = decode_json(data, max_bytes=max_bytes)
    validate_envelope(value, allowed_ops=allowed_ops)
    return value


@dataclass
class MessageTracker:
    limit: int = 8192

    def __post_init__(self) -> None:
        self._seen: set[str] = set()
        self._order: list[str] = []

    def accept(self, envelope: dict[str, Any]) -> None:
        message_id = envelope["message_id"]
        if message_id in self._seen:
            raise DuplicateMessage(message_id)
        self._seen.add(message_id)
        self._order.append(message_id)
        if len(self._order) > self.limit:
            old = self._order.pop(0)
            self._seen.remove(old)
