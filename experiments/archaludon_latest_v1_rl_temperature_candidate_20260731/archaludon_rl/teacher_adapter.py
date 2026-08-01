"""One-call, state-preserving adapter around exact latest-v1."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import sys
import threading
from types import ModuleType
from typing import Any, Iterator, Sequence
import uuid

from .frozen_sources import (
    ENGINE_RECEIPTS,
    find_repo_root,
    latest_source_dir,
    sha256_file,
    verify_frozen_sources,
)
from .semantic_action import validate_engine_action


_SOURCE_CONTEXT_LOCK = threading.RLock()


@contextmanager
def source_execution_context(source_dir: Path) -> Iterator[None]:
    """Temporarily supply the source cwd and restore all process-global state."""

    with _SOURCE_CONTEXT_LOCK:
        previous_cwd = Path.cwd()
        previous_path = list(sys.path)
        try:
            os.chdir(source_dir)
            yield
        finally:
            os.chdir(previous_cwd)
            sys.path[:] = previous_path


@dataclass(frozen=True)
class TeacherDecision:
    action: tuple[int, ...]
    telemetry: tuple[dict[str, Any], ...]
    call_count: int

    def action_list(self) -> list[int]:
        return list(self.action)


class TeacherAdapterError(RuntimeError):
    pass


class LatestV1Teacher:
    """Own one isolated latest-v1 module for a single game/seat."""

    def __init__(
        self,
        *,
        game_id: str,
        seat: int | None,
        source_dir: Path | None = None,
        module: ModuleType | Any | None = None,
        verify_sources: bool = True,
    ) -> None:
        self.game_id = str(game_id)
        self.seat = seat
        self.source_dir = (source_dir or latest_source_dir()).resolve()
        self.call_count = 0
        self.engine_module_receipt: dict[str, str] | None = None
        if module is None:
            if verify_sources:
                verify_frozen_sources()
            self.engine_module_receipt = self._record_preloaded_engine(
                require_frozen=verify_sources
            )
            self.module = self._load_isolated_module()
        else:
            self.module = module
        if not callable(getattr(self.module, "agent", None)):
            raise TeacherAdapterError("latest-v1 module has no callable final agent")
        if not callable(getattr(self.module, "drain_cumulative_telemetry", None)):
            raise TeacherAdapterError(
                "latest-v1 module has no cumulative telemetry drain"
            )

    def _record_preloaded_engine(self, *, require_frozen: bool) -> dict[str, str]:
        api_module = sys.modules.get("cg.api")
        api_file = getattr(api_module, "__file__", None)
        if api_module is None or api_file is None:
            raise TeacherAdapterError("caller-preloaded cg.api has no resolved file")
        path = Path(api_file).resolve()
        receipt = {"path": str(path), "sha256": sha256_file(path)}
        if require_frozen:
            expected = next(
                item
                for item in ENGINE_RECEIPTS
                if item.relative_path.endswith("/cg/api.py")
            )
            expected_path = (find_repo_root() / expected.relative_path).resolve()
            if path != expected_path or receipt["sha256"] != expected.sha256:
                raise TeacherAdapterError(
                    "caller-preloaded cg.api is not the frozen seeded engine: "
                    f"{receipt}"
                )
        return receipt

    def _load_isolated_module(self) -> ModuleType:
        # The engine is selected by the caller.  Refuse to silently import the
        # candidate-bundled copy or any other undeclared engine.
        if "cg" not in sys.modules or "cg.api" not in sys.modules:
            raise TeacherAdapterError(
                "caller must preload the checked cg engine before latest-v1"
            )
        module_name = (
            "_archaludon_latest_v1_"
            f"{self.game_id}_{self.seat}_{uuid.uuid4().hex}"
        ).replace("-", "_")
        source = self.source_dir / "main.py"
        spec = importlib.util.spec_from_file_location(module_name, source)
        if spec is None or spec.loader is None:
            raise TeacherAdapterError(f"cannot load latest-v1 from {source}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            with source_execution_context(self.source_dir):
                spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        return module

    def decide(self, observation: Any) -> TeacherDecision:
        """Call final ``agent`` exactly once, then immediately drain telemetry."""

        self.call_count += 1
        action: Any = None
        error: BaseException | None = None
        telemetry: Sequence[dict[str, Any]] = ()
        with source_execution_context(self.source_dir):
            try:
                action = self.module.agent(observation)
            except BaseException as exc:  # drain before propagating
                error = exc
            try:
                drained = self.module.drain_cumulative_telemetry()
                telemetry = tuple(drained or ())
            except BaseException as drain_exc:
                if error is None:
                    error = drain_exc
        if error is not None:
            raise TeacherAdapterError(
                f"latest-v1 callback failed after one call: {type(error).__name__}: "
                f"{error}"
            ) from error
        try:
            validated = validate_engine_action(observation, action)
        except (TypeError, ValueError) as exc:
            raise TeacherAdapterError(f"latest-v1 returned invalid action: {exc}") from exc
        if not all(isinstance(row, dict) for row in telemetry):
            raise TeacherAdapterError("telemetry drain returned non-dict rows")
        # ``call_count`` is callback-local for the decision contract.  The
        # adapter's cumulative ``self.call_count`` remains available for audits.
        return TeacherDecision(tuple(validated), tuple(telemetry), 1)
