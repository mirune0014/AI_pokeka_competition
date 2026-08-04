from dataclasses import replace

import pytest

from mega_lucario_rule_agent.certificates import (
    CertificateKind,
    CertificateProof,
    safe_fallback_proof,
)
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    OptionType,
    PhysicalRef,
    PlayerView,
    PokemonView,
    PublicState,
    SelectContext,
    SelectType,
    SemanticOption,
    SemanticOptionKey,
)


def ref(card_id, serial, owner, zone):
    return PhysicalRef(card_id, serial, owner, int(zone), serial)


def pokemon(card_id, serial, owner, zone, hp, max_hp):
    return PokemonView(
        ref=ref(card_id, serial, owner, zone),
        hp=hp,
        max_hp=max_hp,
        appear_this_turn=False,
        energy_types=(6,),
        energy_refs=(),
        tool_refs=(),
        pre_evolution_refs=(),
    )


def player(index, active, prizes):
    return PlayerView(
        index=index,
        active=(active,),
        active_slot_count=1,
        hidden_active_count=0,
        bench=(),
        hand_refs=(),
        discard_refs=(),
        prize_refs=(),
        prize_count=prizes,
        deck_count=40,
        hand_count=5,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


def state():
    own_active = pokemon(678, 10, 0, AreaType.ACTIVE, 340, 340)
    target = pokemon(999, 20, 1, AreaType.ACTIVE, 200, 200)
    return PublicState(
        game_epoch=3,
        seat=0,
        turn=5,
        turn_action_count=7,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=-1,
        own=player(0, own_active, 6),
        opponent=player(1, target, 6),
        stadium_refs=(),
        looking_refs=(),
        select_context=int(SelectContext.MAIN),
        min_count=1,
        max_count=1,
        effect_ref=None,
        context_ref=None,
        select_type=int(SelectType.MAIN),
        remaining_damage_counter=0,
        remaining_energy_cost=0,
    )


def action_spec(option_type=OptionType.ATTACK, attack_id=983, player_index=0):
    return ActionSpec.single(
        SemanticOptionKey(
            option_type=int(option_type),
            player_index=player_index,
            attack_id=attack_id,
        )
    )


def options_for(*specs):
    return tuple(
        SemanticOption(index=index, key=spec.choices[0])
        for index, spec in enumerate(specs)
    )


def test_attack_fallback_proof_is_closed_and_bound_to_the_exact_public_state():
    current = state()
    spec = action_spec()
    legal = options_for(spec)
    proof = safe_fallback_proof(
        current,
        legal,
        spec,
        "LEGAL_ATTACK_FALLBACK",
    )

    assert proof.is_valid
    assert proof.kind == CertificateKind.SAFE_FALLBACK
    assert proof.guaranteed_prizes == 0
    assert proof.fact("reason_code") == "LEGAL_ATTACK_FALLBACK"
    assert proof.fact("option_type") == int(OptionType.ATTACK)
    assert proof.fact("attack_id") == 983
    assert len(proof.digest()) == 64

    changed = replace(current, turn_action_count=current.turn_action_count + 1)
    changed_proof = safe_fallback_proof(
        changed,
        legal,
        spec,
        "LEGAL_ATTACK_FALLBACK",
    )
    assert changed_proof.state_fingerprint != proof.state_fingerprint
    assert changed_proof.digest() != proof.digest()

    with pytest.raises(ValueError, match="checked issuer"):
        CertificateProof(
            kind=proof.kind,
            schema=proof.schema,
            state_fingerprint=proof.state_fingerprint,
            action_spec=proof.action_spec,
            is_valid=True,
            guaranteed_prizes=0,
            facts=proof.facts,
            rejection_reasons=(),
            _issuer_token=object(),
        )


def test_end_fallback_is_supported_without_claiming_attack_or_prize_facts():
    current = state()
    spec = action_spec(OptionType.END, attack_id=None)
    proof = safe_fallback_proof(
        current,
        options_for(spec),
        spec,
        "PASS_FALLBACK",
    )

    assert proof.is_valid
    assert proof.kind == CertificateKind.SAFE_FALLBACK
    assert proof.fact("option_type") == int(OptionType.END)
    assert proof.fact("attack_id") is None
    assert proof.guaranteed_prizes == 0


@pytest.mark.parametrize(
    "option_type",
    [
        OptionType.PLAY,
        OptionType.ATTACH,
        OptionType.EVOLVE,
        OptionType.ABILITY,
        OptionType.DISCARD,
        OptionType.RETREAT,
    ],
)
def test_safe_fallback_certificate_rejects_irreversible_or_resource_actions(
    option_type,
):
    spec = action_spec(option_type, attack_id=None)
    with pytest.raises(ValueError, match="only covers ATTACK or END"):
        safe_fallback_proof(
            state(),
            options_for(spec),
            spec,
            "UNSAFE_GENERIC_ACTION",
        )


def test_safe_fallback_requires_one_owned_well_formed_semantic_action():
    current = state()
    with pytest.raises(ValueError, match="exactly one"):
        safe_fallback_proof(
            current,
            (),
            ActionSpec.empty(),
            "EMPTY_ACTION",
        )
    with pytest.raises(ValueError, match="exactly one"):
        safe_fallback_proof(
            current,
            (),
            ActionSpec((action_spec().choices[0], action_spec(OptionType.END, None).choices[0])),
            "MULTI_ACTION",
        )
    with pytest.raises(ValueError, match="acting seat"):
        safe_fallback_proof(
            current,
            options_for(action_spec(player_index=1)),
            action_spec(player_index=1),
            "WRONG_OWNER",
        )

    for invalid_attack_id in (None, 0, -1, True):
        with pytest.raises(ValueError, match="positive attack_id"):
            safe_fallback_proof(
                current,
                options_for(action_spec(attack_id=invalid_attack_id)),
                action_spec(attack_id=invalid_attack_id),
                "INVALID_ATTACK",
            )

    with pytest.raises(ValueError, match="cannot carry an attack_id"):
        safe_fallback_proof(
            current,
            options_for(action_spec(OptionType.END, attack_id=983)),
            action_spec(OptionType.END, attack_id=983),
            "INVALID_END",
        )


def test_safe_fallback_requires_unfinished_main_state_and_nonempty_reason():
    current = state()
    with pytest.raises(ValueError, match="unfinished stable MAIN"):
        safe_fallback_proof(
            replace(current, select_context=int(SelectContext.ATTACK)),
            options_for(action_spec()),
            action_spec(),
            "WRONG_CONTEXT",
        )
    with pytest.raises(ValueError, match="unfinished stable MAIN"):
        safe_fallback_proof(
            replace(current, result=0),
            options_for(action_spec()),
            action_spec(),
            "FINISHED_GAME",
        )
    with pytest.raises(ValueError, match="reason_code"):
        safe_fallback_proof(
            current,
            options_for(action_spec()),
            action_spec(),
            "   ",
        )


def test_safe_fallback_must_bind_uniquely_to_the_live_prompt():
    current = state()
    spec = action_spec()
    other = action_spec(attack_id=982)

    with pytest.raises(ValueError, match="bind uniquely"):
        safe_fallback_proof(current, options_for(other), spec, "ABSENT_ATTACK")
    with pytest.raises(ValueError, match="bind uniquely"):
        safe_fallback_proof(
            current,
            options_for(spec, spec),
            spec,
            "DUPLICATE_ATTACK",
        )

    end_spec = action_spec(OptionType.END, attack_id=None)
    forged_end = ActionSpec.single(
        replace(end_spec.choices[0], card_id=999)
    )
    with pytest.raises(ValueError, match="bind uniquely"):
        safe_fallback_proof(
            current,
            options_for(end_spec),
            forged_end,
            "FORGED_END_FIELDS",
        )

    no_selection_allowed = replace(current, min_count=0, max_count=0)
    with pytest.raises(ValueError, match="stable MAIN"):
        safe_fallback_proof(
            no_selection_allowed,
            options_for(spec),
            spec,
            "COUNT_MISMATCH",
        )


def test_safe_schema_cannot_be_relabelled_as_a_stronger_certificate():
    current = state()
    spec = action_spec()
    proof = safe_fallback_proof(
        current,
        options_for(spec),
        spec,
        "LEGAL_ATTACK_FALLBACK",
    )
    with pytest.raises(ValueError, match="schema and kind"):
        replace(proof, kind=CertificateKind.ATTACK_COMPLETION)
