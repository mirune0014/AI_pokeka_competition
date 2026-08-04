"""Kaggle entry point for the deterministic Mega Lucario rule agent.

The callback keeps raw option indices local to one observation.  Persistent
state stores only public history, semantic transaction plans, and a run-level
fault latch.  Normal MAIN decisions pass through the checked proposal resolver;
bootstrap failures fall back to a deterministic legal containment action.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Optional, Sequence, Tuple


try:
    _MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _MODULE_ROOT = os.getcwd()

for _candidate in (_MODULE_ROOT, "/kaggle_simulations/agent"):
    if _candidate and os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)


try:  # Package imports used by tests.
    from .attack_outcomes import BoundAttackOutcomeTable, build_attack_outcome_table
    from .card_meta import DECK_CARD_IDS
    from .fallback import (
        FallbackDecision,
        fault_containment_action,
        resolve_forced_or_setup,
        safe_fallback,
        validate_live_action,
    )
    from .features import DeckFeatures, build_deck_features, build_resource_ledger
    from .public_effects import PublicEffectRegistry, build_public_effect_registry
    from .resource_ledger import (
        ResourceLedgerError,
        reserve_manual_attach_energy,
        reserve_active_attack_completion_energy,
    )
    from .resolver import Proposal, Resolution, resolve_proposals
    from .routes import (
        enumerate_attack_routes,
        enumerate_active_attack_completion_routes,
        enumerate_basic_bench_routes,
        enumerate_first_turn_riolu_attach_routes,
        enumerate_poke_pad_core_search_routes,
    )
    from .state_view import (
        AreaType,
        OptionType,
        PublicHistoryTracker,
        PublicState,
        SelectContext,
        SemanticOption,
        SemanticOptionKey,
        build_public_state,
        build_semantic_options,
        is_stable_main_state,
        read_field,
    )
    from .telemetry import TelemetryRecorder
    from .transactions import (
        ResumeResult,
        ResumeStatus,
        StartStatus,
        TransactionStore,
    )
except ImportError:  # Flat imports used by Kaggle and the local battle runner.
    from attack_outcomes import BoundAttackOutcomeTable, build_attack_outcome_table
    from card_meta import DECK_CARD_IDS
    from fallback import (
        FallbackDecision,
        fault_containment_action,
        resolve_forced_or_setup,
        safe_fallback,
        validate_live_action,
    )
    from features import DeckFeatures, build_deck_features, build_resource_ledger
    from public_effects import PublicEffectRegistry, build_public_effect_registry
    from resource_ledger import (
        ResourceLedgerError,
        reserve_manual_attach_energy,
        reserve_active_attack_completion_energy,
    )
    from resolver import Proposal, Resolution, resolve_proposals
    from routes import (
        enumerate_attack_routes,
        enumerate_active_attack_completion_routes,
        enumerate_basic_bench_routes,
        enumerate_first_turn_riolu_attach_routes,
        enumerate_poke_pad_core_search_routes,
    )
    from state_view import (
        AreaType,
        OptionType,
        PublicHistoryTracker,
        PublicState,
        SelectContext,
        SemanticOption,
        SemanticOptionKey,
        build_public_state,
        build_semantic_options,
        is_stable_main_state,
        read_field,
    )
    from telemetry import TelemetryRecorder
    from transactions import ResumeResult, ResumeStatus, StartStatus, TransactionStore


_FIXED_DECK = tuple(int(card_id) for card_id in DECK_CARD_IDS)
if len(_FIXED_DECK) != 60:
    raise RuntimeError("Mega Lucario fixed deck must contain exactly 60 cards")
_SETUP_BASIC_CARD_IDS = frozenset((673, 675, 676, 677))


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _raw_options(observation: Any) -> Tuple[Any, ...]:
    select = read_field(observation, "select")
    values = read_field(select, "option", read_field(select, "options", ()))
    if not isinstance(values, Sequence) or isinstance(
        values,
        (str, bytes, bytearray),
    ):
        return ()
    return tuple(values)


def _raw_containment_action(observation: Any) -> list[int]:
    """Return a deterministic minimum-size action without trusting state parsing."""

    select = read_field(observation, "select")
    options = _raw_options(observation)
    min_count = read_field(select, "minCount", 0)
    max_count = read_field(select, "maxCount", 0)
    if (
        not _is_exact_int(min_count)
        or not _is_exact_int(max_count)
        or min_count < 0
        or max_count < min_count
        or min_count > len(options)
    ):
        return []
    if min_count == 0:
        return []

    type_priority = {
        int(OptionType.NO): 0,
        int(OptionType.ATTACK): 1,
        int(OptionType.END): 2,
    }
    ranked = sorted(
        range(len(options)),
        key=lambda index: (
            type_priority.get(read_field(options[index], "type"), 3),
            index,
        ),
    )
    return sorted(ranked[:min_count])


class AgentRuntime:
    """One deterministic runtime instance for one loaded Kaggle agent module."""

    def __init__(
        self,
        *,
        registry: Optional[PublicEffectRegistry] = None,
    ) -> None:
        if registry is not None and not isinstance(registry, PublicEffectRegistry):
            raise ValueError("registry must be a PublicEffectRegistry or None")
        self._registry = registry
        self._telemetry = TelemetryRecorder.off()
        self._game_epoch = -1
        self._history = PublicHistoryTracker()
        self._transactions = TransactionStore()
        self._runtime_fault_latched = False
        self._last_turn: Optional[int] = None
        self._saw_terminal = False
        self._last_features: Optional[DeckFeatures] = None
        self._setup_active_choice: Optional[SemanticOptionKey] = None
        self._begin_game()

    @property
    def game_epoch(self) -> int:
        return self._game_epoch

    @property
    def history(self) -> PublicHistoryTracker:
        return self._history

    @property
    def transactions(self) -> TransactionStore:
        return self._transactions

    @property
    def runtime_fault_latched(self) -> bool:
        return self._runtime_fault_latched

    @property
    def last_features(self) -> Optional[DeckFeatures]:
        return self._last_features

    @property
    def setup_active_choice(self) -> Optional[SemanticOptionKey]:
        return self._setup_active_choice

    def _begin_game(self) -> None:
        self._game_epoch += 1
        self._history = PublicHistoryTracker()
        self._history.begin_game(self._game_epoch)
        self._transactions = TransactionStore()
        self._runtime_fault_latched = False
        self._last_turn = None
        self._saw_terminal = False
        self._last_features = None
        self._setup_active_choice = None

    def _serve_deck(self) -> list[int]:
        self._begin_game()
        return list(_FIXED_DECK)

    def _sync_game_boundary(self, observation: Any) -> None:
        current = read_field(observation, "current")
        turn = read_field(current, "turn")
        result = read_field(current, "result", -1)
        if (
            _is_exact_int(turn)
            and self._last_turn is not None
            and turn < self._last_turn
        ) or (self._saw_terminal and result == -1):
            self._begin_game()

    def _remember_callback(self, state: PublicState) -> None:
        self._last_turn = state.turn
        self._saw_terminal = state.result != -1

    def _get_registry(self) -> PublicEffectRegistry:
        if self._registry is None:
            from cg.api import all_attack, all_card_data

            self._registry = build_public_effect_registry(
                all_card_data(),
                all_attack(),
            )
        return self._registry

    @staticmethod
    def _checked_action(
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        action: Sequence[int],
    ) -> list[int]:
        values = tuple(action)
        reasons = validate_live_action(state, legal_options, values)
        if reasons:
            raise RuntimeError(
                "runtime selected an invalid live action: {0}".format("|".join(reasons))
            )
        return list(values)

    def _record_emitted_attack(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        action: Sequence[int],
    ) -> None:
        selected_attack_ids = tuple(
            legal_options[index].key.attack_id
            for index in action
            if 0 <= index < len(legal_options)
            and legal_options[index].key.option_type == int(OptionType.ATTACK)
            and _is_exact_int(legal_options[index].key.attack_id)
            and int(legal_options[index].key.attack_id) > 0
        )
        if len(selected_attack_ids) == 1:
            self._history.record_emitted_attack(
                state,
                int(selected_attack_ids[0]),
            )

    def _record_setup_active_choice(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        action: Sequence[int],
    ) -> None:
        if state.select_context != int(SelectContext.SETUP_ACTIVE_POKEMON):
            return
        self._setup_active_choice = None
        if len(action) != 1:
            return
        index = action[0]
        if index < 0 or index >= len(legal_options):
            return
        key = legal_options[index].key
        if (
            key.option_type == int(OptionType.CARD)
            and key.player_index == state.seat
            and key.source_zone == int(AreaType.HAND)
            and _is_exact_int(key.card_id)
            and key.card_id in _SETUP_BASIC_CARD_IDS
            and _is_exact_int(key.card_serial)
            and key.card_serial >= 0
        ):
            self._setup_active_choice = key

    def _emit(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        action: Sequence[int],
    ) -> list[int]:
        checked = self._checked_action(state, legal_options, action)
        self._record_setup_active_choice(state, legal_options, checked)
        self._record_emitted_attack(state, legal_options, checked)
        return checked

    def _issue_transaction_resume(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
    ) -> ResumeResult:
        owner_before = self._transactions.owner
        result = self._transactions.resume(state, legal_options)
        self._telemetry.record_transaction(
            state,
            legal_options,
            result,
            owner_before=owner_before,
        )
        return result

    def _issue_resolution(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        proposals: Sequence[Proposal],
        resolution: Resolution,
    ) -> Optional[list[int]]:
        selected = resolution.selected
        if selected is None:
            return None
        if selected.transaction_plan is None:
            if resolution.bound_action is None:
                raise RuntimeError("selected proposal is missing its bound action")
            return self._emit(state, legal_options, resolution.bound_action)

        owner_before = self._transactions.owner
        started = self._transactions.start(
            selected.transaction_plan,
            state,
            legal_options,
        )
        self._telemetry.record_transaction(
            state,
            legal_options,
            started,
            owner_before=owner_before,
            rule_id=selected.rule_id,
        )
        if started.status is not StartStatus.STARTED or started.bound_action is None:
            return None
        return self._emit(state, legal_options, started.bound_action)

    def _forced_action(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        ledger: Any,
        *,
        fault_containment: bool,
    ) -> Optional[list[int]]:
        decision: Optional[FallbackDecision]
        if fault_containment:
            decision = fault_containment_action(
                state,
                legal_options,
                ledger,
                setup_active_choice=self._setup_active_choice,
            )
        else:
            decision = resolve_forced_or_setup(
                state,
                legal_options,
                ledger,
                setup_active_choice=self._setup_active_choice,
            )
        if decision is None:
            return None
        return self._emit(
            state,
            legal_options,
            decision.bind_now(state, legal_options),
        )

    def _safe_main_action(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        ledger: Any,
        *,
        attack_outcomes: Optional[BoundAttackOutcomeTable] = None,
        registry: Optional[PublicEffectRegistry] = None,
    ) -> Optional[list[int]]:
        fallback = safe_fallback(
            state,
            legal_options,
            {},
            ledger,
            attack_outcomes=attack_outcomes,
            registry=registry,
        )
        self._telemetry.record_resolution(
            state,
            legal_options,
            fallback.proposals,
            fallback.resolution,
            ledger,
            decision_source="SAFE_FALLBACK",
        )
        if fallback.resolution.bound_action is None:
            return None
        return self._emit(
            state,
            legal_options,
            fallback.resolution.bound_action,
        )

    def _contained_action(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        ledger: Any,
    ) -> Optional[list[int]]:
        forced = self._forced_action(
            state,
            legal_options,
            ledger,
            fault_containment=True,
        )
        if forced is not None:
            return forced
        if is_stable_main_state(state):
            return self._safe_main_action(state, legal_options, ledger)
        return None

    def _decide_checked(
        self,
        observation: Any,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
    ) -> list[int]:
        ledger = build_resource_ledger(state)

        resume = self._issue_transaction_resume(state, legal_options)
        if resume.bound_action is not None:
            return self._emit(state, legal_options, resume.bound_action)
        if resume.status in (
            ResumeStatus.IRREVERSIBLE_FAULT,
            ResumeStatus.FAULT_CONTAINMENT,
        ):
            contained = self._contained_action(state, legal_options, ledger)
            if contained is not None:
                return contained

        if self._runtime_fault_latched:
            contained = self._contained_action(state, legal_options, ledger)
            if contained is not None:
                return contained

        forced = self._forced_action(
            state,
            legal_options,
            ledger,
            fault_containment=False,
        )
        if forced is not None:
            return forced
        if not is_stable_main_state(state):
            raise RuntimeError("unsupported prompt has no deterministic legal action")

        registry = self._get_registry()
        try:
            self._last_features = build_deck_features(
                state,
                legal_options,
                registry,
            )
        except ValueError:
            self._last_features = None

        attack_outcomes = build_attack_outcome_table(
            state,
            legal_options,
            registry,
        )
        proposals = enumerate_attack_routes(
            state,
            legal_options,
            attack_outcomes,
            registry,
        )
        active_completion_proposals = enumerate_active_attack_completion_routes(
            state,
            legal_options,
            registry,
        )
        if len(active_completion_proposals) == 1:
            completion_cost = active_completion_proposals[
                0
            ].resource_cost.irreversible_refs
            if len(completion_cost) == 1:
                try:
                    reserved_ledger = reserve_active_attack_completion_energy(
                        ledger,
                        completion_cost[0],
                    )
                except ResourceLedgerError:
                    pass
                else:
                    ledger = reserved_ledger
                    proposals += active_completion_proposals
        if self._last_features is not None:
            proposals += enumerate_poke_pad_core_search_routes(
                state,
                legal_options,
                self._last_features,
                attack_outcomes,
                registry,
            )
            attach_proposals = enumerate_first_turn_riolu_attach_routes(
                state,
                legal_options,
                self._last_features,
                registry,
            )
            if len(attach_proposals) == 1:
                attach_cost = attach_proposals[0].resource_cost.irreversible_refs
                if len(attach_cost) == 1:
                    try:
                        reserved_ledger = reserve_manual_attach_energy(
                            ledger,
                            attach_cost[0],
                        )
                    except ResourceLedgerError:
                        pass
                    else:
                        ledger = reserved_ledger
                        proposals += attach_proposals
            proposals += enumerate_basic_bench_routes(
                state,
                legal_options,
                self._last_features,
                registry,
            )
        resolution = resolve_proposals(
            state,
            legal_options,
            ledger,
            proposals,
            registry=registry,
        )
        self._telemetry.record_resolution(
            state,
            legal_options,
            proposals,
            resolution,
            ledger,
        )
        resolved = self._issue_resolution(
            state,
            legal_options,
            proposals,
            resolution,
        )
        if resolved is not None:
            return resolved

        fallback = self._safe_main_action(
            state,
            legal_options,
            ledger,
            attack_outcomes=attack_outcomes,
            registry=registry,
        )
        if fallback is not None:
            return fallback
        raise RuntimeError("stable MAIN prompt has no certified fallback action")

    def act(self, observation: Any) -> list[int]:
        if read_field(observation, "select") is None:
            return self._serve_deck()

        self._sync_game_boundary(observation)
        state: Optional[PublicState] = None
        legal_options: Tuple[SemanticOption, ...] = ()
        try:
            legal_options = build_semantic_options(observation)
            state = build_public_state(
                observation,
                game_epoch=self._game_epoch,
                history_tracker=self._history,
            )
            self._remember_callback(state)
            return self._decide_checked(observation, state, legal_options)
        except Exception as exc:
            self._runtime_fault_latched = True
            if state is not None:
                self._telemetry.record_fault(
                    state,
                    source="AGENT_RUNTIME",
                    code=type(exc).__name__,
                    transaction_state=self._transactions.owner,
                )
                try:
                    ledger = build_resource_ledger(state)
                    contained = self._contained_action(
                        state,
                        legal_options,
                        ledger,
                    )
                    if contained is not None:
                        return contained
                except Exception:
                    pass
            return _raw_containment_action(observation)


_RUNTIME = AgentRuntime()


def agent(observation: dict[str, Any]) -> list[int]:
    return _RUNTIME.act(observation)
