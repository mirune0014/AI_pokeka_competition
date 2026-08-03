"""Runtime-hardening for snapshots, budgets, clocks and action certificates."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

import planner_model as model
import planner_model_corrected as corrected
import planner_model_final as final_model
import planner_option_keys as option_keys_v1


def stable_option_key(parent: Any, obs: Any, option: Any):
    explicit_owner = getattr(option, "playerIndex", None)
    if explicit_owner is not None and explicit_owner not in (0, 1):
        return None
    owner = explicit_owner if explicit_owner in (0, 1) else obs.current.yourIndex
    source = option_keys_v1._source_identity(parent, obs, option)
    area = getattr(option, "area", None)
    index = getattr(option, "index", None)
    source_expected = area in (
        parent.AreaType.DECK,
        parent.AreaType.LOOKING,
        parent.AreaType.HAND,
        parent.AreaType.DISCARD,
        parent.AreaType.ACTIVE,
        parent.AreaType.BENCH,
        parent.AreaType.PRIZE,
        parent.AreaType.STADIUM,
    )
    if source_expected and source is None:
        return None
    target = model._pokemon_for_area(
        parent,
        obs,
        getattr(option, "inPlayArea", None),
        getattr(option, "inPlayIndex", None),
        owner,
    )
    if getattr(option, "inPlayArea", None) in (parent.AreaType.ACTIVE, parent.AreaType.BENCH) and target is None:
        return None
    target_line = model.lineage_key(target, owner)
    target_serial = getattr(target, "serial", None) if target is not None else None
    attached_pokemon = model._pokemon_for_area(parent, obs, area, index, owner)
    attached_serial = None
    energy_index = getattr(option, "energyIndex", None)
    tool_index = getattr(option, "toolIndex", None)
    if energy_index is not None or tool_index is not None:
        if attached_pokemon is None:
            return None
        cards = (
            getattr(attached_pokemon, "energyCards", None) or []
            if energy_index is not None
            else getattr(attached_pokemon, "tools", None) or []
        )
        attached_index = energy_index if energy_index is not None else tool_index
        if not isinstance(attached_index, int) or isinstance(attached_index, bool) or not 0 <= attached_index < len(cards):
            return None
        attached_serial = getattr(cards[attached_index], "serial", None)
        if not isinstance(attached_serial, int) or isinstance(attached_serial, bool) or attached_serial <= 0:
            return None
    normalized = []
    for field in model.OPTION_FIELDS:
        value = model.enum_int(getattr(option, field, None))
        if field == "index" and (source is not None or attached_pokemon is not None):
            value = None
        elif field == "inPlayIndex" and target is not None:
            value = None
        elif field in ("energyIndex", "toolIndex") and attached_serial is not None:
            value = None
        normalized.append(value)
    return tuple(normalized) + (source, target_line, target_serial, attached_serial)


def _legal_ability_rows(parent: Any, obs: Any):
    rows = []
    if obs.select is None:
        return ()
    owner = obs.current.yourIndex
    for option in obs.select.option:
        if option.type != parent.OptionType.ABILITY:
            continue
        pokemon = model._pokemon_for_area(parent, obs, option.area, option.index, owner)
        if pokemon is None:
            return None
        line = model.lineage_key(pokemon, owner)
        if line is None:
            return None
        rows.append((line, pokemon.serial, pokemon.id))
    return tuple(sorted(rows))


def public_snapshot(parent: Any, obs: Any):
    if obs.select is None:
        return None
    keys = tuple(stable_option_key(parent, obs, option) for option in obs.select.option)
    if any(key is None for key in keys):
        return None
    snapshot = corrected.public_snapshot(parent, obs)
    abilities = _legal_ability_rows(parent, obs)
    if snapshot is None or abilities is None:
        return None
    payload = dict(snapshot.payload)
    payload["ability_ledger"] = {
        "legal_serials": abilities,
        "tracked_parent_flags": (
            ("dudunsparce", bool(getattr(parent, "ability_used_dudunsparce", False))),
            ("fezandipiti", bool(getattr(parent, "ability_used_fezandipiti", False))),
        ),
    }
    payload["select"] = dict(payload["select"])
    payload["select"]["options"] = tuple(sorted(keys, key=repr))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
    return model.PublicSnapshot(payload, canonical, digest)


def build_turn_budget(parent: Any, obs: Any, ability_flags: dict[str, bool]):
    if obs.select is None:
        return model.TurnBudget(False, False, False, False, False, 0, (), ())
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    is_main = obs.select.context == parent.SelectContext.MAIN and obs.current.result == -1
    legal = list(obs.select.option) if is_main else []
    legal_abilities = _legal_ability_rows(parent, obs) if is_main else ()
    if legal_abilities is None:
        legal_abilities = ()
    ability_lines = {row[0] for row in legal_abilities}
    tool_slots = []
    abilities = []
    for pokemon in list(mine.active) + list(mine.bench):
        line = model.lineage_key(pokemon, owner)
        if line is None:
            continue
        tool_slots.append((line, 0 if getattr(pokemon, "tools", None) else 1))
        abilities.append((line, line in ability_lines))

    def has(option_type: Any) -> bool:
        return any(option.type == option_type for option in legal)

    supporter = False
    stadium = False
    if is_main:
        for option in legal:
            if option.type != parent.OptionType.PLAY:
                continue
            source = model._option_card(parent, obs, option)
            data = parent.card_table.get(getattr(source, "id", None))
            if data is None:
                continue
            supporter = supporter or data.cardType == parent.CardType.SUPPORTER
            stadium = stadium or data.cardType == parent.CardType.STADIUM
    return model.TurnBudget(
        manual_attachment=is_main and not bool(obs.current.energyAttached) and has(parent.OptionType.ATTACH),
        supporter=is_main and not bool(obs.current.supporterPlayed) and supporter,
        stadium=is_main and not bool(obs.current.stadiumPlayed) and stadium,
        retreat=is_main and not bool(obs.current.retreated) and has(parent.OptionType.RETREAT),
        attack=is_main and has(parent.OptionType.ATTACK),
        bench_slots=max(0, mine.benchMax - len(mine.bench)),
        tool_slots=tuple(sorted(tool_slots)),
        abilities=tuple(sorted(abilities)),
    )


_DRAW_EVENTS = {
    "current_optional_draw_or_search",
    "opponent_turn_helmet_or_fan",
    "next_mandatory_draw",
    "H1_or_recovery",
    "next_opponent_turn",
    "H2_mandatory_draw",
    "Hilda search",
    "Enriching mandatory four",
}


def deck_clock_after(self: Any, name: str, count: int, optional: bool = False):
    if (
        name not in _DRAW_EVENTS
        or not isinstance(self.deck_count, int)
        or isinstance(self.deck_count, bool)
        or self.deck_count < 0
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count < 0
    ):
        return None
    if not optional and count > self.deck_count:
        return None
    resolved = min(count, self.deck_count) if optional else count
    return replace(
        self,
        deck_count=self.deck_count - resolved,
        ordered_draws=self.ordered_draws + ((name, resolved, optional),),
    )


def action_is_certified(
    parent: Any,
    obs: Any,
    action: Any,
    *,
    expected_context: Any = None,
    allowed_keys: tuple[Any, ...] | None = None,
) -> bool:
    if obs is None or obs.select is None or not model.action_is_valid(obs, action):
        return False
    if expected_context is not None and obs.select.context != expected_context:
        return False
    keys = tuple(stable_option_key(parent, obs, obs.select.option[index]) for index in action)
    if any(key is None for key in keys):
        return False
    if allowed_keys is not None and keys != tuple(allowed_keys):
        return False
    # Exact remaining-cost prompts must satisfy their advertised total rather
    # than cardinality alone.  Fan prompts use count=1 and are covered here.
    remaining_energy = getattr(obs.select, "remainEnergyCost", None)
    remaining_damage = getattr(obs.select, "remainDamageCounter", None)
    if isinstance(remaining_energy, int) and remaining_energy > 0:
        total = sum(max(0, int(getattr(obs.select.option[index], "count", 1) or 1)) for index in action)
        if total != remaining_energy:
            return False
    if isinstance(remaining_damage, int) and remaining_damage > 0:
        total = sum(max(0, int(getattr(obs.select.option[index], "number", 0) or 0)) for index in action)
        if total != remaining_damage:
            return False
    return True


def raw_parsed_agree(raw: dict, obs: Any) -> bool:
    """Compare planner-critical raw fields before using parsed dataclasses."""
    try:
        current = raw["current"]
        select = raw["select"]
        if (
            current["turn"] != obs.current.turn
            or current["yourIndex"] != obs.current.yourIndex
            or current["turnActionCount"] != obs.current.turnActionCount
            or current["result"] != obs.current.result
            or select["context"] != int(obs.select.context)
            or select["minCount"] != obs.select.minCount
            or select["maxCount"] != obs.select.maxCount
            or len(select["option"]) != len(obs.select.option)
        ):
            return False
        for owner, (raw_player, player) in enumerate(zip(current["players"], obs.current.players)):
            if (
                raw_player["handCount"] != player.handCount
                or raw_player["deckCount"] != player.deckCount
                or len(raw_player["prize"]) != len(player.prize)
                or len(raw_player["active"]) != len(player.active)
                or len(raw_player["bench"]) != len(player.bench)
            ):
                return False
            for raw_zone, parsed_zone in ((raw_player["active"], player.active), (raw_player["bench"], player.bench)):
                for raw_pokemon, pokemon in zip(raw_zone, parsed_zone):
                    if (
                        raw_pokemon["id"] != pokemon.id
                        or raw_pokemon["serial"] != pokemon.serial
                        or raw_pokemon["hp"] != pokemon.hp
                        or raw_pokemon["maxHp"] != pokemon.maxHp
                        or bool(raw_pokemon["appearThisTurn"]) != bool(pokemon.appearThisTurn)
                        or raw_pokemon["energies"] != list(pokemon.energies)
                        or [row["serial"] for row in raw_pokemon["energyCards"]] != [row.serial for row in pokemon.energyCards]
                        or [row["serial"] for row in raw_pokemon["tools"]] != [row.serial for row in pokemon.tools]
                    ):
                        return False
        raw_option_rows = tuple(
            tuple(row.get(field) for field in model.OPTION_FIELDS)
            for row in select["option"]
        )
        parsed_option_rows = tuple(
            tuple(model.enum_int(getattr(row, field, None)) for field in model.OPTION_FIELDS)
            for row in obs.select.option
        )
        normalized_raw = tuple(
            tuple(model.enum_int(value) for value in row)
            for row in raw_option_rows
        )
        return normalized_raw == parsed_option_rows
    except (KeyError, TypeError, AttributeError, IndexError):
        return False


def install() -> None:
    final_model.install()
    model.stable_option_key = stable_option_key
    model.public_snapshot = public_snapshot
    model.build_turn_budget = build_turn_budget
    model.DeckClock.after = deck_clock_after

