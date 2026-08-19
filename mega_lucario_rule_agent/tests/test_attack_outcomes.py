from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.attack_outcomes import (
    AttackOutcome,
    BoundAttackOutcomeTable,
    build_attack_outcome_table,
    semantic_options_fingerprint,
)
from mega_lucario_rule_agent.card_meta import ATTACK_META_BY_ID
from mega_lucario_rule_agent.certificates import (
    CertificateKind,
    ProofSchema,
    attack_outcome_proof,
)
from mega_lucario_rule_agent.fallback import safe_fallback
from mega_lucario_rule_agent.public_effects import (
    EFFECT_BINDINGS,
    EntryKind,
    build_public_effect_registry,
)
from mega_lucario_rule_agent.resource_ledger import ResourceLedger
from mega_lucario_rule_agent.resolver import (
    ResolverTier,
    resolve_proposals,
)
from mega_lucario_rule_agent.routes import enumerate_attack_routes
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    LogType,
    OptionType,
    PublicHistoryTracker,
    build_public_state,
    build_semantic_options,
)


def card(card_id, serial, player=0):
    return {"id": card_id, "serial": serial, "playerIndex": player}


def pokemon(
    card_id,
    serial,
    *,
    player=0,
    hp=100,
    max_hp=None,
    energy_cards=(),
    tools=(),
    pre=(),
):
    maximum = hp if max_hp is None else max_hp
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": player,
        "hp": hp,
        "maxHp": maximum,
        "appearThisTurn": False,
        "energies": [6 for _ in energy_cards],
        "energyCards": [
            card(card_id_value, serial_value, player)
            for card_id_value, serial_value in energy_cards
        ],
        "tools": [
            card(card_id_value, serial_value, player)
            for card_id_value, serial_value in tools
        ],
        "preEvolution": list(pre),
    }


def pokemon_catalog_row(
    card_id,
    name,
    *,
    hp=100,
    energy_type=6,
    weakness=None,
    resistance=None,
    basic=True,
    stage1=False,
    stage2=False,
    ex=False,
    mega_ex=False,
    tera=False,
    attacks=(),
    skills=(),
):
    return {
        "cardId": card_id,
        "cardType": 0,
        "name": name,
        "hp": hp,
        "energyType": energy_type,
        "weakness": weakness,
        "resistance": resistance,
        "basic": basic,
        "stage1": stage1,
        "stage2": stage2,
        "ex": ex,
        "megaEx": mega_ex,
        "tera": tera,
        "attacks": list(attacks),
        "skills": list(skills),
    }


def basic_energy_catalog_row(card_id=6, energy_type=6):
    return {
        "cardId": card_id,
        "cardType": 5,
        "name": "Basic Fighting Energy",
        "hp": 0,
        "energyType": energy_type,
        "weakness": None,
        "resistance": None,
        "basic": False,
        "stage1": False,
        "stage2": False,
        "ex": False,
        "megaEx": False,
        "tera": False,
        "attacks": [],
        "skills": [],
    }


EFFECT_TEXT = {
    "MYSTERIOUS_ROCK_INN": (
        "Prevent all damage done to this Pok\u00e9mon by attacks from your "
        "opponent\u2019s Pok\u00e9mon {ex}."
    ),
    "STURDY": (
        "If this Pok\u00e9mon has full HP and would be Knocked Out by damage "
        "from an attack, it is not Knocked Out, and its remaining HP becomes 10."
    ),
    "SPIKY_ENERGY": (
        "As long as this card is attached to a Pok\u00e9mon, it provides {C} Energy.\n\n"
        "If the Pok\u00e9mon this card is attached to is in the Active Spot and is "
        "damaged by an attack from your opponent\u2019s Pok\u00e9mon (even if this "
        "Pok\u00e9mon is Knocked Out), put 2 damage counters on the Attacking Pok\u00e9mon."
    ),
    "LEGACY_ENERGY": (
        "As long as this card is attached to a Pok\u00e9mon, it provides every type "
        "of Energy but provides only 1 Energy at a time.\n\nIf the Pok\u00e9mon this "
        "card is attached to is Knocked Out by damage from an attack from your "
        "opponent\u2019s Pok\u00e9mon, that player takes 1 fewer Prize card. This effect "
        "of your Legacy Energy only works once per game."
    ),
    "JAMMING_TOWER": (
        "Pok\u00e9mon Tools attached to each Pok\u00e9mon (both yours and your "
        "opponent\u2019s) have no effect."
    ),
    "HEROS_CAPE": (
        "The Pok\u00e9mon this card is attached to gets +100 HP."
    ),
    "FULL_METAL_LAB": (
        "{M} Pok\u00e9mon (both yours and your opponent\u2019s) take 30 less damage "
        "from attacks from the opponent\u2019s Pok\u00e9mon (after applying Weakness "
        "and Resistance)."
    ),
    "LILLIES_PEARL": (
        "If the Lillie\u2019s Pok\u00e9mon this card is attached to is Knocked Out "
        "by damage from an attack from your opponent\u2019s Pok\u00e9mon, that "
        "player takes 1 fewer Prize card."
    ),
    "HANDHELD_FAN": (
        "If the Pokémon this card is attached to is in the Active Spot and is "
        "damaged by an attack from your opponent’s Pokémon (even if this "
        "Pokémon is Knocked Out), move an Energy from the Attacking Pokémon "
        "to 1 of your opponent’s Benched Pokémon."
    ),
}


SOURCE_PROFILE = {
    673: (70, True, False, False, False),
    674: (140, False, True, False, False),
    675: (110, True, False, False, False),
    676: (110, True, False, False, False),
    677: (80, True, False, False, False),
    678: (340, False, True, False, True),
}


def effect_catalog_row(effect_id):
    binding = next(row for row in EFFECT_BINDINGS if row.effect_id == effect_id)
    if effect_id in {"MYSTERIOUS_ROCK_INN", "STURDY"}:
        hp = 150
        return pokemon_catalog_row(
            binding.card_id,
            binding.card_name,
            hp=hp,
            energy_type=1 if effect_id == "MYSTERIOUS_ROCK_INN" else 6,
            basic=False,
            stage1=True,
            skills=({"name": binding.entry_name, "text": EFFECT_TEXT[effect_id]},),
        )
    if effect_id in {"SPIKY_ENERGY", "LEGACY_ENERGY"}:
        card_type = 6
    elif effect_id in {"HANDHELD_FAN", "HEROS_CAPE", "LILLIES_PEARL"}:
        card_type = 2
    else:
        card_type = 4
    return {
        "cardId": binding.card_id,
        "cardType": card_type,
        "name": binding.card_name,
        "hp": 0,
        "energyType": 0,
        "weakness": None,
        "resistance": None,
        "basic": False,
        "stage1": False,
        "stage2": False,
        "ex": False,
        "megaEx": False,
        "tera": False,
        "attacks": [],
        "skills": ({"name": binding.entry_name, "text": EFFECT_TEXT[effect_id]},),
    }


def registry_for(attack_ids, *, target_row=None, extra_rows=()):
    attack_ids = tuple(attack_ids)
    source_rows = {}
    attack_rows = []
    for attack_id in attack_ids:
        attack = ATTACK_META_BY_ID[attack_id]
        binding = next(
            row
            for row in EFFECT_BINDINGS
            if row.entry_kind is EntryKind.ATTACK and row.entry_id == attack_id
        )
        hp, basic, stage1, stage2, mega_ex = SOURCE_PROFILE[attack.source_card_id]
        source = source_rows.setdefault(
            attack.source_card_id,
            pokemon_catalog_row(
                attack.source_card_id,
                binding.card_name,
                hp=hp,
                basic=basic,
                stage1=stage1,
                stage2=stage2,
                mega_ex=mega_ex,
                attacks=(),
            ),
        )
        source["attacks"].append(attack_id)
        attack_rows.append(
            {
                "attackId": attack_id,
                "name": binding.entry_name,
                "text": attack.effect_text,
                "damage": attack.printed_damage,
                "energies": list(binding.energy_cost),
            }
        )
    target = target_row or pokemon_catalog_row(900, "Test Target", hp=300)
    cards = [basic_energy_catalog_row(), target, *source_rows.values(), *extra_rows]
    by_id = {}
    for row in cards:
        by_id[row["cardId"]] = row
    return build_public_effect_registry(tuple(by_id.values()), attack_rows)


def observation(
    attack_ids,
    *,
    own_active=None,
    own_bench=(),
    own_discard=(),
    opponent_active=None,
    opponent_bench=(),
    own_prizes=6,
    opponent_prizes=6,
    stadium=(),
    confused=False,
    asleep=False,
    paralyzed=False,
):
    active = own_active or pokemon(678, 10, hp=340, energy_cards=((6, 51),))
    target = opponent_active or pokemon(900, 110, player=1, hp=300)
    return {
        "select": {
            "type": 0,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [
                {"type": int(OptionType.ATTACK), "attackId": attack_id}
                for attack_id in attack_ids
            ],
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": 3,
            "turnActionCount": 4,
            "yourIndex": 0,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": list(stadium),
            "looking": None,
            "players": [
                {
                    "active": [active],
                    "bench": list(own_bench),
                    "benchMax": 5,
                    "deckCount": 40,
                    "discard": list(own_discard),
                    "prize": [None] * own_prizes,
                    "handCount": 0,
                    "hand": [],
                    "poisoned": False,
                    "burned": False,
                    "asleep": asleep,
                    "paralyzed": paralyzed,
                    "confused": confused,
                },
                {
                    "active": [target],
                    "bench": list(opponent_bench),
                    "benchMax": 5,
                    "deckCount": 40,
                    "discard": [],
                    "prize": [None] * opponent_prizes,
                    "handCount": 5,
                    "hand": None,
                    "poisoned": False,
                    "burned": False,
                    "asleep": False,
                    "paralyzed": False,
                    "confused": False,
                },
            ],
        },
    }


def checked_state(obs, *, ppp_count=0, previous_attack=None):
    tracker = PublicHistoryTracker()
    initial = deepcopy(obs)
    initial["current"]["turn"] = 1
    initial["current"]["turnActionCount"] = 0
    initial["logs"] = []
    if previous_attack is not None:
        active = initial["current"]["players"][0]["active"][0]
        initial["logs"].append(
            {
                "type": int(LogType.ATTACK),
                "playerIndex": 0,
                "cardId": active["id"],
                "serial": active["serial"],
                "attackId": previous_attack,
            }
        )
    build_public_state(initial, game_epoch=7, history_tracker=tracker)
    current = deepcopy(obs)
    current["logs"] = [
        {
            "type": int(LogType.PLAY),
            "playerIndex": 0,
            "cardId": 1141,
            "serial": 800 + index,
        }
        for index in range(ppp_count)
    ]
    return build_public_state(current, game_epoch=7, history_tracker=tracker)


def table_for(obs, registry, **state_kwargs):
    state = checked_state(obs, **state_kwargs)
    options = build_semantic_options(obs)
    return state, options, build_attack_outcome_table(state, options, registry)


def test_table_binds_state_option_multiset_and_registry_digest():
    obs = observation((982, 983))
    registry = registry_for((982, 983))
    state, options, table = table_for(obs, registry)

    assert semantic_options_fingerprint(options) == semantic_options_fingerprint(
        tuple(reversed(options))
    )
    assert table.matches(state, tuple(reversed(options)), registry)
    assert table.attacker_ref == state.own_active.ref
    assert table.target_ref == state.opponent_active.ref
    assert tuple(row.attack_id for row in table.rows) == (982, 983)

    fewer_options = build_semantic_options(observation((982,)))
    assert not table.matches(state, fewer_options, registry)
    changed_target = pokemon_catalog_row(900, "Test Target", hp=300, weakness=6)
    changed_registry = registry_for((982, 983), target_row=changed_target)
    assert not table.matches(state, options, changed_registry)


def test_safe_fallback_elevates_only_a_current_whole_attack_outcome_table():
    target_row = pokemon_catalog_row(900, "Exact KO Target", hp=100)
    registry = registry_for((983,), target_row=target_row)
    obs = observation(
        (983,),
        opponent_active=pokemon(900, 110, player=1, hp=100),
    )
    state, options, table = table_for(obs, registry)

    strict = safe_fallback(
        state,
        options,
        {},
        ResourceLedger(()),
        attack_outcomes=table,
        registry=registry,
    )
    assert strict.decision.reason_code == "FALLBACK_EXACT_KO_ATTACK_983"

    missing_registry = safe_fallback(
        state,
        options,
        {},
        ResourceLedger(()),
        attack_outcomes=table,
    )
    assert missing_registry.decision.reason_code == "FALLBACK_LEGAL_ATTACK_983"
    assert missing_registry.reasons == ("ATTACK_OUTCOME_REGISTRY_REQUIRED",)

    changed_options = build_semantic_options(observation((982,)))
    option_mismatch = safe_fallback(
        state,
        changed_options,
        {},
        ResourceLedger(()),
        attack_outcomes=table,
        registry=registry,
    )
    assert option_mismatch.decision.reason_code == "FALLBACK_LEGAL_ATTACK_982"
    assert option_mismatch.reasons == (
        "ATTACK_OUTCOME_TABLE_BINDING_MISMATCH",
    )

    changed_target = pokemon_catalog_row(
        900,
        "Exact KO Target",
        hp=100,
        weakness=6,
    )
    changed_registry = registry_for((983,), target_row=changed_target)
    registry_mismatch = safe_fallback(
        state,
        options,
        {},
        ResourceLedger(()),
        attack_outcomes=table,
        registry=changed_registry,
    )
    assert registry_mismatch.decision.reason_code == "FALLBACK_LEGAL_ATTACK_983"
    assert registry_mismatch.reasons == (
        "ATTACK_OUTCOME_TABLE_BINDING_MISMATCH",
    )

    changed_observation = deepcopy(obs)
    changed_observation["current"]["players"][1]["active"][0]["serial"] = 111
    changed_state = checked_state(changed_observation)
    changed_state_options = build_semantic_options(changed_observation)
    state_mismatch = safe_fallback(
        changed_state,
        changed_state_options,
        {},
        ResourceLedger(()),
        attack_outcomes=table,
        registry=registry,
    )
    assert state_mismatch.decision.reason_code == "FALLBACK_LEGAL_ATTACK_983"
    assert state_mismatch.reasons == (
        "ATTACK_OUTCOME_TABLE_BINDING_MISMATCH",
    )


def test_attack_routes_certify_nonterminal_prizes_and_prefer_aura_same_ko():
    target_row = pokemon_catalog_row(900, "Exact KO Target", hp=100)
    bench_row = pokemon_catalog_row(901, "Public Bench", hp=100)
    registry = registry_for(
        (982, 983),
        target_row=target_row,
        extra_rows=(bench_row,),
    )
    obs = observation(
        (982, 983),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        opponent_bench=(pokemon(901, 111, player=1, hp=100),),
        own_prizes=2,
    )
    state, options, table = table_for(obs, registry)

    proposals = enumerate_attack_routes(state, options, table, registry)

    assert len(proposals) == 2
    assert {proposal.certificate_kind for proposal in proposals} == {
        CertificateKind.PRIZE_GAIN_NOW
    }
    assert {proposal.proof.schema for proposal in proposals} == {
        ProofSchema.ATTACK_OUTCOME_V1
    }
    assert all(
        proposal.tier == ResolverTier.EXACT_CURRENT_TURN_PRIZE
        for proposal in proposals
    )
    resolution = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        proposals,
        registry=registry,
    )
    assert resolution.selected.action_spec.choices[0].attack_id == 982
    assert resolution.selected.proof.guaranteed_prizes == 1


def test_attack_routes_choose_greatest_damage_margin_when_both_attacks_win():
    target_row = pokemon_catalog_row(900, "Final Prize Target", hp=100)
    bench_row = pokemon_catalog_row(901, "Public Bench", hp=100)
    registry = registry_for(
        (982, 983),
        target_row=target_row,
        extra_rows=(bench_row,),
    )
    obs = observation(
        (982, 983),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        opponent_bench=(pokemon(901, 111, player=1, hp=100),),
        own_prizes=1,
    )
    state, options, table = table_for(obs, registry)

    proposals = enumerate_attack_routes(state, options, table, registry)
    resolution = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        proposals,
        registry=registry,
    )

    assert len(proposals) == 2
    assert all(
        proposal.certificate_kind == CertificateKind.WIN_NOW
        for proposal in proposals
    )
    assert resolution.selected.tier == ResolverTier.EXACT_WIN_NOW
    assert resolution.selected.action_spec.choices[0].attack_id == 983
    assert resolution.selected.proof.fact("damage_margin") == 170


def test_non_ko_attack_routes_require_the_whole_attack_surface_to_be_exact():
    target_row = pokemon_catalog_row(900, "Large Target", hp=300)
    registry = registry_for((982, 983), target_row=target_row)
    obs = observation(
        (982, 983),
        opponent_active=pokemon(900, 110, player=1, hp=300),
    )
    state, options, table = table_for(obs, registry)
    proposals = enumerate_attack_routes(state, options, table, registry)
    resolution = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        proposals,
        registry=registry,
    )

    assert len(proposals) == 2
    assert all(
        proposal.certificate_kind == CertificateKind.ATTACK_COMPLETION
        for proposal in proposals
    )
    assert resolution.selected.tier == ResolverTier.BEST_CERTIFIED_ATTACK
    assert resolution.selected.action_spec.choices[0].attack_id == 983

    unknown_obs = deepcopy(obs)
    unknown_obs["current"]["players"][0]["confused"] = True
    unknown_state = checked_state(unknown_obs)
    unknown_options = build_semantic_options(unknown_obs)
    unknown_table = build_attack_outcome_table(
        unknown_state,
        unknown_options,
        registry,
    )
    assert not unknown_table.exact
    assert (
        enumerate_attack_routes(
            unknown_state,
            unknown_options,
            unknown_table,
            registry,
        )
        == ()
    )


def test_attack_proof_fails_closed_on_stale_bindings_and_field_replacement():
    target_row = pokemon_catalog_row(900, "Exact KO Target", hp=100)
    bench_row = pokemon_catalog_row(901, "Public Bench", hp=100)
    registry = registry_for(
        (983,),
        target_row=target_row,
        extra_rows=(bench_row,),
    )
    obs = observation(
        (983,),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        opponent_bench=(pokemon(901, 111, player=1, hp=100),),
        own_prizes=2,
    )
    state, options, table = table_for(obs, registry)
    spec = ActionSpec.single(options[0].key)
    proof = attack_outcome_proof(state, options, registry, table, spec)

    with pytest.raises(ValueError, match="integrity receipt"):
        replace(proof, guaranteed_prizes=2)

    changed_obs = deepcopy(obs)
    changed_obs["current"]["turnActionCount"] += 1
    changed_state = checked_state(changed_obs)
    changed_options = build_semantic_options(changed_obs)
    with pytest.raises(ValueError, match="must match"):
        attack_outcome_proof(
            changed_state,
            changed_options,
            registry,
            table,
            spec,
        )
    assert (
        enumerate_attack_routes(
            changed_state,
            changed_options,
            table,
            registry,
        )
        == ()
    )


def test_attack_resolver_rechecks_integrity_and_current_registry():
    target_row = pokemon_catalog_row(900, "Exact KO Target", hp=100)
    bench_row = pokemon_catalog_row(901, "Public Bench", hp=100)
    registry = registry_for(
        (983,),
        target_row=target_row,
        extra_rows=(bench_row,),
    )
    obs = observation(
        (983,),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        opponent_bench=(pokemon(901, 111, player=1, hp=100),),
        own_prizes=2,
    )
    state, options, table = table_for(obs, registry)

    missing_registry_proposal = enumerate_attack_routes(
        state,
        options,
        table,
        registry,
    )[0]
    missing_registry = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        (missing_registry_proposal,),
    )
    assert missing_registry.selected is None
    assert "CURRENT_REGISTRY_REQUIRED" in missing_registry.rejections[0].reasons

    changed_registry = registry_for(
        (983,),
        target_row=pokemon_catalog_row(
            900,
            "Exact KO Target",
            hp=100,
            weakness=6,
        ),
        extra_rows=(bench_row,),
    )
    stale_registry_proposal = enumerate_attack_routes(
        state,
        options,
        table,
        registry,
    )[0]
    stale_registry = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        (stale_registry_proposal,),
        registry=changed_registry,
    )
    assert stale_registry.selected is None
    assert "PROOF_REGISTRY_STALE" in stale_registry.rejections[0].reasons

    tampered_proposal = enumerate_attack_routes(
        state,
        options,
        table,
        registry,
    )[0]
    object.__setattr__(
        tampered_proposal.proof,
        "guaranteed_prizes",
        tampered_proposal.proof.guaranteed_prizes + 1,
    )
    tampered = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        (tampered_proposal,),
        registry=registry,
    )
    assert tampered.selected is None
    assert "PROOF_INTEGRITY_INVALID" in tampered.rejections[0].reasons


def test_terminal_aura_win_does_not_require_irrelevant_callback_completion():
    target_row = pokemon_catalog_row(900, "Final Prize Target", hp=100)
    own_bench_row = pokemon_catalog_row(677, "Riolu", hp=70)
    opponent_bench_row = pokemon_catalog_row(901, "Public Bench", hp=100)
    registry = registry_for(
        (982,),
        target_row=target_row,
        extra_rows=(own_bench_row, opponent_bench_row),
    )
    obs = observation(
        (982,),
        own_bench=(pokemon(677, 12, hp=70),),
        own_discard=(card(6, 51),),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        opponent_bench=(pokemon(901, 111, player=1, hp=100),),
        own_prizes=1,
    )
    state, options, table = table_for(obs, registry)
    outcome = table.get(982)

    assert outcome.exact_game_win
    assert not outcome.exact
    assert outcome.callback.requires_selection
    proposals = enumerate_attack_routes(state, options, table, registry)
    assert len(proposals) == 1
    assert proposals[0].certificate_kind == CertificateKind.WIN_NOW
    resolution = resolve_proposals(
        state,
        options,
        ResourceLedger(()),
        proposals,
        registry=registry,
    )
    assert resolution.selected.action_spec.choices[0].attack_id == 982


def test_board_out_win_can_be_certified_even_when_prize_reduction_yields_zero():
    target_row = pokemon_catalog_row(272, "Lillie's Target", hp=100)
    registry = registry_for(
        (983,),
        target_row=target_row,
        extra_rows=(effect_catalog_row("LILLIES_PEARL"),),
    )
    obs = observation(
        (983,),
        opponent_active=pokemon(
            272,
            110,
            player=1,
            hp=100,
            tools=((1172, 211),),
        ),
        own_prizes=6,
    )
    state, options, table = table_for(obs, registry)

    assert table.get(983).exact_game_win
    assert table.get(983).prizes_taken == 0
    proof = attack_outcome_proof(
        state,
        options,
        registry,
        table,
        ActionSpec.single(options[0].key),
    )
    assert proof.kind == CertificateKind.WIN_NOW
    assert proof.guaranteed_prizes == 0


def test_state_rejects_options_built_from_a_different_observation():
    original = observation((982, 983))
    registry = registry_for((982, 983))
    state = checked_state(original)

    changed = observation((982,))
    changed_options = build_semantic_options(changed)
    table = build_attack_outcome_table(state, changed_options, registry)

    assert table.build_unknown_reasons == (
        "SOURCE_OPTION_FINGERPRINT_MISMATCH",
    )
    assert not table.matches(state, changed_options, registry)
    assert not table.get(982).legality_exact
    assert not table.get(982).exact_damage


def test_raw_prize_count_cannot_override_or_contradict_visible_prize_list():
    obs = observation((983,), own_prizes=2)
    obs["current"]["players"][0]["prizeCount"] = 1
    registry = registry_for((983,))
    state, _, table = table_for(obs, registry)

    assert state.own.prize_count == 2
    assert not state.source_combat_complete
    assert table.build_unknown_reasons == ("INCOMPLETE_PUBLIC_COMBAT_SOURCE",)
    assert not table.get(983).exact_damage


def test_raw_option_reorder_reindexes_and_rebinds_the_same_semantic_attack():
    obs = observation((982, 983))
    registry = registry_for((982, 983))
    state, options, table = table_for(obs, registry)

    reordered_obs = deepcopy(obs)
    reordered_obs["select"]["option"].reverse()
    reordered_options = build_semantic_options(reordered_obs)
    aura = table.get(982)

    assert semantic_options_fingerprint(options) == semantic_options_fingerprint(
        reordered_options
    )
    assert table.matches(state, reordered_options, registry)
    assert ActionSpec.single(aura.option_key).bind(reordered_options) == [1]


def test_changed_physical_endpoints_invalidate_old_table_and_rebuild_refs():
    obs = observation((983,))
    registry = registry_for((983,))
    state, options, table = table_for(obs, registry)

    changed_obs = deepcopy(obs)
    changed_obs["current"]["players"][0]["active"][0]["serial"] = 12
    changed_obs["current"]["players"][1]["active"][0]["serial"] = 112
    changed_state, changed_options, changed_table = table_for(changed_obs, registry)

    assert not table.matches(changed_state, changed_options, registry)
    assert changed_table.get(983).attacker_ref.serial == 12
    assert changed_table.get(983).target_ref.serial == 112
    assert changed_table.matches(changed_state, changed_options, registry)


def test_no_attack_option_never_produces_an_exact_attack_table():
    obs = observation(())
    obs["select"]["option"] = [{"type": int(OptionType.END), "playerIndex": 0}]
    registry = registry_for((982,))
    _, _, table = table_for(obs, registry)

    assert table.rows == ()
    assert table.build_unknown_reasons == ("NO_ATTACK_OPTION",)
    assert not table.exact


def test_unchecked_state_and_replaced_outcome_cannot_be_strong_evidence():
    obs = observation((983,))
    registry = registry_for((983,))
    state, options, table = table_for(obs, registry)
    row = table.get(983)

    forged_state = replace(state)
    forged_table = build_attack_outcome_table(forged_state, options, registry)
    assert forged_table.build_unknown_reasons == ("UNCHECKED_PUBLIC_STATE",)
    assert not forged_table.matches(forged_state, options, registry)
    assert not forged_table.get(983).exact_damage

    forged_row = replace(row)
    assert isinstance(forged_row, AttackOutcome)
    assert not forged_row.authoritative
    assert not forged_row.legality_exact
    assert not forged_row.exact_damage
    assert not forged_row.post_attack_exact
    assert not forged_row.prize_exact
    assert not forged_row.terminal_exact
    assert forged_row.damage_margin is None
    assert forged_row.guaranteed_damage == 0
    assert forged_row.future_lock_cost is None
    with pytest.raises(ValueError, match="checked builder"):
        BoundAttackOutcomeTable(
            state_fingerprint=table.state_fingerprint,
            semantic_options_fingerprint=table.semantic_options_fingerprint,
            registry_digest=table.registry_digest,
            attacker_ref=table.attacker_ref,
            target_ref=table.target_ref,
            rows=(row,),
            build_unknown_reasons=(),
            issuer_token=object(),
        )


def test_aura_target_damage_prize_and_callback_exactness_are_separate():
    target_row = pokemon_catalog_row(900, "Test Target", hp=100)
    bench_row = pokemon_catalog_row(901, "Backup", hp=100)
    registry = registry_for((982,), target_row=target_row, extra_rows=(bench_row,))
    obs = observation(
        (982,),
        own_bench=(pokemon(901, 20, hp=100),),
        own_discard=(card(6, 70), card(6, 71), card(6, 72)),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        own_prizes=1,
    )
    _, _, table = table_for(obs, registry)
    row = table.get(982)

    assert row.authoritative and row.legality_exact and row.legal and row.payable
    assert row.exact_damage and row.final_damage == 130 and row.exact_ko
    assert row.prize_exact and row.prizes_taken == 1 and row.own_prizes_after == 0
    assert row.terminal_exact and row.exact_game_win
    assert not row.post_attack_exact
    assert row.post_attack_unknown_reasons == ("AURA_CALLBACK_REQUIRES_SELECTION",)
    assert row.callback.requires_selection
    assert tuple(ref.serial for ref in row.callback.available_source_refs) == (
        70,
        71,
        72,
    )
    assert tuple(ref.lineage_serial for ref in row.callback.eligible_target_refs) == (
        20,
    )
    assert not row.exact


def test_knocking_out_the_last_opposing_pokemon_is_an_exact_game_win():
    target_row = pokemon_catalog_row(900, "Last Target", hp=100)
    registry = registry_for((983,), target_row=target_row)
    obs = observation(
        (983,),
        opponent_active=pokemon(900, 110, player=1, hp=100),
        own_prizes=6,
    )
    _, _, table = table_for(obs, registry)
    row = table.get(983)

    assert row.exact_ko
    assert row.prizes_taken == 1 and row.own_prizes_after == 5
    assert row.terminal_exact and row.exact_game_win
    assert row.wins_game and not row.loses_game and not row.draws_game


def test_prizes_taken_are_capped_by_visible_remaining_prize_count():
    target_row = pokemon_catalog_row(
        901,
        "Three Prize Target",
        hp=100,
        basic=False,
        stage1=True,
        mega_ex=True,
    )
    backup_row = pokemon_catalog_row(902, "Backup", hp=100)
    registry = registry_for(
        (983,),
        target_row=target_row,
        extra_rows=(backup_row,),
    )
    obs = observation(
        (983,),
        opponent_active=pokemon(901, 110, player=1, hp=100),
        opponent_bench=(pokemon(902, 120, player=1, hp=100),),
        own_prizes=1,
    )
    _, _, table = table_for(obs, registry)
    row = table.get(983)

    assert row.exact_ko
    assert row.prize_exact and row.prizes_taken == 1
    assert row.own_prizes_after == 0 and row.exact_game_win


def test_ppp_applies_before_weakness_and_only_public_history_is_used():
    target_row = pokemon_catalog_row(900, "Weak Target", hp=300, weakness=6)
    registry = registry_for((982,), target_row=target_row)
    obs = observation(
        (982,),
        opponent_active=pokemon(900, 110, player=1, hp=300),
    )
    _, _, table = table_for(obs, registry, ppp_count=2)
    row = table.get(982)

    assert row.ppp_count == 2
    assert row.ppp_bonus == 60
    assert row.before_weakness == 190
    assert row.weakness_multiplier == 2
    assert row.after_weakness_resistance == 380
    assert row.final_damage == 380
    assert row.knockout

    state_without_tracker = build_public_state(obs, game_epoch=7)
    options = build_semantic_options(obs)
    unknown = build_attack_outcome_table(state_without_tracker, options, registry).get(
        982
    )
    assert not unknown.exact_damage
    assert "PUBLIC_ATTACK_HISTORY_INCOMPLETE" in unknown.damage_unknown_reasons


def test_cosmic_beam_false_condition_does_nothing_and_ignores_ppp_and_wr():
    target_row = pokemon_catalog_row(
        900,
        "Weak Target",
        hp=100,
        weakness=6,
        resistance=6,
    )
    registry = registry_for((980,), target_row=target_row)
    obs = observation(
        (980,),
        own_active=pokemon(676, 10, hp=110, energy_cards=((6, 51),)),
        opponent_active=pokemon(900, 110, player=1, hp=100),
    )
    _, _, table = table_for(obs, registry, ppp_count=4)
    row = table.get(980)

    assert row.exact_damage
    assert row.ppp_count == 4 and row.ppp_bonus == 0
    assert row.before_weakness == 0
    assert row.weakness_multiplier == 1 and row.resistance_reduction == 0
    assert row.final_damage == 0 and not row.knockout


def test_same_attack_lock_is_exact_and_lineage_scoped():
    registry = registry_for((983,))
    obs = observation((983,))
    _, _, locked_table = table_for(obs, registry, previous_attack=983)
    locked = locked_table.get(983)

    assert locked.legality_exact
    assert locked.legal is False and locked.payable is False
    assert not locked.exact_damage

    _, _, other_attack_table = table_for(obs, registry, previous_attack=982)
    assert other_attack_table.get(983).legal is True
    assert other_attack_table.get(983).exact_damage


def test_same_attack_lock_does_not_cross_physical_lineages():
    registry = registry_for((983,))
    first = observation(
        (983,),
        own_active=pokemon(
            678,
            10,
            hp=340,
            energy_cards=((6, 51), (6, 52)),
        ),
    )
    first["current"]["turn"] = 1
    first["current"]["turnActionCount"] = 0
    first["logs"] = [
        {
            "type": int(LogType.ATTACK),
            "playerIndex": 0,
            "cardId": 678,
            "serial": 10,
            "attackId": 983,
        }
    ]
    tracker = PublicHistoryTracker()
    build_public_state(first, game_epoch=7, history_tracker=tracker)

    second = observation(
        (983,),
        own_active=pokemon(
            678,
            20,
            hp=340,
            energy_cards=((6, 61), (6, 62)),
        ),
        own_bench=(
            pokemon(
                678,
                10,
                hp=340,
                energy_cards=((6, 51), (6, 52)),
            ),
        ),
    )
    state = build_public_state(second, game_epoch=7, history_tracker=tracker)
    options = build_semantic_options(second)
    row = build_attack_outcome_table(state, options, registry).get(983)

    assert row.legality_exact and row.legal and row.payable
    assert row.exact_damage


def test_same_attack_lock_clears_after_switching_out_and_back():
    bench_row = pokemon_catalog_row(675, "Lunatone", hp=110)
    registry = registry_for((983,), extra_rows=(bench_row,))
    tracker = PublicHistoryTracker()

    first = observation(
        (983,),
        own_bench=(pokemon(675, 20, hp=110),),
    )
    first["current"]["turn"] = 1
    first["current"]["turnActionCount"] = 0
    first["logs"] = [
        {
            "type": int(LogType.ATTACK),
            "playerIndex": 0,
            "cardId": 678,
            "serial": 10,
            "attackId": 983,
        }
    ]
    build_public_state(first, game_epoch=7, history_tracker=tracker)

    returned = observation(
        (983,),
        own_bench=(pokemon(675, 20, hp=110),),
    )
    returned["logs"] = [
        {
            "type": int(LogType.CHANGE),
            "playerIndex": 0,
            "cardIdBefore": 678,
            "serialBefore": 10,
            "cardIdAfter": 675,
            "serialAfter": 20,
        },
        {
            "type": int(LogType.CHANGE),
            "playerIndex": 0,
            "cardIdBefore": 675,
            "serialBefore": 20,
            "cardIdAfter": 678,
            "serialAfter": 10,
        },
    ]
    state = build_public_state(returned, game_epoch=7, history_tracker=tracker)
    options = build_semantic_options(returned)
    row = build_attack_outcome_table(state, options, registry).get(983)

    assert state.history_complete
    assert state.last_attack_by_lineage == ()
    assert row.legality_exact and row.legal and row.payable
    assert row.exact_damage


def test_same_attack_lock_clears_on_evolution_and_after_expiry():
    registry = registry_for((983,))
    tracker = PublicHistoryTracker()
    first = observation(
        (983,),
        own_active=pokemon(
            678,
            10,
            hp=340,
            energy_cards=((6, 51),),
            pre=(card(677, 5),),
        ),
    )
    first["current"]["turn"] = 1
    first["current"]["turnActionCount"] = 0
    first["logs"] = [
        {
            "type": int(LogType.ATTACK),
            "playerIndex": 0,
            "cardId": 678,
            "serial": 10,
            "attackId": 983,
        }
    ]
    build_public_state(first, game_epoch=7, history_tracker=tracker)

    evolved = observation(
        (983,),
        own_active=pokemon(
            678,
            11,
            hp=340,
            energy_cards=((6, 51),),
            pre=(card(677, 5), card(678, 10)),
        ),
    )
    evolved["logs"] = [
        {
            "type": int(LogType.EVOLVE),
            "playerIndex": 0,
            "cardId": 678,
            "serial": 11,
            "cardIdTarget": 678,
            "serialTarget": 10,
        }
    ]
    evolved_state = build_public_state(
        evolved,
        game_epoch=7,
        history_tracker=tracker,
    )
    evolved_row = build_attack_outcome_table(
        evolved_state,
        build_semantic_options(evolved),
        registry,
    ).get(983)
    assert evolved_state.last_attack_by_lineage == ()
    assert evolved_row.legality_exact and evolved_row.legal

    expiry_tracker = PublicHistoryTracker()
    build_public_state(first, game_epoch=8, history_tracker=expiry_tracker)
    expired = deepcopy(first)
    expired["current"]["turn"] = 5
    expired["current"]["turnActionCount"] = 4
    expired["logs"] = []
    expired_state = build_public_state(
        expired,
        game_epoch=8,
        history_tracker=expiry_tracker,
    )
    expired_row = build_attack_outcome_table(
        expired_state,
        build_semantic_options(expired),
        registry,
    ).get(983)
    assert expired_state.last_attack_by_lineage == ()
    assert expired_row.legality_exact and expired_row.legal


def test_future_lock_cost_is_zero_when_the_attacker_is_knocked_out():
    spiky = effect_catalog_row("SPIKY_ENERGY")
    target_row = pokemon_catalog_row(900, "Spiky Target", hp=300)
    backup_row = pokemon_catalog_row(901, "Backup", hp=100)
    registry = registry_for(
        (983,),
        target_row=target_row,
        extra_rows=(spiky, backup_row),
    )
    obs = observation(
        (983,),
        own_active=pokemon(
            678,
            10,
            hp=20,
            max_hp=340,
            energy_cards=((6, 51),),
        ),
        own_bench=(pokemon(901, 20, hp=100),),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=300,
            energy_cards=((14, 151),),
        ),
        opponent_bench=(pokemon(901, 120, player=1, hp=100),),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(983)

    assert row.post_attack_exact and row.attacker_knockout
    assert row.next_turn_lock_applied
    assert row.terminal_exact and not row.wins_game and not row.loses_game
    assert row.future_lock_cost == 0


def test_crustle_prevents_mega_damage_but_aura_callback_remains():
    crustle = effect_catalog_row("MYSTERIOUS_ROCK_INN")
    bench_row = pokemon_catalog_row(901, "Backup", hp=100)
    registry = registry_for(
        (982,),
        target_row=crustle,
        extra_rows=(bench_row,),
    )
    obs = observation(
        (982,),
        own_bench=(pokemon(901, 20, hp=100),),
        own_discard=(card(6, 70),),
        opponent_active=pokemon(345, 110, player=1, hp=150),
    )
    _, _, table = table_for(obs, registry, ppp_count=4)
    row = table.get(982)

    assert row.exact_damage and row.final_damage == 0
    assert row.prevention_effects == ("MYSTERIOUS_ROCK_INN",)
    assert not row.knockout
    assert row.callback.requires_selection
    assert not row.post_attack_exact


def test_resistance_and_after_wr_stadium_reduction_are_exact():
    resistant_target = pokemon_catalog_row(
        900,
        "Resistant Target",
        hp=300,
        resistance=6,
    )
    resistant_registry = registry_for((982,), target_row=resistant_target)
    resistant_obs = observation(
        (982,),
        opponent_active=pokemon(900, 110, player=1, hp=300),
    )
    _, _, resistant_table = table_for(resistant_obs, resistant_registry)
    resistant = resistant_table.get(982)
    assert resistant.after_weakness_resistance == 100
    assert resistant.field_reduction == 0 and resistant.final_damage == 100

    full_metal = effect_catalog_row("FULL_METAL_LAB")
    metal_target = pokemon_catalog_row(
        901,
        "Weak Metal Target",
        hp=300,
        energy_type=8,
        weakness=6,
    )
    metal_registry = registry_for(
        (982,),
        target_row=metal_target,
        extra_rows=(full_metal,),
    )
    metal_obs = observation(
        (982,),
        opponent_active=pokemon(901, 111, player=1, hp=300),
        stadium=(card(1244, 301),),
    )
    _, _, metal_table = table_for(metal_obs, metal_registry)
    metal = metal_table.get(982)
    assert metal.after_weakness_resistance == 260
    assert metal.field_reduction == 30 and metal.final_damage == 230


def test_current_cape_hp_is_used_without_reconstructing_base_hp():
    cape = effect_catalog_row("HEROS_CAPE")
    target_row = pokemon_catalog_row(900, "Cape Target", hp=300)
    registry = registry_for((982,), target_row=target_row, extra_rows=(cape,))
    obs = observation(
        (982,),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=140,
            max_hp=400,
            tools=((1159, 190),),
        ),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(982)

    assert row.exact_damage and row.final_damage == 130
    assert row.target_starting_hp == 140
    assert row.target_hp_after == 10 and not row.knockout


def test_four_ppp_can_still_leave_aura_short_of_a_knockout():
    target_row = pokemon_catalog_row(900, "Large Target", hp=251)
    registry = registry_for((982,), target_row=target_row)
    obs = observation(
        (982,),
        opponent_active=pokemon(900, 110, player=1, hp=251),
    )
    _, _, table = table_for(obs, registry, ppp_count=4)
    row = table.get(982)

    assert row.exact_damage and row.ppp_count == 4
    assert row.final_damage == 250
    assert row.target_hp_after == 1 and not row.knockout


def test_sturdy_keeps_attack_damage_distinct_from_hp_loss_and_self_effects():
    sturdy = effect_catalog_row("STURDY")
    spiky = effect_catalog_row("SPIKY_ENERGY")
    registry = registry_for((978,), target_row=sturdy, extra_rows=(spiky,))
    obs = observation(
        (978,),
        own_active=pokemon(
            674,
            10,
            hp=140,
            energy_cards=((6, 51), (6, 52), (6, 53)),
        ),
        opponent_active=pokemon(
            533,
            110,
            player=1,
            hp=150,
            energy_cards=((14, 151),),
        ),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(978)

    assert row.exact_damage
    assert row.damage_before_ko_prevention == 210
    assert row.final_damage == 210
    assert row.target_hp_loss == 140 and row.target_hp_after == 10
    assert not row.knockout and row.prizes_taken == 0
    assert row.post_attack_exact
    assert row.post_attack_unknown_reasons == ()
    assert row.attacker_attack_effect_damage == 70
    assert row.attacker_damage_counters_placed == 2
    assert row.attacker_damage == 90
    assert row.attacker_hp_after == 50 and not row.attacker_knockout
    assert {"STURDY", "SPIKY_ENERGY", "WILD_PRESS"}.issubset(row.triggered_effects)


def test_each_attached_spiky_energy_adds_its_own_damage_counters():
    spiky = effect_catalog_row("SPIKY_ENERGY")
    target_row = pokemon_catalog_row(900, "Spiky Target", hp=300)
    registry = registry_for((978,), target_row=target_row, extra_rows=(spiky,))
    obs = observation(
        (978,),
        own_active=pokemon(
            674,
            10,
            hp=140,
            energy_cards=((6, 51), (6, 52), (6, 53)),
        ),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=300,
            energy_cards=((14, 151), (14, 152)),
        ),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(978)

    assert row.exact_damage and row.final_damage == 210
    assert row.attacker_attack_effect_damage == 70
    assert row.attacker_damage_counters_placed == 4
    assert row.attacker_damage == 110
    assert row.attacker_hp_after == 30 and not row.attacker_knockout


def test_duplicate_aura_discard_source_fails_post_attack_closed():
    target_row = pokemon_catalog_row(900, "Test Target", hp=300)
    bench_row = pokemon_catalog_row(901, "Backup", hp=100)
    registry = registry_for((982,), target_row=target_row, extra_rows=(bench_row,))
    duplicate_energy = card(6, 70)
    obs = observation(
        (982,),
        own_bench=(pokemon(901, 20, hp=100),),
        own_discard=(duplicate_energy, deepcopy(duplicate_energy)),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(982)

    assert row.exact_damage and row.final_damage == 130
    assert row.callback is None
    assert not row.post_attack_exact
    assert row.post_attack_unknown_reasons == (
        "DUPLICATE_AURA_CALLBACK_SOURCE_REF",
    )


def test_spiky_wild_press_simultaneous_ko_certifies_prizes_and_draw():
    spiky = effect_catalog_row("SPIKY_ENERGY")
    target_row = pokemon_catalog_row(900, "Spiky Target", hp=210)
    registry = registry_for((978,), target_row=target_row, extra_rows=(spiky,))
    obs = observation(
        (978,),
        own_active=pokemon(
            674,
            10,
            hp=80,
            max_hp=140,
            energy_cards=((6, 51), (6, 52), (6, 53)),
        ),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=210,
            energy_cards=((14, 151),),
        ),
        own_prizes=1,
        opponent_prizes=1,
    )
    _, _, table = table_for(obs, registry)
    row = table.get(978)

    assert row.exact_damage and row.knockout
    assert row.attacker_knockout
    assert row.post_attack_exact
    assert row.prize_exact
    assert row.prizes_taken == 1 and row.opponent_prizes_taken == 1
    assert row.own_prizes_after == 0 and row.opponent_prizes_after == 0
    assert row.terminal_exact and row.exact_game_draw
    assert not row.exact_game_win
    assert row.prize_unknown_reasons == ()
    assert row.terminal_unknown_reasons == ()


def test_unknown_attachment_fails_closed_but_jamming_suppresses_unknown_tool():
    target_row = pokemon_catalog_row(900, "Tool Target", hp=300)
    registry = registry_for((983,), target_row=target_row)
    target = pokemon(900, 110, player=1, hp=300, tools=((999, 199),))
    obs = observation((983,), opponent_active=target)
    _, _, unknown_table = table_for(obs, registry)
    unknown = unknown_table.get(983)
    assert not unknown.exact_damage
    assert any(
        "UNREGISTERED_TOOL_CARD_999" in reason
        for reason in unknown.damage_unknown_reasons
    )

    jamming = effect_catalog_row("JAMMING_TOWER")
    jammed_registry = registry_for(
        (983,),
        target_row=target_row,
        extra_rows=(jamming,),
    )
    jammed_obs = observation(
        (983,),
        opponent_active=target,
        stadium=(card(1246, 301),),
    )
    _, _, jammed_table = table_for(jammed_obs, jammed_registry)
    assert jammed_table.get(983).exact_damage


def test_handheld_fan_selection_uses_the_attacking_players_bench():
    fan = effect_catalog_row("HANDHELD_FAN")
    target_row = pokemon_catalog_row(900, "Fan Target", hp=300)
    backup_row = pokemon_catalog_row(901, "Backup", hp=100)
    registry = registry_for(
        (982,),
        target_row=target_row,
        extra_rows=(fan, backup_row),
    )
    target = pokemon(900, 110, player=1, hp=300, tools=((1161, 190),))

    opponent_bench_only = observation(
        (982,),
        opponent_active=target,
        opponent_bench=(pokemon(901, 120, player=1, hp=100),),
    )
    _, _, no_destination_table = table_for(opponent_bench_only, registry)
    no_destination = no_destination_table.get(982)
    assert no_destination.post_attack_exact
    assert "HANDHELD_FAN" in no_destination.triggered_effects

    own_bench_available = observation(
        (982,),
        own_bench=(pokemon(901, 20, hp=100),),
        opponent_active=target,
    )
    _, _, destination_table = table_for(own_bench_available, registry)
    destination = destination_table.get(982)
    assert not destination.post_attack_exact
    assert destination.post_attack_unknown_reasons == (
        "HANDHELD_FAN_REQUIRES_SELECTION",
    )


def test_duplicate_in_play_physical_reference_fails_closed():
    spiky = effect_catalog_row("SPIKY_ENERGY")
    target_row = pokemon_catalog_row(900, "Spiky Target", hp=300)
    registry = registry_for((982,), target_row=target_row, extra_rows=(spiky,))
    obs = observation(
        (982,),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=300,
            energy_cards=((14, 151), (14, 151)),
        ),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(982)

    assert not row.exact_damage
    assert "DUPLICATE_IN_PLAY_PHYSICAL_REF" in row.damage_unknown_reasons


def test_non_pokemon_card_extra_skill_and_wrong_zone_type_fail_closed():
    clean_spiky = effect_catalog_row("SPIKY_ENERGY")
    target_row = pokemon_catalog_row(900, "Spiky Target", hp=300)
    clean_registry = registry_for(
        (982,),
        target_row=target_row,
        extra_rows=(clean_spiky,),
    )

    extra_skill_spiky = deepcopy(clean_spiky)
    extra_skill_spiky["skills"] = tuple(extra_skill_spiky["skills"]) + (
        {"name": "Unknown Energy Aura", "text": "Change combat somehow."},
    )
    extra_registry = registry_for(
        (982,),
        target_row=target_row,
        extra_rows=(extra_skill_spiky,),
    )
    obs = observation(
        (982,),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=300,
            energy_cards=((14, 151),),
        ),
    )
    _, _, extra_table = table_for(obs, extra_registry)
    extra = extra_table.get(982)
    assert extra_registry.digest != clean_registry.digest
    assert not extra.exact_damage
    assert any(
        "UNREGISTERED_ENERGY_SKILL_CARD_14" in reason
        for reason in extra.damage_unknown_reasons
    )

    wrong_type_spiky = deepcopy(clean_spiky)
    wrong_type_spiky["cardType"] = 2
    wrong_registry = registry_for(
        (982,),
        target_row=target_row,
        extra_rows=(wrong_type_spiky,),
    )
    _, _, wrong_table = table_for(obs, wrong_registry)
    wrong = wrong_table.get(982)
    assert not wrong.exact_damage
    assert any(
        "ENERGY_CARD_TYPE_MISMATCH_CARD_14" in reason
        for reason in wrong.damage_unknown_reasons
    )


def test_unknown_stadium_attack_and_nonadmitted_binding_fail_closed():
    registry = registry_for((982,))
    stadium_obs = observation((982,), stadium=(card(999, 301),))
    _, _, stadium_table = table_for(stadium_obs, registry)
    stadium = stadium_table.get(982)
    assert not stadium.exact_damage and stadium.final_damage is None
    assert any(
        "UNREGISTERED_STADIUM_CARD_999" in reason
        for reason in stadium.damage_unknown_reasons
    )

    unknown_attack_obs = observation((9999,))
    _, _, unknown_attack_table = table_for(unknown_attack_obs, registry)
    unknown_attack = unknown_attack_table.get(9999)
    assert not unknown_attack.exact_damage and unknown_attack.final_damage is None
    assert "UNREGISTERED_ATTACK_ID" in unknown_attack.damage_unknown_reasons

    nonadmitted_obs = observation((983,))
    _, _, nonadmitted_table = table_for(nonadmitted_obs, registry)
    nonadmitted = nonadmitted_table.get(983)
    assert not nonadmitted.exact_damage and nonadmitted.final_damage is None
    assert "ATTACK_BINDING_NOT_ADMITTED" in nonadmitted.damage_unknown_reasons


def test_legacy_energy_keeps_damage_exact_but_prize_and_terminal_unknown():
    target_row = pokemon_catalog_row(900, "Legacy Target", hp=100)
    legacy = effect_catalog_row("LEGACY_ENERGY")
    registry = registry_for((983,), target_row=target_row, extra_rows=(legacy,))
    obs = observation(
        (983,),
        opponent_active=pokemon(
            900,
            110,
            player=1,
            hp=100,
            energy_cards=((12, 151),),
        ),
        own_prizes=1,
    )
    _, _, table = table_for(obs, registry)
    row = table.get(983)

    assert row.exact_damage and row.knockout
    assert not row.prize_exact and row.prizes_taken is None
    assert row.prize_unknown_reasons == ("LEGACY_ENERGY_ONCE_PER_GAME_STATE_UNKNOWN",)
    assert not row.terminal_exact and not row.exact_game_win


def test_lillies_pearl_uses_card_id_allowlist_and_jamming_suppression():
    pearl = effect_catalog_row("LILLIES_PEARL")
    lillies_clefairy = pokemon_catalog_row(
        272,
        "Lillie\u2019s Clefairy ex",
        hp=210,
        energy_type=5,
        ex=True,
    )
    registry = registry_for(
        (983,),
        target_row=lillies_clefairy,
        extra_rows=(pearl,),
    )
    obs = observation(
        (983,),
        opponent_active=pokemon(
            272,
            110,
            player=1,
            hp=100,
            max_hp=210,
            tools=((1172, 190),),
        ),
    )
    _, _, table = table_for(obs, registry)
    row = table.get(983)
    assert row.prize_exact and row.prizes_taken == 1

    non_lillie = pokemon_catalog_row(900, "Lillie\u2019s Decoy", hp=100)
    non_lillie_registry = registry_for(
        (983,),
        target_row=non_lillie,
        extra_rows=(pearl,),
    )
    non_lillie_obs = observation(
        (983,),
        opponent_active=pokemon(
            900,
            111,
            player=1,
            hp=100,
            tools=((1172, 191),),
        ),
    )
    _, _, non_lillie_table = table_for(non_lillie_obs, non_lillie_registry)
    assert non_lillie_table.get(983).prizes_taken == 1

    jamming = effect_catalog_row("JAMMING_TOWER")
    jammed_registry = registry_for(
        (983,),
        target_row=lillies_clefairy,
        extra_rows=(pearl, jamming),
    )
    jammed_obs = observation(
        (983,),
        opponent_active=pokemon(
            272,
            112,
            player=1,
            hp=100,
            max_hp=210,
            tools=((1172, 192),),
        ),
        stadium=(card(1246, 301),),
    )
    _, _, jammed_table = table_for(jammed_obs, jammed_registry)
    assert jammed_table.get(983).prizes_taken == 2


@pytest.mark.parametrize(
    ("condition", "expected_legality_exact", "expected_legal", "expected_damage"),
    (
        ("confused", True, True, False),
        ("asleep", False, None, False),
        ("paralyzed", False, None, False),
    ),
)
def test_special_conditions_do_not_upgrade_probabilistic_or_contract_mismatch(
    condition, expected_legality_exact, expected_legal, expected_damage
):
    registry = registry_for((983,))
    obs = observation((983,), **{condition: True})
    _, _, table = table_for(obs, registry)
    row = table.get(983)

    assert row.legality_exact is expected_legality_exact
    assert row.legal is expected_legal
    assert row.exact_damage is expected_damage
    if condition == "confused":
        assert row.damage_unknown_reasons == ("CONFUSION_COIN_FLIP",)
    else:
        assert row.legality_unknown_reasons == (
            f"ATTACK_OPTION_PRESENT_WHILE_{condition.upper()}",
        )


def test_duplicate_attack_option_and_unregistered_skill_fail_closed():
    registry = registry_for((982,))
    duplicate_obs = observation((982, 982))
    _, _, duplicate_table = table_for(duplicate_obs, registry)
    duplicate = duplicate_table.get(982)
    assert duplicate_table.rows == (duplicate,)
    assert not duplicate.legality_exact
    assert duplicate.legality_unknown_reasons == ("DUPLICATE_SEMANTIC_ATTACK_OPTION",)

    unknown_target = pokemon_catalog_row(
        900,
        "Unknown Target",
        hp=300,
        skills=({"name": "Unknown Aura", "text": "Change combat somehow."},),
    )
    unknown_registry = registry_for((982,), target_row=unknown_target)
    obs = observation((982,))
    _, _, unknown_table = table_for(obs, unknown_registry)
    row = unknown_table.get(982)
    assert not row.exact_damage
    assert any(
        "UNREGISTERED_IN_PLAY_SKILL" in reason for reason in row.damage_unknown_reasons
    )
