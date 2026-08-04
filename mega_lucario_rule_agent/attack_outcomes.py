"""State-bound, fail-closed attack outcome evaluation.

The legacy :mod:`damage` module intentionally certifies target damage only.
This module composes the public state, semantic legal surface, checked card
catalog, attack history, post-attack effects, and Prize exchange into a single
immutable preview.  Exactness is tracked per component so that a known target
damage value can never be mistaken for a complete win or Prize certificate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field, replace
import hashlib
import json
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
        _derive_checked_active_energy_attach_state,
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
        _derive_checked_active_energy_attach_state,
        is_stable_main_state,
        public_state_fingerprint,
        semantic_options_fingerprint,
    )


ACTIVE_ATTACK_COMPLETION_EXPECTED_CATALOG_SHA256 = (
    "35499c8fefcd1152b20eb3618c33b8361c5589a2554eab9d33c003a08b0e03fc"
)
ACTIVE_ATTACK_COMPLETION_TRAINER_AUDIT_FINGERPRINT = (
    "049749c7c4f6146d76d44a2eb2e67dcc3ffe9df7ad8cd76f64eaf4b805c548cc"
)
_ACTIVE_ATTACK_COMPLETION_TRAINER_PROFILES = (
    (
        1140,
        "iron defender",
        1,
        0,
        (
            (
                "iron defender",
                "98d6389529ef834dccc37410e87f7d56c9f18a698d301b7a9e23aa6232b06323",
            ),
        ),
        (),
        (
            (
                "iron defender",
                "98d6389529ef834dccc37410e87f7d56c9f18a698d301b7a9e23aa6232b06323",
            ),
        ),
    ),
    (
        1228,
        "acerola's mischief",
        3,
        0,
        (
            (
                "acerola's mischief",
                "5b5b8f38efb7b81d3d9646a2787059ee5ec562f0fc17582686630ca6c04a6b55",
            ),
        ),
        (),
        (
            (
                "acerola's mischief",
                "5b5b8f38efb7b81d3d9646a2787059ee5ec562f0fc17582686630ca6c04a6b55",
            ),
        ),
    ),
)


def active_attack_completion_registry_audit(
    registry: PublicEffectRegistry,
) -> Optional[Tuple[str, str]]:
    """Bind the clause to the production catalog and audited transient Trainers."""

    if (
        not isinstance(registry, PublicEffectRegistry)
        or registry.catalog_sha256 != ACTIVE_ATTACK_COMPLETION_EXPECTED_CATALOG_SHA256
    ):
        return None
    profiles = tuple(registry.effect_profile(card_id) for card_id in (1140, 1228))
    if any(profile is None for profile in profiles):
        return None
    canonical = tuple(
        profile.canonical() for profile in profiles if profile is not None
    )
    if canonical != _ACTIVE_ATTACK_COMPLETION_TRAINER_PROFILES:
        return None
    payload = json.dumps(
        canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    fingerprint = hashlib.sha256(payload).hexdigest()
    if fingerprint != ACTIVE_ATTACK_COMPLETION_TRAINER_AUDIT_FINGERPRINT:
        return None
    return registry.catalog_sha256, fingerprint


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
_EXACT_SPREAD_ATTACKS = {
    154: (
        121,
        "phantom dive",
        "d8f96901640021b5dabbaa4ed8e751745b2c35b6e2bf72f9d4159dcf068e5e7f",
        200,
        (2, 5),
        60,
    ),
    937: (
        648,
        "shadow bullet",
        "ee16136a9e9300bb7e963b6c31b52e77ab1f7eb76ffe01133b3bcb36f405d148",
        180,
        (7, 7),
        30,
    ),
}
_EXACT_SPREAD_SOURCE_FIELDS = {
    121: (
        "dragapult ex",
        "drakloak",
        320,
        9,
        None,
        None,
        False,
        False,
        True,
        True,
        False,
        True,
        (153, 154),
        (),
        (),
        (),
    ),
    648: (
        "marnie's grimmsnarl ex",
        "marnie's morgrem",
        320,
        7,
        1,
        None,
        False,
        False,
        True,
        True,
        False,
        False,
        (937,),
        (
            (
                "punk up",
                "b89ef242ee6bbde36fb333f8010f1461be486d3f8c944a57f94d7887c17b4825",
            ),
        ),
        (),
        (
            (
                "punk up",
                "b89ef242ee6bbde36fb333f8010f1461be486d3f8c944a57f94d7887c17b4825",
            ),
        ),
    ),
}


@dataclass(frozen=True)
class OpponentAttackThreatRow:
    """One exactly payable public opponent attack at two target HP states."""

    attack_id: int
    energy_cost: Tuple[int, ...]
    final_damage: int
    knockout_before_heal: bool
    knockout_after_heal: bool

    def __post_init__(self) -> None:
        if (
            not _is_exact_int(self.attack_id)
            or self.attack_id <= 0
            or not isinstance(self.energy_cost, tuple)
            or any(
                not _is_exact_int(value) or value < 0
                for value in self.energy_cost
            )
            or not _is_exact_int(self.final_damage)
            or self.final_damage < 0
            or not isinstance(self.knockout_before_heal, bool)
            or not isinstance(self.knockout_after_heal, bool)
        ):
            raise ValueError("opponent attack threat row must be exact")


@dataclass(frozen=True)
class OpponentAttackThreatSurface:
    """Fail-closed public next-attack surface used by survival routes."""

    rows: Tuple[OpponentAttackThreatRow, ...]
    unpayable_attack_ids: Tuple[int, ...]
    max_damage: Optional[int]
    max_attack_ids: Tuple[int, ...]
    knockout_before_heal: Optional[bool]
    knockout_after_heal: Optional[bool]
    jamming_active: Optional[bool]
    unknown_reasons: Tuple[str, ...]

    @property
    def exact(self) -> bool:
        return not self.unknown_reasons


@dataclass(frozen=True)
class PostWallyProductiveAttack:
    """Checked same-turn attack restored by one manual post-Wally attach."""

    reattach_ref: PhysicalRef
    attack_id: int
    final_damage: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.reattach_ref, PhysicalRef)
            or not _is_exact_int(self.attack_id)
            or self.attack_id <= 0
            or not _is_exact_int(self.final_damage)
            or self.final_damage <= 0
        ):
            raise ValueError("post-Wally attack must be exact and productive")


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
        if not self._damage_exact and any(
            value is not None for value in damage_outputs
        ):
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
        if not self._terminal_exact and any(
            value is not None for value in terminal_outputs
        ):
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


@dataclass(frozen=True)
class ActivePostAttachAttackCompletion:
    """Clause-only proof for the going-second OT1 Active attach rule."""

    source_ref: PhysicalRef
    target_ref: PhysicalRef
    target_energy_type: int
    catalog_sha256: str
    persistent_trainer_audit_fingerprint: str
    energy_types_before: Tuple[int, ...]
    energy_types_after: Tuple[int, ...]
    pre_payable: Tuple[int, ...]
    post_payable: Tuple[int, ...]
    candidate_rows: Tuple[Tuple[int, int, int, Tuple[int, ...]], ...]
    chosen_attack_id: int
    chosen_final_damage: int
    chosen_future_lock_cost: int
    chosen_energy_cost: Tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, PhysicalRef) or not isinstance(
            self.target_ref,
            PhysicalRef,
        ):
            raise ValueError("post-attach completion requires exact physical refs")
        if (
            self.source_ref.card_id != 6
            or self.source_ref.zone != int(AreaType.HAND)
            or self.target_ref.zone != int(AreaType.ACTIVE)
        ):
            raise ValueError("post-attach completion refs have invalid roles")
        if (
            not _is_exact_int(self.target_energy_type)
            or self.target_energy_type <= 0
            or self.target_energy_type == METAL_ENERGY_TYPE
        ):
            raise ValueError(
                "post-attach completion requires an exact non-Metal target"
            )
        if (
            not _is_sha256(self.catalog_sha256)
            or not _is_sha256(self.persistent_trainer_audit_fingerprint)
            or self.persistent_trainer_audit_fingerprint
            != ACTIVE_ATTACK_COMPLETION_TRAINER_AUDIT_FINGERPRINT
        ):
            raise ValueError(
                "post-attach completion requires the audited production catalog"
            )
        if any(
            not _is_exact_int(value) or value <= 0
            for value in self.energy_types_before + self.energy_types_after
        ):
            raise ValueError("post-attach energy types must be positive exact ints")
        if self.energy_types_after != self.energy_types_before + (
            FIGHTING_ENERGY_TYPE,
        ):
            raise ValueError(
                "post-attach completion must add exactly one Fighting Energy"
            )
        if self.pre_payable:
            raise ValueError("pre-attach payable attack set must be empty")
        if len(self.post_payable) != 1 or any(
            not _is_exact_int(value) or value <= 0 for value in self.post_payable
        ):
            raise ValueError("post-attach payable attack set must be one exact attack")
        if len(self.candidate_rows) != 1:
            raise ValueError("post-attach completion requires one positive candidate")
        for (
            attack_id,
            final_damage,
            future_lock_cost,
            energy_cost,
        ) in self.candidate_rows:
            if (
                not _is_exact_int(attack_id)
                or attack_id <= 0
                or not _is_exact_int(final_damage)
                or final_damage <= 0
                or future_lock_cost not in (0, 1)
                or not energy_cost
                or any(not _is_exact_int(value) or value <= 0 for value in energy_cost)
            ):
                raise ValueError(
                    "post-attach candidate rows must be exact and positive"
                )
        expected = tuple(
            sorted(
                self.candidate_rows,
                key=lambda row: (-row[1], row[2], row[0], row[3]),
            )
        )
        if expected != self.candidate_rows:
            raise ValueError(
                "post-attach candidates must use exact attack-policy order"
            )
        chosen = self.candidate_rows[0]
        if self.post_payable != (chosen[0],):
            raise ValueError("post-attach payable attack must equal the candidate")
        if (
            self.chosen_attack_id,
            self.chosen_final_damage,
            self.chosen_future_lock_cost,
            self.chosen_energy_cost,
        ) != chosen:
            raise ValueError("post-attach chosen attack must lead the candidate set")

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.source_ref.sort_key(),
            self.target_ref.sort_key(),
            self.target_energy_type,
            self.catalog_sha256,
            self.persistent_trainer_audit_fingerprint,
            self.energy_types_before,
            self.energy_types_after,
            self.pre_payable,
            self.post_payable,
            self.candidate_rows,
            self.chosen_attack_id,
            self.chosen_final_damage,
            self.chosen_future_lock_cost,
            self.chosen_energy_cost,
        )


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
            and state.source_options_fingerprint == self.semantic_options_fingerprint
            and self.semantic_options_fingerprint
            == semantic_options_fingerprint(options)
            and self.registry_digest == registry.digest
            and self.attacker_ref
            == (None if state.own_active is None else state.own_active.ref)
            and self.target_ref
            == (None if state.opponent_active is None else state.opponent_active.ref)
        )


def is_fully_exact_attack_completion_outcome(
    table: BoundAttackOutcomeTable,
    outcome: AttackOutcome,
) -> bool:
    """Shared full-exact admission for a non-losing direct attack candidate."""

    return (
        isinstance(table, BoundAttackOutcomeTable)
        and isinstance(outcome, AttackOutcome)
        and table.get_for_option(outcome.option_key) == outcome
        and table.exact
        and outcome.authoritative
        and outcome.legality_exact
        and outcome.legal is True
        and outcome.payable is True
        and outcome.exact
        and outcome.post_attack_exact
        and outcome.prize_exact
        and outcome.prizes_taken is not None
        and outcome.opponent_prizes_taken is not None
        and outcome.own_prizes_after is not None
        and outcome.opponent_prizes_after is not None
        and outcome.terminal_exact
        and isinstance(outcome.wins_game, bool)
        and outcome.loses_game is False
        and outcome.draws_game is False
        and outcome.future_lock_cost is not None
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


def _exact_basic_energy_types(
    pokemon: PokemonView,
    registry: PublicEffectRegistry,
) -> tuple[Tuple[int, ...], Tuple[str, ...]]:
    reasons = []
    if len(pokemon.energy_types) != len(pokemon.energy_refs):
        reasons.append("PUBLIC_ENERGY_TYPE_CARD_COUNT_MISMATCH")
        return (), _canonical_reasons(reasons)
    values = []
    for observed_type, ref_value in zip(
        pokemon.energy_types,
        pokemon.energy_refs,
    ):
        if (
            not _is_exact_int(observed_type)
            or observed_type <= 0
            or ref_value.card_id is None
            or not registry.is_effectless_basic_energy(ref_value.card_id)
        ):
            reasons.append(_ref_reason("NON_BASIC_OR_UNKNOWN_ENERGY", ref_value))
            continue
        profile = registry.effect_profile(ref_value.card_id)
        if profile is None or profile.energy_type != observed_type:
            reasons.append(_ref_reason("ENERGY_TYPE_PROFILE_MISMATCH", ref_value))
            continue
        values.append(int(observed_type))
    if reasons:
        return (), _canonical_reasons(reasons)
    return tuple(values), ()


def _public_cost_is_payable(
    attached_energy_types: Sequence[int],
    energy_cost: Sequence[int],
) -> Optional[bool]:
    if any(
        not _is_exact_int(value) or value <= 0
        for value in attached_energy_types
    ) or any(not _is_exact_int(value) or value < 0 for value in energy_cost):
        return None
    remaining = list(int(value) for value in attached_energy_types)
    for required in (int(value) for value in energy_cost if int(value) > 0):
        try:
            remaining.remove(required)
        except ValueError:
            return False
    colorless_count = sum(int(value) == 0 for value in energy_cost)
    return len(remaining) >= colorless_count


def _fixed_public_attack_damage(
    effects: _CombatEffects,
    printed_damage: int,
    *,
    target_hp: int,
    target_max_hp: int,
) -> tuple[int, bool]:
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
        printed_damage * weakness_multiplier - resistance_reduction,
    )
    field_reduction = 0
    if (
        "FULL_METAL_LAB" in effects.stadium
        and effects.target_profile.energy_type == METAL_ENERGY_TYPE
    ):
        field_reduction += FIELD_DAMAGE_REDUCTION
    if (
        "GRANITE_CAVE" in effects.stadium
        and effects.target_profile.card_id in STEVENS_POKEMON_CARD_IDS
    ):
        field_reduction += FIELD_DAMAGE_REDUCTION
    damage_before_prevention = max(
        0,
        after_weakness_resistance - field_reduction,
    )
    prevented = (
        effects.attacker_profile.rule_box
        and (
            "SAFEGUARD" in effects.target_abilities
            or "MYSTERIOUS_ROCK_INN" in effects.target_abilities
        )
    ) or (
        effects.attacker_profile.has_ability
        and "CORNERSTONE_STANCE" in effects.target_abilities
    ) or (
        "NEUTRALIZATION_ZONE" in effects.stadium
        and effects.attacker_profile.rule_box
        and not effects.target_profile.rule_box
    ) or (
        "IMPERVIOUS_SHELL" in effects.target_abilities
        and damage_before_prevention >= 200
    )
    final_damage = 0 if prevented else damage_before_prevention
    sturdy_applied = (
        "STURDY" in effects.target_abilities
        and target_hp == target_max_hp
        and final_damage >= target_hp
        and final_damage > 0
    )
    return final_damage, not sturdy_applied and final_damage >= target_hp


def _is_exact_spread_source(profile: CombatCardProfile) -> bool:
    expected = _EXACT_SPREAD_SOURCE_FIELDS.get(profile.card_id)
    return expected is not None and profile.canonical()[1:] == expected


def _exact_spread_target_loss(
    attacker_profile: CombatCardProfile,
    attack_profile,
    registry: PublicEffectRegistry,
) -> Optional[int]:
    expected = _EXACT_SPREAD_ATTACKS.get(attack_profile.attack_id)
    if expected is None:
        return None
    (
        source_card_id,
        attack_name,
        text_hash,
        printed_damage,
        energy_cost,
        bench_loss,
    ) = expected
    owners = tuple(
        profile
        for profile in registry.profiles
        if attack_profile.attack_id in profile.attack_ids
    )
    if (
        len(owners) != 1
        or owners[0] != attacker_profile
        or attacker_profile.card_id != source_card_id
        or not _is_exact_spread_source(attacker_profile)
        or attack_profile.attack_name != attack_name
        or attack_profile.text_hash != text_hash
        or attack_profile.printed_damage != printed_damage
        or attack_profile.energy_cost != energy_cost
    ):
        return None
    return bench_loss


def build_public_opponent_attack_threat(
    state: PublicState,
    registry: PublicEffectRegistry,
    *,
    target_ref: Optional[PhysicalRef] = None,
    before_hp_state: Optional[Tuple[int, int]] = None,
    after_hp_state: Optional[Tuple[int, int]] = None,
    admit_spread_attacks: bool = False,
) -> OpponentAttackThreatSurface:
    """Evaluate public opponent attacks at two exact target HP states.

    Hidden draws, future attachments and future evolution are intentionally not
    assumed. Any currently payable attack with unsupported printed text makes
    the survival claim unknown rather than optimistic.
    """

    reasons = []
    attacker = state.opponent_active if isinstance(state, PublicState) else None
    target = None
    if not isinstance(state, PublicState) or not is_checked_public_state(state):
        reasons.append("UNCHECKED_PUBLIC_STATE")
    elif not state.source_combat_complete or not is_stable_main_state(state):
        reasons.append("INCOMPLETE_OR_UNSTABLE_PUBLIC_COMBAT_STATE")
    elif target_ref is None:
        target = state.own_active
    elif not isinstance(target_ref, PhysicalRef):
        reasons.append("INVALID_OWN_TARGET_PHYSICAL_REF")
    else:
        target_matches = tuple(
            pokemon
            for pokemon in state.own.active + state.own.bench
            if pokemon.ref == target_ref
        )
        if len(target_matches) == 1:
            target = target_matches[0]
        else:
            reasons.append("OWN_TARGET_NOT_UNIQUE_AND_PUBLIC")
    if attacker is None or len(state.opponent.active) != 1:
        reasons.append("OPPONENT_ACTIVE_NOT_UNIQUE_AND_PUBLIC")
    if target_ref is None and (target is None or len(state.own.active) != 1):
        reasons.append("OWN_ACTIVE_NOT_UNIQUE_AND_PUBLIC")
    if attacker is not None and not _active_ref_is_complete(
        attacker.ref,
        state.opponent.index,
    ):
        reasons.append("INCOMPLETE_OPPONENT_ATTACKER_PHYSICAL_REF")
    if target is not None and not _board_ref_is_complete(target.ref, state.seat):
        reasons.append("INCOMPLETE_OWN_TARGET_PHYSICAL_REF")
    if any(
        (
            state.opponent.poisoned,
            state.opponent.burned,
            state.opponent.asleep,
            state.opponent.paralyzed,
            state.opponent.confused,
        )
    ):
        reasons.append("OPPONENT_STATUS_NEXT_ATTACK_UNRESOLVED")
    effects = (
        None
        if attacker is None or target is None
        else _collect_combat_effects(state, registry, attacker, target)
    )
    if effects is None:
        reasons.append("MISSING_OPPONENT_COMBAT_PROFILE")
    else:
        reasons.extend(effects.unknown_reasons)
    jamming_active = None if effects is None else effects.jamming_active
    energy_types: Tuple[int, ...] = ()
    if attacker is not None:
        energy_types, energy_reasons = _exact_basic_energy_types(attacker, registry)
        reasons.extend(energy_reasons)
    if target is not None and effects is not None:
        expected_max_hp = effects.target_profile.hp + (
            100 if "HEROS_CAPE" in effects.target_tools else 0
        )
        if (
            target.remaining_hp <= 0
            or target.max_hp <= 0
            or target.remaining_hp > target.max_hp
            or target.max_hp != expected_max_hp
        ):
            reasons.append("OWN_TARGET_HP_NOT_EXACT_FROM_PUBLIC_EFFECTS")
    if target is not None:
        if before_hp_state is None:
            before_hp_state = (target.remaining_hp, target.max_hp)
        if after_hp_state is None:
            after_hp_state = (target.max_hp, target.max_hp)
        for label, hp_state in (
            ("BEFORE", before_hp_state),
            ("AFTER", after_hp_state),
        ):
            if (
                not isinstance(hp_state, tuple)
                or len(hp_state) != 2
                or any(
                    not _is_exact_int(value) or value <= 0
                    for value in hp_state
                )
                or hp_state[0] > hp_state[1]
            ):
                reasons.append(f"{label}_TARGET_HP_STATE_NOT_EXACT")
        if before_hp_state != (target.remaining_hp, target.max_hp):
            reasons.append("BEFORE_TARGET_HP_STATE_NOT_CURRENT_PUBLIC_STATE")
    attack_ids = () if effects is None else effects.attacker_profile.attack_ids
    rows = []
    unpayable = []
    if not reasons:
        for attack_id in attack_ids:
            profile = registry.attack_profile(attack_id)
            if profile is None:
                reasons.append(f"UNKNOWN_PUBLIC_ATTACK_PROFILE_{attack_id}")
                continue
            payable = _public_cost_is_payable(energy_types, profile.energy_cost)
            if payable is None:
                reasons.append(f"UNKNOWN_PUBLIC_ATTACK_COST_{attack_id}")
                continue
            if not payable:
                unpayable.append(attack_id)
                continue
            spread_loss = _exact_spread_target_loss(
                effects.attacker_profile,
                profile,
                registry,
            )
            if profile.effect_text and (
                not admit_spread_attacks or spread_loss is None
            ):
                reasons.append(f"UNSUPPORTED_PAYABLE_ATTACK_EFFECT_{attack_id}")
                continue
            assert before_hp_state is not None
            assert after_hp_state is not None
            assert target is not None
            if target.ref.zone == int(AreaType.BENCH):
                target_loss = spread_loss if profile.effect_text else 0
                assert target_loss is not None
                before_damage = target_loss
                after_damage = target_loss
                before_ko = target_loss >= before_hp_state[0]
                after_ko = target_loss >= after_hp_state[0]
            else:
                before_damage, before_ko = _fixed_public_attack_damage(
                    effects,
                    profile.printed_damage,
                    target_hp=before_hp_state[0],
                    target_max_hp=before_hp_state[1],
                )
                after_damage, after_ko = _fixed_public_attack_damage(
                    effects,
                    profile.printed_damage,
                    target_hp=after_hp_state[0],
                    target_max_hp=after_hp_state[1],
                )
            if before_damage != after_damage:
                reasons.append(f"HP_DEPENDENT_DAMAGE_UNSUPPORTED_{attack_id}")
                continue
            rows.append(
                OpponentAttackThreatRow(
                    attack_id=attack_id,
                    energy_cost=profile.energy_cost,
                    final_damage=before_damage,
                    knockout_before_heal=before_ko,
                    knockout_after_heal=after_ko,
                )
            )
    unknown_reasons = _canonical_reasons(reasons)
    if unknown_reasons:
        max_damage = None
        max_attack_ids: Tuple[int, ...] = ()
        knockout_before: Optional[bool] = None
        knockout_after: Optional[bool] = None
    else:
        max_damage = max((row.final_damage for row in rows), default=0)
        max_attack_ids = tuple(
            row.attack_id for row in rows if row.final_damage == max_damage
        )
        knockout_before = any(row.knockout_before_heal for row in rows)
        knockout_after = any(row.knockout_after_heal for row in rows)
    return OpponentAttackThreatSurface(
        rows=tuple(rows),
        unpayable_attack_ids=tuple(unpayable),
        max_damage=max_damage,
        max_attack_ids=max_attack_ids,
        knockout_before_heal=knockout_before,
        knockout_after_heal=knockout_after,
        jamming_active=jamming_active,
        unknown_reasons=unknown_reasons,
    )


def build_post_wally_productive_attack(
    state: PublicState,
    registry: PublicEffectRegistry,
    wally_ref: PhysicalRef,
    reattach_ref: PhysicalRef,
) -> Optional[PostWallyProductiveAttack]:
    """Recompute the exact attack surface after Wally and one reattach."""

    if (
        not isinstance(state, PublicState)
        or not is_checked_public_state(state)
        or not isinstance(registry, PublicEffectRegistry)
        or not isinstance(wally_ref, PhysicalRef)
        or not isinstance(reattach_ref, PhysicalRef)
        or not is_stable_main_state(state)
        or not state.source_combat_complete
        or not state.history_complete
        or state.supporter_played
        or state.energy_attached
        or state.attacked_this_turn
        or state.own.poisoned
        or state.own.burned
        or state.own.asleep
        or state.own.paralyzed
        or state.own.confused
        or state.own.deck_count < 1
        or wally_ref.card_id != 1229
        or wally_ref.owner != state.seat
        or wally_ref.zone != int(AreaType.HAND)
        or sum(ref_value == wally_ref for ref_value in state.own.hand_refs) != 1
    ):
        return None
    attacker = state.own_active
    defender = state.opponent_active
    if (
        attacker is None
        or defender is None
        or attacker.ref.card_id != 678
        or attacker.damage <= 0
        or not attacker.energy_refs
        or reattach_ref not in attacker.energy_refs
    ):
        return None
    energy_types, energy_reasons = _exact_basic_energy_types(attacker, registry)
    if energy_reasons:
        return None
    typed_refs = tuple(zip(attacker.energy_refs, energy_types))
    selected = tuple(
        energy_type
        for ref_value, energy_type in typed_refs
        if ref_value == reattach_ref
    )
    if len(selected) != 1:
        return None
    reattach_type = selected[0]
    hand_returned = tuple(
        replace(ref_value, zone=int(AreaType.HAND))
        for ref_value in attacker.energy_refs
    )
    selected_hand_ref = replace(reattach_ref, zone=int(AreaType.HAND))
    selected_attached_ref = replace(reattach_ref, zone=int(AreaType.ENERGY))
    post_active = replace(
        attacker,
        hp=attacker.max_hp,
        energy_types=(reattach_type,),
        energy_refs=(selected_attached_ref,),
    )
    post_hand_refs = tuple(
        sorted(
            (
                ref_value
                for ref_value in (
                    *(
                        value
                        for value in state.own.hand_refs
                        if value != wally_ref
                    ),
                    *hand_returned,
                )
                if ref_value != selected_hand_ref
            ),
            key=lambda value: value.sort_key(),
        )
    )
    if len(set(post_hand_refs)) != len(post_hand_refs):
        return None
    post_own = replace(
        state.own,
        active=(post_active,),
        hand_refs=post_hand_refs,
        hand_count=state.own.hand_count - 2 + len(attacker.energy_refs),
    )
    card_profile = registry.profile(post_active.ref.card_id)
    if card_profile is None:
        return None
    payable_attack_ids = []
    for attack_id in card_profile.attack_ids:
        cost = _registered_attack_energy_cost(
            registry,
            int(post_active.ref.card_id),
            int(attack_id),
        )
        if cost is None:
            return None
        deficit = _typed_energy_deficit((reattach_type,), cost)
        if deficit is None:
            return None
        if deficit == 0 and not (
            ATTACK_META_BY_ID[attack_id].semantics.same_attack_lock_next_own_turn
            and _same_attack_is_locked(state, attacker, attack_id)
        ):
            payable_attack_ids.append(attack_id)
    if not payable_attack_ids:
        return None
    hypothetical_options = tuple(
        SemanticOption(
            index=index,
            key=_hypothetical_attack_key(
                state,
                post_active,
                defender,
                attack_id,
            ),
        )
        for index, attack_id in enumerate(payable_attack_ids)
    )
    post_state = replace(
        state,
        own=post_own,
        supporter_played=True,
        energy_attached=True,
        turn_action_count=state.turn_action_count + 2,
        source_options_fingerprint=semantic_options_fingerprint(
            hypothetical_options
        ),
    )
    object.__setattr__(
        post_state,
        "_builder_receipt",
        public_state_fingerprint(post_state),
    )
    if not is_checked_public_state(post_state):
        return None
    table = build_attack_outcome_table(post_state, hypothetical_options, registry)
    candidates = tuple(
        sorted(
            (
                (-int(outcome.final_damage), outcome.attack_id, outcome)
                for outcome in table.rows
                if outcome.authoritative
                and outcome.legality_exact
                and outcome.legal is True
                and outcome.payable is True
                and outcome.exact_damage
                and outcome.final_damage is not None
                and outcome.final_damage > 0
                and outcome.terminal_exact
                and outcome.loses_game is False
                and outcome.draws_game is False
            ),
            key=lambda row: (row[0], row[1]),
        )
    )
    if not candidates:
        return None
    chosen = candidates[0][2]
    return PostWallyProductiveAttack(
        reattach_ref=reattach_ref,
        attack_id=chosen.attack_id,
        final_damage=int(chosen.final_damage),
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


def _board_ref_is_complete(ref_value: PhysicalRef, owner: int) -> bool:
    return (
        ref_value.owner == owner
        and ref_value.zone in (int(AreaType.ACTIVE), int(AreaType.BENCH))
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
    if "LILLIES_PEARL" in tool_effects and profile.card_id in LILLIES_POKEMON_CARD_IDS:
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
        spiky_damage = SPIKY_ENERGY_DAMAGE * effects.target_energy.count("SPIKY_ENERGY")
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
        SPIKY_ENERGY_DAMAGE_COUNTERS * effects.target_energy.count("SPIKY_ENERGY")
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
            (effects.attacker_profile.prize_value if attacker_knockout else 0),
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


def _typed_energy_deficit(
    attached_energy_types: Sequence[int],
    energy_cost: Sequence[int],
) -> Optional[int]:
    if any(not _is_exact_int(value) or value <= 0 for value in attached_energy_types):
        return None
    if not energy_cost or any(
        not _is_exact_int(value) or value <= 0 for value in energy_cost
    ):
        return None
    available = Counter(int(value) for value in attached_energy_types)
    required = Counter(int(value) for value in energy_cost)
    return sum(
        max(0, required[energy_type] - available[energy_type])
        for energy_type in required
    )


def _registered_attack_energy_cost(
    registry: PublicEffectRegistry,
    card_id: int,
    attack_id: int,
) -> Optional[Tuple[int, ...]]:
    attack = ATTACK_META_BY_ID.get(attack_id)
    rows = tuple(
        binding
        for binding in EFFECT_BINDINGS
        if binding.entry_kind is EntryKind.ATTACK
        and binding.card_id == card_id
        and binding.entry_id == attack_id
    )
    if (
        attack is None
        or attack.source_card_id != card_id
        or len(rows) != 1
        or not registry.binding_admitted(
            rows[0].effect_id,
            card_id=card_id,
            entry_id=attack_id,
        )
    ):
        return None
    metadata_cost = tuple(
        FIGHTING_ENERGY_TYPE if getattr(value, "value", None) == "fighting" else 0
        for value in attack.energy_cost
    )
    binding_cost = tuple(int(value) for value in rows[0].energy_cost)
    return (
        metadata_cost
        if metadata_cost and 0 not in metadata_cost and metadata_cost == binding_cost
        else None
    )


def _hypothetical_attack_key(
    state: PublicState,
    attacker: PokemonView,
    target: PokemonView,
    attack_id: int,
) -> SemanticOptionKey:
    return SemanticOptionKey(
        option_type=int(OptionType.ATTACK),
        player_index=state.seat,
        card_id=attacker.ref.card_id,
        card_serial=attacker.ref.serial,
        source_zone=int(AreaType.ACTIVE),
        source_lineage_serial=attacker.ref.lineage_serial,
        target_zone=int(AreaType.ACTIVE),
        target_lineage_serial=target.ref.lineage_serial,
        attack_id=attack_id,
    )


def build_active_post_attach_attack_completion(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    source_ref: PhysicalRef,
    target_ref: PhysicalRef,
) -> Optional[ActivePostAttachAttackCompletion]:
    """Prove only the going-second OT1 single-attack completion clause.

    This does not claim the unresolved opponent-derived attack-lock requirement
    or full requirement compliance.
    """

    if (
        not isinstance(state, PublicState)
        or not is_checked_public_state(state)
        or not isinstance(registry, PublicEffectRegistry)
        or not isinstance(source_ref, PhysicalRef)
        or not isinstance(target_ref, PhysicalRef)
        or not is_stable_main_state(state)
        or not state.source_combat_complete
        or not state.history_complete
        or state.source_options_fingerprint
        != semantic_options_fingerprint(legal_options)
        or state.attacked_this_turn
        or state.energy_attached
        or state.first_player not in (0, 1)
        or state.turn != 2
        or state.seat == state.first_player
        or (state.first_player if state.turn % 2 == 1 else 1 - state.first_player)
        != state.seat
        or state.own.asleep
        or state.own.paralyzed
        or state.own.confused
        or any(
            option.key.option_type == int(OptionType.ATTACK) for option in legal_options
        )
    ):
        return None
    attacker = state.own_active
    defender = state.opponent_active
    if (
        attacker is None
        or defender is None
        or len(state.own.active) != 1
        or len(state.opponent.active) != 1
        or target_ref != attacker.ref
        or target_ref.owner != state.seat
        or target_ref.zone != int(AreaType.ACTIVE)
        or source_ref.card_id != 6
        or source_ref.owner != state.seat
        or source_ref.zone != int(AreaType.HAND)
        or sum(ref_value == source_ref for ref_value in state.own.hand_refs) != 1
        or len(attacker.energy_types) != len(attacker.energy_refs)
    ):
        return None
    registry_audit = active_attack_completion_registry_audit(registry)
    if registry_audit is None:
        return None
    energy_profile = registry.effect_profile(6)
    target_profiles = tuple(
        profile
        for profile in registry.profiles
        if profile.card_id == defender.ref.card_id
    )
    if (
        len(target_profiles) != 1
        or not _is_exact_int(target_profiles[0].energy_type)
        or target_profiles[0].energy_type <= 0
        or target_profiles[0].energy_type == METAL_ENERGY_TYPE
    ):
        return None
    if (
        not registry.is_effectless_basic_energy(6)
        or energy_profile is None
        or energy_profile.energy_type != FIGHTING_ENERGY_TYPE
    ):
        return None
    card_profile = registry.profile(attacker.ref.card_id)
    if (
        card_profile is None
        or not card_profile.attack_ids
        or (state.opponent.prize_count <= 2 and card_profile.rule_box)
    ):
        return None

    energy_types_before = tuple(attacker.energy_types)
    energy_types_after = energy_types_before + (FIGHTING_ENERGY_TYPE,)
    pre_payable = []
    post_payable = []
    cost_by_attack = {}
    for attack_id in tuple(sorted(card_profile.attack_ids)):
        cost = _registered_attack_energy_cost(
            registry,
            int(attacker.ref.card_id),
            int(attack_id),
        )
        if cost is None:
            return None
        deficit_before = _typed_energy_deficit(energy_types_before, cost)
        deficit_after = _typed_energy_deficit(energy_types_after, cost)
        if deficit_before is None or deficit_after is None:
            return None
        attack = ATTACK_META_BY_ID[int(attack_id)]
        locked = (
            attack.semantics.same_attack_lock_next_own_turn
            and _same_attack_is_locked(state, attacker, int(attack_id))
        )
        if deficit_before == 0 and not locked:
            pre_payable.append(int(attack_id))
        if deficit_after == 0 and not locked:
            cost_by_attack[int(attack_id)] = cost
            post_payable.append(int(attack_id))
    if pre_payable or len(post_payable) != 1:
        return None

    attached_ref = PhysicalRef(
        card_id=6,
        serial=source_ref.serial,
        owner=state.seat,
        zone=int(AreaType.ENERGY),
        lineage_serial=source_ref.serial,
    )
    post_attacker = replace(
        attacker,
        energy_types=energy_types_after,
        energy_refs=attacker.energy_refs + (attached_ref,),
    )
    hypothetical_options = tuple(
        SemanticOption(
            index=index,
            key=_hypothetical_attack_key(
                state,
                post_attacker,
                defender,
                attack_id,
            ),
        )
        for index, attack_id in enumerate(post_payable)
    )
    try:
        post_state = _derive_checked_active_energy_attach_state(
            state,
            source_ref,
            FIGHTING_ENERGY_TYPE,
            hypothetical_options,
        )
    except ValueError:
        return None
    if post_state.own_active != post_attacker:
        return None
    table = build_attack_outcome_table(post_state, hypothetical_options, registry)
    if table.build_unknown_reasons or len(table.rows) != len(hypothetical_options):
        return None

    candidate_rows = []
    for outcome in table.rows:
        if not is_fully_exact_attack_completion_outcome(table, outcome):
            return None
        if outcome.final_damage is None:
            return None
        if outcome.final_damage <= 0:
            continue
        cost = cost_by_attack[outcome.attack_id]
        if (
            _typed_energy_deficit(energy_types_before, cost) != 1
            or _typed_energy_deficit(energy_types_after, cost) != 0
        ):
            continue
        future_lock_cost = outcome.future_lock_cost
        if future_lock_cost is None:
            return None
        candidate_rows.append(
            (
                outcome.attack_id,
                int(outcome.final_damage),
                int(future_lock_cost),
                cost,
            )
        )
    ranked = tuple(
        sorted(
            candidate_rows,
            key=lambda row: (-row[1], row[2], row[0], row[3]),
        )
    )
    # Existing direct attack selection changes rank shape for wins and Prize KOs.
    # A singleton makes the post-attach action identical under every such tier.
    if len(ranked) != 1:
        return None
    chosen = ranked[0]
    return ActivePostAttachAttackCompletion(
        catalog_sha256=registry_audit[0],
        persistent_trainer_audit_fingerprint=registry_audit[1],
        source_ref=source_ref,
        target_ref=target_ref,
        energy_types_before=energy_types_before,
        target_energy_type=target_profiles[0].energy_type,
        energy_types_after=energy_types_after,
        pre_payable=tuple(pre_payable),
        post_payable=tuple(post_payable),
        candidate_rows=ranked,
        chosen_attack_id=chosen[0],
        chosen_final_damage=chosen[1],
        chosen_future_lock_cost=chosen[2],
        chosen_energy_cost=chosen[3],
    )


def build_gust_attack_outcome_table(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    target_ref: PhysicalRef,
    current_attack_ids: Tuple[int, ...],
    *,
    evolution_source_ref: Optional[PhysicalRef] = None,
    evolution_target_ref: Optional[PhysicalRef] = None,
) -> Optional[Tuple[PublicState, BoundAttackOutcomeTable]]:
    """Build the checked current-attack surface after one exact public gust.

    The promoted Bench Pokémon and demoted Active preserve card, serial, and
    lineage identity; only their zones change. Opponent Active status flags
    are cleared because they belong to the Pokémon leaving the Active Spot.
    """

    if (
        not isinstance(state, PublicState)
        or not is_checked_public_state(state)
        or not isinstance(registry, PublicEffectRegistry)
        or not isinstance(target_ref, PhysicalRef)
        or state.source_options_fingerprint
        != semantic_options_fingerprint(legal_options)
        or not state.source_combat_complete
        or not is_stable_main_state(state)
        or not isinstance(current_attack_ids, tuple)
        or not current_attack_ids
        or any(
            not _is_exact_int(attack_id) or attack_id <= 0
            for attack_id in current_attack_ids
        )
        or len(set(current_attack_ids)) != len(current_attack_ids)
    ):
        return None

    base_state = state
    if evolution_source_ref is not None or evolution_target_ref is not None:
        if not isinstance(evolution_source_ref, PhysicalRef) or not isinstance(
            evolution_target_ref, PhysicalRef
        ):
            return None
        source_matches = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value == evolution_source_ref
        )
        target_matches = tuple(
            pokemon
            for pokemon in state.own.bench
            if pokemon.ref == evolution_target_ref
        )
        evolved_profile = (
            None
            if evolution_source_ref.card_id is None
            else registry.profile(evolution_source_ref.card_id)
        )
        base_profile = (
            None
            if evolution_target_ref.card_id is None
            else registry.profile(evolution_target_ref.card_id)
        )
        if (
            len(source_matches) != 1
            or len(target_matches) != 1
            or evolution_source_ref.card_id != 674
            or evolution_source_ref.owner != state.seat
            or evolution_source_ref.zone != int(AreaType.HAND)
            or evolution_target_ref.card_id != 673
            or evolution_target_ref.owner != state.seat
            or evolution_target_ref.zone != int(AreaType.BENCH)
            or evolved_profile is None
            or base_profile is None
            or evolved_profile.evolves_from != base_profile.card_name
        ):
            return None
        evolution_target = target_matches[0]
        damage = evolution_target.max_hp - evolution_target.remaining_hp
        evolved_hp = evolved_profile.hp - damage
        if damage < 0 or evolved_hp <= 0:
            return None
        evolved_ref = PhysicalRef(
            card_id=evolution_source_ref.card_id,
            serial=evolution_source_ref.serial,
            owner=state.seat,
            zone=int(AreaType.BENCH),
            lineage_serial=evolution_target.ref.lineage_serial,
        )
        pre_ref = replace(
            evolution_target.ref,
            zone=int(AreaType.PRE_EVOLUTION),
        )
        evolved = replace(
            evolution_target,
            ref=evolved_ref,
            hp=evolved_hp,
            max_hp=evolved_profile.hp,
            pre_evolution_refs=evolution_target.pre_evolution_refs + (pre_ref,),
        )
        post_bench = tuple(
            evolved if pokemon.ref == evolution_target_ref else pokemon
            for pokemon in state.own.bench
        )
        post_own = replace(
            state.own,
            bench=post_bench,
            hand_refs=tuple(
                ref_value
                for ref_value in state.own.hand_refs
                if ref_value != evolution_source_ref
            ),
            hand_count=state.own.hand_count - 1,
        )
        base_state = replace(
            state,
            own=post_own,
            turn_action_count=state.turn_action_count + 1,
        )
        object.__setattr__(
            base_state,
            "_builder_receipt",
            public_state_fingerprint(base_state),
        )
        if not is_checked_public_state(base_state):
            return None

    current_active = base_state.opponent_active
    target_matches = tuple(
        pokemon
        for pokemon in base_state.opponent.bench
        if pokemon.ref == target_ref
    )
    if current_active is None or len(target_matches) != 1:
        return None
    promoted = replace(
        target_matches[0],
        ref=replace(target_matches[0].ref, zone=int(AreaType.ACTIVE)),
    )
    demoted = replace(
        current_active,
        ref=replace(current_active.ref, zone=int(AreaType.BENCH)),
    )
    post_opponent = replace(
        base_state.opponent,
        active=(promoted,),
        bench=tuple(
            demoted if pokemon.ref == target_ref else pokemon
            for pokemon in base_state.opponent.bench
        ),
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )
    attacker = base_state.own_active
    if attacker is None:
        return None
    hypothetical_options = tuple(
        SemanticOption(
            index=index,
            key=_hypothetical_attack_key(
                base_state,
                attacker,
                promoted,
                int(attack_id),
            ),
        )
        for index, attack_id in enumerate(current_attack_ids)
    )
    post_state = replace(
        base_state,
        opponent=post_opponent,
        source_options_fingerprint=semantic_options_fingerprint(
            hypothetical_options
        ),
    )
    object.__setattr__(
        post_state,
        "_builder_receipt",
        public_state_fingerprint(post_state),
    )
    if not is_checked_public_state(post_state):
        return None
    return post_state, build_attack_outcome_table(
        post_state,
        hypothetical_options,
        registry,
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
    "ActivePostAttachAttackCompletion",
    "active_attack_completion_registry_audit",
    "AttackCallbackPreview",
    "AttackOutcome",
    "BoundAttackOutcomeTable",
    "OpponentAttackThreatRow",
    "OpponentAttackThreatSurface",
    "PostWallyProductiveAttack",
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
    "build_active_post_attach_attack_completion",
    "build_attack_outcome_table",
    "build_gust_attack_outcome_table",
    "build_post_wally_productive_attack",
    "build_public_opponent_attack_threat",
    "is_fully_exact_attack_completion_outcome",
    "semantic_options_fingerprint",
]
