"""Finite, checked route enumeration for the Mega Lucario deck."""

from __future__ import annotations

import hashlib
import json
from math import ceil
from typing import Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import (
        BoundAttackOutcomeTable,
    )
    from .card_meta import ATTACK_META_BY_ID, CARD_META_BY_ID
    from .certificates import (
        CertificateKind,
        ACTIVE_ATTACK_COMPLETION_RULE_ID,
        active_post_attach_attack_completion_proof,
        attack_outcome_proof,
        deck_rule_proof,
        basic_bench_proof,
        first_turn_riolu_attach_proof,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
        verify_cape_survival_certificate,
        verify_gust_dominance_certificate,
        verify_wally_survival_certificate,
    )
    from .features import DeckFeatures, PublicMatchupFlag, build_resource_ledger
    from .public_effects import EFFECT_BINDINGS, EntryKind, PublicEffectRegistry
    from .resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        ResourceLedger,
        prove_deck_availability_from_state,
    )
    from .resolver import (
        Proposal,
        ResourceCost,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from .state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticOption,
    )
    from .transactions import (
        build_aura_jab_plan,
        build_boss_gust_plan,
        build_hariyama_gust_plan,
        build_switch_plan,
        build_deck_search_plan,
        build_lunar_cycle_plan,
        build_poke_pad_core_search_plan,
        build_ultra_ball_plan,
        build_wally_plan,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import (
        BoundAttackOutcomeTable,
    )
    from card_meta import ATTACK_META_BY_ID, CARD_META_BY_ID
    from certificates import (
        deck_rule_proof,
        CertificateKind,
        ACTIVE_ATTACK_COMPLETION_RULE_ID,
        active_post_attach_attack_completion_proof,
        attack_outcome_proof,
        basic_bench_proof,
        first_turn_riolu_attach_proof,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
        verify_cape_survival_certificate,
        verify_gust_dominance_certificate,
        verify_wally_survival_certificate,
    )
    from features import DeckFeatures, PublicMatchupFlag, build_resource_ledger
    from public_effects import EFFECT_BINDINGS, EntryKind, PublicEffectRegistry
    from resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        prove_deck_availability_from_state,
        ResourceLedger,
    )
    from resolver import (
        Proposal,
        ResourceCost,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticOption,
    )
    from transactions import (
        build_aura_jab_plan,
        build_deck_search_plan,
        build_boss_gust_plan,
        build_hariyama_gust_plan,
        build_switch_plan,
        build_lunar_cycle_plan,
        build_poke_pad_core_search_plan,
        build_ultra_ball_plan,
        build_wally_plan,
    )


_ATTACK_TIERS = {
    CertificateKind.WIN_NOW: ResolverTier.EXACT_WIN_NOW,
    CertificateKind.PRIZE_GAIN_NOW: ResolverTier.EXACT_CURRENT_TURN_PRIZE,
    CertificateKind.ATTACK_COMPLETION: ResolverTier.BEST_CERTIFIED_ATTACK,
}


def _semantic_key_suffix(action_spec: ActionSpec) -> str:
    payload = json.dumps(
        action_spec.canonical(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def enumerate_attack_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Enumerate direct attacks whose result can be certified from public state."""

    if not isinstance(state, PublicState):
        raise ValueError("attack routes require a PublicState")
    if not isinstance(attack_outcomes, BoundAttackOutcomeTable):
        raise ValueError("attack routes require a checked attack outcome table")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("attack routes require a checked public effect registry")
    if not attack_outcomes.matches(state, legal_options, registry):
        return ()

    proposals = []
    for outcome in attack_outcomes.rows:
        action_spec = ActionSpec.single(outcome.option_key)
        try:
            proof = attack_outcome_proof(
                state,
                legal_options,
                registry,
                attack_outcomes,
                action_spec,
            )
        except ValueError:
            continue
        tier = _ATTACK_TIERS.get(proof.kind)
        if tier is None:
            continue
        proposals.append(
            Proposal(
                rule_id="DIRECT_{0}_{1}_{2}".format(
                    proof.kind.name,
                    outcome.attack_id,
                    _semantic_key_suffix(action_spec),
                ),
                tier=tier,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            )
        )
    return tuple(
        sorted(
            proposals,
            key=lambda proposal: (
                int(proposal.tier),
                proposal.rule_id,
                proposal.action_spec.canonical(),
            ),
        )
    )


def enumerate_basic_bench_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Enumerate only role-improving, flex-slot-safe Basic placements."""

    if not isinstance(state, PublicState):
        raise ValueError("Basic Bench routes require a PublicState")
    if not isinstance(features, DeckFeatures):
        raise ValueError("Basic Bench routes require checked DeckFeatures")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Basic Bench routes require a checked registry")
    if not features.matches(state, legal_options, registry):
        return ()

    proposals = []
    for option in legal_options:
        if option.key.option_type != int(OptionType.PLAY):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = basic_bench_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
            )
        except ValueError:
            continue
        proposals.append(
            Proposal(
                rule_id="BASIC_BENCH_{0}_{1}_{2}".format(
                    proof.fact("purpose"),
                    option.key.card_id,
                    _semantic_key_suffix(action_spec),
                ),
                tier=ResolverTier.SAFE_ENGINE_COMPLETION,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            )
        )
    return tuple(
        sorted(
            proposals,
            key=lambda proposal: (
                int(proposal.tier),
                proposal.deterministic_tiebreak,
                proposal.rule_id,
                proposal.action_spec.canonical(),
            ),
        )
    )


def enumerate_first_turn_riolu_attach_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit at most one exact default-clause R-ATTACH-001 proposal."""

    if not isinstance(state, PublicState):
        raise ValueError("first-turn Riolu attach routes require a PublicState")
    if not isinstance(features, DeckFeatures):
        raise ValueError("first-turn Riolu attach routes require DeckFeatures")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("first-turn Riolu attach routes require a checked registry")
    if not features.matches(state, legal_options, registry):
        return ()

    for option in legal_options:
        if option.key.option_type != int(OptionType.ATTACH):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = first_turn_riolu_attach_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
            )
        except ValueError:
            continue
        source_refs = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == proof.fact("source_ref")
        )
        if len(source_refs) != 1:
            continue
        proposal = Proposal(
            rule_id="R_ATTACH_001_{0}".format(
                _semantic_key_suffix(action_spec),
            ),
            tier=ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            action_spec=action_spec,
            certificate_kind=CertificateKind.FIRST_ATTACK_ACCELERATION,
            proof=proof,
            resource_cost=ResourceCost(source_refs),
            reservation_ids=(MANUAL_ATTACH_ENERGY_RESERVATION_ID,),
            deterministic_tiebreak=canonical_proposal_tiebreak(
                action_spec,
                proof,
            ),
        )
        return (proposal,)
    return ()


def enumerate_active_attack_completion_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit at most one exact current-turn Active attack completion."""

    if not isinstance(state, PublicState):
        raise ValueError("Active attack completion routes require a PublicState")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Active attack completion routes require a checked registry")
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.ATTACH):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = active_post_attach_attack_completion_proof(
                state,
                legal_options,
                registry,
                action_spec,
            )
        except ValueError:
            continue
        source_refs = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == proof.fact("source_ref")
        )
        if len(source_refs) != 1:
            continue
        proposal = Proposal(
            rule_id=ACTIVE_ATTACK_COMPLETION_RULE_ID,
            tier=ResolverTier.ATTACK_COMPLETION,
            action_spec=action_spec,
            certificate_kind=CertificateKind.ATTACK_COMPLETION,
            proof=proof,
            resource_cost=ResourceCost(source_refs),
            reservation_ids=(ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,),
            deterministic_tiebreak=canonical_proposal_tiebreak(
                action_spec,
                proof,
            ),
        )
        return (proposal,)
    return ()


def enumerate_poke_pad_core_search_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit at most one closed Poke Pad core-formation transaction."""

    if not isinstance(state, PublicState):
        raise ValueError("Poke Pad routes require a PublicState")
    if not isinstance(features, DeckFeatures):
        raise ValueError("Poke Pad routes require checked DeckFeatures")
    if not isinstance(attack_outcomes, BoundAttackOutcomeTable):
        raise ValueError("Poke Pad routes require a checked attack table")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Poke Pad routes require a checked registry")
    if not features.matches(state, legal_options, registry):
        return ()
    classes = poke_pad_core_eligible_classes(state)
    if not classes:
        return ()
    acceptable_ids = tuple(
        sorted(card_id for card_class in classes for card_id in card_class)
    )
    availability = prove_deck_availability_from_state(
        state,
        acceptable_ids,
        required_count=1,
    )
    if not availability.is_guaranteed:
        return ()
    for option in sorted(
        legal_options,
        key=lambda value: value.key.sort_key(),
    ):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1152:
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = poke_pad_core_formation_proof(
                state,
                legal_options,
                registry,
                features,
                attack_outcomes,
                availability,
                action_spec,
            )
        except ValueError:
            continue
        source_fact = proof.fact("source_ref")
        source_refs = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        if len(source_refs) != 1:
            continue
        transaction_plan = build_poke_pad_core_search_plan(
            state,
            source_refs[0],
            action_spec,
            classes,
            availability,
            proof.digest(),
        )
        return (
            Proposal(
                rule_id="R_SEARCH_POKE_PAD_CORE_FORMATION_V1",
                tier=ResolverTier.ROUTE_CRITICAL_SEARCH,
                action_spec=action_spec,
                certificate_kind=CertificateKind.RESOURCE_IMPROVEMENT,
                proof=proof,
                resource_cost=ResourceCost(source_refs),
                transaction_plan=transaction_plan,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            ),
        )
    return ()


def _exact_hand_ref(state: PublicState, option: SemanticOption) -> PhysicalRef | None:
    key = option.key
    matches = tuple(
        ref_value
        for ref_value in state.own.hand_refs
        if ref_value.card_id == key.card_id
        and ref_value.serial == key.card_serial
        and ref_value.owner == state.seat
        and ref_value.zone == int(AreaType.HAND)
    )
    return matches[0] if len(matches) == 1 else None


def _board_pokemon_for_option(state: PublicState, option: SemanticOption):
    key = option.key
    return next(
        (
            pokemon
            for pokemon in state.own.active + state.own.bench
            if pokemon.ref.zone == key.target_zone
            and pokemon.ref.lineage_serial == key.target_lineage_serial
        ),
        None,
    )


def _in_play_source_ref(
    state: PublicState, option: SemanticOption
) -> PhysicalRef | None:
    key = option.key
    matches = tuple(
        pokemon.ref
        for pokemon in state.own.active + state.own.bench
        if pokemon.ref.card_id == key.card_id
        and pokemon.ref.serial == key.card_serial
        and pokemon.ref.zone == key.source_zone
        and pokemon.ref.lineage_serial == key.source_lineage_serial
    )
    return matches[0] if len(matches) == 1 else None


def enumerate_fighting_gong_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Search only a guaranteed route-critical Fighting target."""

    if not features.matches(state, legal_options, registry):
        return ()
    hand_ids = tuple(ref_value.card_id for ref_value in state.own.hand_refs)
    active_deficit = next(
        (
            value.deficit_now
            for value in features.attack_energy_deficit_by_target
            if state.own_active is not None and value.target_ref == state.own_active.ref
        ),
        None,
    )
    active_solrock_attach_legal = any(
        option.key.option_type == int(OptionType.ATTACH)
        and option.key.card_id == 6
        and _exact_hand_ref(state, option) is not None
        and _board_pokemon_for_option(state, option) == state.own_active
        for option in legal_options
    )
    classes: Tuple[Tuple[int, ...], ...] = ()
    purpose = ""
    if (
        not features.ready_now
        and not state.energy_attached
        and features.hand_fighting_energy_count == 0
        and active_deficit == 1
    ):
        classes = ((6,),)
        purpose = "CURRENT_ATTACK_ENERGY"
    elif (
        state.own_active is not None
        and state.own_active.ref.card_id == 676
        and state.seat == state.first_player
        and features.own_turn_number == 1
        and 675 not in hand_ids
        and all(
            pokemon.ref.card_id != 675 for pokemon in state.own.active + state.own.bench
        )
    ):
        if (
            not any(
                ref_value.card_id in (677, 678) for ref_value in state.own.hand_refs
            )
            and not any(
                pokemon.ref.card_id in (677, 678)
                for pokemon in state.own.active + state.own.bench
            )
            and len(state.own.bench) < state.own.bench_max
            and not state.energy_attached
            and features.hand_fighting_energy_count > 0
            and active_deficit == 1
            and active_solrock_attach_legal
            and not features.ready_now
            and not features.wally_reboot_candidate
        ):
            classes = ((675,), (677,), (6,))
            purpose = "STALLED_SOLROCK_OPENING"
    elif features.missing_engine_card_ids:
        classes = tuple((card_id,) for card_id in features.missing_engine_card_ids)
        purpose = "MISSING_ENGINE"
    elif features.lucario_line_count == 0 and 677 not in hand_ids:
        classes = ((677,),)
        purpose = "FIRST_RIOLU"
    elif (
        features.hariyama_line_count == 0
        and 673 not in hand_ids
        and PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    ):
        classes = ((673,),)
        purpose = "FIRST_MAKUHITA"
    if not classes or state.own.deck_count <= 1:
        return ()
    acceptable_ids = tuple(sorted(card_id for values in classes for card_id in values))
    availability = prove_deck_availability_from_state(
        state,
        acceptable_ids,
        required_count=1,
    )
    if not availability.is_guaranteed:
        return ()
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1142:
            continue
        source_ref = _exact_hand_ref(state, option)
        if source_ref is None:
            continue
        action_spec = ActionSpec.single(option.key)
        proof = deck_rule_proof(
            state,
            legal_options,
            registry,
            features,
            action_spec,
            route_code="R_SEARCH_FIGHTING_GONG_ROUTE_CRITICAL_V1",
            kind=CertificateKind.RESOURCE_IMPROVEMENT,
            facts={
                "route_priority": 0,
                "purpose": purpose,
                "ordered_card_id_classes": classes,
                "availability": availability.canonical(),
                "source_ref": source_ref,
            },
        )
        plan = build_deck_search_plan(
            state,
            source_ref,
            action_spec,
            classes,
            availability,
            proof.digest(),
        )
        return (
            Proposal(
                rule_id="R_SEARCH_FIGHTING_GONG_ROUTE_CRITICAL_V1",
                tier=ResolverTier.ROUTE_CRITICAL_SEARCH,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                resource_cost=ResourceCost((source_ref,)),
                transaction_plan=plan,
                deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
            ),
        )
    return ()


def _registered_attack_deficit(
    features: DeckFeatures,
    registry: PublicEffectRegistry,
    target,
) -> int | None:
    meta = CARD_META_BY_ID.get(target.ref.card_id)
    profile = registry.profile(target.ref.card_id)
    registered_attacks = tuple(
        binding
        for binding in EFFECT_BINDINGS
        if binding.entry_kind is EntryKind.ATTACK
        and binding.card_id == target.ref.card_id
        and binding.entry_id in (() if meta is None else meta.attack_ids)
    )
    if (
        meta is None
        or profile is None
        or not meta.attack_ids
        or tuple(profile.attack_ids) != tuple(meta.attack_ids)
        or len(registered_attacks) != len(meta.attack_ids)
        or {binding.entry_id for binding in registered_attacks} != set(meta.attack_ids)
        or any(
            not registry.binding_admitted(
                binding.effect_id,
                binding.card_id,
                binding.entry_id,
            )
            or binding.entry_id not in ATTACK_META_BY_ID
            or len(binding.energy_cost)
            != len(ATTACK_META_BY_ID[binding.entry_id].energy_cost)
            for binding in registered_attacks
        )
    ):
        return None
    minimum_cost = min(len(binding.energy_cost) for binding in registered_attacks)
    feature_rows = tuple(
        value
        for value in features.attack_energy_deficit_by_target
        if value.target_ref == target.ref
    )
    if (
        len(feature_rows) != 1
        or feature_rows[0].minimum_attack_cost != minimum_cost
        or feature_rows[0].attached_energy_count != len(target.energy_refs)
    ):
        return None
    return max(0, minimum_cost - len(target.energy_refs))


def enumerate_continuity_attach_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
    ledger: ResourceLedger,
) -> Tuple[Proposal, ...]:
    """Attach one exact Fighting Energy for current or next-attacker continuity."""

    if (
        not features.matches(state, legal_options, registry)
        or features.own_turn_number <= 1
        or state.energy_attached
    ):
        return ()
    board_ids = {pokemon.ref.card_id for pokemon in state.own.active + state.own.bench}
    ex_block = PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    candidates = []
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.ATTACH):
            continue
        source_ref = _exact_hand_ref(state, option)
        target = _board_pokemon_for_option(state, option)
        if (
            source_ref is None
            or source_ref.card_id != 6
            or target is None
            or not ledger.affords((source_ref,))
        ):
            continue
        deficit = _registered_attack_deficit(features, registry, target)
        if (
            deficit is not None
            and target.ref.card_id == 673
            and any(ref_value.card_id == 674 for ref_value in state.own.hand_refs)
        ):
            deficit = max(0, 3 - len(target.energy_refs))
        if deficit is None or deficit <= 0:
            continue
        if target.ref.card_id == 676 and 675 not in board_ids:
            continue
        if target.ref.zone == int(AreaType.ACTIVE):
            if (
                features.ready_now
                or deficit != 1
                or state.own.asleep
                or state.own.paralyzed
                or state.own.confused
            ):
                continue
            rank = (0, 0, 0, target.ref.sort_key())
            purpose = "CURRENT_ATTACK_COMPLETION"
            kind = CertificateKind.ATTACK_COMPLETION
        elif target.ref.zone == int(AreaType.BENCH) and features.ready_now:
            role_priority = {
                678: 0,
                677: 0,
                674: 1,
                673: 1,
                676: 2,
                675: 2,
            }.get(target.ref.card_id)
            if role_priority is None:
                continue
            meta = CARD_META_BY_ID[target.ref.card_id]
            non_ex = not meta.ex and not meta.mega_ex
            rank = (
                1,
                int(ex_block and not non_ex),
                int(deficit != 1),
                role_priority,
                deficit,
                target.ref.sort_key(),
            )
            purpose = "NEXT_ATTACKER_CONCENTRATION"
            kind = CertificateKind.FIRST_ATTACK_ACCELERATION
        else:
            continue
        candidates.append((rank, option, source_ref, target, deficit, purpose, kind))
    if not candidates:
        return ()
    _, option, source_ref, target, deficit, purpose, kind = min(
        candidates, key=lambda value: value[0]
    )
    action_spec = ActionSpec.single(option.key)
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code="R_ATTACH_002_CONTINUITY_V1",
        kind=kind,
        facts={
            "route_priority": 0 if purpose == "CURRENT_ATTACK_COMPLETION" else 1,
            "source_ref": source_ref,
            "target_ref": target.ref,
            "purpose": purpose,
            "deficit_before": deficit,
            "deficit_after": deficit - 1,
            "current_attack_preserved": features.ready_now,
            "ex_damage_prevention": ex_block,
        },
    )
    return (
        Proposal(
            rule_id="R_ATTACH_002_CONTINUITY_V1",
            tier=ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        ),
    )


def enumerate_evolution_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Prefer attack-ready/protective Mega evolution, with a non-ex escape."""

    if not features.matches(state, legal_options, registry):
        return ()
    mega_proposals = []
    hariyama_proposals = []
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.EVOLVE):
            continue
        source_ref = _exact_hand_ref(state, option)
        target = _board_pokemon_for_option(state, option)
        if source_ref is None or target is None:
            continue
        action_spec = ActionSpec.single(option.key)
        if source_ref.card_id == 678 and target.ref.card_id == 677:
            energy_continuity = (
                len(target.energy_refs) >= 1 and features.opponent_prizes_remaining > 3
            )
            active_ready = (
                target.ref.zone == int(AreaType.ACTIVE)
                and len(target.energy_refs) >= 1
                and not state.own.asleep
                and not state.own.paralyzed
            )
            spread_protection = (
                target.ref.zone == int(AreaType.BENCH)
                and features.public_bench_damage_threat is True
            )
            if not active_ready and not spread_protection and not energy_continuity:
                continue
            if features.opponent_prizes_remaining <= 3:
                active_target = features.opponent_active
                immediate_prize = (
                    active_ready
                    and features.public_damage_prevention is False
                    and active_target is not None
                    and active_target.remaining_hp <= 130
                )
                if not immediate_prize and not spread_protection:
                    continue
            kind = (
                CertificateKind.ATTACK_COMPLETION
                if active_ready
                else CertificateKind.FIRST_ATTACK_ACCELERATION
            )
            proof = deck_rule_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
                route_code="R_EVO_MEGA_ATTACK_OR_PROTECTION_V1",
                kind=kind,
                facts={
                    "route_priority": 0 if active_ready else 1,
                    "source_ref": source_ref,
                    "target_ref": target.ref,
                    "same_turn_attack": active_ready,
                    "spread_protection": spread_protection,
                    "energy_continuity": energy_continuity,
                    "opponent_prizes_remaining": features.opponent_prizes_remaining,
                },
            )
            mega_proposals.append(
                Proposal(
                    rule_id="R_EVO_MEGA_{0}".format(_semantic_key_suffix(action_spec)),
                    tier=ResolverTier.CERTIFIED_EVOLUTION,
                    action_spec=action_spec,
                    certificate_kind=proof.kind,
                    proof=proof,
                    resource_cost=ResourceCost((source_ref,)),
                    deterministic_tiebreak=canonical_proposal_tiebreak(
                        action_spec, proof
                    ),
                )
            )
        elif source_ref.card_id == 674 and target.ref.card_id == 673:
            energy_ready = len(target.energy_refs) >= 3
            ex_prevention = (
                PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
            )
            if not energy_ready and not ex_prevention:
                continue
            proof = deck_rule_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
                route_code="R_EVO_HARIYAMA_NONEX_ESCAPE_V1",
                kind=CertificateKind.FIRST_ATTACK_ACCELERATION,
                facts={
                    "route_priority": 2,
                    "source_ref": source_ref,
                    "target_ref": target.ref,
                    "energy_ready": energy_ready,
                    "ex_damage_prevention": ex_prevention,
                },
            )
            hariyama_proposals.append(
                Proposal(
                    rule_id="R_EVO_HARIYAMA_{0}".format(
                        _semantic_key_suffix(action_spec)
                    ),
                    tier=ResolverTier.CERTIFIED_EVOLUTION,
                    action_spec=action_spec,
                    certificate_kind=proof.kind,
                    proof=proof,
                    resource_cost=ResourceCost((source_ref,)),
                    deterministic_tiebreak=canonical_proposal_tiebreak(
                        action_spec, proof
                    ),
                )
            )
    return tuple(mega_proposals or hariyama_proposals)


def enumerate_aura_continuity_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Concentrate Aura Jab Energy on one incomplete Bench attacker."""

    if not features.matches(
        state, legal_options, registry
    ) or not attack_outcomes.matches(state, legal_options, registry):
        return ()
    aura_option = next(
        (
            option
            for option in legal_options
            if option.key.option_type == int(OptionType.ATTACK)
            and option.key.attack_id == 982
        ),
        None,
    )
    if aura_option is None:
        return ()
    outcome = attack_outcomes.get_for_option(aura_option.key)
    callback = None if outcome is None else outcome.callback
    if callback is None or not callback.requires_selection:
        return ()
    available = tuple(callback.available_source_refs[:3])
    if not available:
        return ()
    deficits = {
        value.target_ref: value.deficit_now
        for value in features.attack_energy_deficit_by_target
    }
    hand_ids = {ref_value.card_id for ref_value in state.own.hand_refs}
    ex_block = PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    non_ex_ids = frozenset((673, 674, 675, 676, 677))
    normal_priority = {678: 0, 677: 1, 674: 2, 673: 3, 676: 4, 675: 5}
    blocked_priority = {674: 0, 673: 1, 676: 2, 675: 3, 677: 4}
    candidates = []
    for target_ref in callback.eligible_target_refs:
        deficit = deficits.get(target_ref)
        if target_ref.card_id == 673 and 674 in hand_ids:
            attached = next(
                (
                    len(pokemon.energy_refs)
                    for pokemon in state.own.active + state.own.bench
                    if pokemon.ref == target_ref
                ),
                0,
            )
            deficit = max(0, 3 - attached)
        if (
            not isinstance(deficit, int)
            or isinstance(deficit, bool)
            or deficit <= 0
            or deficit > len(available)
            or deficit > 3
        ):
            continue
        if ex_block and target_ref.card_id not in non_ex_ids:
            continue
        priority = (blocked_priority if ex_block else normal_priority).get(
            target_ref.card_id,
            99,
        )
        candidates.append((priority, deficit, target_ref.sort_key(), target_ref))
    if not candidates:
        return ()
    _, count, _, target_ref = min(candidates)
    energy_refs = available[:count]
    action_spec = ActionSpec.single(aura_option.key)
    if outcome.exact_game_win:
        kind = CertificateKind.WIN_NOW
        tier = ResolverTier.EXACT_WIN_NOW
        guaranteed_prizes = int(outcome.prizes_taken or 0)
    elif (
        outcome.exact_ko
        and isinstance(outcome.prizes_taken, int)
        and outcome.prizes_taken > 0
    ):
        kind = CertificateKind.PRIZE_GAIN_NOW
        tier = ResolverTier.EXACT_CURRENT_TURN_PRIZE
        guaranteed_prizes = int(outcome.prizes_taken)
    else:
        kind = CertificateKind.SAME_ATTACK_PLUS_CONTINUITY
        tier = ResolverTier.SAME_ATTACK_PLUS_CONTINUITY
        guaranteed_prizes = 0
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code="R_AURA_JAB_CONCENTRATED_COMPLETION_V1",
        kind=kind,
        guaranteed_prizes=guaranteed_prizes,
        facts={
            "route_priority": 0,
            "target_ref": target_ref,
            "energy_refs": tuple(ref_value.sort_key() for ref_value in energy_refs),
            "energy_count": count,
            "ex_damage_prevention": ex_block,
            "exact_ko": outcome.exact_ko,
        },
    )
    plan = build_aura_jab_plan(
        state,
        action_spec,
        energy_refs,
        target_ref,
        proof.digest(),
    )
    return (
        Proposal(
            rule_id="R_AURA_JAB_CONCENTRATED_COMPLETION_V1",
            tier=tier,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            transaction_plan=plan,
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        ),
    )


def enumerate_minimal_ppp_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Play one PPP only while progressing toward the exact minimal breakpoint."""

    if (
        not features.matches(state, legal_options, registry)
        or not attack_outcomes.matches(state, legal_options, registry)
        or not isinstance(state.ppp_count, int)
        or isinstance(state.ppp_count, bool)
    ):
        return ()
    ppp_options = tuple(
        sorted(
            (
                option
                for option in legal_options
                if option.key.option_type == int(OptionType.PLAY)
                and option.key.card_id == 1141
            ),
            key=lambda value: value.key.sort_key(),
        )
    )
    if not ppp_options or any(outcome.exact_ko for outcome in attack_outcomes.rows):
        return ()
    candidates = []
    for outcome in attack_outcomes.rows:
        if (
            not outcome.exact_damage
            or outcome.final_damage is None
            or outcome.final_damage <= 0
            or outcome.before_weakness is None
            or outcome.weakness_multiplier is None
            or outcome.resistance_reduction is None
            or outcome.field_reduction is None
            or outcome.damage_before_prevention != outcome.final_damage
            or outcome.damage_before_ko_prevention != outcome.final_damage
            or outcome.prevention_effects
        ):
            continue
        old_attacks = ceil(outcome.target_starting_hp / outcome.final_damage)
        for additional in range(1, len(ppp_options) + 1):
            before = outcome.before_weakness + 30 * additional
            after = max(
                0,
                before * outcome.weakness_multiplier - outcome.resistance_reduction,
            )
            new_damage = max(0, after - outcome.field_reduction)
            if new_damage <= 0:
                continue
            new_attacks = ceil(outcome.target_starting_hp / new_damage)
            is_ko = new_damage >= outcome.target_starting_hp
            if not is_ko and new_attacks >= old_attacks:
                continue
            candidates.append(
                (
                    0 if is_ko else 1,
                    additional,
                    new_attacks,
                    outcome.attack_id,
                    new_damage,
                    old_attacks,
                )
            )
            break
    if not candidates:
        return ()
    ko_rank, required, new_attacks, attack_id, new_damage, old_attacks = min(candidates)
    option = ppp_options[0]
    source_ref = _exact_hand_ref(state, option)
    if source_ref is None:
        return ()
    action_spec = ActionSpec.single(option.key)
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code="R_PPP_EXACT_MINIMUM_BREAKPOINT_V1",
        kind=CertificateKind.ATTACK_COMPLETION,
        facts={
            "route_priority": required,
            "attack_id": attack_id,
            "additional_ppp_required": required,
            "new_damage": new_damage,
            "old_attacks_needed": old_attacks,
            "new_attacks_needed": new_attacks,
            "reaches_ko": ko_rank == 0,
            "source_ref": source_ref,
        },
    )
    return (
        Proposal(
            rule_id="R_PPP_EXACT_MINIMUM_BREAKPOINT_V1",
            tier=ResolverTier.MINIMAL_PPP,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        ),
    )


def enumerate_safe_draw_supporter_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit safe Lunar/Judge/Lillie prefixes and replan after their draw."""

    if not features.matches(state, legal_options, registry):
        return ()
    proposals = []
    if features.lunar_cycle_feasible:
        energies = tuple(
            sorted(
                (
                    ref_value
                    for ref_value in state.own.hand_refs
                    if ref_value.card_id == 6
                ),
                key=lambda value: value.sort_key(),
            )
        )
        reserve = int(not state.energy_attached and not features.ready_now)
        if len(energies) > reserve:
            energy_ref = energies[-1]
            for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
                if (
                    option.key.option_type
                    not in (int(OptionType.ABILITY), int(OptionType.SKILL))
                    or option.key.card_id != 675
                ):
                    continue
                source_ref = _in_play_source_ref(state, option)
                if source_ref is None:
                    continue
                action_spec = ActionSpec.single(option.key)
                proof = deck_rule_proof(
                    state,
                    legal_options,
                    registry,
                    features,
                    action_spec,
                    route_code="R_LUNAR_SAFE_PREFIX_V1",
                    kind=CertificateKind.RESOURCE_IMPROVEMENT,
                    facts={
                        "route_priority": 0,
                        "source_ref": source_ref,
                        "energy_ref": energy_ref,
                        "draw_buffer_after": features.draw_buffer_after_plan,
                        "manual_attach_reserve": reserve,
                    },
                )
                plan = build_lunar_cycle_plan(
                    state,
                    source_ref,
                    energy_ref,
                    action_spec,
                    proof.digest(),
                )
                proposals.append(
                    Proposal(
                        rule_id="R_LUNAR_SAFE_PREFIX_V1",
                        tier=ResolverTier.SAFE_DRAW_OR_DISRUPTION,
                        action_spec=action_spec,
                        certificate_kind=proof.kind,
                        proof=proof,
                        resource_cost=ResourceCost((energy_ref,)),
                        transaction_plan=plan,
                        deterministic_tiebreak=canonical_proposal_tiebreak(
                            action_spec, proof
                        ),
                    )
                )
                break

    if state.supporter_played:
        return tuple(proposals)
    hand_ids = tuple(ref_value.card_id for ref_value in state.own.hand_refs)
    missing_role = (
        bool(features.missing_engine_card_ids)
        or features.lucario_line_count == 0
        or (features.hand_fighting_energy_count == 0 and not features.ready_now)
        or (
            677
            in tuple(
                pokemon.ref.card_id for pokemon in state.own.active + state.own.bench
            )
            and 678 not in hand_ids
        )
    )
    supporter_choice = None
    supporter_code = ""
    route_priority = 99
    if (
        features.opponent_hand_count >= 8
        and state.own.hand_count <= 4
        and state.own.deck_count >= 5
    ):
        supporter_choice = 1213
        supporter_code = "R_SUPPORTER_JUDGE_LARGE_PUBLIC_HAND_V1"
        route_priority = 1
    else:
        lillie_target = 8 if state.own.prize_count == 6 else 6
        if (
            missing_role
            and state.own.hand_count <= lillie_target - 2
            and state.own.deck_count >= lillie_target + 1
        ):
            supporter_choice = 1227
            supporter_code = "R_SUPPORTER_LILLIE_ROLE_REBUILD_V1"
            route_priority = 2
    if supporter_choice is None:
        return tuple(proposals)
    option = next(
        (
            value
            for value in sorted(legal_options, key=lambda row: row.key.sort_key())
            if value.key.option_type == int(OptionType.PLAY)
            and value.key.card_id == supporter_choice
        ),
        None,
    )
    if option is None:
        return tuple(proposals)
    source_ref = _exact_hand_ref(state, option)
    if source_ref is None:
        return tuple(proposals)
    action_spec = ActionSpec.single(option.key)
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code=supporter_code,
        kind=CertificateKind.RESOURCE_IMPROVEMENT,
        facts={
            "route_priority": route_priority,
            "source_ref": source_ref,
            "own_hand_count": state.own.hand_count,
            "opponent_hand_count": features.opponent_hand_count,
            "missing_role": missing_role,
            "draw_buffer_after": features.draw_buffer_after_plan,
        },
    )
    proposals.append(
        Proposal(
            rule_id=supporter_code,
            tier=ResolverTier.SAFE_DRAW_OR_DISRUPTION,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        )
    )
    return tuple(proposals)


def _ultra_search_classes(
    state: PublicState,
    features: DeckFeatures,
) -> Tuple[Tuple[int, ...], ...]:
    board_ids = tuple(
        pokemon.ref.card_id for pokemon in state.own.active + state.own.bench
    )
    hand_ids = tuple(ref_value.card_id for ref_value in state.own.hand_refs)
    classes = []
    if 677 in board_ids and 678 not in board_ids and 678 not in hand_ids:
        classes.append((678,))
    classes.extend(
        (card_id,)
        for card_id in features.missing_engine_card_ids
        if card_id not in hand_ids
    )
    if features.lucario_line_count == 0 and 677 not in hand_ids:
        classes.append((677,))
    if 673 in board_ids and 674 not in board_ids and 674 not in hand_ids:
        classes.append((674,))
    return tuple(classes)


def _ultra_discard_pair(
    state: PublicState,
    ledger: ResourceLedger,
    source_ref: PhysicalRef,
) -> Tuple[PhysicalRef, ...]:
    if ledger.is_reserved(source_ref):
        return ()
    unreserved = tuple(
        ref_value
        for ref_value in ledger.unreserved_refs(allowed_zones=(int(AreaType.HAND),))
        if ref_value != source_ref
    )
    candidates = []
    for card_id in (1121, 1142, 1152, 1213, 1227):
        values = tuple(
            sorted(
                (ref_value for ref_value in unreserved if ref_value.card_id == card_id),
                key=lambda value: value.sort_key(),
            )
        )
        keep = 0 if card_id == 1121 else 1
        candidates.extend(values[keep:])
    return tuple(candidates[:2]) if len(candidates) >= 2 else ()


def enumerate_ultra_ball_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
    ledger: ResourceLedger,
) -> Tuple[Proposal, ...]:
    """Use Ultra Ball only with a guaranteed target and two safe surplus costs."""

    if (
        not features.matches(state, legal_options, registry)
        or not isinstance(ledger, ResourceLedger)
        or state.own.deck_count <= 1
    ):
        return ()
    classes = _ultra_search_classes(state, features)
    if not classes:
        return ()
    acceptable_ids = tuple(
        sorted(card_id for card_class in classes for card_id in card_class)
    )
    availability = prove_deck_availability_from_state(
        state,
        acceptable_ids,
        required_count=1,
    )
    if not availability.is_guaranteed:
        return ()
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1121:
            continue
        source_ref = _exact_hand_ref(state, option)
        if source_ref is None:
            continue
        discard_refs = _ultra_discard_pair(state, ledger, source_ref)
        if len(discard_refs) != 2:
            continue
        action_spec = ActionSpec.single(option.key)
        proof = deck_rule_proof(
            state,
            legal_options,
            registry,
            features,
            action_spec,
            route_code="R_SEARCH_ULTRA_BALL_SAFE_GUARANTEED_V1",
            kind=CertificateKind.RESOURCE_IMPROVEMENT,
            facts={
                "route_priority": 0,
                "source_ref": source_ref,
                "discard_refs": tuple(
                    ref_value.sort_key() for ref_value in discard_refs
                ),
                "ordered_card_id_classes": classes,
                "availability": availability.canonical(),
            },
        )
        plan = build_ultra_ball_plan(
            state,
            source_ref,
            discard_refs,
            action_spec,
            classes,
            availability,
            proof.digest(),
        )
        return (
            Proposal(
                rule_id="R_SEARCH_ULTRA_BALL_SAFE_GUARANTEED_V1",
                tier=ResolverTier.ROUTE_CRITICAL_SEARCH,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                resource_cost=ResourceCost((source_ref,) + discard_refs),
                transaction_plan=plan,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            ),
        )
    return ()


def enumerate_switch_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Switch only to a ready attacker or effective anti-ex non-ex pivot."""

    if not features.matches(state, legal_options, registry):
        return ()
    active = state.own_active
    if active is None or not state.own.bench:
        return ()
    ex_block = PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    status_block = state.own.asleep or state.own.paralyzed or state.own.confused
    if (
        features.ready_now
        and not status_block
        and not (ex_block and active.ref.card_id == 678)
    ):
        return ()
    deficits = {
        value.target_ref: value.deficit_now
        for value in features.attack_energy_deficit_by_target
    }
    board_ids = tuple(
        pokemon.ref.card_id for pokemon in state.own.active + state.own.bench
    )
    candidates = []
    for target in state.own.bench:
        meta = CARD_META_BY_ID.get(target.ref.card_id)
        non_ex = meta is not None and not meta.ex and not meta.mega_ex
        if deficits.get(target.ref) != 0:
            continue
        if target.ref.card_id == 676 and 675 not in board_ids:
            continue
        if ex_block and not non_ex:
            continue
        prize_value = (
            meta.prize_value
            if meta is not None
            and isinstance(meta.prize_value, int)
            and not isinstance(meta.prize_value, bool)
            else 99
        )
        candidates.append(
            (
                0 if non_ex else 1,
                prize_value,
                -target.remaining_hp,
                target.ref.sort_key(),
                target,
            )
        )
    if not candidates:
        return ()
    target = min(candidates)[-1]
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1123:
            continue
        source_ref = _exact_hand_ref(state, option)
        if source_ref is None:
            continue
        action_spec = ActionSpec.single(option.key)
        proof = deck_rule_proof(
            state,
            legal_options,
            registry,
            features,
            action_spec,
            route_code="R_SWITCH_READY_ATTACKER_V1",
            kind=CertificateKind.ATTACK_COMPLETION,
            facts={
                "route_priority": 0,
                "source_ref": source_ref,
                "target_ref": target.ref,
                "status_block": status_block,
                "ex_damage_prevention": ex_block,
            },
        )
        plan = build_switch_plan(
            state,
            source_ref,
            target.ref,
            action_spec,
            proof.digest(),
        )
        return (
            Proposal(
                rule_id="R_SWITCH_READY_ATTACKER_V1",
                tier=ResolverTier.ATTACK_COMPLETION,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                resource_cost=ResourceCost((source_ref,)),
                transaction_plan=plan,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            ),
        )
    return ()


def _a4_ref_by_fact(refs, fact):
    matches = tuple(ref_value for ref_value in refs if ref_value.sort_key() == fact)
    return matches[0] if len(matches) == 1 else None


def enumerate_gust_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    ledger: ResourceLedger | None = None,
) -> Tuple[Proposal, ...]:
    if ledger is None:
        ledger = build_resource_ledger(state)
    """Issue only verifier-derived Gate A4 gust proposals."""

    if not features.matches(state, legal_options, registry):
        return ()
    verified = []
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if not (
            option.key.option_type == int(OptionType.EVOLVE)
            and option.key.card_id == 674
            or option.key.option_type == int(OptionType.PLAY)
            and option.key.card_id == 1182
        ):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = verify_gust_dominance_certificate(
                state,
                legal_options,
                ledger,
                attack_outcomes,
                registry,
                action_spec,
            )
        except ValueError:
            continue
        source_ref = _a4_ref_by_fact(state.own.hand_refs, proof.fact("source_ref"))
        target_ref = _a4_ref_by_fact(
            tuple(pokemon.ref for pokemon in state.opponent.bench),
            proof.fact("gust_target_ref"),
        )
        if source_ref is None or target_ref is None:
            continue
        route_code = proof.fact("route_code")
        if route_code == "R_GUST_HARIYAMA_EXACT_DOMINANCE_A3":
            evolution_target_ref = _a4_ref_by_fact(
                tuple(pokemon.ref for pokemon in state.own.bench),
                proof.fact("evolution_target_ref"),
            )
            if evolution_target_ref is None:
                continue
            plan = build_hariyama_gust_plan(
                state,
                source_ref,
                target_ref,
                action_spec,
                proof.digest(),
            )
            tier = ResolverTier.TERMINAL_OR_SUPERIOR_GUST
        elif route_code == "R_GUST_BOSS_EXACT_DOMINANCE_A3":
            plan = build_boss_gust_plan(
                state,
                source_ref,
                target_ref,
                action_spec,
                proof.digest(),
            )
            tier = (
                ResolverTier.TERMINAL_OR_SUPERIOR_GUST
                if proof.fact("terminal") is True
                else ResolverTier.STRICTLY_SUPERIOR_GUST
            )
        else:
            continue
        proposal = Proposal(
            rule_id=route_code,
            tier=tier,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            transaction_plan=plan,
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        )
        verified.append((proof.fact("route_priority"), option.key.sort_key(), proposal))
    if not verified:
        return ()
    heave = tuple(
        row
        for row in verified
        if row[-1].action_spec.choices[0].option_type == int(OptionType.EVOLVE)
    )
    return (min(heave or tuple(verified))[-1],)


def enumerate_wally_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    ledger: ResourceLedger | None = None,
) -> Tuple[Proposal, ...]:
    if ledger is None:
        ledger = build_resource_ledger(state)
    """Issue a local Gate A4 Wally proof without suppressing higher routes."""

    if not features.matches(state, legal_options, registry):
        return ()
    candidates = []
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1229:
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = verify_wally_survival_certificate(
                state,
                legal_options,
                ledger,
                attack_outcomes,
                registry,
                action_spec,
            )
        except ValueError:
            continue
        source_ref = _a4_ref_by_fact(state.own.hand_refs, proof.fact("source_ref"))
        target_ref = _a4_ref_by_fact(
            tuple(pokemon.ref for pokemon in state.own.active),
            proof.fact("target_ref"),
        )
        reattach_ref = _a4_ref_by_fact(
            () if state.own_active is None else state.own_active.energy_refs,
            proof.fact("reattach_ref"),
        )
        if source_ref is None or target_ref is None or reattach_ref is None:
            continue
        plan = build_wally_plan(
            state,
            source_ref,
            target_ref,
            reattach_ref,
            action_spec,
            proof.digest(),
        )
        proposal = Proposal(
            rule_id="R_WALLY_THREE_PRIZE_REBOOT_V1",
            tier=ResolverTier.SURVIVAL_CRITICAL_WALLY,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            transaction_plan=plan,
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        )
        candidates.append((option.key.sort_key(), proposal))
    return () if not candidates else (min(candidates)[-1],)


def enumerate_cape_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    ledger: ResourceLedger | None = None,
) -> Tuple[Proposal, ...]:
    if ledger is None:
        ledger = build_resource_ledger(state)
    """Issue only the verifier-selected global Gate A4 Cape candidate."""

    if not features.matches(state, legal_options, registry):
        return ()
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if (
            option.key.option_type != int(OptionType.ATTACH)
            or option.key.card_id != 1159
        ):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = verify_cape_survival_certificate(
                state,
                legal_options,
                ledger,
                attack_outcomes,
                registry,
                action_spec,
            )
        except ValueError:
            continue
        source_ref = _a4_ref_by_fact(state.own.hand_refs, proof.fact("source_ref"))
        if source_ref is None:
            continue
        return (
            Proposal(
                rule_id="R_CAPE_EXPLICIT_PROTECTION_V1",
                tier=ResolverTier.CERTIFIED_SURVIVAL,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                resource_cost=ResourceCost((source_ref,)),
                deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
            ),
        )
    return ()


def enumerate_requirement_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    ledger: ResourceLedger,
) -> Tuple[Proposal, ...]:
    """Enumerate the integrated fixed-deck productive routes."""

    proposals = []
    proposals.extend(
        enumerate_gust_routes(
            state,
            legal_options,
            features,
            attack_outcomes,
            registry,
            ledger,
        )
    )
    proposals.extend(
        enumerate_wally_routes(
            state, legal_options, features, attack_outcomes, registry, ledger
        )
    )
    proposals.extend(
        enumerate_aura_continuity_routes(
            state, legal_options, features, attack_outcomes, registry
        )
    )
    proposals.extend(enumerate_switch_routes(state, legal_options, features, registry))
    proposals.extend(
        enumerate_evolution_routes(state, legal_options, features, registry)
    )
    proposals.extend(
        enumerate_continuity_attach_routes(
            state,
            legal_options,
            features,
            registry,
            ledger,
        )
    )
    proposals.extend(
        enumerate_ultra_ball_routes(
            state,
            legal_options,
            features,
            registry,
            ledger,
        )
    )
    proposals.extend(
        enumerate_fighting_gong_routes(state, legal_options, features, registry)
    )
    proposals.extend(
        enumerate_cape_routes(
            state, legal_options, features, attack_outcomes, registry, ledger
        )
    )
    proposals.extend(
        enumerate_safe_draw_supporter_routes(state, legal_options, features, registry)
    )
    proposals.extend(
        enumerate_minimal_ppp_routes(
            state, legal_options, features, attack_outcomes, registry
        )
    )
    return tuple(proposals)


__all__ = [
    "enumerate_active_attack_completion_routes",
    "enumerate_attack_routes",
    "enumerate_aura_continuity_routes",
    "enumerate_basic_bench_routes",
    "enumerate_cape_routes",
    "enumerate_continuity_attach_routes",
    "enumerate_evolution_routes",
    "enumerate_fighting_gong_routes",
    "enumerate_gust_routes",
    "enumerate_first_turn_riolu_attach_routes",
    "enumerate_minimal_ppp_routes",
    "enumerate_poke_pad_core_search_routes",
    "enumerate_requirement_routes",
    "enumerate_safe_draw_supporter_routes",
    "enumerate_switch_routes",
    "enumerate_ultra_ball_routes",
    "enumerate_wally_routes",
]
