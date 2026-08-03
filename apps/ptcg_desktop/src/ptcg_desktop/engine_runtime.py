from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@contextmanager
def working_directory(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def read_flat_deck(path: Path) -> list[int]:
    deck = [int(line.strip()) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(deck) != 60:
        raise ValueError(f"expected 60 cards, got {len(deck)}")
    return deck


@dataclass
class EngineRuntime:
    stage_path: Path
    battle_start: Callable[..., Any]
    battle_select: Callable[..., Any]
    battle_finish: Callable[..., Any]
    visualize_data: Callable[..., str]
    card_names: dict[int, str]
    attack_names: dict[int, str]
    agent: Callable[[dict[str, Any]], list[int]] | None
    agent_deck: list[int]


def load_runtime(stage_path: str | Path, *, load_agent: bool = True) -> EngineRuntime:
    stage = Path(stage_path).resolve()
    if not (stage / "main.py").is_file() or not (stage / "cg" / "cg.dll").is_file():
        raise FileNotFoundError("staged artifact is incomplete")
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if str(stage) not in sys.path:
        sys.path.insert(0, str(stage))
    with working_directory(stage):
        from cg.api import all_attack, all_card_data
        from cg.game import battle_finish, battle_select, battle_start, visualize_data

        cards = all_card_data()
        attacks = all_attack()
    card_names = {int(card.cardId): str(card.name) for card in cards}
    attack_names = {int(attack.attackId): str(attack.name) for attack in attacks}
    agent_callable: Callable[[dict[str, Any]], list[int]] | None = None
    if load_agent:
        module_name = f"ptcg_verified_agent_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, stage / "main.py")
        if spec is None or spec.loader is None:
            raise ImportError("could not create agent module spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        with working_directory(stage):
            spec.loader.exec_module(module)
        raw_agent = getattr(module, "agent", None)
        if not callable(raw_agent):
            raise AttributeError("verified main.py does not define agent(obs)")

        def call_agent(obs: dict[str, Any]) -> list[int]:
            with working_directory(stage):
                return raw_agent(obs)

        agent_callable = call_agent
    return EngineRuntime(
        stage,
        battle_start,
        battle_select,
        battle_finish,
        visualize_data,
        card_names,
        attack_names,
        agent_callable,
        read_flat_deck(stage / "deck.csv"),
    )
