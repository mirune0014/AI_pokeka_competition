'''Fresh, state-preserving loading of research agents.'''

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import random
import sys
from types import ModuleType
from typing import Any, Iterator
import uuid

from infrastructure.tools.ptcg_common import pushd, read_deck


@dataclass
class LoadedPolicy:
    policy_id: str
    agent_dir: Path
    module: ModuleType
    parent_module: ModuleType | None = None

    def __call__(self, observation: Any) -> list[int]:
        with pushd(self.agent_dir):
            action = self.module.agent(observation)
        if not isinstance(action, list) or any(
            not isinstance(value, int) or isinstance(value, bool) for value in action
        ):
            raise TypeError(f'{self.policy_id} returned a non-list[int] action')
        return list(action)

    @property
    def deck(self) -> list[int]:
        return read_deck(self.agent_dir / 'deck.csv')

    def seed(self, seed: int) -> None:
        seen: set[int] = set()
        for module in (self.module, self.parent_module):
            if module is None or id(module) in seen:
                continue
            seen.add(id(module))
            module_random = getattr(module, 'random', None)
            if hasattr(module_random, 'seed'):
                module_random.seed(int(seed))

    @property
    def owner(self) -> Any:
        return getattr(self.module, '_materialization_owner', None)

    @property
    def telemetry(self) -> dict[str, Any]:
        value = getattr(self.module, '_last_telemetry', {})
        return dict(value) if isinstance(value, dict) else {}


@contextmanager
def _module_import_context(agent_dir: Path) -> Iterator[None]:
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(agent_dir))
        with pushd(agent_dir):
            yield
    finally:
        sys.path[:] = previous


def load_policy(agent_dir: Path, policy_id: str | None = None) -> LoadedPolicy:
    agent_dir = agent_dir.resolve()
    main_path = agent_dir / 'main.py'
    if not main_path.is_file():
        raise FileNotFoundError(main_path)
    module_name = f'_rollout_q_{policy_id or agent_dir.name}_{uuid.uuid4().hex}'
    parent_path = agent_dir / '_historical_silver_parent.py'
    parent_name = f'_rollout_q_parent_{policy_id or agent_dir.name}_{uuid.uuid4().hex}'
    parent_module: ModuleType | None = None
    parent_spec = None
    if parent_path.is_file():
        parent_spec = importlib.util.spec_from_file_location(parent_name, parent_path)
        if parent_spec is None or parent_spec.loader is None:
            raise ImportError(f'cannot load {parent_path}')
        parent_module = importlib.util.module_from_spec(parent_spec)
        sys.modules[parent_name] = parent_module
        try:
            with _module_import_context(agent_dir):
                parent_spec.loader.exec_module(parent_module)
        except Exception:
            sys.modules.pop(parent_name, None)
            raise
    spec = importlib.util.spec_from_file_location(module_name, main_path)
    if spec is None or spec.loader is None:
        if parent_module is not None:
            sys.modules.pop(parent_name, None)
        raise ImportError(f'cannot load {main_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sentinel = object()
    previous_parent = sys.modules.get('_historical_silver_parent', sentinel)
    try:
        if parent_module is not None:
            sys.modules['_historical_silver_parent'] = parent_module
        with _module_import_context(agent_dir):
            spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        if parent_module is not None:
            sys.modules.pop(parent_name, None)
        if previous_parent is sentinel:
            sys.modules.pop('_historical_silver_parent', None)
        else:
            sys.modules['_historical_silver_parent'] = previous_parent
        raise
    if previous_parent is sentinel:
        sys.modules.pop('_historical_silver_parent', None)
    else:
        sys.modules['_historical_silver_parent'] = previous_parent
    if not callable(getattr(module, 'agent', None)):
        raise AttributeError(f'{main_path} has no callable agent')
    return LoadedPolicy(str(policy_id or agent_dir.name), agent_dir, module, parent_module)


def load_baseline(baseline_dir: Path, policy_id: str = 'BASELINE_POLICY') -> LoadedPolicy:
    return load_policy(baseline_dir, policy_id)


def load_opponent(opponent_dir: Path, opponent_id: str) -> LoadedPolicy:
    return load_policy(opponent_dir, opponent_id)


def owner_is_empty(policy: LoadedPolicy) -> bool:
    return policy.owner is None


def owner_view(policy: LoadedPolicy) -> Any:
    owner = policy.owner
    if owner is None:
        return None
    if isinstance(owner, dict):
        return dict(owner)
    return repr(owner)


def reset_python_seed(seed: int) -> None:
    random.seed(int(seed))
