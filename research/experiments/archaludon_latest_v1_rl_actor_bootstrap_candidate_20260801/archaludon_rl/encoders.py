"""Stable fixed-size public-state and semantic-action encoders."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .effect_features import (
    EFFECT_SCHEMA_VERSION,
    EFFECT_FIELD_NAMES,
    EffectFeatureSet,
    FeatureStatus,
)
from .semantic_action import SemanticOption


ENCODER_SCHEMA_VERSION = "encoder-v4"
STATE_SCALAR_DIM = 40
STATE_CARD_HASH_BUCKETS = 8
STATE_CARD_ZONE_COUNT = 8
STATE_DIM = STATE_SCALAR_DIM + STATE_CARD_HASH_BUCKETS * STATE_CARD_ZONE_COUNT
ACTION_SEMANTIC_FINGERPRINT_DIM = 16
ACTION_DIM = 86 + ACTION_SEMANTIC_FINGERPRINT_DIM
CARD_HASH_BUCKETS = 8


def _number(value: Any, scale: float = 1.0) -> float:
    if value is None:
        return 0.0
    return float(value) / scale


def _status_count(status: Mapping[str, Any]) -> float:
    return float(sum(bool(value) for value in status.values()))


def _card_ids(cards: Any) -> list[int]:
    result: list[int] = []
    for card in cards or ():
        if not isinstance(card, Mapping):
            continue
        card_id = card.get("id")
        if isinstance(card_id, int) and not isinstance(card_id, bool):
            result.append(card_id)
    return result


def _pokemon_ids(pokemon: Any) -> list[int]:
    if not isinstance(pokemon, Mapping):
        return []
    result = _card_ids((pokemon,))
    for field in ("energy_cards", "tools", "pre_evolution"):
        result.extend(_card_ids(pokemon.get(field)))
    return result


def _board_ids(pokemon: Any) -> list[int]:
    result: list[int] = []
    for card in pokemon or ():
        result.extend(_pokemon_ids(card))
    return result


def _state_zone_hash(card_ids: list[int]) -> list[float]:
    buckets = [0.0] * STATE_CARD_HASH_BUCKETS
    for card_id in card_ids:
        digest = hashlib.sha256(f"state-card:{card_id}".encode()).digest()
        bucket = int.from_bytes(digest[:2], "big") % STATE_CARD_HASH_BUCKETS
        sign = 1.0 if digest[2] & 1 else -1.0
        buckets[bucket] += sign
    return [max(-2.0, min(2.0, value / 4.0)) for value in buckets]


def encode_state(projection: Mapping[str, Any]) -> list[float]:
    players = projection.get("players") or ({}, {})
    own = players[0] if len(players) > 0 else {}
    opp = players[1] if len(players) > 1 else {}
    own_active = (own.get("active") or [None])[0]
    opp_active = (opp.get("active") or [None])[0]
    own_active = own_active or {}
    opp_active = opp_active or {}
    select = projection.get("select") or {}
    values = [
        _number(projection.get("turn"), 50),
        _number(projection.get("turn_action_count"), 20),
        float(bool(projection.get("supporter_played"))),
        float(bool(projection.get("stadium_played"))),
        float(bool(projection.get("energy_attached"))),
        float(bool(projection.get("retreated"))),
        _number(own.get("deck_count"), 60),
        _number(opp.get("deck_count"), 60),
        _number(own.get("hand_count"), 20),
        _number(opp.get("hand_count"), 20),
        _number(own.get("prize_count"), 6),
        _number(opp.get("prize_count"), 6),
        _number(len(own.get("discard") or ()), 60),
        _number(len(opp.get("discard") or ()), 60),
        _number(len(own.get("bench") or ()), 5),
        _number(len(opp.get("bench") or ()), 5),
        _number(own_active.get("hp"), max(1, own_active.get("max_hp") or 1)),
        _number(opp_active.get("hp"), max(1, opp_active.get("max_hp") or 1)),
        _number(len(own_active.get("energies") or ()), 8),
        _number(len(opp_active.get("energies") or ()), 8),
        _number(len(own_active.get("tools") or ()), 3),
        _number(len(opp_active.get("tools") or ()), 3),
        _status_count(own.get("status") or {}) / 5.0,
        _status_count(opp.get("status") or {}) / 5.0,
        _number(select.get("type"), 16),
        _number(select.get("context"), 64),
        _number(select.get("min_count"), 6),
        _number(select.get("max_count"), 6),
        _number(select.get("option_count"), 64),
        _number(select.get("remain_damage_counter"), 30),
        _number(select.get("remain_energy_cost"), 10),
        _number(len(projection.get("stadium") or ()), 1),
        _number(len(projection.get("logs") or ()), 50),
        _number(len(projection.get("looking_visible") or ()), 60),
        float(projection.get("first_player_relative") == 0),
        float(projection.get("first_player_relative") == 1),
        float(projection.get("result_relative") == 0),
        float(projection.get("result_relative") == 1),
        float(bool(own_active)),
        float(bool(opp_active)),
    ]
    if len(values) != STATE_SCALAR_DIM:
        raise AssertionError(f"state scalar dimension drift: {len(values)}")
    zones = (
        _card_ids(own.get("hand")),
        _board_ids(own.get("active")),
        _board_ids(own.get("bench")),
        _card_ids(own.get("discard")),
        _board_ids(opp.get("active")),
        _board_ids(opp.get("bench")),
        _card_ids(opp.get("discard")),
        _card_ids(projection.get("stadium")),
    )
    for zone in zones:
        values.extend(_state_zone_hash(zone))
    if len(values) != STATE_DIM:
        raise AssertionError(f"state encoder dimension drift: {len(values)}")
    return values


def _card_hash(card_id: int | None) -> list[float]:
    buckets = [0.0] * CARD_HASH_BUCKETS
    if card_id is None:
        return buckets
    digest = hashlib.sha256(f"card:{card_id}".encode()).digest()
    bucket = int.from_bytes(digest[:2], "big") % CARD_HASH_BUCKETS
    buckets[bucket] = 1.0 if digest[2] & 1 else -1.0
    return buckets


def _feature_pair(feature: Any) -> tuple[float, float]:
    status_value = {
        FeatureStatus.NOT_APPLICABLE: -1.0,
        FeatureStatus.UNKNOWN: 0.0,
        FeatureStatus.KNOWN: 1.0,
    }[feature.status]
    if feature.status is not FeatureStatus.KNOWN:
        return status_value, 0.0
    value = feature.value
    if isinstance(value, bool):
        return status_value, float(value)
    return status_value, max(-10.0, min(10.0, float(value) / 100.0))


def _semantic_fingerprint(identity: str) -> list[float]:
    digest = bytes.fromhex(identity)
    return [
        (float(value) - 127.5) / 127.5
        for value in digest[:ACTION_SEMANTIC_FINGERPRINT_DIM]
    ]


def encode_action(
    option: SemanticOption, effects: EffectFeatureSet
) -> list[float]:
    # Card hashes are a deliberately small adjunct; named effect values occupy
    # most of the vector and cannot be replaced by IDs.
    option_type = [0.0] * 16
    if 0 <= option.option_type < len(option_type):
        option_type[option.option_type] = 1.0
    values = option_type
    values += _card_hash(option.source_card_id)
    values += _card_hash(option.target_card_id)
    values += _semantic_fingerprint(option.identity)
    for name in EFFECT_FIELD_NAMES:
        values.extend(_feature_pair(effects.fields[name]))
    # Two structural fields complete the fixed schema.
    values.extend(
        [
            float(option.source_card_id is not None),
            float(option.target_card_id is not None),
        ]
    )
    if len(values) != ACTION_DIM:
        raise AssertionError(f"action encoder dimension drift: {len(values)}")
    return values


def encoder_metadata() -> dict[str, Any]:
    return {
        "schema_version": ENCODER_SCHEMA_VERSION,
        "state_dim": STATE_DIM,
        "action_dim": ACTION_DIM,
        "effect_schema_version": EFFECT_SCHEMA_VERSION,
        "state_scalar_dim": STATE_SCALAR_DIM,
        "state_card_hash_buckets": STATE_CARD_HASH_BUCKETS,
        "state_card_zone_count": STATE_CARD_ZONE_COUNT,
        "card_hash_buckets": CARD_HASH_BUCKETS,
        "action_semantic_fingerprint_dim": ACTION_SEMANTIC_FINGERPRINT_DIM,
        "serials_encoded": False,
        "indices_encoded": False,
    }
