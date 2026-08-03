from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import settings_path


DEFAULT_SETTINGS: dict[str, Any] = {
    "artifact_path": "",
    "deck_path": "",
    "image_folder": "",
    "human_seat": 0,
    "replay_folder": "",
    "ai_display_delay_ms": 1000,
    "agent_timeout_seconds": 45,
}


def load_settings(path: Path | None = None) -> dict[str, Any]:
    target = path or settings_path()
    if not target.is_file():
        return dict(DEFAULT_SETTINGS)
    try:
        value = json.loads(target.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)
    if not isinstance(value, dict):
        return dict(DEFAULT_SETTINGS)
    result = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in value and type(value[key]) is type(DEFAULT_SETTINGS[key]):
            result[key] = value[key]
    if result["human_seat"] not in (-1, 0, 1):
        result["human_seat"] = 0
    if not 400 <= result["ai_display_delay_ms"] <= 10_000:
        result["ai_display_delay_ms"] = 1000
    if not 1 <= result["agent_timeout_seconds"] <= 600:
        result["agent_timeout_seconds"] = 45
    return result


def save_settings(value: dict[str, Any], path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: value.get(key, default) for key, default in DEFAULT_SETTINGS.items()}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
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
