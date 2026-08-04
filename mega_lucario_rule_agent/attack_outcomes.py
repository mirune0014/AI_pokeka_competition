"""State-bound, fail-closed attack outcome evaluation.

The legacy :mod:`damage` module intentionally certifies target damage only.
This module composes the public state, semantic legal surface, checked card
catalog, attack history, post-attack effects, and Prize exchange into a single
immutable preview.  Exactness is tracked per component so that a known target
damage value can never be mistaken for a complete win or Prize certificate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field
import re
from typing import Iterable, Optional, Sequence, Tuple

try:  # Package import in tests.
    from .card_meta import (
        ATTACK_META_BY_ID,
        AttackCallbackKind,
        AttackCondition,
    )
    from .public_effects import (
        EFFECT_BINDINGS,
        CombatCardProfile,
        EntryKind,
        PublicEffectRegistry,
    )
    from .state_view import (
        AreaType,
        OptionType,
        PhysicalRef,
        PokemonView,
        PublicState,
        SemanticOption,
        SemanticOptionKey,
        is_checked_public_state,
        is_stable_main_state,
        public_state_fingerprint,
        semantic_options_fingerprint,
    )
except ImportError:  # Flat submission import from main.py.
    from card_meta import (  # type: ignore[no-redef]
        ATTACK_META_BY_ID,
        AttackCallbackKind,
        AttackCondition,
    )
    from public_effects import (  # type: ignore[no-redef]
        EFFECT_BINDINGS,
        CombatCardProfile,
        EntryKind,
        PublicEffectRegistry,
    )
    from state_view import (  # type: ignore[no-redef]
        AreaType,
        OptionType,
        PhysicalRef,
        PokemonView,
        PublicState,
        SemanticOption,
        SemanticOptionKey,
        is_checked_public_state,
        is_stable_main_state,
        public_state_fingerprint,
        semantic_options_fingerprint,
    )


FIGHTING_ENERGY_TYPE = 6
METAL_ENERGY_TYPE = 8
PPP_DAMAGE_BONUS = 30
RESISTANCE_REDUCTION = 30
FIELD_DAMAGE_REDUCTION = 30
SPIKY_ENERGY_DAMAGE = 20
SPIKY_ENERGY_DAMAGE_COUNTERS = 2
MAX_PPP_COUNT = 4
LILLIES_POKEMON_CARD_IDS = frozenset((272, 278, 279, 280))
STEVENS_POKEMON_CARD_IDS = frozenset((635, 636, 637, 638, 639, 640, 641))


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _canonical_reasons(values: Iterable[str]) -> Tuple[str, ...]:
    rows = tuple(values)
    if any(not isinstance(value, str) or not value for value in rows):
        raise ValueError("unknown reasons must be nonempty strings")
    return tuple(sorted(set(rows)))


@dataclass(frozen=True)
class AttackCallbackPreview:
    """Exact public choice surface created by a post-attack callback."""

    kind: AttackCallbackKind
    source_basic_energy_card_id: int
    max_count: int
    available_source_refs: Tuple[PhysicalRef, ...]
    eligible_target_refs: Tuple[PhysicalRef, ...]
    requires_selection: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AttackCallbackKind):
            raise ValueError("callback kind must be registered")
        if (
            not _is_exact_int(self.source_basic_energy_card_id)
            or self.source_basic_energy_card_id <= 0
            or not _is_exact_int(self.max_count)
            or self.max_count <= 0
        ):
            raise ValueError("callback source and limit must be positive exact ints")
        if not isinstance(self.requires_selection, bool):
            raise ValueError("callback selection flag must be an exact bool")
        for refs in (self.available_source_refs, self.eligible_target_refs):
            if not isinstance(refs, tuple) or any(
                not isinstance(ref_value, PhysicalRef) for ref_value in refs
            ):
                raise ValueError("callback refs must be PhysicalRef tuples")
            if tuple(sorted(refs, key=lambda ref_value: ref_value.sort_key())) != refs:
                raise ValueError("callback refs must be deterministically sorted")
            if len(set(refs)) != len(refs):
                raise ValueError("callback refs cannot repeat")
        expected_selection = bool(
            self.available_source_refs and self.eligible_target_refs
        )
        if self.requires_selection != expected_selection:
            raise ValueError("callback selection flag must match its public choices")


_ATTACK_OUTCOME_ISSUER_TOKEN = object()


@dataclass(frozen=True)
class AttackOutcome:
    """A component-wise exact preview for one unique ATTACK semantic option."""

    option_key: SemanticOptionKey
    attack_id: int
    attacker_ref: PhysicalRef
    target_ref: PhysicalRef
    _legality_exact: bool
    legal: Optional[bool]
    payable: Optional[bool]
    _damage_exact: bool
    base_damage: int
    ppp_count: Optional[int]
    ppp_bonus: Optional[int]
    before_weakness: Optional[int]
    weakness_multiplier: Optional[int]
    resistance_reduction: Optional[int]
    after_weakness_resistance: Optional[int]
    field_reduction: Optional[int]
    damage_before_prevention: Optional[int]
    damage_before_ko_prevention: Optional[int]
    final_damage: Optional[int]
    target_starting_hp: int
    target_hp_loss: Optional[int]
    target_hp_after: Optional[int]
    knockout: Optional[bool]
    prevention_effects: Tuple[str, ...]
    _post_attack_exact: bool
    attacker_starting_hp: int
    attacker_attack_effect_damage: Optional[int]
    attacker_damage_counters_placed: Optional[int]
    attacker_damage: Optional[int]
    attacker_hp_after: Optional[int]
    attacker_knockout: Optional[bool]
    callback: Optional[AttackCallbackPreview]
    next_turn_lock_applied: Optional[bool]
    _prize_exact: bool
    prizes_taken: Optional[int]
    opponent_prizes_taken: Optional[int]
    own_prizes_after: Optional[int]
    opponent_prizes_after: Optional[int]
    _terminal_exact: bool
    wins_game: Optional[bool]
    loses_game: Optional[bool]
    draws_game: Optional[bool]
    triggered_effects: Tuple[str, ...]
    legality_unknown_reasons: Tuple[str, ...]
    damage_unknown_reasons: Tuple[str, ...]
    prize_unknown_reasons: Tuple[str, ...]
    post_attack_unknown_reasons: Tuple[str, ...]
    terminal_unknown_reasons: Tuple[str, ...]
    _issuer_token: object = dataclass_field(
        init=False,
        default=None,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(self.option_key, SemanticOptionKey):
            raise ValueError("attack outcome requires a semantic option key")
        if (
            not _is_exact_int(self.attack_id)
            or self.attack_id <= 0
            or self.option_key.attack_id != self.attack_id
            or self.option_key.option_type != int(OptionType.ATTACK)
        ):
            raise ValueError("attack outcome key must match a positive ATTACK ID")
        if not isinstance(self.attacker_ref, PhysicalRef) or not isinstance(
            self.target_ref, PhysicalRef
        ):
            raise ValueError(
                "attack outcome requires physical attacker and target refs"
            )
        exact_flags = (
            self._legality_exact,
            self._damage_exact,
            self._post_attack_exact,
            self._prize_exact,
            self._terminal_exact,
        )
        if any(not isinstance(value, bool) for value in exact_flags):
            raise ValueError("attack exactness flags must be exact bools")
        if any(
            value is not None and not isinstance(value, bool)
            for value in (
                self.legal,
                self.payable,
                self.knockout,
                self.attacker_knockout,
                self.next_turn_lock_applied,
                self.wins_game,
                self.loses_game,
                self.draws_game,
            )
        ):
            raise ValueError("attack truth values must be exact bools or None")
        numeric_values = (
            self.base_damage,
            self.ppp_count,
            self.ppp_bonus,
            self.before_weakness,
            self.weakness_multiplier,
            self.resistance_reduction,
            self.after_weakness_resistance,
            self.field_reduction,
            self.damage_before_prevention,
            self.damage_before_ko_prevention,
            self.final_damage,
            self.target_starting_hp,
            self.target_hp_loss,
            self.target_hp_after,
            self.attacker_starting_hp,
            self.attacker_attack_effect_damage,
            self.attacker_damage_counters_placed,
            self.attacker_damage,
            self.attacker_hp_after,
            self.prizes_taken,
            self.opponent_prizes_taken,
            self.own_prizes_after,
            self.opponent_prizes_after,
        )
        if any(
            value is not None and (not _is_exact_int(value) or value < 0)
            for value in numeric_values
        ):
            raise ValueError("attack numeric values must be nonnegative exact ints")
        if self.target_starting_hp <= 0 or self.attacker_starting_hp <= 0:
            raise ValueError("attack endpoints must start with positive HP")
        for name in (
            "prevention_effects",
            "triggered_effects",
            "legality_unknown_reasons",
            "damage_unknown_reasons",
            "prize_unknown_reasons",
            "post_attack_unknown_reasons",
            "terminal_unknown_reasons",
        ):
            values = getattr(self, name)
            if not isinstance(values, tuple) or tuple(sorted(set(values))) != values:
                raise ValueError(f"{name} must be a sorted unique tuple")
            _canonical_reasons(values)
        if self.callback is not None and not isinstance(
            self.callback, AttackCallbackPreview
        ):
            raise ValueError("attack callback must be a checked preview")
        if self._legality_exact != (not self.legality_unknown_reasons):
            raise ValueError("legality exactness must match its reasons")
        if self._damage_exact != (not self.damage_unknown_reasons):
            raise ValueError("damage exactness must match its reasons")
        if self._prize_exact != (not self.prize_unknown_reasons):
            raise ValueError("Prize exactness must match its reasons")
        if self._post_attack_exact != (not self.post_attack_unknown_reasons):
            raise ValueError("post-attack exactness must match its reasons")
        if self._terminal_exact != (not self.terminal_unknown_reasons):
            raise ValueError("terminal exactness must match its reasons")
        if self._legality_exact and (self.legal is None or self.payable is None):
            raise ValueError("exact legality requires legal and payable values")
        if not self._legality_exact and (
            self.legal is not None or self.payable is not None
        ):
            raise ValueError("unknown legality cannot publish legal or payable values")
        damage_outputs = (
            self.ppp_bonus,
            self.before_weakness,
            self.weakness_multiplier,
            self.resistance_reduction,
            self.after_weakness_resistance,
            self.field_reduction,
            self.damage_before_prevention,
            self.damage_before_ko_prevention,
            self.final_damage,
            self.target_hp_loss,
            self.target_hp_after,
            self.knockout,
        )
        if self._damage_exact and any(value is None for value in damage_outputs):
            raise ValueError("exact damage requires a complete numeric trace")
        if not self._damage_exact and any(value is not None for value in damage_outputs):
            raise ValueError("unknown damage cannot publish a partial exact trace")
        if self._damage_exact and (
            not self._legality_exact
            or self.legal is not True
            or self.payable is not True
        ):
            raise ValueError("exact damage requires an exact legal payable attack")
        post_outputs = (
            self.attacker_attack_effect_damage,
            self.attacker_damage_counters_placed,
            self.attacker_damage,
            self.attacker_hp_after,
            self.attacker_knockout,
            self.next_turn_lock_applied,
        )
        if self._post_attack_exact and any(value is None for value in post_outputs):
            raise ValueError("exact post-attack state requires complete outputs")
        prize_outputs = (
            self.prizes_taken,
            self.opponent_prizes_taken,
            self.own_prizes_after,
            self.opponent_prizes_after,
        )
        if self._prize_exact and any(value is None for value in prize_outputs):
            raise ValueError("exact Prize state requires complete outputs")
        if not self._prize_exact and any(value is not None for value in prize_outputs):
            raise ValueError("unknown Prize state cannot publish exact outputs")
        terminal_outputs = (self.wins_game, self.loses_game, self.draws_game)
        if self._terminal_exact and any(value is None for value in terminal_outputs):
            raise ValueError("exact terminal state requires complete outputs")
        if not self._terminal_exact and any(value is not None for value in terminal_outputs):
            raise ValueError("unknown terminal state cannot publish exact outputs")

    @property
    def authoritative(self) -> bool:
        return self._issuer_token is _ATTACK_OUTCOME_ISSUER_TOKEN

    @property
    def legality_exact(self) -> bool:
        return self.authoritative and self._legality_exact

    @property
    def exact_damage(self) -> bool:
        return self.authoritative and self._damage_exact

    @property
    def post_attack_exact(self) -> bool:
        return self.authoritative and self._post_attack_exact

    @property
    def prize_exact(self) -> bool:
        return self.authoritative and self._prize_exact

    @property
    def terminal_exact(self) -> bool:
        return self.authoritative and self._terminal_exact

    @property
    def exact(self) -> bool:
        return (
            self.authoritative
            and self.legality_exact
            and self.legal is True
            and self.payable is True
            and self.exact_damage
            and self.prize_exact
            and self.post_attack_exact
            and self.terminal_exact
        )

    @property
    def exact_ko(self) -> bool:
        return (
            self.authoritative
            and self.legality_exact
            and self.legal is True
            and self.payable is True
            and self.exact_damage
            and self.knockout is True
        )

    @property
    def exact_game_win(self) -> bool:
        return (
            self.exact_ko
            and self.prize_exact
            and self.terminal_exact
            and self.wins_game is True
        )

    @property
    def exact_game_draw(self) -> bool:
        return (
            self.authoritative
            and self.prize_exact
            and self.terminal_exact
            and self.draws_game is True
        )

    @property
    def damage_margin(self) -> Optional[int]:
        if not self.exact_damage or self.final_damage is None:
            return None
        return self.final_damage - self.target_starting_hp

    @property
    def guaranteed_damage(self) -> int:
        return (
            self.final_damage
            if self.exact_damage and self.final_damage is not None
            else 0
        )

    @property
    def future_lock_cost(self) -> Optional[int]:
        if (
            not self.authoritative
            or self.next_turn_lock_applied is None
            or not self.terminal_exact
        ):
            return None
        if (
            self.wins_game
            or self.loses_game
            or self.draws_game
            or self.attacker_knockout is True
        ):
            return 0
        return 1 if self.next_turn_lock_applied else 0


_BOUND_ATTACK_OUTCOME_ISSUER_TOKEN = object()


@dataclass(frozen=True, init=False)
class BoundAttackOutcomeTable:
    """Authoritative rows bound to state, legal surface, and catalog digest."""

    state_fingerprint: str = dataclass_field(init=False)
    semantic_options_fingerprint: str = dataclass_field(init=False)
    registry_digest: str = dataclass_field(init=False)
    attacker_ref: Optional[PhysicalRef] = dataclass_field(init=False)
    target_ref: Optional[PhysicalRef] = dataclass_field(init=False)
    rows: Tuple[AttackOutcome, ...] = dataclass_field(init=False)
    build_unknown_reasons: Tuple[str, ...] = dataclass_field(init=False)

    def __init__(
        self,
        *,
        state_fingerprint: str,
        semantic_options_fingerprint: str,
        registry_digest: str,
        attacker_ref: Optional[PhysicalRef],
        target_ref: Optional[PhysicalRef],
        rows: Tuple[AttackOutcome, ...],
        build_unknown_reasons: Tuple[str, ...],
        issuer_token: object,
    ) -> None:
        if issuer_token is not _BOUND_ATTACK_OUTCOME_ISSUER_TOKEN:
            raise ValueError("attack outcome tables require the checked builder")
        if not all(
            _is_sha256(value)
            for value in (
                state_fingerprint,
                semantic_options_fingerprint,
                registry_digest,
            )
        ):
            raise ValueError("attack outcome bindings require lowercase SHA-256 values")
        if any(
            value is not None and not isinstance(value, PhysicalRef)
            for value in (attacker_ref, target_ref)
        ):
            raise ValueError("attack outcome endpoints must be PhysicalRef values")
        if not isinstance(rows, tuple) or any(
            not isinstance(row, AttackOutcome) or not row.authoritative for row in rows
        ):
            raise ValueError(
                "attack outcome rows must be issued by the checked evaluator"
            )
        normalized_rows = tuple(sorted(rows, key=lambda row: row.option_key.sort_key()))
        keys = tuple(row.option_key for row in normalized_rows)
        if len(set(keys)) != len(keys):
            raise ValueError("attack outcome table cannot repeat a semantic option")
        if any(
            attacker_ref is not None
            and row.attacker_ref != attacker_ref
            or target_ref is not None
            and row.target_ref != target_ref
            for row in normalized_rows
        ):
            raise ValueError("attack outcome rows must match the bound endpoints")
        reasons = _canonical_reasons(build_unknown_reasons)
        values = {
            "state_fingerprint": state_fingerprint,
            "semantic_options_fingerprint": semantic_options_fingerprint,
            "registry_digest": registry_digest,
            "attacker_ref": attacker_ref,
            "target_ref": target_ref,
            "rows": normalized_rows,
            "build_unknown_reasons": reasons,
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)

    @property
    def exact(self) -> bool:
        return (
            bool(self.rows)
            and not self.build_unknown_reasons
            and all(row.exact for row in self.rows)
        )

    def get_for_option(self, key: SemanticOptionKey) -> Optional[AttackOutcome]:
        matches = tuple(row for row in self.rows if row.option_key == key)
        return matches[0] if len(matches) == 1 else None

    def get(self, attack_id: int) -> Optional[AttackOutcome]:
        matches = tuple(row for row in self.rows if row.attack_id == attack_id)
        return matches[0] if len(matches) == 1 else None

    def as_dict(self) -> dict[int, AttackOutcome]:
        counts = Counter(row.attack_id for row in self.rows)
        return {row.attack_id: row for row in self.rows if counts[row.attack_id] == 1}

    def matches(
        self,
        state: PublicState,
        options: Sequence[SemanticOption],
        registry: PublicEffectRegistry,
    ) -> bool:
        return (
            isinstance(state, PublicState)
            and is_checked_public_state(state)
            and state.source_combat_complete
            and isinstance(registry, PublicEffectRegistry)
            and self.state_fingerprint == public_state_fingerprint(state)
            and state.source_options_fingerprint
            == self.semantic_options_fingerprint
            and self.semantic_options_fingerprint
            == semantic_options_fingerprint(options)
            and self.registry_digest == registry.digest
            and self.attacker_ref
            == (None if state.own_active is None else state.own_active.ref)
            and self.target_ref
            == (None if state.opponent_active is None else state.opponent_active.ref)
        )


def _mint_outcome(**values: object) -> AttackOutcome:
    for public_name, private_name in (
        ("legality_exact", "_legality_exact"),
        ("exact_damage", "_damage_exact"),
        ("post_attack_exact", "_post_attack_exact"),
        ("prize_exact", "_prize_exact"),
        ("terminal_exact", "_terminal_exact"),
    ):
        values[private_name] = values.pop(public_name)
    outcome = AttackOutcome(**values)  # type: ignore[arg-type]
    object.__setattr__(outcome, "_issuer_token", _ATTACK_OUTCOME_ISSUER_TOKEN)
    return outcome


@dataclass(frozen=True)
class _CombatEffects:
    attacker_profile: CombatCardProfile
    target_profile: CombatCardProfile
    attacker_abilities: Tuple[str, ...]
    target_abilities: Tuple[str, ...]
    attacker_energy: Tuple[str, ...]
    target_energy: Tuple[str, ...]
    attacker_tools: Tuple[str, ...]
    target_tools: Tuple[str, ...]
    stadium: Tuple[str, ...]
    jamming_active: bool
    unknown_reasons: Tuple[str, ...]


def _ref_reason(prefix: str, ref_value: PhysicalRef) -> str:
    card_id = "NONE" if ref_value.card_id is None else str(ref_value.card_id)
    serial = "NONE" if ref_value.serial is None else str(ref_value.serial)
    return f"{prefix}_CARD_{card_id}_SERIAL_{serial}"


def _attachment_effects(
    refs: Tuple[PhysicalRef, ...],
    registry: PublicEffectRegistry,
    *,
    kind: str,
    suppressed: bool = False,
) -> tuple[Tuple[str, ...], Tuple[str, ...]]:
    expected_types = {
        "ENERGY": (5, 6),
        "TOOL": (2,),
        "STADIUM": (4,),
    }
    allowed_types = expected_types.get(kind)
    if allowed_types is None:
        raise ValueError("attachment kind must have an exact catalog card type")
    effects = []
    reasons = []
    for ref_value in refs:
        if ref_value.card_id is None:
            if suppressed:
                continue
            reasons.append(_ref_reason(f"UNKNOWN_{kind}", ref_value))
            continue
        if kind == "ENERGY" and registry.is_effectless_basic_energy(ref_value.card_id):
            continue
        profile = registry.effect_profile(ref_value.card_id)
        if suppressed and profile is None:
            continue
        if profile is None:
            reasons.append(_ref_reason(f"UNREGISTERED_{kind}", ref_value))
            continue
        if profile.card_type not in allowed_types:
            reasons.append(_ref_reason(f"{kind}_CARD_TYPE_MISMATCH", ref_value))
            continue
        if suppressed:
            continue
        if not profile.all_skills_registered:
            reasons.append(_ref_reason(f"UNREGISTERED_{kind}_SKILL", ref_value))
            continue
        rows = profile.registered_skill_effect_ids
        if not rows:
            reasons.append(_ref_reason(f"UNREGISTERED_{kind}", ref_value))
            continue
        effects.extend(rows)
    return tuple(sorted(effects)), _canonical_reasons(reasons)


def _profile_for(
    pokemon: PokemonView,
    registry: PublicEffectRegistry,
) -> Optional[CombatCardProfile]:
    if pokemon.ref.card_id is None:
        return None
    return registry.profile(pokemon.ref.card_id)


def _collect_combat_effects(
    state: PublicState,
    registry: PublicEffectRegistry,
    attacker: PokemonView,
    target: PokemonView,
) -> Optional[_CombatEffects]:
    attacker_profile = _profile_for(attacker, registry)
    target_profile = _profile_for(target, registry)
    if attacker_profile is None or target_profile is None:
        return None

    reasons = []
    if len(state.stadium_refs) > 1:
        reasons.append("MULTIPLE_PUBLIC_STADIUM_CARDS")
    stadium, stadium_reasons = _attachment_effects(
        state.stadium_refs,
        registry,
        kind="STADIUM",
    )
    reasons.extend(stadium_reasons)
    jamming_active = "JAMMING_TOWER" in stadium

    all_pokemon = (
        state.own.active
        + state.own.bench
        + state.opponent.active
        + state.opponent.bench
    )
    in_play_refs = tuple(
        ref_value
        for pokemon in all_pokemon
        for ref_value in (
            pokemon.ref,
            *pokemon.energy_refs,
            *pokemon.tool_refs,
            *pokemon.pre_evolution_refs,
        )
    )
    physical_identities = tuple(
        (ref_value.owner, ref_value.serial)
        for ref_value in in_play_refs
        if ref_value.owner is not None and ref_value.serial is not None
    )
    if len(set(physical_identities)) != len(physical_identities):
        reasons.append("DUPLICATE_IN_PLAY_PHYSICAL_REF")
    for pokemon in all_pokemon:
        profile = _profile_for(pokemon, registry)
        if profile is None:
            reasons.append(_ref_reason("UNKNOWN_POKEMON_PROFILE", pokemon.ref))
        elif not profile.all_skills_registered:
            reasons.append(_ref_reason("UNREGISTERED_IN_PLAY_SKILL", pokemon.ref))
        _, energy_reasons = _attachment_effects(
            pokemon.energy_refs,
            registry,
            kind="ENERGY",
        )
        _, tool_reasons = _attachment_effects(
            pokemon.tool_refs,
            registry,
            kind="TOOL",
            suppressed=jamming_active,
        )
        reasons.extend(energy_reasons)
        reasons.extend(tool_reasons)

    attacker_energy, attacker_energy_reasons = _attachment_effects(
        attacker.energy_refs,
        registry,
        kind="ENERGY",
    )
    target_energy, target_energy_reasons = _attachment_effects(
        target.energy_refs,
        registry,
        kind="ENERGY",
    )
    attacker_tools, attacker_tool_reasons = _attachment_effects(
        attacker.tool_refs,
        registry,
        kind="TOOL",
        suppressed=jamming_active,
    )
    target_tools, target_tool_reasons = _attachment_effects(
        target.tool_refs,
        registry,
        kind="TOOL",
        suppressed=jamming_active,
    )
    reasons.extend(attacker_energy_reasons)
    reasons.extend(target_energy_reasons)
    reasons.extend(attacker_tool_reasons)
    reasons.extend(target_tool_reasons)
    return _CombatEffects(
        attacker_profile=attacker_profile,
        target_profile=target_profile,
        attacker_abilities=attacker_profile.registered_skill_effect_ids,
        target_abilities=target_profile.registered_skill_effect_ids,
        attacker_energy=attacker_energy,
        target_energy=target_energy,
        attacker_tools=attacker_tools,
        target_tools=target_tools,
        stadium=stadium,
        jamming_active=jamming_active,
        unknown_reasons=_canonical_reasons(reasons),
    )


def _attack_effect_id(
    attack_id: int,
    source_card_id: int,
    registry: PublicEffectRegistry,
) -> Optional[str]:
    rows = tuple(
        binding
        for binding in EFFECT_BINDINGS
        if binding.entry_kind is EntryKind.ATTACK
        and binding.entry_id == attack_id
        and binding.card_id == source_card_id
    )
    if len(rows) != 1:
        return None
    row = rows[0]
    return (
        row.effect_id
        if registry.binding_admitted(
            row.effect_id,
            card_id=source_card_id,
            entry_id=attack_id,
        )
        else None
    )


def _active_ref_is_complete(ref_value: PhysicalRef, owner: int) -> bool:
    return (
        ref_value.owner == owner
        and ref_value.zone == int(AreaType.ACTIVE)
        and _is_exact_int(ref_value.card_id)
        and ref_value.card_id > 0
        and _is_exact_int(ref_value.serial)
        and ref_value.serial >= 0
        and _is_exact_int(ref_value.lineage_serial)
        and ref_value.lineage_serial >= 0
    )


def _option_matches_endpoints(
    key: SemanticOptionKey,
    state: PublicState,
    attacker: PokemonView,
    target: PokemonView,
) -> bool:
    checks = (
        key.player_index in (None, state.seat),
        key.card_id in (None, attacker.ref.card_id),
        key.card_serial in (None, attacker.ref.serial),
        key.source_zone in (None, int(AreaType.ACTIVE)),
        key.source_lineage_serial in (None, attacker.ref.lineage_serial),
        key.target_zone in (None, int(AreaType.ACTIVE)),
        key.target_lineage_serial in (None, target.ref.lineage_serial),
    )
    return all(checks)


def _callback_preview(
    state: PublicState,
    registry: PublicEffectRegistry,
    attack_id: int,
) -> tuple[Optional[AttackCallbackPreview], Tuple[str, ...]]:
    attack = ATTACK_META_BY_ID[attack_id]
    semantics = attack.semantics
    if semantics.callback_kind is None:
        return None, ()
    source_card_id = semantics.callback_source_basic_energy_card_id
    if (
        source_card_id is None
        or not registry.is_effectless_basic_energy(source_card_id)
        or semantics.callback_kind
        is not AttackCallbackKind.AURA_BASIC_FIGHTING_TO_BENCH
        or not semantics.callback_targets_bench_only
    ):
        return None, ("UNREGISTERED_ATTACK_CALLBACK_SOURCE",)
    sources = tuple(
        sorted(
            (
                ref_value
                for ref_value in state.own.discard_refs
                if ref_value.card_id == source_card_id
                and ref_value.owner == state.seat
                and ref_value.zone == int(AreaType.DISCARD)
                and _is_exact_int(ref_value.serial)
            ),
            key=lambda ref_value: ref_value.sort_key(),
        )
    )
    if len(set(sources)) != len(sources):
        return None, ("DUPLICATE_AURA_CALLBACK_SOURCE_REF",)
    targets = tuple(
        sorted(
            (pokemon.ref for pokemon in state.own.bench),
            key=lambda ref_value: ref_value.sort_key(),
        )
    )
    preview = AttackCallbackPreview(
        kind=semantics.callback_kind,
        source_basic_energy_card_id=source_card_id,
        max_count=semantics.callback_max_count,
        available_source_refs=sources,
        eligible_target_refs=targets,
        requires_selection=bool(sources and targets),
    )
    return preview, ()


def _fully_unknown_outcome(
    *,
    state: PublicState,
    option_key: SemanticOptionKey,
    attacker: PokemonView,
    target: PokemonView,
    legality_reasons: Iterable[str],
    damage_reasons: Iterable[str],
    legal: Optional[bool] = None,
) -> AttackOutcome:
    attack_id = option_key.attack_id
    if not _is_exact_int(attack_id) or attack_id <= 0:
        raise ValueError("unknown attack rows still require a positive attack ID")
    attack = ATTACK_META_BY_ID.get(attack_id)
    base_damage = (
        int(attack.printed_damage)
        if attack is not None and _is_exact_int(attack.printed_damage)
        else 0
    )
    legality_unknown = _canonical_reasons(legality_reasons)
    damage_unknown = _canonical_reasons(damage_reasons)
    if not damage_unknown:
        damage_unknown = ("ATTACK_DAMAGE_NOT_CERTIFIED",)
    if legality_unknown:
        legal_value = None
        payable_value = None
    else:
        if legal is None:
            raise ValueError("known legality requires a legal value")
        legal_value = legal
        payable_value = legal
    return _mint_outcome(
        option_key=option_key,
        attack_id=attack_id,
        attacker_ref=attacker.ref,
        target_ref=target.ref,
        legality_exact=not legality_unknown,
        legal=legal_value,
        payable=payable_value,
        exact_damage=False,
        base_damage=base_damage,
        ppp_count=state.ppp_count if _is_exact_int(state.ppp_count) else None,
        ppp_bonus=None,
        before_weakness=None,
        weakness_multiplier=None,
        resistance_reduction=None,
        after_weakness_resistance=None,
        field_reduction=None,
        damage_before_prevention=None,
        damage_before_ko_prevention=None,
        final_damage=None,
        target_starting_hp=target.remaining_hp,
        target_hp_loss=None,
        target_hp_after=None,
        knockout=None,
        prevention_effects=(),
        post_attack_exact=False,
        attacker_starting_hp=attacker.remaining_hp,
        attacker_attack_effect_damage=None,
        attacker_damage_counters_placed=None,
        attacker_damage=None,
        attacker_hp_after=None,
        attacker_knockout=None,
        callback=None,
        next_turn_lock_applied=None,
        prize_exact=False,
        prizes_taken=None,
        opponent_prizes_taken=None,
        own_prizes_after=None,
        opponent_prizes_after=None,
        terminal_exact=False,
        wins_game=None,
        loses_game=None,
        draws_game=None,
        triggered_effects=(),
        legality_unknown_reasons=legality_unknown,
        damage_unknown_reasons=damage_unknown,
        prize_unknown_reasons=("TARGET_DAMAGE_NOT_EXACT",),
        post_attack_unknown_reasons=("ATTACK_EXECUTION_NOT_EXACT",),
        terminal_unknown_reasons=("PRIZE_EXCHANGE_NOT_EXACT",),
    )


def _same_attack_is_locked(
    state: PublicState,
    attacker: PokemonView,
    attack_id: int,
) -> bool:
    lineage = attacker.ref.lineage_serial
    return any(
        entry.owner == state.seat
        and entry.lineage_serial == lineage
        and entry.attack_id == attack_id
        and entry.turn == state.turn - 2
        for entry in state.last_attack_by_lineage
    )


def _prize_reduction(
    profile: CombatCardProfile,
    energy_effects: Tuple[str, ...],
    tool_effects: Tuple[str, ...],
) -> tuple[int, Tuple[str, ...]]:
    reasons = []
    exact_reduction = 0
    if "LEGACY_ENERGY" in energy_effects:
        reasons.append("LEGACY_ENERGY_ONCE_PER_GAME_STATE_UNKNOWN")
    if (
        "LILLIES_PEARL" in tool_effects
        and profile.card_id in LILLIES_POKEMON_CARD_IDS
    ):
        exact_reduction += 1
    return exact_reduction, _canonical_reasons(reasons)


def _evaluate_unique_attack(
    *,
    state: PublicState,
    registry: PublicEffectRegistry,
    option_key: SemanticOptionKey,
    attacker: PokemonView,
    target: PokemonView,
    effects: Optional[_CombatEffects],
    common_reasons: Tuple[str, ...],
    duplicate_option: bool,
) -> AttackOutcome:
    attack_id = option_key.attack_id
    if not _is_exact_int(attack_id) or attack_id <= 0:
        raise ValueError("attack evaluation requires a positive attack ID")

    legality_reasons = list(common_reasons)
    damage_reasons = list(common_reasons)
    legal = True
    if duplicate_option:
        legality_reasons.append("DUPLICATE_SEMANTIC_ATTACK_OPTION")
    if not _option_matches_endpoints(option_key, state, attacker, target):
        legality_reasons.append("ATTACK_OPTION_ENDPOINT_MISMATCH")

    attack = ATTACK_META_BY_ID.get(attack_id)
    if attack is None:
        legality_reasons.append("UNREGISTERED_ATTACK_ID")
        damage_reasons.append("UNREGISTERED_ATTACK_ID")
        return _fully_unknown_outcome(
            state=state,
            option_key=option_key,
            attacker=attacker,
            target=target,
            legality_reasons=legality_reasons,
            damage_reasons=damage_reasons,
        )
    if not _is_exact_int(attack.printed_damage):
        damage_reasons.append("UNKNOWN_PRINTED_DAMAGE")
    if effects is None:
        legality_reasons.append("MISSING_ACTIVE_COMBAT_PROFILE")
        damage_reasons.append("MISSING_ACTIVE_COMBAT_PROFILE")
        return _fully_unknown_outcome(
            state=state,
            option_key=option_key,
            attacker=attacker,
            target=target,
            legality_reasons=legality_reasons,
            damage_reasons=damage_reasons,
        )

    if (
        attacker.ref.card_id != attack.source_card_id
        or effects.attacker_profile.card_id != attack.source_card_id
        or attack_id not in effects.attacker_profile.attack_ids
    ):
        legality_reasons.append("ATTACK_SOURCE_PROFILE_MISMATCH")
        damage_reasons.append("ATTACK_SOURCE_PROFILE_MISMATCH")
    attack_effect_id = _attack_effect_id(
        attack_id,
        attack.source_card_id,
        registry,
    )
    if attack_effect_id is None:
        legality_reasons.append("ATTACK_BINDING_NOT_ADMITTED")
        damage_reasons.append("ATTACK_BINDING_NOT_ADMITTED")

    if not state.history_complete:
        damage_reasons.append("PUBLIC_ATTACK_HISTORY_INCOMPLETE")
        if attack.semantics.same_attack_lock_next_own_turn:
            legality_reasons.append("PUBLIC_ATTACK_LOCK_HISTORY_INCOMPLETE")
    if (
        not _is_exact_int(state.ppp_count)
        or state.ppp_count < 0
        or state.ppp_count > MAX_PPP_COUNT
    ):
        damage_reasons.append("INVALID_OR_UNKNOWN_PPP_COUNT")

    if state.history_complete and state.attacked_this_turn:
        legal = False
    if state.own.asleep:
        legality_reasons.append("ATTACK_OPTION_PRESENT_WHILE_ASLEEP")
    if state.own.paralyzed:
        legality_reasons.append("ATTACK_OPTION_PRESENT_WHILE_PARALYZED")
    if (
        state.history_complete
        and attack.semantics.same_attack_lock_next_own_turn
        and _same_attack_is_locked(state, attacker, attack_id)
    ):
        legal = False
    if state.own.confused:
        damage_reasons.append("CONFUSION_COIN_FLIP")
    damage_reasons.extend(effects.unknown_reasons)

    if legality_reasons or not legal or damage_reasons:
        return _fully_unknown_outcome(
            state=state,
            option_key=option_key,
            attacker=attacker,
            target=target,
            legality_reasons=legality_reasons,
            damage_reasons=damage_reasons,
            legal=legal if not legality_reasons else None,
        )

    base_damage = int(attack.printed_damage)
    ppp_count = int(state.ppp_count)
    triggered_effects = []
    condition_false = False
    if attack.semantics.condition is AttackCondition.LUNATONE_ON_BENCH:
        condition_false = not any(
            pokemon.ref.card_id == 675 for pokemon in state.own.bench
        )
        triggered_effects.append("COSMIC_BEAM")
    elif attack.semantics.condition is not AttackCondition.NONE:
        return _fully_unknown_outcome(
            state=state,
            option_key=option_key,
            attacker=attacker,
            target=target,
            legality_reasons=(),
            damage_reasons=("UNREGISTERED_ATTACK_CONDITION",),
            legal=True,
        )

    if condition_false:
        ppp_bonus = 0
        before_weakness = int(attack.semantics.condition_false_damage or 0)
        weakness_multiplier = 1
        resistance_reduction = 0
    else:
        ppp_bonus = (
            PPP_DAMAGE_BONUS * ppp_count
            if effects.attacker_profile.energy_type == FIGHTING_ENERGY_TYPE
            else 0
        )
        if ppp_bonus:
            triggered_effects.append("PREMIUM_POWER_PRO")
        before_weakness = max(0, base_damage + ppp_bonus)
        if attack.semantics.ignores_weakness_resistance:
            weakness_multiplier = 1
            resistance_reduction = 0
        else:
            weakness_multiplier = (
                2
                if effects.target_profile.weakness
                == effects.attacker_profile.energy_type
                else 1
            )
            resistance_reduction = (
                RESISTANCE_REDUCTION
                if effects.target_profile.resistance
                == effects.attacker_profile.energy_type
                else 0
            )
    after_weakness_resistance = max(
        0,
        before_weakness * weakness_multiplier - resistance_reduction,
    )

    field_reduction = 0
    if (
        "FULL_METAL_LAB" in effects.stadium
        and effects.target_profile.energy_type == METAL_ENERGY_TYPE
    ):
        field_reduction += FIELD_DAMAGE_REDUCTION
        triggered_effects.append("FULL_METAL_LAB")
    if (
        "GRANITE_CAVE" in effects.stadium
        and effects.target_profile.card_id in STEVENS_POKEMON_CARD_IDS
    ):
        field_reduction += FIELD_DAMAGE_REDUCTION
        triggered_effects.append("GRANITE_CAVE")
    damage_before_prevention = max(
        0,
        after_weakness_resistance - field_reduction,
    )

    prevention_effects = []
    if effects.attacker_profile.rule_box and (
        "SAFEGUARD" in effects.target_abilities
        or "MYSTERIOUS_ROCK_INN" in effects.target_abilities
    ):
        prevention_effects.extend(
            effect_id
            for effect_id in ("SAFEGUARD", "MYSTERIOUS_ROCK_INN")
            if effect_id in effects.target_abilities
        )
    if (
        effects.attacker_profile.has_ability
        and "CORNERSTONE_STANCE" in effects.target_abilities
    ):
        prevention_effects.append("CORNERSTONE_STANCE")
    if (
        "NEUTRALIZATION_ZONE" in effects.stadium
        and effects.attacker_profile.rule_box
        and not effects.target_profile.rule_box
    ):
        prevention_effects.append("NEUTRALIZATION_ZONE")
    if (
        "IMPERVIOUS_SHELL" in effects.target_abilities
        and damage_before_prevention >= 200
    ):
        prevention_effects.append("IMPERVIOUS_SHELL")
    prevention_effects_tuple = tuple(sorted(set(prevention_effects)))
    damage_before_ko_prevention = (
        0 if prevention_effects_tuple else damage_before_prevention
    )
    final_damage = damage_before_ko_prevention
    sturdy_applied = False
    if (
        "STURDY" in effects.target_abilities
        and target.remaining_hp == target.max_hp
        and damage_before_ko_prevention >= target.remaining_hp
        and damage_before_ko_prevention > 0
    ):
        sturdy_applied = True
        triggered_effects.append("STURDY")
    triggered_effects.extend(prevention_effects_tuple)
    target_hp_loss = (
        max(0, target.remaining_hp - 10)
        if sturdy_applied
        else min(target.remaining_hp, final_damage)
    )
    target_hp_after = max(0, target.remaining_hp - target_hp_loss)
    knockout = not sturdy_applied and final_damage >= target.remaining_hp

    callback, callback_reasons = _callback_preview(state, registry, attack_id)
    post_reasons = list(callback_reasons)
    if callback is not None:
        triggered_effects.append("AURA_JAB")
        if callback.requires_selection:
            post_reasons.append("AURA_CALLBACK_REQUIRES_SELECTION")
    if attack.semantics.self_damage:
        triggered_effects.append("WILD_PRESS")
    if attack.semantics.same_attack_lock_next_own_turn:
        if attack_effect_id is not None:
            triggered_effects.append(attack_effect_id)

    target_was_damaged = final_damage > 0
    spiky_damage = 0
    if target_was_damaged and "SPIKY_ENERGY" in effects.target_energy:
        spiky_damage = SPIKY_ENERGY_DAMAGE * effects.target_energy.count(
            "SPIKY_ENERGY"
        )
        triggered_effects.append("SPIKY_ENERGY")
    if target_was_damaged and "LUCKY_HELMET" in effects.target_tools:
        triggered_effects.append("LUCKY_HELMET")
        post_reasons.append("LUCKY_HELMET_HIDDEN_DRAW")
    if target_was_damaged and "HANDHELD_FAN" in effects.target_tools:
        triggered_effects.append("HANDHELD_FAN")
        if attacker.energy_refs and state.own.bench:
            post_reasons.append("HANDHELD_FAN_REQUIRES_SELECTION")
    attacker_attack_effect_damage = attack.semantics.self_damage
    attacker_damage_counters_placed = (
        SPIKY_ENERGY_DAMAGE_COUNTERS
        * effects.target_energy.count("SPIKY_ENERGY")
        if spiky_damage
        else 0
    )
    attacker_damage = attacker_attack_effect_damage + spiky_damage
    attacker_hp_after = max(0, attacker.remaining_hp - attacker_damage)
    attacker_knockout = attacker_damage >= attacker.remaining_hp
    next_turn_lock_applied = attack.semantics.same_attack_lock_next_own_turn

    prize_reasons = []
    target_prize_reduction = 0
    if knockout:
        target_prize_reduction, target_prize_reasons = _prize_reduction(
            effects.target_profile,
            effects.target_energy,
            effects.target_tools,
        )
        prize_reasons.extend(target_prize_reasons)
    prize_unknown = _canonical_reasons(prize_reasons)
    if prize_unknown:
        prizes_taken = None
        opponent_prizes_taken = None
        own_prizes_after = None
        opponent_prizes_after = None
    else:
        prizes_taken = min(
            state.own.prize_count,
            (
                max(
                    0,
                    effects.target_profile.prize_value - target_prize_reduction,
                )
                if knockout
                else 0
            ),
        )
        opponent_prizes_taken = min(
            state.opponent.prize_count,
            (
                effects.attacker_profile.prize_value
                if attacker_knockout
                else 0
            ),
        )
        own_prizes_after = max(0, state.own.prize_count - prizes_taken)
        opponent_prizes_after = max(
            0,
            state.opponent.prize_count - opponent_prizes_taken,
        )

    terminal_reasons = []
    wins_game: Optional[bool]
    loses_game: Optional[bool]
    draws_game: Optional[bool]
    if prize_unknown:
        terminal_reasons.append("PRIZE_EXCHANGE_NOT_EXACT")
        wins_game = None
        loses_game = None
        draws_game = None
    else:
        own_score = int(own_prizes_after == 0) + int(
            knockout and not state.opponent.bench
        )
        opponent_score = int(opponent_prizes_after == 0) + int(
            attacker_knockout and not state.own.bench
        )
        terminal = own_score > 0 or opponent_score > 0
        wins_game = terminal and own_score > opponent_score
        loses_game = terminal and opponent_score > own_score
        draws_game = terminal and own_score == opponent_score

    return _mint_outcome(
        option_key=option_key,
        attack_id=attack_id,
        attacker_ref=attacker.ref,
        target_ref=target.ref,
        legality_exact=True,
        legal=True,
        payable=True,
        exact_damage=True,
        base_damage=base_damage,
        ppp_count=ppp_count,
        ppp_bonus=ppp_bonus,
        before_weakness=before_weakness,
        weakness_multiplier=weakness_multiplier,
        resistance_reduction=resistance_reduction,
        after_weakness_resistance=after_weakness_resistance,
        field_reduction=field_reduction,
        damage_before_prevention=damage_before_prevention,
        damage_before_ko_prevention=damage_before_ko_prevention,
        final_damage=final_damage,
        target_starting_hp=target.remaining_hp,
        target_hp_loss=target_hp_loss,
        target_hp_after=target_hp_after,
        knockout=knockout,
        prevention_effects=prevention_effects_tuple,
        post_attack_exact=not post_reasons,
        attacker_starting_hp=attacker.remaining_hp,
        attacker_attack_effect_damage=attacker_attack_effect_damage,
        attacker_damage_counters_placed=attacker_damage_counters_placed,
        attacker_damage=attacker_damage,
        attacker_hp_after=attacker_hp_after,
        attacker_knockout=attacker_knockout,
        callback=callback,
        next_turn_lock_applied=next_turn_lock_applied,
        prize_exact=not prize_unknown,
        prizes_taken=prizes_taken,
        opponent_prizes_taken=opponent_prizes_taken,
        own_prizes_after=own_prizes_after,
        opponent_prizes_after=opponent_prizes_after,
        terminal_exact=not terminal_reasons,
        wins_game=wins_game,
        loses_game=loses_game,
        draws_game=draws_game,
        triggered_effects=_canonical_reasons(triggered_effects),
        legality_unknown_reasons=(),
        damage_unknown_reasons=(),
        prize_unknown_reasons=prize_unknown,
        post_attack_unknown_reasons=_canonical_reasons(post_reasons),
        terminal_unknown_reasons=_canonical_reasons(terminal_reasons),
    )


def build_attack_outcome_table(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
) -> BoundAttackOutcomeTable:
    """Build all unique ATTACK rows for one exact public MAIN prompt.

    Invalid or incomplete public evidence produces non-authoritative rows and
    explicit reasons; it is never repaired by guessing from card names or
    option indices.  Programmer-level type and option-index errors raise.
    """

    if not isinstance(state, PublicState):
        raise ValueError("attack outcomes require a PublicState")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("attack outcomes require a checked PublicEffectRegistry")
    options_fingerprint = semantic_options_fingerprint(legal_options)
    state_fingerprint = public_state_fingerprint(state)
    build_reasons = []
    if not is_checked_public_state(state):
        build_reasons.append("UNCHECKED_PUBLIC_STATE")
    if not state.source_combat_complete:
        build_reasons.append("INCOMPLETE_PUBLIC_COMBAT_SOURCE")
    if state.source_options_fingerprint != options_fingerprint:
        build_reasons.append("SOURCE_OPTION_FINGERPRINT_MISMATCH")
    if not is_stable_main_state(state):
        build_reasons.append("UNSTABLE_OR_NON_MAIN_ATTACK_STATE")
    if not _is_sha256(registry.digest):
        raise ValueError("public effect registry digest is malformed")

    attacker = state.own_active
    target = state.opponent_active
    if (
        attacker is None
        or len(state.own.active) != 1
        or state.own.active_slot_count != 1
        or state.own.hidden_active_count != 0
    ):
        build_reasons.append("OWN_ACTIVE_NOT_UNIQUE_AND_PUBLIC")
    if (
        target is None
        or len(state.opponent.active) != 1
        or state.opponent.active_slot_count != 1
        or state.opponent.hidden_active_count != 0
    ):
        build_reasons.append("OPPONENT_ACTIVE_NOT_UNIQUE_AND_PUBLIC")
    if attacker is not None and not _active_ref_is_complete(attacker.ref, state.seat):
        build_reasons.append("INCOMPLETE_ATTACKER_PHYSICAL_REF")
    if target is not None and not _active_ref_is_complete(
        target.ref,
        state.opponent.index,
    ):
        build_reasons.append("INCOMPLETE_TARGET_PHYSICAL_REF")
    if attacker is not None and (
        attacker.remaining_hp <= 0
        or attacker.max_hp <= 0
        or attacker.remaining_hp > attacker.max_hp
    ):
        build_reasons.append("INVALID_ATTACKER_PUBLIC_HP")
    if target is not None and (
        target.remaining_hp <= 0
        or target.max_hp <= 0
        or target.remaining_hp > target.max_hp
    ):
        build_reasons.append("INVALID_TARGET_PUBLIC_HP")

    attack_key_counts = Counter(
        option.key
        for option in legal_options
        if option.key.option_type == int(OptionType.ATTACK)
    )
    if not attack_key_counts:
        build_reasons.append("NO_ATTACK_OPTION")
    malformed_attack_keys = tuple(
        key
        for key in attack_key_counts
        if not _is_exact_int(key.attack_id) or key.attack_id <= 0
    )
    if malformed_attack_keys:
        build_reasons.append("ATTACK_OPTION_WITHOUT_POSITIVE_ATTACK_ID")

    rows = []
    effects: Optional[_CombatEffects] = None
    endpoints_usable = (
        attacker is not None
        and target is not None
        and attacker.remaining_hp > 0
        and target.remaining_hp > 0
    )
    if endpoints_usable:
        effects = _collect_combat_effects(state, registry, attacker, target)
        if effects is None:
            build_reasons.append("MISSING_ACTIVE_COMBAT_PROFILE")
        common_reasons = _canonical_reasons(build_reasons)
        for key, count in sorted(
            attack_key_counts.items(),
            key=lambda item: item[0].sort_key(),
        ):
            if not _is_exact_int(key.attack_id) or key.attack_id <= 0:
                continue
            rows.append(
                _evaluate_unique_attack(
                    state=state,
                    registry=registry,
                    option_key=key,
                    attacker=attacker,
                    target=target,
                    effects=effects,
                    common_reasons=common_reasons,
                    duplicate_option=count != 1,
                )
            )

    return BoundAttackOutcomeTable(
        state_fingerprint=state_fingerprint,
        semantic_options_fingerprint=options_fingerprint,
        registry_digest=registry.digest,
        attacker_ref=None if attacker is None else attacker.ref,
        target_ref=None if target is None else target.ref,
        rows=tuple(rows),
        build_unknown_reasons=_canonical_reasons(build_reasons),
        issuer_token=_BOUND_ATTACK_OUTCOME_ISSUER_TOKEN,
    )


__all__ = [
    "AttackCallbackPreview",
    "AttackOutcome",
    "BoundAttackOutcomeTable",
    "FIELD_DAMAGE_REDUCTION",
    "FIGHTING_ENERGY_TYPE",
    "LILLIES_POKEMON_CARD_IDS",
    "MAX_PPP_COUNT",
    "METAL_ENERGY_TYPE",
    "PPP_DAMAGE_BONUS",
    "RESISTANCE_REDUCTION",
    "SPIKY_ENERGY_DAMAGE",
    "SPIKY_ENERGY_DAMAGE_COUNTERS",
    "STEVENS_POKEMON_CARD_IDS",
    "build_attack_outcome_table",
    "semantic_options_fingerprint",
]
