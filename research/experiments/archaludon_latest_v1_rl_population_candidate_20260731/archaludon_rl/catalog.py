"""Build conservative immutable facts from the caller-preloaded checked API."""

from __future__ import annotations

from typing import Any

from .effect_features import AttackFact, CardFact, EffectCatalog


def catalog_from_cg(api_module: Any | None = None) -> EffectCatalog:
    """Convert public static card data without interpreting free-form effects.

    Nonempty attack text and card skills are marked unknown for damage
    semantics until an explicit visible contract is implemented.
    """

    if api_module is None:
        from cg import api as api_module

    cards: dict[int, CardFact] = {}
    attacks: dict[int, AttackFact] = {}
    card_attack_sources: dict[int, int] = {}
    for card in api_module.all_card_data():
        card_id = int(card.cardId)
        for attack_id in card.attacks or ():
            card_attack_sources[int(attack_id)] = card_id
        if bool(card.megaEx):
            prizes = 3
        elif bool(card.ex):
            prizes = 2
        elif int(card.hp or 0) > 0:
            prizes = 1
        else:
            prizes = None
        stage = (
            "basic"
            if bool(card.basic)
            else (
                "stage1"
                if bool(card.stage1)
                else ("stage2" if bool(card.stage2) else "nonpokemon")
            )
        )
        skills = tuple(card.skills or ())
        cards[card_id] = CardFact(
            card_id=card_id,
            card_type=str(int(card.cardType)),
            energy_type=(
                None if card.energyType is None else int(card.energyType)
            ),
            weakness=None if card.weakness is None else int(card.weakness),
            resistance=(
                None if card.resistance is None else int(card.resistance)
            ),
            attacker_class=stage,
            prize_value=prizes,
            ability_tags=(),
            board_bench_delta=(
                1
                if bool(card.basic) and int(card.cardType) == 0
                else None
            ),
            damage_modifiers_known=not bool(skills),
        )
    for attack in api_module.all_attack():
        text = str(attack.text or "").strip()
        known_plain_attack = not text
        attacks[int(attack.attackId)] = AttackFact(
            attack_id=int(attack.attackId),
            source_card_id=card_attack_sources.get(int(attack.attackId)),
            printed_damage=int(attack.damage),
            energy_cost=tuple(int(energy) for energy in (attack.energies or ())),
            damage_kind="damage" if known_plain_attack else "unknown",
            bench_damage=0 if known_plain_attack else None,
            deterministic_energy_delta=0 if known_plain_attack else None,
        )
    return EffectCatalog(cards=cards, attacks=attacks)
