"""Deterministic, action-conditioned semantic effect features.

The extractor never invokes the engine.  It consumes only the sanitized public
projection plus immutable card/attack facts and explicit visible-effect
contracts supplied by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .semantic_action import SemanticOption


EFFECT_SCHEMA_VERSION = "effect-features-v3"


class FeatureStatus(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class FeatureValue:
    status: FeatureStatus
    value: float | int | bool | None = None

    @classmethod
    def known(cls, value: float | int | bool) -> "FeatureValue":
        return cls(FeatureStatus.KNOWN, value)

    @classmethod
    def unknown(cls) -> "FeatureValue":
        return cls(FeatureStatus.UNKNOWN, None)

    @classmethod
    def not_applicable(cls) -> "FeatureValue":
        return cls(FeatureStatus.NOT_APPLICABLE, None)


@dataclass(frozen=True)
class CardFact:
    card_id: int
    card_type: str = "unknown"
    energy_type: int | None = None
    weakness: int | None = None
    resistance: int | None = None
    attacker_class: str = "unknown"
    prize_value: int | None = None
    ability_tags: tuple[str, ...] = ()
    resource_delta: int | None = None
    board_active_delta: int | None = None
    board_bench_delta: int | None = None
    # False means a visible card has unmodeled text that may change damage.
    # The extractor must then report UNKNOWN rather than silently assuming zero.
    damage_modifiers_known: bool = True


@dataclass(frozen=True)
class AttackFact:
    attack_id: int
    printed_damage: int | None
    source_card_id: int | None = None
    energy_cost: tuple[int, ...] = ()
    damage_kind: str = "damage"  # damage | counters | unknown
    counter_amount: int | None = None
    bench_damage: int | None = None
    deterministic_energy_delta: int | None = None


@dataclass(frozen=True)
class VisibleEffectContracts:
    # Stadium card -> deterministic attack-damage reduction.
    stadium_damage_reduction: Mapping[int, int] = field(default_factory=dict)
    # Public target ability tag -> deterministic attack-damage reduction.
    ability_damage_reduction: Mapping[str, int] = field(default_factory=dict)
    # Public target ability tag -> attacker classes whose attack damage is zero.
    ability_prevents_attacker_classes: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    # Statuses that deterministically prevent attacking.
    status_attack_locks: tuple[str, ...] = ("asleep", "paralyzed")
    # Statuses that make usability stochastic rather than deterministic.
    status_attack_unknown: tuple[str, ...] = ("confused",)


@dataclass(frozen=True)
class EffectCatalog:
    cards: Mapping[int, CardFact] = field(default_factory=dict)
    attacks: Mapping[int, AttackFact] = field(default_factory=dict)
    contracts: VisibleEffectContracts = field(default_factory=VisibleEffectContracts)


EFFECT_FIELD_NAMES = (
    "printed_damage",
    "effective_damage",
    "places_damage_counters",
    "damage_counter_amount",
    "prevented_attack_damage",
    "damage_reduction",
    "weakness_multiplier",
    "resistance_delta",
    "expected_ko",
    "prizes_on_ko",
    "bench_damage",
    "attack_usable",
    "public_attack_lock",
    "deterministic_energy_delta",
    "deterministic_resource_delta",
    "board_active_delta",
    "board_bench_delta",
    "current_attacker_ready",
    "next_attacker_ready",
    "target_hp_ratio",
    "target_energy_count",
    "target_tool_count",
    "target_is_active",
    "target_appeared_this_turn",
    "target_ready_before",
    "target_ready_after",
)


@dataclass(frozen=True)
class EffectFeatureSet:
    option_identity: str
    fields: Mapping[str, FeatureValue]
    schema_version: str = EFFECT_SCHEMA_VERSION

    @property
    def unknown_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name in EFFECT_FIELD_NAMES
            if self.fields[name].status is FeatureStatus.UNKNOWN
        )

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "option_identity": self.option_identity,
            "fields": {
                name: {
                    "status": self.fields[name].status.value,
                    "value": self.fields[name].value,
                }
                for name in EFFECT_FIELD_NAMES
            },
        }


def _field_dict(default: FeatureValue | None = None) -> dict[str, FeatureValue]:
    value = default or FeatureValue.not_applicable()
    return {name: value for name in EFFECT_FIELD_NAMES}


def _field(option: SemanticOption, name: str) -> int | None:
    return dict(option.fields).get(name)


def _active(projection: Mapping[str, Any], relative_player: int) -> Mapping[str, Any] | None:
    players = projection.get("players") or ()
    if len(players) != 2:
        return None
    active = players[relative_player].get("active") or ()
    return active[0] if active and active[0] is not None else None


def _energy_ready(
    pokemon: Mapping[str, Any] | None, attacks: list[AttackFact]
) -> FeatureValue:
    if pokemon is None:
        return FeatureValue.known(False)
    if not attacks:
        return FeatureValue.unknown()
    energies = [int(value) for value in (pokemon.get("energies") or ())]

    def payable(cost: tuple[int, ...]) -> bool:
        available = list(energies)
        colorless = sum(1 for value in cost if value == 0)
        for required in (value for value in cost if value != 0):
            if required in available:
                available.remove(required)
            elif 10 in available:  # Rainbow Energy unit.
                available.remove(10)
            else:
                return False
        return len(available) >= colorless

    return FeatureValue.known(any(payable(attack.energy_cost) for attack in attacks))


def _attacks_for(card_id: int | None, catalog: EffectCatalog) -> list[AttackFact]:
    return [
        fact
        for fact in catalog.attacks.values()
        if card_id is not None and fact.source_card_id == card_id
    ]


def _option_target(
    projection: Mapping[str, Any], option: SemanticOption
) -> tuple[Mapping[str, Any] | None, int | None]:
    fields = dict(option.fields)
    area = fields.get("inPlayArea")
    index = fields.get("inPlayIndex")
    players = projection.get("players") or ()
    if len(players) != 2 or not isinstance(index, int) or index < 0:
        return None, area
    own = players[0]
    if area == 4:
        values = own.get("active") or ()
    elif area == 5:
        values = own.get("bench") or ()
    else:
        return None, area
    if index >= len(values):
        return None, area
    return values[index], area


def _readiness(
    projection: Mapping[str, Any], catalog: EffectCatalog
) -> tuple[FeatureValue, FeatureValue]:
    players = projection.get("players") or ()
    if len(players) != 2:
        return FeatureValue.unknown(), FeatureValue.unknown()
    own = players[0]
    active = _active(projection, 0)
    active_attacks = _attacks_for(
        None if active is None else active.get("id"), catalog
    )
    current = _energy_ready(active, active_attacks)
    bench_ready: list[bool] = []
    unknown = False
    for pokemon in own.get("bench") or ():
        attacks = _attacks_for(pokemon.get("id"), catalog)
        ready = _energy_ready(pokemon, attacks)
        if ready.status is FeatureStatus.UNKNOWN:
            unknown = True
        elif bool(ready.value):
            bench_ready.append(True)
    if bench_ready:
        next_ready = FeatureValue.known(True)
    elif unknown or (own.get("bench") and not catalog.attacks):
        next_ready = FeatureValue.unknown()
    else:
        next_ready = FeatureValue.known(False)
    return current, next_ready


def extract_effect_features(
    projection: Mapping[str, Any],
    option: SemanticOption,
    catalog: EffectCatalog,
) -> EffectFeatureSet:
    fields = _field_dict()
    current_ready, next_ready = _readiness(projection, catalog)
    fields["current_attacker_ready"] = current_ready
    fields["next_attacker_ready"] = next_ready
    target_candidate, target_area = _option_target(projection, option)
    if target_candidate is None:
        for name in (
            "target_hp_ratio",
            "target_energy_count",
            "target_tool_count",
            "target_is_active",
            "target_appeared_this_turn",
            "target_ready_before",
            "target_ready_after",
        ):
            fields[name] = FeatureValue.not_applicable()
    else:
        maximum_hp = int(target_candidate.get("max_hp") or 0)
        fields["target_hp_ratio"] = (
            FeatureValue.known(
                float(target_candidate.get("hp") or 0) / maximum_hp
            )
            if maximum_hp > 0
            else FeatureValue.unknown()
        )
        fields["target_energy_count"] = FeatureValue.known(
            len(target_candidate.get("energies") or ())
        )
        fields["target_tool_count"] = FeatureValue.known(
            len(target_candidate.get("tools") or ())
        )
        fields["target_is_active"] = FeatureValue.known(target_area == 4)
        fields["target_appeared_this_turn"] = FeatureValue.known(
            bool(target_candidate.get("appeared_this_turn"))
        )
        before_ready = _energy_ready(
            target_candidate,
            _attacks_for(target_candidate.get("id"), catalog),
        )
        after_ready = before_ready
        if option.option_type == 8:  # ATTACH
            source_fact = (
                catalog.cards.get(option.source_card_id)
                if option.source_card_id is not None
                else None
            )
            if source_fact is None or source_fact.energy_type is None:
                after_ready = FeatureValue.unknown()
            else:
                after_target = dict(target_candidate)
                after_target["energies"] = [
                    *(target_candidate.get("energies") or ()),
                    source_fact.energy_type,
                ]
                after_ready = _energy_ready(
                    after_target,
                    _attacks_for(target_candidate.get("id"), catalog),
                )
        elif option.option_type == 9:  # EVOLVE
            after_ready = _energy_ready(
                target_candidate,
                _attacks_for(option.source_card_id, catalog),
            )
        fields["target_ready_before"] = before_ready
        fields["target_ready_after"] = after_ready
        if target_area == 4:
            fields["current_attacker_ready"] = after_ready
        elif target_area == 5:
            if after_ready.status is FeatureStatus.KNOWN and bool(after_ready.value):
                fields["next_attacker_ready"] = FeatureValue.known(True)
            elif next_ready.status is FeatureStatus.UNKNOWN:
                fields["next_attacker_ready"] = FeatureValue.unknown()

    card_fact = (
        None
        if option.source_card_id is None
        else catalog.cards.get(option.source_card_id)
    )
    # Card-level board deltas describe playing that card, not every option
    # whose source happens to be the card.  In particular, a Basic Pokémon's
    # "+1 bench" fact must never leak onto its ATTACK option.
    if (
        option.option_type == 7
        and option.source_card_id is not None
        and card_fact is None
    ):
        for name in (
            "deterministic_resource_delta",
            "board_active_delta",
            "board_bench_delta",
        ):
            fields[name] = FeatureValue.unknown()
    elif option.option_type == 7 and card_fact is not None:
        fields["deterministic_resource_delta"] = (
            FeatureValue.known(card_fact.resource_delta)
            if card_fact.resource_delta is not None
            else FeatureValue.unknown()
        )
        fields["board_active_delta"] = (
            FeatureValue.known(card_fact.board_active_delta)
            if card_fact.board_active_delta is not None
            else FeatureValue.unknown()
        )
        fields["board_bench_delta"] = (
            FeatureValue.known(card_fact.board_bench_delta)
            if card_fact.board_bench_delta is not None
            else FeatureValue.unknown()
        )
    elif option.option_type == 14:
        fields["deterministic_resource_delta"] = FeatureValue.known(0)
        fields["board_active_delta"] = FeatureValue.known(0)
        fields["board_bench_delta"] = FeatureValue.known(0)
    else:
        fields["deterministic_resource_delta"] = FeatureValue.unknown()
        fields["board_active_delta"] = FeatureValue.unknown()
        fields["board_bench_delta"] = FeatureValue.unknown()

    if option.option_type == 8:  # ATTACH
        fields["deterministic_energy_delta"] = FeatureValue.known(1)
    elif option.option_type in (11,):  # DISCARD
        fields["deterministic_energy_delta"] = FeatureValue.unknown()
    else:
        fields["deterministic_energy_delta"] = FeatureValue.known(0)

    if option.option_type != 13:
        return EffectFeatureSet(option.identity, fields)

    attack_id = _field(option, "attackId")
    attack = catalog.attacks.get(attack_id) if attack_id is not None else None
    attacker = _active(projection, 0)
    target = _active(projection, 1)
    attacker_fact = (
        catalog.cards.get(attacker.get("id")) if attacker is not None else None
    )
    target_fact = catalog.cards.get(target.get("id")) if target is not None else None
    own_status = (
        ((projection.get("players") or ({},))[0].get("status") or {})
        if projection.get("players")
        else {}
    )
    locked = any(
        own_status.get(status, False)
        for status in catalog.contracts.status_attack_locks
    )
    stochastic_lock = any(
        own_status.get(status, False)
        for status in catalog.contracts.status_attack_unknown
    )
    fields["public_attack_lock"] = FeatureValue.known(locked)
    if locked:
        fields["attack_usable"] = FeatureValue.known(False)
    elif stochastic_lock:
        fields["attack_usable"] = FeatureValue.unknown()
    elif attack is None:
        fields["attack_usable"] = FeatureValue.unknown()
    else:
        energy_count = len((attacker or {}).get("energies") or ())
        fields["attack_usable"] = FeatureValue.known(
            energy_count >= len(attack.energy_cost)
        )

    if attack is None:
        for name in (
            "printed_damage",
            "effective_damage",
            "places_damage_counters",
            "damage_counter_amount",
            "prevented_attack_damage",
            "damage_reduction",
            "weakness_multiplier",
            "resistance_delta",
            "expected_ko",
            "prizes_on_ko",
            "bench_damage",
            "deterministic_energy_delta",
        ):
            fields[name] = FeatureValue.unknown()
        return EffectFeatureSet(option.identity, fields)

    fields["deterministic_energy_delta"] = (
        FeatureValue.known(attack.deterministic_energy_delta)
        if attack.deterministic_energy_delta is not None
        else FeatureValue.unknown()
    )
    fields["bench_damage"] = (
        FeatureValue.known(attack.bench_damage)
        if attack.bench_damage is not None
        else FeatureValue.unknown()
    )
    if attack.damage_kind == "counters":
        fields["printed_damage"] = FeatureValue.not_applicable()
        fields["effective_damage"] = FeatureValue.not_applicable()
        fields["places_damage_counters"] = FeatureValue.known(True)
        fields["damage_counter_amount"] = (
            FeatureValue.known(attack.counter_amount)
            if attack.counter_amount is not None
            else FeatureValue.unknown()
        )
        fields["prevented_attack_damage"] = FeatureValue.not_applicable()
        fields["damage_reduction"] = FeatureValue.not_applicable()
        fields["weakness_multiplier"] = FeatureValue.not_applicable()
        fields["resistance_delta"] = FeatureValue.not_applicable()
        if target is not None and attack.counter_amount is not None:
            counter_damage = 10 * attack.counter_amount
            fields["expected_ko"] = FeatureValue.known(
                counter_damage >= int(target.get("hp") or 0)
            )
        else:
            fields["expected_ko"] = FeatureValue.unknown()
    elif attack.damage_kind != "damage" or attack.printed_damage is None:
        for name in (
            "printed_damage",
            "effective_damage",
            "places_damage_counters",
            "damage_counter_amount",
            "prevented_attack_damage",
            "damage_reduction",
            "weakness_multiplier",
            "resistance_delta",
            "expected_ko",
        ):
            fields[name] = FeatureValue.unknown()
    else:
        fields["printed_damage"] = FeatureValue.known(attack.printed_damage)
        fields["places_damage_counters"] = FeatureValue.known(False)
        fields["damage_counter_amount"] = FeatureValue.not_applicable()
        stadium_ids = [
            int(card["id"])
            for card in projection.get("stadium") or ()
            if card.get("id") is not None
        ]
        unknown_modifier = (
            attacker_fact is None
            or target_fact is None
            or not attacker_fact.damage_modifiers_known
            or not target_fact.damage_modifiers_known
            or any(
                (
                    stadium_fact := catalog.cards.get(card_id)
                ) is not None
                and not stadium_fact.damage_modifiers_known
                and card_id
                not in catalog.contracts.stadium_damage_reduction
                for card_id in stadium_ids
            )
        )
        reduction = sum(
            int(catalog.contracts.stadium_damage_reduction.get(card_id, 0))
            for card_id in stadium_ids
        )
        ability_tags = target_fact.ability_tags if target_fact else ()
        reduction += sum(
            int(catalog.contracts.ability_damage_reduction.get(tag, 0))
            for tag in ability_tags
        )
        attacker_class = (
            attacker_fact.attacker_class if attacker_fact else "unknown"
        )
        prevented = any(
            attacker_class
            in catalog.contracts.ability_prevents_attacker_classes.get(tag, ())
            for tag in ability_tags
        )
        fields["damage_reduction"] = (
            FeatureValue.unknown()
            if unknown_modifier
            else FeatureValue.known(reduction)
        )
        fields["prevented_attack_damage"] = (
            FeatureValue.unknown()
            if unknown_modifier
            else FeatureValue.known(prevented)
        )
        if attacker_fact is None or target_fact is None:
            weakness = 1
            resistance = 0
            fields["weakness_multiplier"] = FeatureValue.unknown()
            fields["resistance_delta"] = FeatureValue.unknown()
        else:
            weakness = (
                2
                if target_fact.weakness is not None
                and target_fact.weakness == attacker_fact.energy_type
                else 1
            )
            resistance = (
                -30
                if target_fact.resistance is not None
                and target_fact.resistance == attacker_fact.energy_type
                else 0
            )
            fields["weakness_multiplier"] = FeatureValue.known(weakness)
            fields["resistance_delta"] = FeatureValue.known(resistance)
        if unknown_modifier:
            fields["effective_damage"] = FeatureValue.unknown()
            fields["expected_ko"] = FeatureValue.unknown()
        else:
            effective = 0 if prevented else max(
                0, attack.printed_damage * weakness + resistance - reduction
            )
            fields["effective_damage"] = FeatureValue.known(effective)
            fields["expected_ko"] = (
                FeatureValue.known(effective >= int(target.get("hp") or 0))
                if target is not None
                else FeatureValue.unknown()
            )
    fields["prizes_on_ko"] = (
        FeatureValue.known(target_fact.prize_value)
        if target_fact is not None and target_fact.prize_value is not None
        else FeatureValue.unknown()
    )
    return EffectFeatureSet(option.identity, fields)
