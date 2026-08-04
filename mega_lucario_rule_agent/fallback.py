"""Deterministic, resource-conservative fallback selection.

The normal MAIN surface still flows through certificates and the single
resolver.  Forced, setup, and unsupported effect prompts use a callback-local
semantic decision whose raw option indices are produced only by ``bind_now``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from typing import Mapping, Optional, Sequence, Tuple, Union

try:  # Package import in tests.
    from .attack_outcomes import BoundAttackOutcomeTable
    from .card_meta import get_attack_meta, get_card_meta
    from .certificates import CertificateKind, safe_fallback_proof
    from .damage import BoundDamageTable, DamageResult
    from .public_effects import PublicEffectRegistry
    from .resolver import (
        Proposal,
        Resolution,
        ResolverTier,
        resolve_proposals,
    )
    from .resource_ledger import ResourceLedger
    from .state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SelectContext,
        SemanticOption,
        SemanticOptionKey,
        is_stable_main_state,
        public_state_fingerprint,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import BoundAttackOutcomeTable
    from card_meta import get_attack_meta, get_card_meta
    from certificates import CertificateKind, safe_fallback_proof
    from damage import BoundDamageTable, DamageResult
    from public_effects import PublicEffectRegistry
    from resolver import Proposal, Resolution, ResolverTier, resolve_proposals
    from resource_ledger import ResourceLedger
    from state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SelectContext,
        SemanticOption,
        SemanticOptionKey,
        is_stable_main_state,
        public_state_fingerprint,
    )


_SETUP_ACTIVE_ORDER = {
    676: 0,  # Solrock
    677: 1,  # Riolu
    675: 2,  # Lunatone
    673: 3,  # Makuhita
}
_SETUP_BASIC_CARD_IDS = frozenset(_SETUP_ACTIVE_ORDER)
_SETUP_NORMAL_BENCH_LIMIT = 4
_SETUP_ROLE_BY_CARD_ID = {
    673: "HARIYAMA_LINE",
    674: "HARIYAMA_LINE",
    675: "LUNATONE_ENGINE",
    676: "SOLROCK_ENGINE",
    677: "LUCARIO_LINE",
    678: "LUCARIO_LINE",
}
_RESOURCE_CONSUMING_TYPES = frozenset(
    (
        int(OptionType.PLAY),
        int(OptionType.ATTACH),
        int(OptionType.EVOLVE),
        int(OptionType.ABILITY),
        int(OptionType.DISCARD),
        int(OptionType.RETREAT),
        int(OptionType.SKILL),
    )
)


class FallbackBindError(ValueError):
    """Raised when a semantic fallback cannot bind to the current prompt."""


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _surface_reasons(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
) -> Tuple[str, ...]:
    reasons = []
    if (
        not _is_exact_int(state.min_count)
        or not _is_exact_int(state.max_count)
        or state.min_count < 0
        or state.max_count < state.min_count
    ):
        reasons.append("INVALID_SELECTION_BOUNDS")
    if any(not isinstance(option, SemanticOption) for option in legal_options):
        reasons.append("INVALID_SEMANTIC_OPTION")
        return tuple(sorted(set(reasons)))
    indices = tuple(option.index for option in legal_options)
    exact_indices = tuple(index for index in indices if _is_exact_int(index))
    if len(exact_indices) != len(indices) or any(
        index < 0 or index >= len(legal_options) for index in exact_indices
    ):
        reasons.append("LEGAL_OPTION_INDEX_INVALID")
    if len(set(exact_indices)) != len(exact_indices):
        reasons.append("LEGAL_OPTION_INDEX_COLLISION")
    if set(exact_indices) != set(range(len(legal_options))):
        reasons.append("LEGAL_OPTION_INDEX_SET_INCOMPLETE")
    if _is_exact_int(state.min_count) and state.min_count > len(legal_options):
        reasons.append("INSUFFICIENT_LEGAL_OPTIONS")
    return tuple(sorted(set(reasons)))


def validate_live_action(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    action: Sequence[int],
) -> Tuple[str, ...]:
    """Validate the exact action vector accepted by the engine callback."""

    reasons = list(_surface_reasons(state, legal_options))
    try:
        values = tuple(action)
    except TypeError:
        return tuple(sorted(set(reasons + ["ACTION_NOT_A_SEQUENCE"])))
    exact_values = tuple(value for value in values if _is_exact_int(value))
    if len(exact_values) != len(values):
        reasons.append("ACTION_INDEX_INVALID")
    if len(set(exact_values)) != len(exact_values):
        reasons.append("ACTION_INDEX_DUPLICATE")
    if any(value < 0 or value >= len(legal_options) for value in exact_values):
        reasons.append("ACTION_INDEX_OUT_OF_RANGE")
    if _is_exact_int(state.min_count) and len(values) < state.min_count:
        reasons.append("ACTION_BELOW_MIN_COUNT")
    if _is_exact_int(state.max_count) and len(values) > state.max_count:
        reasons.append("ACTION_ABOVE_MAX_COUNT")
    return tuple(sorted(set(reasons)))


@dataclass(frozen=True)
class FallbackDecision:
    """A semantic decision with no persisted raw option index."""

    choices: Tuple[SemanticOptionKey, ...]
    reason_code: str
    order_sensitive: bool = False
    unsupported_effect: bool = False
    fault_containment: bool = False
    proposal: Optional[Proposal] = None

    def __post_init__(self) -> None:
        choices = tuple(self.choices)
        if any(not isinstance(choice, SemanticOptionKey) for choice in choices):
            raise ValueError("fallback choices must be SemanticOptionKey values")
        if (
            not isinstance(self.reason_code, str)
            or not self.reason_code
            or self.reason_code != self.reason_code.strip()
        ):
            raise ValueError("fallback reason_code must be a non-empty trimmed string")
        if not isinstance(self.order_sensitive, bool):
            raise ValueError("order_sensitive must be boolean")
        if not isinstance(self.unsupported_effect, bool):
            raise ValueError("unsupported_effect must be boolean")
        if not isinstance(self.fault_containment, bool):
            raise ValueError("fault_containment must be boolean")
        if self.proposal is not None:
            if not isinstance(self.proposal, Proposal):
                raise ValueError("fallback proposal must be a Proposal")
            if self.proposal.action_spec != self.action_spec:
                raise ValueError("fallback proposal action does not match its choices")
        object.__setattr__(self, "choices", choices)

    @property
    def action_spec(self) -> ActionSpec:
        return ActionSpec(self.choices, order_sensitive=self.order_sensitive)

    def bind_now(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
    ) -> Tuple[int, ...]:
        """Bind using only the current callback, including duplicate semantics."""

        surface_reasons = _surface_reasons(state, legal_options)
        if surface_reasons:
            raise FallbackBindError("|".join(surface_reasons))
        remaining = list(legal_options)
        bound = []
        for choice in self.choices:
            hits = sorted(
                (option for option in remaining if option.key == choice),
                key=lambda option: option.index,
            )
            if not hits:
                raise FallbackBindError("SEMANTIC_CHOICE_NOT_FOUND")
            selected = hits[0]
            bound.append(selected.index)
            remaining.remove(selected)
        if not self.order_sensitive:
            bound.sort()
        reasons = validate_live_action(state, legal_options, bound)
        if reasons:
            raise FallbackBindError("|".join(reasons))
        return tuple(bound)


@dataclass(frozen=True)
class FallbackOutcome:
    decision: Optional[FallbackDecision]
    proposals: Tuple[Proposal, ...]
    resolution: Resolution
    reasons: Tuple[str, ...]


def _key_ref(key: SemanticOptionKey) -> Optional[PhysicalRef]:
    values = (key.card_id, key.card_serial, key.player_index, key.source_zone)
    if (
        any(not _is_exact_int(value) for value in values)
        or int(key.card_id) <= 0
        or int(key.card_serial) < 0
        or int(key.player_index) not in (0, 1)
        or int(key.source_zone) <= 0
    ):
        return None
    return PhysicalRef(
        card_id=int(key.card_id),
        serial=int(key.card_serial),
        owner=int(key.player_index),
        zone=int(key.source_zone),
        lineage_serial=int(key.card_serial),
    )


def _reservation_rank(key: SemanticOptionKey, ledger: ResourceLedger) -> int:
    ref_value = _key_ref(key)
    return int(ref_value is not None and ledger.is_hard_reserved(ref_value))


def _generic_rank(
    option: SemanticOption,
    ledger: ResourceLedger,
) -> Tuple[object, ...]:
    key = option.key
    return (
        _reservation_rank(key, ledger),
        int(key.option_type in _RESOURCE_CONSUMING_TYPES),
        key.sort_key(),
        option.index,
    )


def _setup_rank(option: SemanticOption) -> Tuple[object, ...]:
    key = option.key
    return (
        _SETUP_ACTIVE_ORDER.get(key.card_id, len(_SETUP_ACTIVE_ORDER)),
        key.card_id if _is_exact_int(key.card_id) else 2**63 - 1,
        key.card_serial if _is_exact_int(key.card_serial) else 2**63 - 1,
        key.sort_key(),
        option.index,
    )


def _setup_choice_identity(
    key: Optional[SemanticOptionKey],
    seat: int,
) -> Optional[Tuple[int, int, int, int]]:
    """Return an exact own setup-Basic identity or fail closed."""

    if key is None or not isinstance(key, SemanticOptionKey):
        return None
    values = (key.card_id, key.card_serial, key.player_index, key.source_zone)
    if any(not _is_exact_int(value) for value in values):
        return None
    if (
        key.option_type != int(OptionType.CARD)
        or key.player_index != seat
        or key.source_zone != int(AreaType.HAND)
        or key.card_id not in _SETUP_BASIC_CARD_IDS
        or key.card_serial < 0
    ):
        return None
    return (
        int(key.card_id),
        int(key.card_serial),
        int(key.player_index),
        int(key.source_zone),
    )


def _setup_candidate_options(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
) -> Tuple[SemanticOption, ...]:
    """Bind legal setup candidates to exact cards in the public own hand."""

    hand_identities = {
        (
            ref_value.card_id,
            ref_value.serial,
            ref_value.owner,
            ref_value.zone,
        )
        for ref_value in state.own.hand_refs
        if ref_value.card_id in _SETUP_BASIC_CARD_IDS
    }
    selected = []
    seen = set()
    for option in sorted(legal_options, key=_setup_rank):
        identity = _setup_choice_identity(option.key, state.seat)
        if identity is None or identity not in hand_identities or identity in seen:
            continue
        seen.add(identity)
        selected.append(option)
    return tuple(selected)


def _setup_visible_active_identity(
    state: PublicState,
) -> Optional[Tuple[int, int, int, int]]:
    visible = tuple(
        pokemon.ref
        for pokemon in state.own.active
        if (
            pokemon.ref.card_id in _SETUP_BASIC_CARD_IDS
            and _is_exact_int(pokemon.ref.serial)
            and pokemon.ref.owner == state.seat
            and pokemon.ref.zone == int(AreaType.ACTIVE)
        )
    )
    if len(visible) != 1:
        return None
    ref_value = visible[0]
    return (
        int(ref_value.card_id),
        int(ref_value.serial),
        int(ref_value.owner),
        int(AreaType.HAND),
    )


def _setup_active_card_id(
    state: PublicState,
    setup_active_choice: Optional[SemanticOptionKey],
) -> Optional[int]:
    cached = _setup_choice_identity(setup_active_choice, state.seat)
    visible = _setup_visible_active_identity(state)
    if cached is not None and visible is not None and cached[:3] != visible[:3]:
        return None
    identity = cached if cached is not None else visible
    return None if identity is None else int(identity[0])


def _setup_role(card_id: Optional[int]) -> Optional[str]:
    if not _is_exact_int(card_id):
        return None
    return _SETUP_ROLE_BY_CARD_ID.get(int(card_id))


def _setup_boardout_rank(
    option: SemanticOption,
    occupied_roles: frozenset[str],
) -> Tuple[object, ...]:
    key = option.key
    role = _setup_role(key.card_id)
    meta = get_card_meta(key.card_id) if _is_exact_int(key.card_id) else None
    hp = meta.hp if meta is not None and _is_exact_int(meta.hp) else 0
    return (
        int(role is None or role in occupied_roles),
        -int(hp),
        key.card_id if _is_exact_int(key.card_id) else 2**63 - 1,
        key.card_serial if _is_exact_int(key.card_serial) else 2**63 - 1,
        key.sort_key(),
        option.index,
    )


def _setup_bench_decision(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    setup_active_choice: Optional[SemanticOptionKey],
) -> FallbackDecision:
    """Build a role-aware initial Bench from exact own public identities."""

    candidates = list(_setup_candidate_options(state, legal_options))
    active_card_id = _setup_active_card_id(state, setup_active_choice)
    existing_card_ids = tuple(
        pokemon.ref.card_id
        for pokemon in state.own.bench
        if _is_exact_int(pokemon.ref.card_id)
    )
    occupied_card_ids = tuple(
        value for value in (active_card_id,) + existing_card_ids if _is_exact_int(value)
    )
    occupied_roles = {
        role
        for role in (_setup_role(value) for value in occupied_card_ids)
        if role is not None
    }

    physical_slots = max(0, state.own.bench_max - len(state.own.bench))
    prompt_capacity = min(state.max_count, len(legal_options))
    normal_capacity = min(
        prompt_capacity,
        physical_slots,
        max(0, _SETUP_NORMAL_BENCH_LIMIT - len(state.own.bench)),
    )
    chosen = []

    def take_card(card_id: int) -> bool:
        if len(chosen) >= normal_capacity:
            return False
        for index, option in enumerate(candidates):
            if option.key.card_id == card_id:
                chosen.append(option)
                candidates.pop(index)
                occupied_roles.add(_SETUP_ROLE_BY_CARD_ID[card_id])
                return True
        return False

    # When the cached Active is unavailable or conflicts with a visible Active,
    # do not speculate about roles. The board-out guard below remains valid.
    if active_card_id is not None:
        if active_card_id == 676:
            engine_order = (675,)
        elif active_card_id == 675:
            engine_order = (676,)
        else:
            engine_order = (676, 675)
        for card_id in engine_order:
            if _setup_role(card_id) not in occupied_roles:
                take_card(card_id)

        if "LUCARIO_LINE" not in occupied_roles:
            take_card(677)

    conceptual_active_count = max(
        state.own.active_slot_count,
        int(active_card_id is not None),
    )
    if (
        conceptual_active_count + len(state.own.bench) + len(chosen) < 2
        and len(chosen) < normal_capacity
        and candidates
    ):
        boardout = min(
            candidates,
            key=lambda option: _setup_boardout_rank(
                option,
                frozenset(occupied_roles),
            ),
        )
        chosen.append(boardout)
        candidates.remove(boardout)
        role = _setup_role(boardout.key.card_id)
        if role is not None:
            occupied_roles.add(role)

    if active_card_id is not None and "HARIYAMA_LINE" not in occupied_roles:
        take_card(673)

    # A second Riolu is deliberately held during the hidden-information setup
    # prompt. It is promoted only by a later public spread/high-damage rule.

    # Engine minCount is authoritative. Fill it without treating unknown or
    # duplicate cards as strategic choices, and never persist raw indices.
    mandatory_target = min(state.min_count, prompt_capacity)
    if len(chosen) < mandatory_target:
        remaining = [option for option in legal_options if option not in chosen]
        remaining.sort(
            key=lambda option: (
                int(option not in candidates),
                _setup_boardout_rank(option, frozenset(occupied_roles)),
            )
        )
        chosen.extend(remaining[: mandatory_target - len(chosen)])

    if not chosen:
        return FallbackDecision((), "SETUP_BENCH_ROLE_HOLD")
    return FallbackDecision(
        tuple(option.key for option in chosen),
        "SETUP_BENCH_ROLE_PLAN",
    )


def _promotion_rank(
    state: PublicState,
    option: SemanticOption,
) -> Tuple[object, ...]:
    key = option.key
    meta = get_card_meta(key.card_id) if _is_exact_int(key.card_id) else None
    prize_value = (
        meta.prize_value if meta is not None and _is_exact_int(meta.prize_value) else 99
    )
    serial = key.card_serial if _is_exact_int(key.card_serial) else None
    pokemon = next(
        (
            value
            for value in state.own.active + state.own.bench
            if serial is not None and serial in (value.ref.serial, value.lineage_serial)
        ),
        None,
    )
    energy_count = len(pokemon.energy_refs) if pokemon is not None else 0
    costs = tuple(
        len(attack.energy_cost)
        for attack_id in (() if meta is None else meta.attack_ids)
        for attack in (get_attack_meta(attack_id),)
        if attack is not None
    )
    minimum_cost = min(costs) if costs else None
    ready_one_prize = (
        prize_value == 1 and minimum_cost is not None and energy_count >= minimum_cost
    )
    mega_in_hand = any(ref_value.card_id == 678 for ref_value in state.own.hand_refs)
    evolvable_riolu = (
        key.card_id == 677
        and mega_in_hand
        and pokemon is not None
        and not pokemon.appear_this_turn
    )
    if ready_one_prize:
        category = 0
    elif evolvable_riolu:
        category = 1
    elif key.card_id != 678:
        category = 2
    else:
        category = 3
    remaining_hp = pokemon.remaining_hp if pokemon is not None else 0
    return (
        category,
        int(prize_value),
        -remaining_hp,
        -energy_count,
        key.card_id if _is_exact_int(key.card_id) else 2**63 - 1,
        serial if serial is not None else 2**63 - 1,
        key.sort_key(),
        option.index,
    )


def _decision_from_options(
    options: Sequence[SemanticOption],
    count: int,
    reason_code: str,
    rank,
    *,
    unsupported_effect: bool,
) -> FallbackDecision:
    ordered = tuple(sorted(options, key=rank))
    return FallbackDecision(
        choices=tuple(option.key for option in ordered[:count]),
        reason_code=reason_code,
        unsupported_effect=unsupported_effect,
    )


def resolve_forced_or_setup(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    *,
    setup_active_choice: Optional[SemanticOptionKey] = None,
) -> Optional[FallbackDecision]:
    """Resolve setup or a mandatory non-MAIN prompt without starting effects."""

    if not isinstance(ledger, ResourceLedger):
        raise ValueError("forced/setup fallback requires a ResourceLedger")
    if is_stable_main_state(state) or _surface_reasons(state, legal_options):
        return None
    option_values = tuple(legal_options)
    if not option_values:
        if state.min_count == 0:
            return FallbackDecision(
                (), "EMPTY_OPTIONAL_PROMPT", unsupported_effect=True
            )
        return None

    if state.select_context == int(SelectContext.IS_FIRST):
        yes = tuple(
            option
            for option in option_values
            if option.key.option_type == int(OptionType.YES)
        )
        if yes:
            return _decision_from_options(
                yes,
                1,
                "SETUP_CHOOSE_FIRST",
                lambda option: (option.key.sort_key(), option.index),
                unsupported_effect=False,
            )

    if state.select_context == int(SelectContext.SETUP_ACTIVE_POKEMON):
        return _decision_from_options(
            option_values,
            state.min_count,
            "SETUP_ACTIVE_PRIORITY",
            _setup_rank,
            unsupported_effect=False,
        )

    if state.select_context == int(SelectContext.SETUP_BENCH_POKEMON):
        return _setup_bench_decision(
            state,
            option_values,
            setup_active_choice,
        )

    if state.min_count == 0:
        return FallbackDecision(
            (), "UNSUPPORTED_OPTIONAL_SKIP", unsupported_effect=True
        )
    if len(option_values) == 1:
        return FallbackDecision(
            (option_values[0].key,),
            "UNIQUE_LEGAL_ACTION",
            unsupported_effect=True,
        )

    no_options = tuple(
        option
        for option in option_values
        if option.key.option_type == int(OptionType.NO)
    )
    if no_options and state.min_count == 1:
        return _decision_from_options(
            no_options,
            1,
            "UNSUPPORTED_EFFECT_DECLINE",
            lambda option: (option.key.sort_key(), option.index),
            unsupported_effect=True,
        )

    end_options = tuple(
        option
        for option in option_values
        if option.key.option_type == int(OptionType.END)
    )
    if end_options and state.min_count == 1:
        return _decision_from_options(
            end_options,
            1,
            "UNSUPPORTED_EFFECT_END",
            lambda option: (option.key.sort_key(), option.index),
            unsupported_effect=True,
        )

    if state.select_context in (
        int(SelectContext.SWITCH),
        int(SelectContext.TO_ACTIVE),
    ):
        return _decision_from_options(
            option_values,
            state.min_count,
            "FORCED_PROMOTION_LOWEST_LIABILITY",
            lambda option: _promotion_rank(state, option),
            unsupported_effect=True,
        )

    return _decision_from_options(
        option_values,
        state.min_count,
        "UNSUPPORTED_MANDATORY_MINIMUM",
        lambda option: _generic_rank(option, ledger),
        unsupported_effect=True,
    )


def fault_containment_action(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    *,
    setup_active_choice: Optional[SemanticOptionKey] = None,
) -> Optional[FallbackDecision]:
    """Choose a legal conservative response without clearing the fault latch."""

    decision = resolve_forced_or_setup(
        state,
        legal_options,
        ledger,
        setup_active_choice=setup_active_choice,
    )
    if decision is None:
        return None
    return replace(
        decision,
        reason_code="IRREVERSIBLE_FAULT:{0}".format(decision.reason_code),
        unsupported_effect=True,
        fault_containment=True,
        proposal=None,
    )


def _normalize_damage_table(
    state: PublicState,
    damage_table: Union[Mapping[int, DamageResult], BoundDamageTable],
) -> Tuple[Mapping[int, DamageResult], Tuple[str, ...]]:
    """Validate legacy target-only rows without granting outcome authority."""

    if isinstance(damage_table, BoundDamageTable):
        values = damage_table.as_dict()
        active = state.opponent_active
        current = damage_table.state_fingerprint == public_state_fingerprint(
            state
        ) and damage_table.target_ref == (None if active is None else active.ref)
        reasons = [] if current else ["DAMAGE_TABLE_STATE_STALE"]
    elif isinstance(damage_table, Mapping):
        values = damage_table
        reasons = ["DAMAGE_TABLE_UNBOUND"] if values else []
    else:
        raise ValueError("damage_table must be a mapping or BoundDamageTable")
    for attack_id, result in values.items():
        if not _is_exact_int(attack_id) or attack_id <= 0:
            raise ValueError("damage table keys must be positive exact attack IDs")
        if not isinstance(result, DamageResult) or result.attack_id != attack_id:
            raise ValueError("damage table entries must match their attack ID")
    if values:
        reasons.append("LEGACY_TARGET_ONLY_DAMAGE_UNTRUSTED")
    return values, tuple(sorted(set(reasons)))


def safe_fallback(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    damage_table: Union[Mapping[int, DamageResult], BoundDamageTable],
    ledger: ResourceLedger,
    *,
    attack_outcomes: Optional[BoundAttackOutcomeTable] = None,
    registry: Optional[PublicEffectRegistry] = None,
) -> FallbackOutcome:
    """Resolve stable-MAIN ATTACK > PASS without trusting target-only damage."""

    if not isinstance(ledger, ResourceLedger):
        raise ValueError("safe_fallback requires a ResourceLedger")
    _, damage_reasons = _normalize_damage_table(
        state,
        damage_table,
    )
    construction_reasons = list(damage_reasons)
    outcomes_are_current = False
    if attack_outcomes is not None:
        if not isinstance(attack_outcomes, BoundAttackOutcomeTable):
            raise ValueError(
                "attack_outcomes must be a BoundAttackOutcomeTable or None"
            )
        if registry is None:
            construction_reasons.append("ATTACK_OUTCOME_REGISTRY_REQUIRED")
        elif not isinstance(registry, PublicEffectRegistry):
            raise ValueError("registry must be a PublicEffectRegistry or None")
        elif attack_outcomes.build_unknown_reasons or not attack_outcomes.matches(
            state, legal_options, registry
        ):
            construction_reasons.append("ATTACK_OUTCOME_TABLE_BINDING_MISMATCH")
        else:
            outcomes_are_current = True
    proposals = []
    if not is_stable_main_state(state):
        construction_reasons.append("UNSTABLE_MAIN_STATE")
    else:
        counts = Counter(option.key for option in legal_options)
        attack_options = tuple(
            option
            for option in legal_options
            if option.key.option_type == int(OptionType.ATTACK)
            and option.key.player_index == state.seat
            and _is_exact_int(option.key.attack_id)
            and option.key.attack_id > 0
        )
        unique_attacks = tuple(
            option for option in attack_options if counts[option.key] == 1
        )
        if len(unique_attacks) != len(attack_options):
            construction_reasons.append("DUPLICATE_SEMANTIC_ATTACK")
        exact_knockouts = tuple(
            option
            for option in unique_attacks
            if outcomes_are_current
            and (
                attack_outcomes.get_for_option(option.key)
                if attack_outcomes is not None
                else None
            )
            is not None
            and attack_outcomes.get_for_option(option.key).exact_ko
        )
        selected_attacks = exact_knockouts or unique_attacks
        for option in selected_attacks:
            attack_id = int(option.key.attack_id)
            prefix = "EXACT_KO" if exact_knockouts else "LEGAL"
            rule_id = "FALLBACK_{0}_ATTACK_{1}".format(prefix, attack_id)
            action_spec = ActionSpec.single(option.key)
            proof = safe_fallback_proof(
                state,
                legal_options,
                action_spec,
                rule_id,
            )
            proposals.append(
                Proposal(
                    rule_id=rule_id,
                    tier=ResolverTier.RESOURCE_PRESERVING_FALLBACK,
                    action_spec=action_spec,
                    certificate_kind=CertificateKind.SAFE_FALLBACK,
                    proof=proof,
                    deterministic_tiebreak=(int(OptionType.ATTACK), attack_id),
                )
            )

        if not selected_attacks:
            end_options = tuple(
                option
                for option in legal_options
                if option.key.option_type == int(OptionType.END)
                and option.key.player_index == state.seat
            )
            unique_ends = tuple(
                option for option in end_options if counts[option.key] == 1
            )
            if len(unique_ends) != len(end_options):
                construction_reasons.append("DUPLICATE_SEMANTIC_END")
            for option in unique_ends:
                rule_id = "FALLBACK_PASS"
                action_spec = ActionSpec.single(option.key)
                proof = safe_fallback_proof(
                    state,
                    legal_options,
                    action_spec,
                    rule_id,
                )
                proposals.append(
                    Proposal(
                        rule_id=rule_id,
                        tier=ResolverTier.PASS,
                        action_spec=action_spec,
                        certificate_kind=CertificateKind.SAFE_FALLBACK,
                        proof=proof,
                        deterministic_tiebreak=(int(OptionType.END),),
                    )
                )

    resolution = resolve_proposals(state, legal_options, ledger, proposals)
    for rejection in resolution.rejections:
        construction_reasons.extend(
            "RESOLVER_REJECTED:{0}:{1}".format(rejection.rule_id, reason)
            for reason in rejection.reasons
        )
    decision = None
    if resolution.selected is not None:
        decision = FallbackDecision(
            choices=resolution.selected.action_spec.choices,
            reason_code=resolution.selected.rule_id,
            order_sensitive=resolution.selected.action_spec.order_sensitive,
            proposal=resolution.selected,
        )
    if decision is None and not construction_reasons:
        construction_reasons.append("NO_SAFE_FALLBACK_ACTION")
    return FallbackOutcome(
        decision=decision,
        proposals=tuple(proposals),
        resolution=resolution,
        reasons=tuple(sorted(set(construction_reasons))),
    )


__all__ = [
    "FallbackBindError",
    "FallbackDecision",
    "FallbackOutcome",
    "fault_containment_action",
    "resolve_forced_or_setup",
    "safe_fallback",
    "validate_live_action",
]
