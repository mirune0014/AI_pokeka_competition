from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "PTCGHumanClient"
APP_VERSION = "0.1.0"
PROTOCOL_VERSION = 1
HUMAN_VIEW_SCHEMA_VERSION = 1
REPLAY_SCHEMA_VERSION = 1
MAX_IPC_BYTES = 1024 * 1024
MAX_REPLAY_MEMBER_BYTES = 256 * 1024 * 1024
MAX_REPLAY_TOTAL_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_STEPS = 2000
DEFAULT_AGENT_TIMEOUT_SECONDS = 45.0
DEFAULT_ENGINE_TIMEOUT_SECONDS = 30.0


def local_app_data() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / ".ptcg_human_client"


def documents_dir() -> Path:
    profile = os.environ.get("USERPROFILE")
    base = Path(profile) / "Documents" if profile else Path.home() / "Documents"
    return base / "PTCG Human Client"


def staging_root() -> Path:
    return local_app_data() / "staging"


def settings_path() -> Path:
    return local_app_data() / "settings.json"


def logs_dir() -> Path:
    return local_app_data() / "logs"


def default_replay_dir() -> Path:
    return documents_dir() / "Replays"
