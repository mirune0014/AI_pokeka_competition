from __future__ import annotations

import csv
import importlib.util
import os
import sys
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENGINE_DIR = REPO_ROOT / "submission_archaludon"
DEFAULT_AGENT_DIR = REPO_ROOT / "submission_archaludon"


@contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def ensure_engine_on_path(engine_dir: Path) -> None:
    engine_dir = engine_dir.resolve()
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))


def read_deck(deck_path: Path) -> list[int]:
    deck = [int(line.strip()) for line in deck_path.read_text().splitlines() if line.strip()]
    if len(deck) != 60:
        raise ValueError(f"{deck_path} has {len(deck)} cards; expected 60.")
    return deck


def load_agent(agent_dir: Path, module_name: str) -> Callable[[dict[str, Any]], list[int]]:
    agent_dir = agent_dir.resolve()
    main_path = agent_dir / "main.py"
    if not main_path.exists():
        raise FileNotFoundError(main_path)

    spec = importlib.util.spec_from_file_location(module_name, main_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load {main_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    agent = getattr(module, "agent", None)
    if not callable(agent):
        raise AttributeError(f"{main_path} does not define callable agent(obs)")

    def call(obs: dict[str, Any]) -> list[int]:
        with pushd(agent_dir):
            action = agent(obs)
        if not isinstance(action, list) or not all(isinstance(v, int) for v in action):
            raise TypeError(f"agent returned {action!r}; expected list[int]")
        return action

    setattr(call, "agent_dir", agent_dir)
    setattr(call, "module", module)
    return call


def dataclass_to_dict(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [dataclass_to_dict(v) for v in value]
    if isinstance(value, dict):
        return {k: dataclass_to_dict(v) for k, v in value.items()}
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
