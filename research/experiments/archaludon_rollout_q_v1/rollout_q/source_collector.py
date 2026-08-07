'''Collect deterministic source traces from the fixed Archaludon policy.'''

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import random
import re
import sys
from types import ModuleType
from typing import Any, Iterable, Mapping

from .complete_action import (
    observation_complete_actions,
    observation_option_rows,
)
from research.experiments.archaludon_latest_v1_rl_pcgrad_candidate_20260801.archaludon_rl.public_state import (
    enum_int,
    get_field,
    project_public_state,
    raw_observation_hash,
)
from research.rl_ptcg.encoding import encode_observation

from .agent_loader import load_baseline, load_opponent, owner_is_empty, owner_view
from .config import (
    REPO_ROOT,
    RolloutQConfig,
    ensure_input_layout,
    round_dir,
    terminal_reward,
    write_json,
)
from .override_policy import RolloutQOverridePolicy, RoundPolicyResources
from .trace_schema import BranchPoint, SourceTrace, TraceStep, write_record


POPULATION_SPEC = (
    REPO_ROOT
    / 'research'
    / 'experiments'
    / 'archaludon_latest_v1_rl_pcgrad_candidate_20260801'
    / 'specs'
    / 'phase1_iteration_002_population.json'
)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _current(observation: Any) -> Any:
    return _field(observation, 'current', {}) or {}


def _result(observation: Any) -> int | None:
    value = _field(_current(observation), 'result', None)
    if value is None:
        return None
    value = enum_int(value)
    return int(value)


def _player(observation: Any) -> int:
    value = _field(_current(observation), 'yourIndex', 0)
    return int(enum_int(value))


def _context(observation: Any) -> int | None:
    select = _field(observation, 'select', None)
    if select is None:
        return None
    value = _field(select, 'context', None)
    return None if value is None else int(enum_int(value))


def trace_observation_hash(observation: Any) -> str:
    '''Hash the deterministic engine payload, excluding its search scratch buffer.'''

    if isinstance(observation, Mapping):
        value = dict(observation)
        value.pop('search_begin_input', None)
        return raw_observation_hash(value)
    return raw_observation_hash(observation)


def _load_engine() -> tuple[Any, Any, Any, Path]:
    '''Load the repository's checked local engine without copying it.'''

    engine_dir = (
        REPO_ROOT
        / '_local_generated'
        / 'analysis_outputs'
        / 'cynthia_v9_vs_v11_poffin_role_selection_20260713'
        / 'seeded_engine'
    )
    game_path = engine_dir / 'cg' / 'game.py'
    if not game_path.is_file():
        raise RuntimeError('BLOCKED: seeded engine unavailable')

    # A previous import of the formal bundled ``cg`` package must not shadow
    # the checked seeded runtime.  The engine is loaded once per process, so
    # removing only an incompatible pre-import is safe before a battle starts.
    incompatible_cg = False
    for name, loaded in tuple(sys.modules.items()):
        if name != 'cg' and not name.startswith('cg.'):
            continue
        loaded_file = getattr(loaded, '__file__', None)
        try:
            if loaded_file is not None and Path(loaded_file).resolve().is_relative_to(engine_dir.resolve()):
                continue
        except (OSError, ValueError):
            pass
        if name != 'cg':
            incompatible_cg = True
            break
    if incompatible_cg:
        for name in tuple(sys.modules):
            if name == 'cg' or name.startswith('cg.'):
                sys.modules.pop(name, None)
    existing_api = sys.modules.get('cg.api')
    if existing_api is not None and not hasattr(existing_api, 'AreaType'):
        sys.modules.pop('cg.api', None)
    if str(engine_dir) not in sys.path:
        sys.path.insert(0, str(engine_dir))
    importlib.invalidate_caches()
    def import_checked(name: str, path: Path) -> Any:
        try:
            return importlib.import_module(name)
        except TypeError as exc:
            if 'unsupported operand type(s) for |' not in str(exc) or sys.version_info >= (3, 10):
                raise
            sys.modules.pop(name, None)
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None:
                raise RuntimeError('BLOCKED: seeded engine unavailable') from exc
            module = ModuleType(name)
            module.__file__ = str(path)
            module.__package__ = 'cg'
            module.__spec__ = spec
            sys.modules[name] = module
            source = path.read_text(encoding='utf-8-sig')
            if path.name == 'api.py':
                source = source.replace('list[Pokemon | None]', 'list[Optional[Pokemon]]')
                source = source.replace('list[Card | None]', 'list[Optional[Card]]')
                source = source.replace('list[Card] | None', 'Optional[list[Card]]')
                source = source.replace('list[Optional[Card]] | None', 'Optional[list[Optional[Card]]]')
                for token in (
                    'int', 'bool', 'str', 'Pokemon', 'Card', 'SelectData', 'State',
                    'SearchState', 'EnergyType', 'SpecialConditionType', 'AreaType',
                ):
                    source = re.sub(
                        rf'\b{re.escape(token)}\s*\|\s*None\b',
                        f'Optional[{token}]',
                        source,
                    )
                source = 'from typing import Optional\n' + source
            elif path.name == 'game.py':
                source = 'from typing import Optional\n' + source.replace('int | None', 'Optional[int]')
            code = compile(source, str(path), 'exec', dont_inherit=True)
            exec(code, module.__dict__)
            return module

    import_checked('cg.api', engine_dir / 'cg' / 'api.py')
    game = import_checked('cg.game', game_path)
    try:
        parameters = inspect.signature(game.battle_start).parameters
    except (TypeError, ValueError) as exc:
        raise RuntimeError('BLOCKED: seeded engine unavailable') from exc
    if 'seed' not in parameters:
        raise RuntimeError('BLOCKED: seeded engine unavailable')
    return game.battle_start, game.battle_select, game.battle_finish, engine_dir

def _battle_start(battle_start: Any, decks: tuple[list[int], list[int]], seed: int) -> tuple[Any, Any]:
    random.seed(int(seed))
    return battle_start(*decks, seed=int(seed))


def _opponent_rows() -> list[dict[str, Any]]:
    if POPULATION_SPEC.is_file():
        raw = json.loads(POPULATION_SPEC.read_text(encoding='utf-8'))
        rows = raw.get('opponents', ()) if isinstance(raw, Mapping) else ()
        if isinstance(rows, list) and len(rows) == 8:
            return [dict(row) for row in rows]
    # Keep the fixed eight-opponent schedule usable even when the historical
    # population receipt is not present in a minimal checkout.
    return [
        {'id': 'historical_silver', 'path': 'archaludon/baseline/historical_silver_archaludon_54495224'},
        {'id': 'alakazam_public', 'path': 'opponents/meta_agents/alakazam_psychic_public_simple'},
        {'id': 'alakazam_rmy_live', 'path': 'opponents/meta_agents/alakazam_rmy_live_85082271_simple'},
        {'id': 'marnie_kazuki_live', 'path': 'opponents/meta_agents/marnie_kazuki_live_85083586_simple'},
        {'id': 'mega_lucario_public', 'path': 'opponents/meta_agents/mega_lucario_public_simple'},
        {'id': 'starmie_public', 'path': 'opponents/meta_agents/starmie_public_simple'},
        {'id': 'dragapult_live', 'path': 'opponents/meta_agents/dragapult_live_simple'},
        {'id': 'ogerpon_cornerstone_public', 'path': 'opponents/meta_agents/ogerpon_cornerstone_public_simple'},
    ]


def resolve_opponent_dir(row: Mapping[str, Any], config: RolloutQConfig) -> Path:
    opponent_id = str(row.get('id', ''))
    if opponent_id == 'historical_silver':
        path = config.historical_silver_dir
    else:
        raw_path = Path(str(row.get('path', '')))
        candidates = (REPO_ROOT / raw_path, REPO_ROOT / 'opponents' / raw_path)
        path = next((item for item in candidates if (item / 'main.py').is_file()), candidates[0])
    if not (path / 'main.py').is_file() or not (path / 'deck.csv').is_file():
        raise FileNotFoundError(f'opponent input is incomplete: {path}')
    return path


def _seed_for(round_index: int, cell_index: int, game_index: int) -> int:
    return 910000000 + int(round_index) * 1000000 + int(cell_index) * 10000 + int(game_index)


def _cell_counts(total_games: int, cells: int = 16) -> list[int]:
    base, remainder = divmod(int(total_games), int(cells))
    return [base + (1 if index < remainder else 0) for index in range(cells)]


def build_source_policy(
    config: RolloutQConfig,
    round_index: int,
    baseline: Any,
    resources: RoundPolicyResources | None = None,
) -> Any:
    """Build the fixed source policy for one expert-iteration round.

    Round 0 uses the formal baseline directly.  Later rounds use the prior
    round's frozen three-model override ensemble around that same baseline
    object.  The returned object is kept for the complete replay lifetime.
    """

    if int(round_index) == 0:
        return baseline
    if int(round_index) < 0 or int(round_index) >= config.rounds:
        raise ValueError('round index is outside the fixed specification')
    if resources is None:
        resources = RoundPolicyResources.load(config, int(round_index) - 1)
    if resources.checkpoint_round != int(round_index) - 1:
        raise ValueError('source policy resources do not match the requested prior round')
    return resources.bind(baseline, config)


def _candidate_record(candidate: Any) -> dict[str, Any]:
    return {
        'candidate_index': int(candidate.candidate_index),
        'action': list(candidate.action),
        'canonical_identity': str(candidate.canonical_identity),
        'selected_options': [dict(item) for item in candidate.selected_options],
        'order_sensitive': bool(candidate.order_sensitive),
    }


def _collect_one(
    *,
    config: RolloutQConfig,
    round_index: int,
    opponent_id: str,
    opponent_dir: Path,
    seat: int,
    seed: int,
    engine: tuple[Any, Any, Any, Path],
    max_steps: int,
    source_policy_factory: Any = None,
) -> SourceTrace:
    battle_start, battle_select, battle_finish, _ = engine
    baseline = load_baseline(config.baseline_dir, config.baseline_dir.name)
    opponent = load_opponent(opponent_dir, opponent_id)
    source_policy = source_policy_factory(baseline) if source_policy_factory is not None else baseline
    baseline.seed(seed)
    opponent.seed(seed)
    baseline_deck = baseline.deck
    opponent_deck = opponent.deck
    decks = (baseline_deck, opponent_deck) if seat == 0 else (opponent_deck, baseline_deck)
    episode_id = f'round_{round_index:02d}_{opponent_id}_seat{seat}_seed{seed}'
    steps: list[TraceStep] = []
    eligible_points: list[BranchPoint] = []
    started = False
    action_errors = 0
    max_step_hit = False
    terminal_result = -1
    error: str | None = None
    observation: Any = None
    try:
        observation, start_data = _battle_start(battle_start, decks, seed)
        if not observation:
            error_player = getattr(start_data, 'errorPlayer', None)
            error_type = getattr(start_data, 'errorType', None)
            raise RuntimeError(f'engine start failed: {error_player}/{error_type}')
        started = True
        for step_index in range(int(max_steps)):
            current_result = _result(observation)
            if current_result in (0, 1, 2):
                terminal_result = int(current_result)
                break
            if not _field(observation, 'select', None):
                break
            current_player = _player(observation)
            source = 'BASELINE' if current_player == seat else 'OPPONENT'
            public_state = project_public_state(observation)
            action: list[int]
            owner_before = owner_view(baseline) if source == 'BASELINE' else None
            try:
                action = source_policy(observation) if source == 'BASELINE' else opponent(observation)
                action = [int(value) for value in action]
            except Exception:
                action_errors += 1
                raise
            owner_after = owner_view(baseline) if source == 'BASELINE' else None
            step = TraceStep(
                step_index=step_index,
                current_player=current_player,
                raw_observation_sha256=trace_observation_hash(observation),
                public_state=public_state,
                action=tuple(action),
                action_source=source,
                select_context=_context(observation),
            )
            steps.append(step)
            if source == 'BASELINE' and _context(observation) in config.branch_contexts:
                try:
                    candidates = observation_complete_actions(observation)
                    option_rows = observation_option_rows(observation)
                    baseline_index = candidates.candidate_index_for(option_rows, action)
                    if (
                        config.minimum_candidate_count <= len(candidates.candidates) <= config.maximum_candidate_count
                        and baseline_index is not None
                        and owner_before is None
                        and owner_after is None
                    ):
                        encoded = encode_observation(observation)
                        eligible_points.append(
                            BranchPoint(
                                branch_group_id='',
                                step_index=step_index,
                                raw_observation_sha256=step.raw_observation_sha256,
                                public_state=public_state,
                                baseline_action=tuple(action),
                                baseline_candidate_index=int(baseline_index),
                                candidates=tuple(_candidate_record(candidate) for candidate in candidates.candidates),
                                state_vector=tuple(float(item) for item in encoded.state_vector),
                                option_vectors=tuple(
                                    tuple(float(item) for item in vector)
                                    for vector in encoded.option_vectors
                                ),
                                owner_before=owner_before,
                                owner_after=owner_after,
                            )
                        )
                except Exception:
                    # Candidate construction is diagnostic; a normal baseline
                    # trace remains valid when an unusual MAIN surface cannot
                    # be materialized by the research bridge.
                    pass
            try:
                observation = battle_select(action)
            except Exception:
                action_errors += 1
                raise
        else:
            max_step_hit = True
        current_result = _result(observation)
        if current_result in (0, 1, 2):
            terminal_result = int(current_result)
        clean_terminal = terminal_result in (0, 1, 2) and not max_step_hit and action_errors == 0
    except Exception as exc:
        clean_terminal = False
        error = f'{type(exc).__name__}: {exc}'
    finally:
        if started:
            try:
                battle_finish()
            except Exception as exc:
                clean_terminal = False
                error = error or f'{type(exc).__name__}: {exc}'
    if len(eligible_points) > config.maximum_branch_points_per_source_game:
        keyed = []
        for point in eligible_points:
            key = hashlib.sha256(
                f'{opponent_id}|{seat}|{seed}|{point.step_index}'.encode('utf-8')
            ).hexdigest()
            keyed.append((key, point))
        eligible_points = [point for _, point in sorted(keyed)[: config.maximum_branch_points_per_source_game]]
    branch_points = tuple(
        BranchPoint(
            branch_group_id=hashlib.sha256(f'{episode_id}|{point.step_index}'.encode('utf-8')).hexdigest(),
            step_index=point.step_index,
            raw_observation_sha256=point.raw_observation_sha256,
            public_state=point.public_state,
            baseline_action=point.baseline_action,
            baseline_candidate_index=point.baseline_candidate_index,
            candidates=point.candidates,
            state_vector=point.state_vector,
            option_vectors=point.option_vectors,
            owner_before=point.owner_before,
            owner_after=point.owner_after,
        )
        for point in sorted(eligible_points, key=lambda item: item.step_index)
    )
    reward = terminal_reward(terminal_result, seat) if terminal_result in (0, 1, 2) else 0.0
    source_override_count = 0
    source_fallback_count = 0
    source_model_failure_count = 0
    if isinstance(source_policy, RolloutQOverridePolicy):
        source_override_count = int(source_policy.telemetry.override_count)
        source_fallback_count = int(source_policy.telemetry.fallback_count)
        source_model_failure_count = int(source_policy.telemetry.model_failure_count)
    return SourceTrace(
        episode_id=episode_id,
        opponent_id=opponent_id,
        seat=seat,
        seed=seed,
        terminal_result=terminal_result,
        terminal_reward=reward,
        clean_terminal=bool(clean_terminal),
        steps=tuple(steps),
        branch_points=branch_points,
        engine_steps=len(steps),
        action_errors=action_errors,
        max_step_hit=max_step_hit,
        source_override_count=source_override_count,
        source_fallback_count=source_fallback_count,
        source_model_failure_count=source_model_failure_count,
        error=error,
    )


def collect_source_round(
    config: RolloutQConfig,
    round_index: int,
    *,
    games: int | None = None,
    max_steps: int | None = None,
) -> dict[str, Any]:
    ensure_input_layout(config)
    destination = round_dir(config, round_index) / 'source_traces'
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f'source trace output already exists: {destination}')
    destination.mkdir(parents=True, exist_ok=True)
    engine = _load_engine()
    rows = _opponent_rows()
    if len(rows) != 8:
        raise ValueError('fixed source schedule requires exactly eight opponents')
    requested = config.source_games_per_round if games is None else int(games)
    if requested <= 0 or requested > config.source_games_per_round:
        raise ValueError('games must be in 1..source_games_per_round')
    counts = _cell_counts(requested)
    resources = None if int(round_index) == 0 else RoundPolicyResources.load(config, int(round_index) - 1)
    source_policy_factory = lambda baseline: (
        baseline if resources is None else resources.bind(baseline, config)
    )
    traces: list[SourceTrace] = []
    emitted = 0
    for cell_index, row in enumerate(rows):
        opponent_id = str(row['id'])
        opponent_dir = resolve_opponent_dir(row, config)
        for seat in (0, 1):
            cell_count = counts[cell_index * 2 + seat]
            for game_index in range(cell_count):
                if emitted >= requested:
                    break
                seed = _seed_for(round_index, cell_index * 2 + seat, game_index)
                trace = _collect_one(
                    config=config,
                    round_index=round_index,
                    opponent_id=opponent_id,
                    opponent_dir=opponent_dir,
                    seat=seat,
                    seed=seed,
                    engine=engine,
                    max_steps=max_steps or config.worker_max_steps,
                    source_policy_factory=source_policy_factory,
                )
                write_record(destination / f'{trace.episode_id}.json', trace.to_dict())
                traces.append(trace)
                emitted += 1
            if emitted >= requested:
                break
        if emitted >= requested:
            break
    summary = {
        'schema_version': 'archaludon-source-collection-summary-v1',
        'round': int(round_index),
        'requested_games': requested,
        'emitted_games': len(traces),
        'cell_counts': {
            f"{str(row['id'])}|seat{seat}": counts[cell_index * 2 + seat]
            for cell_index, row in enumerate(rows)
            for seat in (0, 1)
        },
        'clean_terminal_games': sum(int(item.clean_terminal) for item in traces),
        'eligible_branch_points': sum(len(item.branch_points) for item in traces),
        'action_errors': sum(item.action_errors for item in traces),
        'max_step_hits': sum(int(item.max_step_hit) for item in traces),
        'source_override_count': sum(item.source_override_count for item in traces),
        'source_fallback_count': sum(item.source_fallback_count for item in traces),
        'source_model_failure_count': sum(item.source_model_failure_count for item in traces),
        'engine_dir': str(engine[3]),
    }
    write_json(round_dir(config, round_index) / 'source_summary.json', summary)
    return summary


__all__ = [
    'build_source_policy',
    'collect_source_round',
    'resolve_opponent_dir',
    'trace_observation_hash',
]
