"""Deterministic public-board features for the fixed Mega Lucario deck."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import secrets
from typing import Optional, Sequence, Tuple

try:  # Package import in tests.
    from .card_meta import ATTACK_META_BY_ID, CARD_META_BY_ID
    from .public_effects import (
        EFFECT_BINDINGS,
        EntryKind,
        PublicEffectRegistry,
    )
    from .resource_ledger import ResourceLedger
    from .state_view import (
        AreaType,
        AttackHistoryEntry,
        OptionType,
        PhysicalRef,
        PokemonView,
        PublicState,
        SemanticOption,
        is_checked_public_state,
        public_state_fingerprint,
        semantic_options_fingerprint,
    )
except ImportError:  # Flat submission import from main.py.
    from card_meta import ATTACK_META_BY_ID, CARD_META_BY_ID
    from public_effects import EFFECT_BINDINGS, EntryKind, PublicEffectRegistry
    from resource_ledger import ResourceLedger
    from state_view import (
        AreaType,
        AttackHistoryEntry,
        OptionType,
        PhysicalRef,
        PokemonView,
        PublicState,
        SemanticOption,
        is_checked_public_state,
        public_state_fingerprint,
        semantic_options_fingerprint,
    )


FIGHTING_ENERGY_CARD_ID = 6
FIGHTING_ENERGY_TYPE = 6
MAKUHITA_CARD_ID = 673
HARIYAMA_CARD_ID = 674
LUNATONE_CARD_ID = 675
SOLROCK_CARD_ID = 676
RIOLU_CARD_ID = 677
MEGA_LUCARIO_CARD_ID = 678
WALLY_CARD_ID = 1229
MEGA_BRAVE_ATTACK_ID = 983

_EVOLUTION_TARGET = {
    MAKUHITA_CARD_ID: HARIYAMA_CARD_ID,
    RIOLU_CARD_ID: MEGA_LUCARIO_CARD_ID,
}
_KNOWN_SPREAD_THREAT_CARD_IDS = frozenset((121, 648))
_FEATURE_ISSUER_TOKEN = object()
_FEATURE_INTEGRITY_KEY = secrets.token_bytes(32)


class PublicMatchupFlag(str, Enum):
    EX_DAMAGE_PREVENTION = "EX_DAMAGE_PREVENTION"
    ONE_PRIZE_MEDIUM_HP_RESISTANT = "ONE_PRIZE_MEDIUM_HP_RESISTANT"
    FIGHTING_WEAK_HIGH_PRIZE = "FIGHTING_WEAK_HIGH_PRIZE"
    BENCH_SPREAD_THREAT = "BENCH_SPREAD_THREAT"
    LARGE_PUBLIC_HAND = "LARGE_PUBLIC_HAND"


@dataclass(frozen=True)
class AttackEnergyDeficit:
    target_ref: PhysicalRef
    current_card_id: int
    minimum_attack_cost: Optional[int]
    attached_energy_count: int
    deficit_now: Optional[int]
    deficit_after_one_attach: Optional[int]

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.target_ref.sort_key(),
            self.current_card_id,
            self.minimum_attack_cost,
            self.attached_energy_count,
            self.deficit_now,
            self.deficit_after_one_attach,
        )


@dataclass(frozen=True)
class OpponentPokemonFeatures:
    ref: PhysicalRef
    remaining_hp: int
    prize_value: Optional[int]
    energy_types: Tuple[int, ...]
    energy_payable_attack_ids: Optional[Tuple[int, ...]]
    ready_attack_ids: Optional[Tuple[int, ...]]

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.ref.sort_key(),
            self.remaining_hp,
            self.prize_value,
            self.energy_types,
            self.energy_payable_attack_ids,
            self.ready_attack_ids,
        )


@dataclass(frozen=True)
class DeckFeatures:
    state_fingerprint: str
    semantic_options_fingerprint: str
    registry_digest: str
    own_active_ref: Optional[PhysicalRef]
    own_bench_refs: Tuple[PhysicalRef, ...]
    own_hand_refs: Tuple[PhysicalRef, ...]
    own_discard_refs: Tuple[PhysicalRef, ...]
    own_deck_count: int
    own_prizes_remaining: int
    manual_attach_used: bool
    supporter_used: bool
    retreat_used: bool
    attacked_this_turn: bool
    turn_number: int
    own_turn_number: int
    status_conditions: Tuple[str, ...]
    stadium_refs: Tuple[PhysicalRef, ...]
    last_attack_by_lineage: Tuple[AttackHistoryEntry, ...]
    opponent_active: Optional[OpponentPokemonFeatures]
    opponent_bench: Tuple[OpponentPokemonFeatures, ...]
    opponent_hand_count: int
    opponent_prizes_remaining: int
    public_flags: Tuple[PublicMatchupFlag, ...]
    public_damage_prevention: Optional[bool]
    public_bench_damage_threat: Optional[bool]
    public_gust_or_lock_threat: Optional[bool]
    engine_complete: bool
    missing_engine_card_ids: Tuple[int, ...]
    lucario_line_count: int
    mega_count: int
    hariyama_line_count: int
    ready_now: bool
    legal_attack_ids: Tuple[int, ...]
    ready_attacker_count: int
    ready_non_ex_attacker_count: int
    next_turn_ready_attacker_count: int
    discard_fighting_energy_count: int
    hand_fighting_energy_count: int
    attack_energy_deficit_by_target: Tuple[AttackEnergyDeficit, ...]
    safe_bench_slots: int
    board_out_risk: bool
    mega_brave_locked: Optional[bool]
    wally_reboot_candidate: bool
    wally_reboot_feasible: Optional[bool]
    cape_survival_delta: Optional[int]
    lunar_cycle_feasible: bool
    draw_buffer_after_plan: int
    unknown_reasons: Tuple[str, ...]
    _builder_token: object = dataclass_field(
        init=False,
        default=None,
        repr=False,
        compare=False,
    )
    _integrity_receipt: str = dataclass_field(
        init=False,
        default="",
        repr=False,
        compare=False,
    )

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.state_fingerprint,
            self.semantic_options_fingerprint,
            self.registry_digest,
            None if self.own_active_ref is None else self.own_active_ref.sort_key(),
            tuple(ref_value.sort_key() for ref_value in self.own_bench_refs),
            tuple(ref_value.sort_key() for ref_value in self.own_hand_refs),
            tuple(ref_value.sort_key() for ref_value in self.own_discard_refs),
            self.own_deck_count,
            self.own_prizes_remaining,
            self.manual_attach_used,
            self.supporter_used,
            self.retreat_used,
            self.attacked_this_turn,
            self.turn_number,
            self.own_turn_number,
            self.status_conditions,
            tuple(ref_value.sort_key() for ref_value in self.stadium_refs),
            tuple(entry.canonical() for entry in self.last_attack_by_lineage),
            None if self.opponent_active is None else self.opponent_active.canonical(),
            tuple(value.canonical() for value in self.opponent_bench),
            self.opponent_hand_count,
            self.opponent_prizes_remaining,
            tuple(value.value for value in self.public_flags),
            self.public_damage_prevention,
            self.public_bench_damage_threat,
            self.public_gust_or_lock_threat,
            self.engine_complete,
            self.missing_engine_card_ids,
            self.lucario_line_count,
            self.mega_count,
            self.hariyama_line_count,
            self.ready_now,
            self.legal_attack_ids,
            self.ready_attacker_count,
            self.ready_non_ex_attacker_count,
            self.next_turn_ready_attacker_count,
            self.discard_fighting_energy_count,
            self.hand_fighting_energy_count,
            tuple(value.canonical() for value in self.attack_energy_deficit_by_target),
            self.safe_bench_slots,
            self.board_out_risk,
            self.mega_brave_locked,
            self.wally_reboot_candidate,
            self.wally_reboot_feasible,
            self.cape_survival_delta,
            self.lunar_cycle_feasible,
            self.draw_buffer_after_plan,
            self.unknown_reasons,
        )

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.canonical(),
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def verify_integrity(self) -> bool:
        if self._builder_token is not _FEATURE_ISSUER_TOKEN:
            return False
        expected = hashlib.sha256(
            _FEATURE_INTEGRITY_KEY + self.digest().encode("ascii")
        ).hexdigest()
        return secrets.compare_digest(self._integrity_receipt, expected)

    def matches(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        registry: PublicEffectRegistry,
    ) -> bool:
        return (
            self.verify_integrity()
            and is_checked_public_state(state)
            and isinstance(registry, PublicEffectRegistry)
            and self.state_fingerprint == public_state_fingerprint(state)
            and self.semantic_options_fingerprint
            == semantic_options_fingerprint(legal_options)
            and self.semantic_options_fingerprint == state.source_options_fingerprint
            and self.registry_digest == registry.digest
        )


def _own_turn_number(state: PublicState) -> int:
    if state.turn <= 0:
        return 0
    return (
        (state.turn + 1) // 2
        if state.seat == state.first_player
        else state.turn // 2
    )


def _minimum_attack_cost(card_id: int) -> Optional[int]:
    card = CARD_META_BY_ID.get(card_id)
    if card is None or not card.attack_ids:
        return None
    costs = tuple(
        len(ATTACK_META_BY_ID[attack_id].energy_cost)
        for attack_id in card.attack_ids
        if attack_id in ATTACK_META_BY_ID
    )
    return min(costs) if costs else None


def _energy_deficit(pokemon: PokemonView) -> AttackEnergyDeficit:
    cost = _minimum_attack_cost(pokemon.ref.card_id)
    attached = len(pokemon.energy_types)
    return AttackEnergyDeficit(
        target_ref=pokemon.ref,
        current_card_id=pokemon.ref.card_id,
        minimum_attack_cost=cost,
        attached_energy_count=attached,
        deficit_now=None if cost is None else max(0, cost - attached),
        deficit_after_one_attach=(
            None if cost is None else max(0, cost - attached - 1)
        ),
    )


def _resource_ready(pokemon: PokemonView) -> bool:
    cost = _minimum_attack_cost(pokemon.ref.card_id)
    return cost is not None and len(pokemon.energy_types) >= cost


def _next_turn_energy_deficit(
    pokemon: PokemonView,
    hand_card_ids: frozenset[int],
) -> Optional[int]:
    candidate_card_ids = [pokemon.ref.card_id]
    evolution_card_id = _EVOLUTION_TARGET.get(pokemon.ref.card_id)
    if evolution_card_id is not None and evolution_card_id in hand_card_ids:
        candidate_card_ids.append(evolution_card_id)
    costs = tuple(
        cost
        for cost in (_minimum_attack_cost(card_id) for card_id in candidate_card_ids)
        if cost is not None
    )
    if not costs:
        return None
    return max(0, min(costs) - len(pokemon.energy_types))


def _registered_attack_cost(
    registry: PublicEffectRegistry,
    card_id: int,
    attack_id: int,
) -> Optional[Tuple[int, ...]]:
    matches = tuple(
        binding
        for binding in EFFECT_BINDINGS
        if binding.entry_kind is EntryKind.ATTACK
        and binding.card_id == card_id
        and binding.entry_id == attack_id
        and registry.binding_admitted(
            binding.effect_id,
            card_id=binding.card_id,
            entry_id=binding.entry_id,
        )
    )
    return matches[0].energy_cost if len(matches) == 1 else None


def _can_pay_energy(
    attached_energy_types: Sequence[int],
    cost: Sequence[int],
) -> bool:
    available = Counter(int(value) for value in attached_energy_types)
    required = Counter(int(value) for value in cost)
    return all(available[energy_type] >= count for energy_type, count in required.items())


def _opponent_pokemon_features(
    pokemon: PokemonView,
    registry: PublicEffectRegistry,
) -> Tuple[OpponentPokemonFeatures, Tuple[str, ...]]:
    profile = registry.profile(pokemon.ref.card_id)
    reasons = []
    prize_value = None if profile is None else profile.prize_value
    energy_payable_attack_ids: Optional[Tuple[int, ...]] = None
    if profile is None:
        reasons.append(
            "MISSING_OPPONENT_PROFILE:{0}".format(pokemon.ref.card_id)
        )
    else:
        costs = tuple(
            (
                attack_id,
                _registered_attack_cost(
                    registry,
                    pokemon.ref.card_id,
                    attack_id,
                ),
            )
            for attack_id in profile.attack_ids
        )
        if all(cost is not None for _, cost in costs):
            energy_payable_attack_ids = tuple(
                attack_id
                for attack_id, cost in costs
                if cost is not None and _can_pay_energy(pokemon.energy_types, cost)
            )
        else:
            reasons.append(
                "OPPONENT_ATTACK_COST_NOT_PROVEN:{0}".format(
                    pokemon.ref.card_id
                )
            )
        if profile.attack_ids:
            reasons.append(
                "OPPONENT_ATTACK_LEGALITY_NOT_PROVEN:{0}".format(
                    pokemon.ref.card_id
                )
            )
    return (
        OpponentPokemonFeatures(
            ref=pokemon.ref,
            remaining_hp=pokemon.remaining_hp,
            prize_value=prize_value,
            energy_types=tuple(pokemon.energy_types),
            energy_payable_attack_ids=energy_payable_attack_ids,
            ready_attack_ids=None,
        ),
        tuple(reasons),
    )


def _public_flags(
    state: PublicState,
    registry: PublicEffectRegistry,
) -> Tuple[
    Tuple[PublicMatchupFlag, ...],
    Optional[bool],
    Optional[bool],
    Tuple[str, ...],
]:
    flags = set()
    reasons = []
    active = state.opponent_active
    own_active = state.own_active
    active_profile = (
        None
        if active is None
        else registry.profile(active.ref.card_id)
    )
    attacker_profile = (
        None
        if own_active is None
        else registry.profile(own_active.ref.card_id)
    )
    damage_prevention: Optional[bool] = None
    if active_profile is None:
        reasons.append("OPPONENT_ACTIVE_PROFILE_NOT_PROVEN")
    elif not active_profile.all_skills_registered:
        reasons.append("OPPONENT_ACTIVE_SKILLS_NOT_FULLY_REGISTERED")
    else:
        active_effect_ids = set(active_profile.registered_skill_effect_ids)
        carrier_refs = (
            ()
            if active is None
            else active.energy_refs + active.tool_refs
        ) + state.stadium_refs
        carrier_profiles = tuple(
            registry.effect_profile(ref_value.card_id)
            for ref_value in carrier_refs
        )
        carriers_complete = all(
            profile is not None and profile.all_skills_registered
            for profile in carrier_profiles
        )
        carrier_effect_ids = {
            effect_id
            for profile in carrier_profiles
            if profile is not None
            for effect_id in profile.registered_skill_effect_ids
        }
        ex_prevention = bool(
            {"SAFEGUARD", "MYSTERIOUS_ROCK_INN"} & active_effect_ids
            or (
                "NEUTRALIZATION_ZONE" in carrier_effect_ids
                and not active_profile.rule_box
            )
        )
        conditional_impervious = "IMPERVIOUS_SHELL" in active_effect_ids
        if attacker_profile is None:
            reasons.append("OWN_ACTIVE_PROFILE_NOT_PROVEN")
        elif carriers_complete and not conditional_impervious:
            damage_prevention = bool(
                (
                    attacker_profile.rule_box
                    and bool(
                        {"SAFEGUARD", "MYSTERIOUS_ROCK_INN"}
                        & active_effect_ids
                    )
                )
                or (
                    attacker_profile.has_ability
                    and "CORNERSTONE_STANCE" in active_effect_ids
                )
                or (
                    attacker_profile.rule_box
                    and "NEUTRALIZATION_ZONE" in carrier_effect_ids
                    and not active_profile.rule_box
                )
            )
        elif conditional_impervious:
            reasons.append("DAMAGE_CONDITIONAL_PREVENTION_NOT_PROVEN")
        else:
            reasons.append("PUBLIC_EFFECT_CARRIER_PROFILE_NOT_PROVEN")
        if ex_prevention:
            flags.add(PublicMatchupFlag.EX_DAMAGE_PREVENTION)
        if (
            active_profile.prize_value == 1
            and 100 <= active_profile.hp <= 200
            and active_profile.resistance == FIGHTING_ENERGY_TYPE
        ):
            flags.add(PublicMatchupFlag.ONE_PRIZE_MEDIUM_HP_RESISTANT)

    opponent_board = state.opponent.active + state.opponent.bench
    for pokemon in opponent_board:
        profile = registry.profile(pokemon.ref.card_id)
        if (
            profile is not None
            and profile.prize_value >= 2
            and profile.weakness == FIGHTING_ENERGY_TYPE
        ):
            flags.add(PublicMatchupFlag.FIGHTING_WEAK_HIGH_PRIZE)
    spread_present = any(
        pokemon.ref.card_id in _KNOWN_SPREAD_THREAT_CARD_IDS
        for pokemon in opponent_board
    )
    bench_damage_threat: Optional[bool] = True if spread_present else None
    if spread_present:
        flags.add(PublicMatchupFlag.BENCH_SPREAD_THREAT)
    else:
        reasons.append("BENCH_SPREAD_THREAT_ABSENCE_NOT_PROVEN")
    if state.opponent.hand_count >= 8:
        flags.add(PublicMatchupFlag.LARGE_PUBLIC_HAND)
    return (
        tuple(sorted(flags, key=lambda value: value.value)),
        damage_prevention,
        bench_damage_threat,
        tuple(reasons),
    )


def build_resource_ledger(state: PublicState) -> ResourceLedger:
    """Build one exact-owner ledger from every currently visible own card."""

    if not is_checked_public_state(state):
        raise ValueError("resource ledger requires a checked PublicState")
    refs = list(state.own.hand_refs)
    refs.extend(state.own.discard_refs)
    refs.extend(state.own.prize_refs)
    for pokemon in state.own.active + state.own.bench:
        refs.append(pokemon.ref)
        refs.extend(pokemon.energy_refs)
        refs.extend(pokemon.tool_refs)
        refs.extend(pokemon.pre_evolution_refs)
    refs.extend(
        ref_value
        for ref_value in state.stadium_refs + state.looking_refs
        if ref_value.owner == state.seat
    )
    return ResourceLedger(tuple(refs))


def build_deck_features(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
) -> DeckFeatures:
    """Derive immutable deck features without hidden information or deck labels."""

    if not is_checked_public_state(state):
        raise ValueError("deck features require a checked PublicState")
    if not state.source_combat_complete or not state.history_complete:
        raise ValueError(
            "deck features require complete public combat and history sources"
        )
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("deck features require a checked PublicEffectRegistry")
    options_fingerprint = semantic_options_fingerprint(legal_options)
    if state.source_options_fingerprint != options_fingerprint:
        raise ValueError("deck features require options from the same observation")

    own_board = state.own.active + state.own.bench
    own_board_card_ids = tuple(pokemon.ref.card_id for pokemon in own_board)
    hand_card_ids = frozenset(ref_value.card_id for ref_value in state.own.hand_refs)
    engine_complete = (
        LUNATONE_CARD_ID in own_board_card_ids
        and SOLROCK_CARD_ID in own_board_card_ids
    )
    missing_engine = tuple(
        card_id
        for card_id in (LUNATONE_CARD_ID, SOLROCK_CARD_ID)
        if card_id not in own_board_card_ids
    )
    legal_attack_ids = tuple(
        sorted(
            {
                int(option.key.attack_id)
                for option in legal_options
                if option.key.option_type == int(OptionType.ATTACK)
                and isinstance(option.key.attack_id, int)
                and not isinstance(option.key.attack_id, bool)
                and option.key.attack_id > 0
            }
        )
    )
    resource_ready = tuple(
        pokemon for pokemon in own_board if _resource_ready(pokemon)
    )
    ready_non_ex = tuple(
        pokemon
        for pokemon in resource_ready
        if (
            pokemon.ref.card_id in CARD_META_BY_ID
            and not CARD_META_BY_ID[pokemon.ref.card_id].ex
            and not CARD_META_BY_ID[pokemon.ref.card_id].mega_ex
        )
    )
    hand_fighting = sum(
        ref_value.card_id == FIGHTING_ENERGY_CARD_ID
        for ref_value in state.own.hand_refs
    )
    next_turn_deficits = tuple(
        _next_turn_energy_deficit(pokemon, hand_card_ids)
        for pokemon in state.own.bench
    )
    next_turn_ready_count = sum(
        deficit == 0 for deficit in next_turn_deficits
    ) + int(
        hand_fighting > 0
        and any(deficit == 1 for deficit in next_turn_deficits)
    )
    deficits = tuple(
        sorted(
            (_energy_deficit(pokemon) for pokemon in own_board),
            key=lambda value: value.target_ref.sort_key(),
        )
    )

    opponent_values = []
    unknown_reasons = []
    for pokemon in state.opponent.active + state.opponent.bench:
        value, reasons = _opponent_pokemon_features(pokemon, registry)
        opponent_values.append(value)
        unknown_reasons.extend(reasons)
    opponent_active = opponent_values[0] if state.opponent.active else None
    opponent_bench = tuple(
        sorted(
            opponent_values[len(state.opponent.active) :],
            key=lambda value: value.ref.sort_key(),
        )
    )
    flags, prevention, spread_threat, flag_reasons = _public_flags(
        state,
        registry,
    )
    unknown_reasons.extend(flag_reasons)
    unknown_reasons.extend(
        (
            "PUBLIC_GUST_OR_LOCK_THREAT_NOT_PROVEN",
            "CAPE_SURVIVAL_DELTA_NOT_PROVEN",
        )
    )

    active = state.own_active
    mega_brave_locked: Optional[bool]
    if active is None or active.ref.card_id != MEGA_LUCARIO_CARD_ID:
        mega_brave_locked = False
    elif not state.history_complete or active.ref.lineage_serial is None:
        mega_brave_locked = None
        unknown_reasons.append("MEGA_BRAVE_HISTORY_NOT_PROVEN")
    else:
        mega_brave_locked = any(
            entry.owner == state.seat
            and entry.lineage_serial == active.ref.lineage_serial
            and entry.attack_id == MEGA_BRAVE_ATTACK_ID
            and entry.turn == state.turn - 2
            for entry in state.last_attack_by_lineage
        )

    wally_option_legal = any(
        option.key.option_type == int(OptionType.PLAY)
        and option.key.card_id == WALLY_CARD_ID
        for option in legal_options
    )
    wally_reboot_candidate = (
        WALLY_CARD_ID in hand_card_ids
        and wally_option_legal
        and not state.supporter_played
        and not state.energy_attached
        and active is not None
        and active.ref.card_id == MEGA_LUCARIO_CARD_ID
        and active.damage > 0
        and any(
            ref_value.card_id == FIGHTING_ENERGY_CARD_ID
            for ref_value in active.energy_refs
        )
        and not state.own.asleep
        and not state.own.paralyzed
        and not state.own.confused
    )
    if wally_reboot_candidate:
        unknown_reasons.append("WALLY_REBOOT_SURVIVAL_NOT_PROVEN")
    lunar_option_legal = any(
        option.key.option_type in (
            int(OptionType.ABILITY),
            int(OptionType.SKILL),
        )
        and option.key.card_id == LUNATONE_CARD_ID
        for option in legal_options
    )
    active_deficit = next(
        (
            value.deficit_now
            for value in deficits
            if active is not None and value.target_ref == active.ref
        ),
        None,
    )
    current_attach_reserve: Optional[int] = 0
    if not state.energy_attached and not legal_attack_ids:
        if active is None or active_deficit is None:
            current_attach_reserve = None
            unknown_reasons.append("CURRENT_ATTACK_ENERGY_RESERVE_NOT_PROVEN")
        else:
            current_attach_reserve = int(active_deficit > 0)
    discard_fighting = sum(
        ref_value.card_id == FIGHTING_ENERGY_CARD_ID
        for ref_value in state.own.discard_refs
    )
    status_conditions = tuple(
        name
        for name, active_value in (
            ("ASLEEP", state.own.asleep),
            ("BURNED", state.own.burned),
            ("CONFUSED", state.own.confused),
            ("PARALYZED", state.own.paralyzed),
            ("POISONED", state.own.poisoned),
        )
        if active_value
    )
    features = DeckFeatures(
        state_fingerprint=public_state_fingerprint(state),
        semantic_options_fingerprint=options_fingerprint,
        registry_digest=registry.digest,
        own_active_ref=None if active is None else active.ref,
        own_bench_refs=tuple(pokemon.ref for pokemon in state.own.bench),
        own_hand_refs=state.own.hand_refs,
        own_discard_refs=state.own.discard_refs,
        own_deck_count=state.own.deck_count,
        own_prizes_remaining=state.own.prize_count,
        manual_attach_used=state.energy_attached,
        supporter_used=state.supporter_played,
        retreat_used=state.retreated,
        attacked_this_turn=state.attacked_this_turn,
        turn_number=state.turn,
        own_turn_number=_own_turn_number(state),
        status_conditions=status_conditions,
        stadium_refs=state.stadium_refs,
        last_attack_by_lineage=state.last_attack_by_lineage,
        opponent_active=opponent_active,
        opponent_bench=opponent_bench,
        opponent_hand_count=state.opponent.hand_count,
        opponent_prizes_remaining=state.opponent.prize_count,
        public_flags=flags,
        public_damage_prevention=prevention,
        public_bench_damage_threat=spread_threat,
        public_gust_or_lock_threat=None,
        engine_complete=engine_complete,
        missing_engine_card_ids=missing_engine,
        lucario_line_count=sum(
            card_id in (RIOLU_CARD_ID, MEGA_LUCARIO_CARD_ID)
            for card_id in own_board_card_ids
        ),
        mega_count=sum(
            card_id == MEGA_LUCARIO_CARD_ID for card_id in own_board_card_ids
        ),
        hariyama_line_count=sum(
            card_id in (MAKUHITA_CARD_ID, HARIYAMA_CARD_ID)
            for card_id in own_board_card_ids
        ),
        ready_now=bool(legal_attack_ids),
        legal_attack_ids=legal_attack_ids,
        ready_attacker_count=len(resource_ready),
        ready_non_ex_attacker_count=len(ready_non_ex),
        next_turn_ready_attacker_count=next_turn_ready_count,
        discard_fighting_energy_count=discard_fighting,
        hand_fighting_energy_count=hand_fighting,
        attack_energy_deficit_by_target=deficits,
        safe_bench_slots=max(
            0,
            state.own.bench_max - len(state.own.bench) - 1,
        ),
        board_out_risk=len(own_board) <= 1,
        mega_brave_locked=mega_brave_locked,
        wally_reboot_candidate=wally_reboot_candidate,
        wally_reboot_feasible=None,
        cape_survival_delta=None,
        lunar_cycle_feasible=(
            engine_complete
            and lunar_option_legal
            and current_attach_reserve is not None
            and hand_fighting > current_attach_reserve
            and state.own.deck_count >= 4
        ),
        draw_buffer_after_plan=state.own.deck_count - 1,
        unknown_reasons=tuple(sorted(set(unknown_reasons))),
    )
    object.__setattr__(features, "_builder_token", _FEATURE_ISSUER_TOKEN)
    object.__setattr__(
        features,
        "_integrity_receipt",
        hashlib.sha256(
            _FEATURE_INTEGRITY_KEY + features.digest().encode("ascii")
        ).hexdigest(),
    )
    if not features.matches(state, legal_options, registry):
        raise RuntimeError("deck feature binding invariant failed")
    return features


__all__ = [
    "AttackEnergyDeficit",
    "DeckFeatures",
    "FIGHTING_ENERGY_CARD_ID",
    "FIGHTING_ENERGY_TYPE",
    "HARIYAMA_CARD_ID",
    "LUNATONE_CARD_ID",
    "MAKUHITA_CARD_ID",
    "MEGA_BRAVE_ATTACK_ID",
    "MEGA_LUCARIO_CARD_ID",
    "OpponentPokemonFeatures",
    "PublicMatchupFlag",
    "RIOLU_CARD_ID",
    "SOLROCK_CARD_ID",
    "WALLY_CARD_ID",
    "build_deck_features",
    "build_resource_ledger",
]
