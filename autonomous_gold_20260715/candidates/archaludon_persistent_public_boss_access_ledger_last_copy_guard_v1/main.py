"""Archaludon ex + Cinderace — Rule-based agent (Public version)

Deck Concept:
  Cinderace's Explosiveness places it face-down as Active during setup.
  Turn 1 Turbo Flare ({C}=50) accelerates up to 3 Basic Energy from deck
  to benched Duraludon. Evolving into Archaludon ex triggers Assemble Alloy,
  attaching up to 2 Basic Metal Energy from discard to Metal Pokemon.
  Metal Defender ({M}{M}{M}=220) is the main attack; no Weakness next turn.
  Non-ex Archaludon is included as an Ogerpon answer: Coated Attack does 120
  and prevents attack damage from Basic Pokemon on the next opponent turn.
  Duraludon can attack directly with Raging Hammer ({M}{M}{C}=80 + 10 per
  damage counter) without evolving. This variant cuts Relicanth to restore a
  third Full Metal Lab while keeping Boss's Orders x4. Hero's Cape gives +100
  HP (HP400). Full Metal Lab reduces attack damage to Metal Pokemon by 30.

Pokemon:
  Duraludon (169)      - Basic Metal HP130. Hammer In {M}=30.
                         Raging Hammer {M}{M}{C}=80+10*damage_counters.
  Archaludon ex (190)  - Stage 1 from Duraludon, HP300. Assemble Alloy: on evolve
                         from hand, attach up to 2 Metal Energy from discard.
                         Metal Defender {M}{M}{M}=220, no Weakness next turn.
  Archaludon (840)     - Stage 1 from Duraludon, HP180. Coated Attack
                         {M}{M}{M}=120, prevents Basic Pokemon attack damage.
  Cinderace (666)      - Stage 2 HP160. Explosiveness: place face-down as Active
                         in setup from opening hand. Turbo Flare {C}=50, attach
                         up to 3 Basic Energy from deck to benched Pokemon.

Trainers:
  Poke Pad (1152), Ultra Ball (1121), Pokegear 3.0 (1122), Night Stretcher (1097),
  Jumbo Ice Cream (1147), Hero's Cape (1159), Boss's Orders (1182),
  Explorer's Guidance (1185), Lillie's Determination (1227), Full Metal Lab (1244) x3.

Energy: Basic Metal Energy (8) x11

Score system:
  Setup/play/evolve/attach: 1000~28000 (high = do first)
  Attack: damage value (always last — attacking ends the turn)
  Negative = skip if above minCount
"""

import os
import random
import sys
from collections import Counter

try:
    ROOT = __file__
except NameError:
    ROOT = None
CG_PATH = "/kaggle_simulations/agent"
for p in ([os.path.dirname(os.path.abspath(ROOT))] if ROOT else []) + [CG_PATH]:
    if p and p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

from cg.api import (
    AreaType,
    LogType,
    OptionType,
    SelectContext,
    all_card_data,
    to_observation_class,
)

try:
    from cg.api import all_attack
    ALL_ATTACKS = {a.attackId: a for a in all_attack()}
except Exception:
    ALL_ATTACKS = {}

# ── Card IDs ──

DURALUDON = 169
ARCHALUDON = 840
ARCHALUDON_EX = 190
CINDERACE = 666
RELICANTH = 57
CRUSTLE_LINE = {344, 345, 532}
GREAT_TUSK_LINE = {58, 607}
STARMIE_LINE = {1030, 1031}
LUCARIO_LINE = {677, 678}
OGERPON_LINE = {116, 117, 1051, 1052, 1256, 134, 712, 713, 748}
HOP_LINE = {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}
HOP_SNORLAX = 304
CHANDELURE_LINE = {97, 98, 494}

METAL_ENERGY = 8

POKE_PAD = 1152
ULTRA_BALL = 1121
POKEGEAR = 1122
NIGHT_STRETCHER = 1097
JUMBO_ICE_CREAM = 1147
HERO_CAPE = 1159
BOSS = 1182
EXPLORER = 1185
LILLIE = 1227
FULL_METAL_LAB = 1244

RAGING_HAMMER = 224
COATED_ATTACK = 1212
METAL_DEFENDER = 253

_ATTACK_BASE_DMG = {METAL_DEFENDER: 220, COATED_ATTACK: 120, 965: 50, 223: 30, 61: 30}

_SETUP_ACTIVE_PRIORITY = {
    CINDERACE: (100000, "Active: Cinderace Explosiveness"),
    DURALUDON: (20000, "Active fallback: Duraludon"),
    RELICANTH: (5000, "Active fallback: Relicanth"),
}

ALWAYS_SAFE_DISCARD = {METAL_ENERGY, CINDERACE}

CARD_DB = {c.cardId: c for c in all_card_data()}

MEGA_BRAVE = 983
PREMIUM_POWER_PRO = 1141
HARIYAMA_LINE = {673, 674}

# Track opponent's last-turn attack via logs
_opp_last_attack_id = None
_cur_turn_logs = []


# Passive public access ledger and isolated Ultra Ball consumer.
#
# This component deliberately uses only the frozen deck manifest and the
# current public observation.  It does not infer identities in the deck or
# Prizes.  Returning an action never mutates a zone; only the next novel
# observation can confirm a transition.
PUBLIC_BOSS_LEDGER_RULE_ID = (
    "PERSISTENT_PUBLIC_BOSS_ACCESS_LEDGER_WITH_PLAN_EQUIVALENT_"
    "LAST_COPY_DISCARD_GUARD_V1"
)
PUBLIC_BOSS_LEDGER_DECK_SHA256 = (
    "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"
)
_PUBLIC_LEDGER_DECK_COUNTS = {
    8: 12,
    169: 4,
    190: 4,
    666: 4,
    840: 2,
    1097: 3,
    1121: 4,
    1122: 4,
    1147: 3,
    1152: 4,
    1159: 1,
    1182: 4,
    1185: 4,
    1227: 4,
    1244: 3,
}
_PUBLIC_LEDGER_ZONES = {
    "HAND",
    "PUBLIC_DISCARD",
    "PUBLIC_LOST",
    "CURRENT_REVEAL",
    "UNKNOWN_HIDDEN",
}
_ULTRA_BALL_PUBLIC_TEXT = (
    "You can use this card only if you discard 2 other cards from your hand."
    "\n\nSearch your deck for a Pokémon, reveal it, and put it into your hand. "
    "Then, shuffle your deck."
)
_UNFAIR_STAMP = 1080


def _new_public_ledger_state(epoch=0):
    return {
        "epoch": epoch,
        "key": None,
        "last_turn": None,
        "last_action_count": None,
        "last_fingerprint": None,
        "last_action": None,
        "last_action_semantics": None,
        "cards": {},
        "physical": {},
        "transaction": None,
        "last_resolution": None,
        "events": [],
        "reset_count": 0,
        "last_reset_reason": None,
    }


_public_boss_ledger = _new_public_ledger_state()


def _ledger_event(kind, **payload):
    event = {"kind": kind, "rule": PUBLIC_BOSS_LEDGER_RULE_ID}
    event.update(payload)
    _public_boss_ledger["events"].append(event)
    if len(_public_boss_ledger["events"]) > 256:
        del _public_boss_ledger["events"][:-256]


def _set_boss_guard_resolution(
    obs,
    *,
    owner,
    suppression_reason,
    parent_semantics,
    final_semantics,
    proposal=False,
    fail_closed_reason=None,
):
    transaction = _public_boss_ledger.get("transaction")
    row = {
        "rule_id": PUBLIC_BOSS_LEDGER_RULE_ID,
        "proposal": bool(proposal),
        "owner": owner,
        "suppression_reason": suppression_reason,
        "fail_closed_reason": fail_closed_reason,
        "turn": None if obs is None else obs.current.turn,
        "action_count": None if obs is None else obs.current.turnActionCount,
        "parent_semantics": parent_semantics,
        "final_semantics": final_semantics,
        "transaction_stage": (
            None if transaction is None else transaction["stage"]
        ),
        "duplicate_policy": "IDENTICAL_RETRY_CACHED_WITHOUT_STATE_MUTATION",
    }
    _public_boss_ledger["last_resolution"] = row
    _ledger_event("RESOLUTION", **row)


def _reset_public_boss_ledger(reason, *, advance_epoch=True):
    global _public_boss_ledger
    previous = _public_boss_ledger
    epoch = previous.get("epoch", 0) + (1 if advance_epoch else 0)
    reset_count = previous.get("reset_count", 0) + 1
    events = list(previous.get("events", ()))
    _public_boss_ledger = _new_public_ledger_state(epoch)
    _public_boss_ledger["reset_count"] = reset_count
    _public_boss_ledger["last_reset_reason"] = reason
    _public_boss_ledger["events"] = events[-255:]
    _ledger_event("RESET", reason=reason, epoch=epoch)


def _boss_guard_debug_state():
    """Return a detached, JSON-friendly test view of the passive component."""
    cards = {
        str(serial): {"id": row["id"], "zone": row["zone"]}
        for serial, row in sorted(_public_boss_ledger["cards"].items())
    }
    transaction = _public_boss_ledger.get("transaction")
    if transaction is not None:
        transaction = {
            "stage": transaction["stage"],
            "boss": list(transaction["boss"]),
            "replacement": list(transaction["replacement"]),
            "metal": list(transaction["metal"]),
            "source_turn": transaction["source_turn"],
            "source_action_count": transaction["source_action_count"],
        }
    return {
        "epoch": _public_boss_ledger["epoch"],
        "key": (
            None
            if _public_boss_ledger["key"] is None
            else list(_public_boss_ledger["key"])
        ),
        "last_turn": _public_boss_ledger["last_turn"],
        "last_action_count": _public_boss_ledger["last_action_count"],
        "cards": cards,
        "transaction": transaction,
        "last_resolution": (
            None
            if _public_boss_ledger["last_resolution"] is None
            else dict(_public_boss_ledger["last_resolution"])
        ),
        "reset_count": _public_boss_ledger["reset_count"],
        "last_reset_reason": _public_boss_ledger["last_reset_reason"],
        "events": [dict(row) for row in _public_boss_ledger["events"]],
    }


def _boss_guard_reset_for_tests():
    global _public_boss_ledger
    _public_boss_ledger = _new_public_ledger_state()


def _card_semantic(card):
    if card is None:
        return None
    card_id = getattr(card, "id", None)
    serial = getattr(card, "serial", None)
    if not isinstance(card_id, int) or not isinstance(serial, int):
        return None
    return (card_id, serial)


def _valid_own_card(card, your_index):
    semantic = _card_semantic(card)
    if semantic is None:
        return False
    card_id, serial = semantic
    if serial <= 0 or card_id not in _PUBLIC_LEDGER_DECK_COUNTS:
        return False
    return getattr(card, "playerIndex", your_index) == your_index


def _public_physical_snapshot(obs):
    """Collect each physical own card once; reveal overlays are separate."""
    current = obs.current
    if current is None or current.yourIndex not in (0, 1):
        raise ValueError("missing current state or seat")
    yi = current.yourIndex
    if not isinstance(current.players, list) or len(current.players) != 2:
        raise ValueError("malformed players")
    mine = current.players[yi]
    if mine.hand is None or mine.handCount != len(mine.hand):
        raise ValueError("incomplete own hand")
    if (
        not isinstance(mine.deckCount, int)
        or mine.deckCount < 0
        or mine.deckCount > 60
        or mine.prize is None
    ):
        raise ValueError("malformed hidden-zone counts")

    physical = {}
    zones = {}

    def add(card, zone, *, alias_ok=False):
        if not _valid_own_card(card, yi):
            raise ValueError("malformed own card")
        card_id, serial = _card_semantic(card)
        old = physical.get(serial)
        if old is not None:
            if old["id"] != card_id:
                raise ValueError("duplicate serial with different card ids")
            if alias_ok:
                return
            raise ValueError("duplicate serial in physical zones")
        physical[serial] = {"id": card_id, "physical_zone": zone}
        if zone in _PUBLIC_LEDGER_ZONES:
            zones[serial] = {"id": card_id, "zone": zone}

    for card in mine.hand:
        add(card, "HAND")
    for card in mine.discard or ():
        add(card, "PUBLIC_DISCARD")
    for card in getattr(mine, "lostZone", None) or ():
        add(card, "PUBLIC_LOST")

    def add_pokemon(pokemon, zone):
        add(pokemon, zone)
        for card in getattr(pokemon, "preEvolution", None) or ():
            add(card, zone + "_PRE_EVOLUTION")
        for card in getattr(pokemon, "energyCards", None) or ():
            add(card, zone + "_ENERGY")
        for card in getattr(pokemon, "tools", None) or ():
            add(card, zone + "_TOOL")

    for pokemon in mine.active or ():
        if pokemon is None:
            raise ValueError("face-down own Active is unsupported")
        add_pokemon(pokemon, "PUBLIC_ACTIVE")
    for pokemon in mine.bench or ():
        if pokemon is None:
            raise ValueError("malformed own Bench")
        add_pokemon(pokemon, "PUBLIC_BENCH")

    for card in current.stadium or ():
        if card is not None and getattr(card, "playerIndex", None) == yi:
            add(card, "PUBLIC_STADIUM")

    # A played card can remain in effect limbo until the effect completes.
    # A context card, by contrast, can be a deck/reveal overlay (for example a
    # Turbo Flare Energy), so it is reconciled with reveal overlays below.
    card = getattr(obs.select, "effect", None)
    if card is not None and getattr(card, "playerIndex", None) == yi:
        add(card, "PUBLIC_EFFECT", alias_ok=True)

    # `current.looking` cards have left deckCount and therefore count as
    # physical CURRENT_REVEAL cards.  Face-down looking slots contribute only
    # to conservation.  `select.deck` is an overlay over deckCount.
    looking_hidden_count = 0
    for card in getattr(current, "looking", None) or ():
        if card is None:
            looking_hidden_count += 1
            continue
        add(card, "CURRENT_REVEAL", alias_ok=True)

    reveal = {}
    reveal_sources = []
    reveal_sources.extend(getattr(obs.select, "deck", None) or ())
    context_card = getattr(obs.select, "contextCard", None)
    if (
        context_card is not None
        and getattr(context_card, "playerIndex", None) == yi
    ):
        reveal_sources.append(context_card)
    for card in reveal_sources:
        if card is None:
            continue
        if not _valid_own_card(card, yi):
            raise ValueError("malformed revealed card")
        card_id, serial = _card_semantic(card)
        old = reveal.get(serial)
        if old is not None and old != card_id:
            raise ValueError("duplicate reveal serial with different ids")
        if serial in physical and physical[serial]["id"] != card_id:
            raise ValueError("reveal/physical serial collision")
        reveal[serial] = card_id
    for serial, card_id in reveal.items():
        if serial not in physical:
            zones[serial] = {"id": card_id, "zone": "CURRENT_REVEAL"}

    prize_count = len(mine.prize)
    if (
        len(physical)
        + looking_hidden_count
        + mine.deckCount
        + prize_count
        != 60
    ):
        raise ValueError("60-card conservation failure")
    visible_counts = Counter(row["id"] for row in physical.values())
    for card_id, count in visible_counts.items():
        if count > _PUBLIC_LEDGER_DECK_COUNTS.get(card_id, 0):
            raise ValueError("deck-manifest conservation failure")
    return {
        "physical": physical,
        "zones": zones,
        "reveal": reveal,
        "hand": {
            serial: row["id"]
            for serial, row in physical.items()
            if row["physical_zone"] == "HAND"
        },
        "discard": {
            serial: row["id"]
            for serial, row in physical.items()
            if row["physical_zone"] == "PUBLIC_DISCARD"
        },
        "lost": {
            serial: row["id"]
            for serial, row in physical.items()
            if row["physical_zone"] == "PUBLIC_LOST"
        },
        "deck_count": mine.deckCount,
        "prize_count": prize_count,
        "looking_hidden_count": looking_hidden_count,
    }


def _log_signature(entry):
    fields = (
        "type",
        "playerIndex",
        "cardId",
        "serial",
        "fromArea",
        "toArea",
        "cardIdActive",
        "serialActive",
        "cardIdBench",
        "serialBench",
        "cardIdBefore",
        "serialBefore",
        "cardIdAfter",
        "serialAfter",
        "cardIdTarget",
        "serialTarget",
        "attackId",
        "value",
        "result",
        "reason",
    )
    result = []
    for field in fields:
        value = getattr(entry, field, None)
        try:
            value = int(value) if value is not None else None
        except (TypeError, ValueError):
            value = repr(value)
        result.append(value)
    return tuple(result)


def _option_signature(obs, position, option):
    semantic = None
    try:
        semantic = _card_semantic(option_card(obs, option))
    except Exception:
        semantic = None
    fields = (
        "type",
        "number",
        "area",
        "index",
        "playerIndex",
        "toolIndex",
        "energyIndex",
        "count",
        "inPlayArea",
        "inPlayIndex",
        "attackId",
        "cardId",
        "serial",
    )
    encoded = []
    for field in fields:
        value = getattr(option, field, None)
        try:
            value = int(value) if value is not None else None
        except (TypeError, ValueError):
            value = repr(value)
        encoded.append(value)
    return (position, tuple(encoded), semantic)


def _observation_fingerprint(obs, snapshot):
    current = obs.current
    select = obs.select
    effect = _card_semantic(getattr(select, "effect", None))
    context_card = _card_semantic(getattr(select, "contextCard", None))
    stadium = tuple(
        sorted(
            semantic
            for semantic in (_card_semantic(card) for card in current.stadium or ())
            if semantic is not None
        )
    )
    return (
        current.yourIndex,
        current.firstPlayer,
        current.turn,
        current.turnActionCount,
        current.result,
        bool(current.supporterPlayed),
        bool(current.energyAttached),
        bool(current.retreated),
        tuple(
            sorted(
                (serial, row["id"], row["physical_zone"])
                for serial, row in snapshot["physical"].items()
            )
        ),
        tuple(sorted(snapshot["reveal"].items())),
        snapshot["deck_count"],
        snapshot["prize_count"],
        stadium,
        int(select.type),
        int(select.context),
        select.minCount,
        select.maxCount,
        effect,
        context_card,
        tuple(
            _option_signature(obs, position, option)
            for position, option in enumerate(select.option or ())
        ),
        tuple(_log_signature(entry) for entry in obs.logs or ()),
    )


def _played_card_moves_hands(obs):
    for entry in obs.logs or ():
        if entry.type != LogType.PLAY:
            continue
        card_id = getattr(entry, "cardId", None)
        if card_id == _UNFAIR_STAMP:
            return True
        data = CARD_DB.get(card_id)
        if data is None:
            continue
        text = " ".join(
            getattr(skill, "text", "") for skill in getattr(data, "skills", ())
        ).lower()
        if (
            "shuffle your hand" in text
            or "shuffles your hand" in text
            or "shuffle their hand" in text
            or "shuffles their hand" in text
            or "hand into their deck" in text
            or "hand into your deck" in text
            or "discard your hand" in text
            or ("hand" in text and "bottom of" in text and "deck" in text)
        ):
            return True
    return False


def _has_own_shuffle(obs):
    yi = obs.current.yourIndex
    return any(
        entry.type == LogType.SHUFFLE
        and getattr(entry, "playerIndex", None) == yi
        for entry in obs.logs or ()
    )


def _explicit_move_serials(obs):
    result = set()
    yi = obs.current.yourIndex
    seen = set()
    for entry in obs.logs or ():
        if entry.type != LogType.MOVE_CARD:
            continue
        if getattr(entry, "playerIndex", None) != yi:
            continue
        card_id = getattr(entry, "cardId", None)
        serial = getattr(entry, "serial", None)
        if (
            not isinstance(card_id, int)
            or not isinstance(serial, int)
            or serial <= 0
            or card_id not in _PUBLIC_LEDGER_DECK_COUNTS
        ):
            raise ValueError("malformed move log")
        signature = (
            card_id,
            serial,
            getattr(entry, "fromArea", None),
            getattr(entry, "toArea", None),
        )
        if signature in seen:
            raise ValueError("duplicate move log")
        seen.add(signature)
        result.add(serial)
    if any(
        entry.type == LogType.MOVE_CARD_REVERSE
        and getattr(entry, "playerIndex", None) == yi
        for entry in obs.logs or ()
    ):
        raise ValueError("unsupported face-down zone move")
    return result


def _reconcile_public_ledger(obs, snapshot):
    previous = _public_boss_ledger["cards"]
    current_zones = dict(snapshot["zones"])
    physical = snapshot["physical"]
    moved = _explicit_move_serials(obs)
    disruption = _played_card_moves_hands(obs)
    shuffled = _has_own_shuffle(obs)

    for serial, row in previous.items():
        old_zone = row["zone"]
        if old_zone == "PUBLIC_LOST":
            if serial not in snapshot["lost"]:
                raise ValueError("card left public lost zone")
        elif old_zone == "PUBLIC_DISCARD":
            if serial not in physical and serial not in snapshot["reveal"] and serial not in moved:
                raise ValueError("discard serial disappeared without confirmation")
        elif old_zone == "HAND":
            if (
                serial not in physical
                and serial not in snapshot["reveal"]
                and serial not in moved
                and not disruption
            ):
                raise ValueError("held serial disappeared without confirmation")
        elif old_zone == "CURRENT_REVEAL":
            if (
                serial not in physical
                and serial not in snapshot["reveal"]
                and serial not in moved
                and not shuffled
            ):
                raise ValueError("revealed serial disappeared without shuffle")

    reconciled = {
        serial: {"id": row["id"], "zone": "UNKNOWN_HIDDEN"}
        for serial, row in previous.items()
    }
    for serial, row in physical.items():
        if serial not in current_zones:
            reconciled[serial] = {
                "id": row["id"],
                "zone": "UNKNOWN_HIDDEN",
            }
    for serial, row in current_zones.items():
        old = reconciled.get(serial)
        if old is not None and old["id"] != row["id"]:
            raise ValueError("serial identity mutation")
        reconciled[serial] = dict(row)
    if any(row["zone"] not in _PUBLIC_LEDGER_ZONES for row in reconciled.values()):
        raise ValueError("unsupported ledger zone")
    return reconciled, disruption


def _transaction_confirmation(obs, snapshot):
    transaction = _public_boss_ledger.get("transaction")
    if transaction is None:
        return False
    expected = {
        transaction["replacement"][1]: transaction["replacement"][0],
        transaction["metal"][1]: transaction["metal"][0],
    }
    boss_id, boss_serial = transaction["boss"]
    exact_discard = all(
        snapshot["discard"].get(serial) == card_id
        for serial, card_id in expected.items()
    )
    boss_held = snapshot["hand"].get(boss_serial) == boss_id
    moved = {
        (getattr(entry, "cardId", None), getattr(entry, "serial", None))
        for entry in obs.logs or ()
        if entry.type == LogType.MOVE_CARD
        and getattr(entry, "playerIndex", None) == obs.current.yourIndex
        and getattr(entry, "fromArea", None) == AreaType.HAND
        and getattr(entry, "toArea", None) == AreaType.DISCARD
    }
    exact_logs = {
        transaction["replacement"],
        transaction["metal"],
    }.issubset(moved)
    if exact_discard and boss_held and exact_logs:
        _ledger_event(
            "TRANSACTION_CONFIRMED",
            boss=list(transaction["boss"]),
            replacement=list(transaction["replacement"]),
            metal=list(transaction["metal"]),
            turn=obs.current.turn,
            action_count=obs.current.turnActionCount,
        )
        _public_boss_ledger["transaction"] = None
        return True
    raise ValueError("emitted discard was not exactly confirmed")


def _observe_public_ledger(obs):
    """Reconcile one novel observation and report whether proposals are safe."""
    if obs.current is None or obs.select is None:
        _reset_public_boss_ledger("new_game_or_deck_request")
        return None, None, False, False
    current = obs.current
    if current.result != -1 or any(
        entry.type == LogType.RESULT for entry in obs.logs or ()
    ):
        _reset_public_boss_ledger("result")
        return None, None, False, False
    if (
        current.yourIndex not in (0, 1)
        or current.firstPlayer not in (0, 1)
        or not isinstance(current.turn, int)
        or not isinstance(current.turnActionCount, int)
        or current.turn < 0
        or current.turnActionCount < 0
    ):
        _reset_public_boss_ledger("malformed_game_key")
        return None, None, False, False
    if current.turn == 0 or obs.select.context in {
        SelectContext.IS_FIRST,
        SelectContext.MULLIGAN,
        SelectContext.SETUP_ACTIVE_POKEMON,
        SelectContext.SETUP_BENCH_POKEMON,
    }:
        _reset_public_boss_ledger("setup_or_new_game")
        return None, None, False, False

    snapshot = _public_physical_snapshot(obs)
    fingerprint = _observation_fingerprint(obs, snapshot)
    if fingerprint == _public_boss_ledger["last_fingerprint"]:
        return snapshot, fingerprint, True, True

    key_tail = (
        current.yourIndex,
        current.firstPlayer,
        PUBLIC_BOSS_LEDGER_DECK_SHA256,
    )
    old_key = _public_boss_ledger["key"]
    if old_key is not None and old_key[1:] != key_tail:
        _reset_public_boss_ledger("seat_or_first_player_change")
        return snapshot, fingerprint, False, False
    last_turn = _public_boss_ledger["last_turn"]
    last_action = _public_boss_ledger["last_action_count"]
    if last_turn is not None:
        if current.turn < last_turn:
            _reset_public_boss_ledger("turn_regression")
            return snapshot, fingerprint, False, False
        if current.turn == last_turn and current.turnActionCount < last_action:
            _reset_public_boss_ledger("action_regression")
            return snapshot, fingerprint, False, False
        if current.turn > last_turn + 2:
            _reset_public_boss_ledger("observation_discontinuity")
            return snapshot, fingerprint, False, False

    reconciled, disruption = _reconcile_public_ledger(obs, snapshot)
    _public_boss_ledger["key"] = (
        _public_boss_ledger["epoch"],
        *key_tail,
    )
    _public_boss_ledger["cards"] = reconciled
    _public_boss_ledger["physical"] = snapshot["physical"]
    _public_boss_ledger["last_turn"] = current.turn
    _public_boss_ledger["last_action_count"] = current.turnActionCount
    _public_boss_ledger["last_fingerprint"] = fingerprint
    _public_boss_ledger["last_action"] = None
    _public_boss_ledger["last_action_semantics"] = None
    _ledger_event(
        "OBSERVATION_RECONCILED",
        turn=current.turn,
        action_count=current.turnActionCount,
        disruption=disruption,
        hand_access=sum(
            1 for row in reconciled.values() if row["zone"] == "HAND"
        ),
    )
    confirmed = _transaction_confirmation(obs, snapshot)
    return snapshot, fingerprint, True, confirmed


def _update_opp_attack_tracking(obs):
    global _opp_last_attack_id, _cur_turn_logs
    yi = obs.current.yourIndex
    for entry in obs.logs:
        if entry.type == LogType.TURN_END:
            for prev in _cur_turn_logs:
                if prev.type == LogType.ATTACK and getattr(prev, 'playerIndex', yi) != yi:
                    _opp_last_attack_id = prev.attackId
            _cur_turn_logs.clear()
        else:
            _cur_turn_logs.append(entry)


# ── Board helpers ──

def read_deck_csv():
    fp = "deck.csv"
    if not os.path.exists(fp):
        fp = "/kaggle_simulations/agent/deck.csv"
    with open(fp) as f:
        return [int(line) for line in f.read().strip().split("\n")]


def get_card(obs, area, index, player_index):
    if area is None or index is None:
        return None
    ps = obs.current.players[player_index]
    if area == AreaType.DECK and obs.select and obs.select.deck is not None:
        return obs.select.deck[index] if index < len(obs.select.deck) else None
    if area == AreaType.HAND and ps.hand is not None:
        return ps.hand[index] if index < len(ps.hand) else None
    if area == AreaType.DISCARD:
        return ps.discard[index] if index < len(ps.discard) else None
    if area == AreaType.ACTIVE:
        return ps.active[index] if index < len(ps.active) else None
    if area == AreaType.BENCH:
        return ps.bench[index] if index < len(ps.bench) else None
    if area == AreaType.PRIZE:
        return ps.prize[index] if index < len(ps.prize) else None
    if area == AreaType.STADIUM:
        return obs.current.stadium[index] if index < len(obs.current.stadium) else None
    if area == AreaType.LOOKING and obs.current.looking is not None:
        return obs.current.looking[index] if index < len(obs.current.looking) else None
    return None


def option_card(obs, opt):
    yi = obs.current.yourIndex
    pi = opt.playerIndex if opt.playerIndex is not None else yi
    if opt.type == OptionType.PLAY:
        return get_card(obs, AreaType.HAND, opt.index, pi)
    return get_card(obs, opt.area, opt.index, pi)


def option_target(obs, opt):
    if opt.inPlayArea is None or opt.inPlayIndex is None:
        return None
    return get_card(obs, opt.inPlayArea, opt.inPlayIndex, obs.current.yourIndex)


def my_state(obs):
    return obs.current.players[obs.current.yourIndex]


def opp_state(obs):
    return obs.current.players[1 - obs.current.yourIndex]


def active_pokemon(obs):
    ps = my_state(obs)
    return ps.active[0] if ps.active else None


def opp_active_pokemon(obs):
    ps = opp_state(obs)
    return ps.active[0] if ps.active else None


def opp_bench_pokemon(obs):
    return [p for p in opp_state(obs).bench if p]


def all_my_pokemon(obs):
    ps = my_state(obs)
    return [p for p in (ps.active + ps.bench) if p]


def hand_ids(obs):
    hand = my_state(obs).hand
    return [c.id for c in hand if c] if hand else []


def discard_ids(obs):
    return [c.id for c in (my_state(obs).discard or []) if c]


def opp_visible_card_ids(obs):
    opp = opp_state(obs)
    ids = [c.id for c in (opp.discard or []) if c]
    for pokemon in (opp.active + opp.bench):
        if not pokemon:
            continue
        ids.append(pokemon.id)
        ids.extend(c.id for c in (getattr(pokemon, "energyCards", None) or []) if c)
        ids.extend(c.id for c in (getattr(pokemon, "tools", None) or []) if c)
    return set(ids)


def metal_in_discard(obs):
    return sum(1 for c in (my_state(obs).discard or []) if c and c.id == METAL_ENERGY)


def energy_count(pokemon):
    if pokemon is None:
        return 0
    if getattr(pokemon, "energyCards", None) is not None:
        return len(pokemon.energyCards)
    return len(getattr(pokemon, "energies", []) or [])


def retreat_cost(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    return getattr(data, "retreatCost", 0) if data else 0


def damage_on(pokemon):
    if pokemon is None:
        return 0
    return max(0, getattr(pokemon, "maxHp", pokemon.hp) - pokemon.hp)


def has_tool(pokemon):
    return bool(getattr(pokemon, "tools", []) or [])


def count_in_play(obs, card_id):
    return sum(1 for p in all_my_pokemon(obs) if p.id == card_id)


def has_in_play(obs, card_id):
    return any(p.id == card_id for p in all_my_pokemon(obs))


def live_alakazam_marker_visible(obs):
    if detect_matchup(obs) != "alakazam":
        return False
    seen = opp_visible_card_ids(obs)
    if seen & KETCHUM_ALAKAZAM_MARKERS:
        return False
    return bool(seen & LIVE_ALAKAZAM_MARKERS)


def need_duraludon(obs):
    if detect_matchup(obs) == "alakazam":
        target_count = 4 if live_alakazam_marker_visible(obs) else 3
        return sum(1 for p in all_my_pokemon(obs) if p.id in {DURALUDON, ARCHALUDON_EX}) < target_count
    return sum(1 for p in all_my_pokemon(obs) if p.id in {DURALUDON, ARCHALUDON_EX}) < 2


def need_archaludon(obs):
    has_dura, ex_count = False, 0
    for p in all_my_pokemon(obs):
        if p.id == DURALUDON:
            has_dura = True
        elif p.id == ARCHALUDON_EX:
            ex_count += 1
    if detect_matchup(obs) == "alakazam":
        target_ex_count = 4 if live_alakazam_marker_visible(obs) else 3
    else:
        target_ex_count = 2
    return has_dura and ex_count < target_ex_count


def need_nonex_archaludon(obs):
    if detect_matchup(obs) != "ogerpon":
        return False
    has_dura = any(p.id == DURALUDON for p in all_my_pokemon(obs))
    return has_dura and not has_in_play(obs, ARCHALUDON)


def final_prize_nonex_no_backup(obs):
    matchup = detect_matchup(obs)
    if matchup not in {"iono", "alakazam"}:
        return False
    if len(opp_state(obs).prize or []) > 2:
        return False
    if matchup == "alakazam":
        if not live_alakazam_marker_visible(obs):
            return False
    return not any(prize_value(p) == 1 for p in my_state(obs).bench if p)


def safe_discard_count(obs):
    ids = hand_ids(obs)
    mt = metal_in_discard(obs)
    safe = 0
    for cid in ids:
        if cid == METAL_ENERGY and mt + safe < 2:
            safe += 1
        elif cid == CINDERACE:
            safe += 1
    draw_in_hand = sum(1 for c in ids if c in (LILLIE, EXPLORER))
    if draw_in_hand >= 2:
        safe += draw_in_hand - 1
    return safe


def prize_value(pokemon):
    data = CARD_DB.get(pokemon.id) if pokemon else None
    if data and getattr(data, "megaEx", False):
        return 3
    if data and getattr(data, "ex", False):
        return 2
    return 1


def best_attack_damage(obs, attack_id):
    if attack_id == RAGING_HAMMER:
        return 80 + damage_on(active_pokemon(obs)) // 10 * 10
    return _ATTACK_BASE_DMG.get(attack_id, 0)


def is_metal_weak(pokemon):
    if pokemon is None:
        return False
    data = CARD_DB.get(pokemon.id)
    w = getattr(data, "weakness", None) if data else None
    if w is None:
        return False
    return getattr(w, "value", w) == METAL_ENERGY


def effective_damage(base_damage, target):
    return base_damage * 2 if is_metal_weak(target) else base_damage


def _first_option_index(obs, card_id):
    for o in obs.select.option:
        oc = option_card(obs, o)
        if oc and oc.id == card_id:
            return getattr(o, 'index', None)
    return None


# ── Attack routes ──

def direct_attack_energy_route(obs, pokemon):
    e = energy_count(pokemon)
    if e >= 3:
        return True, False
    if e == 2 and not obs.current.energyAttached and METAL_ENERGY in hand_ids(obs):
        return True, True
    return False, False


def can_evolve_to_archaludon_now(pokemon, obs):
    if pokemon is None or pokemon.id != DURALUDON:
        return False
    if ARCHALUDON_EX not in hand_ids(obs):
        return False
    return not getattr(pokemon, "appearThisTurn", True)


def alloy_attack_energy_route(obs, pokemon):
    if not can_evolve_to_archaludon_now(pokemon, obs):
        return False, False
    current = energy_count(pokemon)
    alloy = min(2, metal_in_discard(obs))
    total = current + alloy
    if total >= 3:
        return True, False
    if total == 2 and not obs.current.energyAttached and METAL_ENERGY in hand_ids(obs):
        return True, True
    return False, False


def attack_energy_route(obs, pokemon):
    if pokemon is None:
        return False, False
    if pokemon.id == ARCHALUDON:
        return direct_attack_energy_route(obs, pokemon)
    if pokemon.id == ARCHALUDON_EX:
        return direct_attack_energy_route(obs, pokemon)
    if pokemon.id == DURALUDON:
        ok, uses_attach = direct_attack_energy_route(obs, pokemon)
        if ok:
            return True, uses_attach
        return alloy_attack_energy_route(obs, pokemon)
    return False, False


def archaludon_ex_attack_route(obs):
    active = active_pokemon(obs)
    if active and active.id in {ARCHALUDON, ARCHALUDON_EX, DURALUDON}:
        ok, uses_attach = attack_energy_route(obs, active)
        if ok:
            return {"attacker": active, "uses_attach": uses_attach, "needs_retreat": False}

    if active is None or obs.current.retreated or energy_count(active) < retreat_cost(active):
        return None
    ps = my_state(obs)
    for pokemon in [p for p in ps.bench if p]:
        if pokemon.id not in {ARCHALUDON, ARCHALUDON_EX, DURALUDON}:
            continue
        ok, uses_attach = attack_energy_route(obs, pokemon)
        if ok:
            return {"attacker": pokemon, "uses_attach": uses_attach, "needs_retreat": True}
    return None


def planned_archaludon_attacks(obs):
    route = archaludon_ex_attack_route(obs)
    if route is None:
        return []
    attacker = route["attacker"]
    attacks = []
    if attacker.id == ARCHALUDON:
        attacks.append({"damage": 120})
    if attacker.id == ARCHALUDON_EX:
        attacks.append({"damage": 220})
        if has_in_play(obs, RELICANTH):
            attacks.append({"damage": 80 + damage_on(attacker) // 10 * 10})
    if attacker.id == DURALUDON:
        attacks.append({"damage": 80 + damage_on(attacker) // 10 * 10})
        if can_evolve_to_archaludon_now(attacker, obs):
            attacks.append({"damage": 220})
    return attacks


# ── Matchup detection & opponent max damage ──

ALAKAZAM_LINE = {741, 742, 743}
IONO_LINE = {265, 268, 269, 270, 271}
KETCHUM_ALAKAZAM_MARKERS = {1246, 1247}
LIVE_ALAKAZAM_MARKERS = {1264, 858, 174}
ARCHALUDON_LINE = {169, 190, 840}
_ALA_BOARD_GAIN = {66: 3, 742: 2, 305: 2, 65: 2, 741: 1}  # Dudunsparce, Kadabra, Dunsparce×2, Abra


def _estimate_alakazam_from_pokes(opp, pokes):
    """(floor, ceiling, ceiling_with_boss) damage from visible Alakazam line."""
    ids = [p.id for p in pokes if p]
    if not (ALAKAZAM_LINE & set(ids)):
        return 0, 0, 0
    base = opp.handCount + 1
    gain = sum(_ALA_BOARD_GAIN.get(i, 0) for i in ids)
    enriching_seen = (
        any(c and c.id == 13 for c in (opp.discard or []))
        or any(c and c.id == 13 for p in pokes if p for c in (getattr(p, "energyCards", None) or []))
    )
    if not enriching_seen:
        gain += 3
    if any(i == 140 for i in ids):
        gain += 3
    return base * 20, (base + gain + 2) * 20, (base + gain - 1) * 20


def _estimate_alakazam(obs):
    """(floor, ceiling, ceiling_with_boss) damage from Powerful Hand."""
    opp = opp_state(obs)
    pokes = ([opp.active[0]] if opp.active else []) + list(opp.bench or [])
    return _estimate_alakazam_from_pokes(opp, pokes)


def detect_matchup(obs):
    opp = opp_state(obs)
    ids = {p.id for p in (opp.active + opp.bench) if p}
    if ids & (CRUSTLE_LINE | GREAT_TUSK_LINE):
        return "crustle"
    if ids & OGERPON_LINE:
        return "ogerpon"
    if ids & HOP_LINE:
        return "hop"
    if ids & STARMIE_LINE:
        return "starmie"
    if ids & LUCARIO_LINE:
        return "lucario"
    if ids & CHANDELURE_LINE:
        return "chandelure"
    if ids & ALAKAZAM_LINE:
        return "alakazam"
    if ids & IONO_LINE:
        return "iono"
    if ids & ARCHALUDON_LINE:
        return "archaludon"
    return "generic"


def opp_max_damage(obs):
    matchup = detect_matchup(obs)
    if matchup == "alakazam":
        _, ceiling, _ = _estimate_alakazam(obs)
        return ceiling
    if matchup == "crustle":
        return 120
    if matchup == "ogerpon":
        return 180
    if matchup == "hop":
        return 220
    if matchup == "lucario":
        return 270  # Mega Brave base. PPP adds +30 each but unpredictable
    if matchup == "starmie":
        return 210
    if matchup == "chandelure":
        return max(60, 20 * int(getattr(my_state(obs), "handCount", 0) or 0))
    return 220


# ── Overrides ──

def apply_overrides(obs, opt, score, reason):
    # Hard rule: don't Explorer with low deck
    if opt.type == OptionType.PLAY:
        card = option_card(obs, opt)
        cid = card.id if card else None
        if detect_matchup(obs) == "chandelure" and my_state(obs).deckCount <= 25 and cid == EXPLORER:
            return -5000, "Chandelure: don't Explorer near deckout"
        if my_state(obs).deckCount <= 10 and cid == EXPLORER:
            return -5000, "hard: don't Explorer with low deck"

    if detect_matchup(obs) == "ogerpon":
        card = option_card(obs, opt)
        cid = card.id if card else getattr(opt, 'cardId', None)
        ctx = obs.select.context
        opp_ids = {p.id for p in (opp_state(obs).active + opp_state(obs).bench) if p}
        cornerstone_seen = 117 in opp_ids

        opp_act = opp_active_pokemon(obs)
        if cornerstone_seen and opt.type == OptionType.EVOLVE and cid == ARCHALUDON_EX and opp_act and opp_act.id == 117:
            return -10000, "Ogerpon: don't evolve into Ability attacker"
        if cornerstone_seen and opt.type == OptionType.EVOLVE and cid == ARCHALUDON:
            return max(score, 30000), "Ogerpon: evolve to non-Ability Archaludon"
        if cornerstone_seen and opt.type == OptionType.ATTACK:
            aid = getattr(opt, 'attackId', None)
            active = active_pokemon(obs)
            opp_act = opp_active_pokemon(obs)
            if active and active.id == ARCHALUDON and opp_act and opp_act.id == 117 and aid == COATED_ATTACK:
                return max(score, 28000), "Ogerpon: Coated Attack Cornerstone"
            if active and active.id == ARCHALUDON_EX and opp_act and opp_act.id == 117 and aid == METAL_DEFENDER:
                return -5000, "Ogerpon: Metal Defender blocked"
            if active and active.id == DURALUDON and aid == RAGING_HAMMER:
                return max(score, 25000), "Ogerpon: Duraludon Raging Hammer"
        if cornerstone_seen and ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON_EX:
            return -3000, "Ogerpon: skip Archaludon ex"
        if cornerstone_seen and ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON:
            return 25000, "Ogerpon: take non-Ability Archaludon"
        if cornerstone_seen and ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD} and cid == ARCHALUDON_EX:
            return 9000, "Ogerpon: discard Archaludon ex"
        if cornerstone_seen and ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD} and cid == ARCHALUDON:
            return -5000, "Ogerpon: keep non-Ability Archaludon"

    if detect_matchup(obs) != "crustle":
        return score, reason

    # Crustle overrides
    card = option_card(obs, opt)
    cid = card.id if card else getattr(opt, 'cardId', None)
    ctx = obs.select.context

    if opt.type == OptionType.EVOLVE and cid == ARCHALUDON_EX:
        return -10000, "Crustle: don't evolve to ex"

    if opt.type == OptionType.ATTACK:
        aid = getattr(opt, 'attackId', None)
        active = active_pokemon(obs)
        opp_act = opp_active_pokemon(obs)
        opp_has_spiky = bool(opp_act and any(
            getattr(c, 'id', None) == 14
            for c in (getattr(opp_act, 'energyCards', None) or [])))
        if (active and active.id == DURALUDON and active.hp == 130
                and opp_act and opp_act.id == 345 and energy_count(opp_act) >= 2
                and opp_has_spiky):
            return -3000, "Crustle: full HP Duraludon waits out Spiky"
        if aid == METAL_DEFENDER:
            return -5000, "Crustle: Metal Defender does 0"
        if aid == RAGING_HAMMER:
            rh_dmg = 80 + damage_on(active_pokemon(obs)) // 10 * 10
            return max(score, 200), "Crustle: Raging Hammer"

    if opt.type == OptionType.PLAY:
        if cid == RELICANTH:
            return -5000, "Crustle: skip Relicanth"
        dc = my_state(obs).deckCount
        hc = my_state(obs).handCount
        line_count = (
            count_in_play(obs, DURALUDON)
            + count_in_play(obs, ARCHALUDON)
            + count_in_play(obs, ARCHALUDON_EX)
        )
        has_stable_attacker = any(
            p and p.id in {DURALUDON, ARCHALUDON, ARCHALUDON_EX} and energy_count(p) >= 3
            for p in all_my_pokemon(obs)
        )
        if cid == LILLIE and dc <= 16:
            if hc > 6:
                return 18000 + min(5000, (hc - 6) * 1000), "Crustle: Lillie refills low deck"
            if dc <= 10:
                return -5000, "Crustle: skip Lillie with low deck and small hand"
        if cid in (POKE_PAD, POKEGEAR) and (dc <= 18 or has_stable_attacker):
            return -5000, "Crustle: preserve deck, skip search item"
        if cid == EXPLORER and (dc <= 24 or (dc <= 30 and (line_count >= 2 or has_stable_attacker))):
            return -5000, "Crustle: preserve deck, skip Explorer"
        if cid == ULTRA_BALL and dc <= 18 and line_count >= 2:
            return -3000, "Crustle: preserve deck, skip Ultra Ball"
        opp_ids = {p.id for p in (opp_state(obs).active + opp_state(obs).bench) if p}
        if opp_ids & GREAT_TUSK_LINE:
            if cid == LILLIE and dc <= 38:
                if hc > 6:
                    return 17000 + min(5000, (hc - 6) * 1000), "Great Tusk: Lillie refills deck earlier"
                return -5000, "Great Tusk: skip Lillie with low deck and small hand"
            if cid in (POKE_PAD, POKEGEAR) and (dc <= 30 or has_stable_attacker):
                return -5000, "Great Tusk: preserve deck, skip search item"
            if cid == EXPLORER and (dc <= 40 or (dc <= 30 and (line_count >= 2 or has_stable_attacker))):
                return -5000, "Great Tusk: preserve deck, skip Explorer"
            if cid == ULTRA_BALL and dc <= 34 and line_count >= 2:
                return -3000, "Great Tusk: preserve deck, skip Ultra Ball"
        if dc <= 10 and cid in (EXPLORER, LILLIE):
            if cid == LILLIE and dc <= 3 and my_state(obs).handCount >= dc + 6:
                return 15000, "Crustle: Lillie to refill deck"
            return -5000, "Crustle: don't draw with low deck"
        if cid == LILLIE:
            has_metal = any(c and c.id == METAL_ENERGY for c in (my_state(obs).hand or []) if c)
            if not has_metal:
                return score, "Crustle: Lillie OK (no energy in hand)"

    if opt.type == OptionType.ATTACH:
        target = option_target(obs, opt)
        tid = target.id if target else None
        if getattr(opt, 'inPlayArea', None) == AreaType.BENCH and tid == DURALUDON:
            return score + 10000, "Crustle: bench Duraludon energy priority"
        if getattr(opt, 'inPlayArea', None) == AreaType.ACTIVE:
            active = active_pokemon(obs)
            if active and energy_count(active) >= 2:
                return score + 3000, "Crustle: Active 3rd energy"

    if ctx == SelectContext.TO_HAND and opt.type == OptionType.CARD and cid == ARCHALUDON_EX:
        return -3000, "Crustle: skip Archaludon ex"

    if ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        if cid == ARCHALUDON_EX and score < 0:
            return 9000, "Crustle: discard Archaludon ex"

    return score, reason


# ── Scoring ──

def score_setup(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ctx = obs.select.context

    if ctx == SelectContext.MULLIGAN:
        return (10000, "no mulligan") if opt.type == OptionType.NO else (0, "mulligan")
    if ctx == SelectContext.IS_FIRST:
        return (10000, "choose second") if opt.type == OptionType.NO else (0, "go first")
    if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
        return _SETUP_ACTIVE_PRIORITY.get(cid, (0, "unknown Active"))
    if ctx == SelectContext.SETUP_BENCH_POKEMON:
        return -10000, "never bench during setup"
    return 0, "non-setup"


# HP threshold per matchup: skip Ice Cream if HP > this value
_ICE_CREAM_HP_THRESHOLD = {
    "lucario": 270,
    "starmie": 210,
    "crustle": 120,
    "hop": 220,
    "generic": 230,
}


def should_skip_ice_cream(obs, active):
    """Decide whether to skip Jumbo Ice Cream. Returns (skip: bool, reason: str)."""
    # 1. Active must be Archaludon ex
    if active.id != ARCHALUDON_EX:
        return True, "skip Ice Cream: not Archaludon ex"
    # 2. Raging Hammer KO guard: don't heal if it loses a KO (but 220 Metal Defender still KOs → heal OK)
    opp_act = opp_active_pokemon(obs)
    if opp_act and has_in_play(obs, RELICANTH):
        md_kills = effective_damage(220, opp_act) >= opp_act.hp
        if not md_kills:
            rh_dmg = 80 + damage_on(active) // 10 * 10
            rh_after = 80 + max(0, damage_on(active) - 80) // 10 * 10
            if effective_damage(rh_dmg, opp_act) >= opp_act.hp and effective_damage(rh_after, opp_act) < opp_act.hp:
                return True, "skip Ice Cream: healing loses Raging Hammer KO"
    # 3. Alakazam: all-or-nothing Ice Cream decision
    matchup = detect_matchup(obs)
    if matchup == "alakazam":
        floor, ceiling, _ = _estimate_alakazam(obs)
        opp_a = opp_active_pokemon(obs)
        attacks = planned_archaludon_attacks(obs)
        if opp_a and attacks and any(effective_damage(a["damage"], opp_a) >= opp_a.hp for a in attacks):
            _, ceiling, _ = _estimate_alakazam_from_pokes(opp_state(obs), opp_bench_pokemon(obs))
        ice_count = sum(1 for c in (my_state(obs).hand or []) if c and c.id == JUMBO_ICE_CREAM)
        max_hp = getattr(active, "maxHp", active.hp)
        hp_after_all = min(max_hp, active.hp + ice_count * 80)
        if hp_after_all <= active.hp:
            return True, "skip Ice Cream: no effective healing"
        if hp_after_all < floor:
            return True, f"skip Ice Cream: even {ice_count}x heal ({hp_after_all}) < floor {floor}"
        if hp_after_all >= ceiling:
            return False, f"use Ice Cream: {ice_count}x heal ({hp_after_all}) >= ceil {ceiling}"
        return False, f"use Ice Cream: {ice_count}x heal ({hp_after_all}) between floor={floor} ceil={ceiling}"
    # 4. HP above matchup threshold
    threshold = _ICE_CREAM_HP_THRESHOLD.get(matchup, 220)
    if active.hp > threshold:
        return True, f"skip Ice Cream: HP {active.hp} > {threshold} ({matchup})"
    # 5. Use it
    return False, ""


ITEMS = {POKE_PAD, ULTRA_BALL, POKEGEAR, NIGHT_STRETCHER, JUMBO_ICE_CREAM, HERO_CAPE}


def score_play(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else None
    ids = hand_ids(obs)

    # ── Pokemon: bench if available ──
    if cid in {DURALUDON, RELICANTH}:
        return 18000, "play Pokemon"

    # ── Stadium ──
    if cid == FULL_METAL_LAB:
        active = active_pokemon(obs)
        if active and active.id not in {DURALUDON, ARCHALUDON_EX}:
            return -200, "skip FML: Active not Metal"
        return 20000, "play Full Metal Lab"

    # ── Items: default 20000, only negative exceptions ──
    if cid in ITEMS:
        if cid == HERO_CAPE:
            if not any(p.id in {ARCHALUDON_EX, DURALUDON} and not has_tool(p) for p in all_my_pokemon(obs)):
                return -500, "save Hero's Cape: no target"
        if cid == JUMBO_ICE_CREAM:
            active = active_pokemon(obs)
            if active:
                skip, reason = should_skip_ice_cream(obs, active)
                if skip:
                    return -500, reason
        if cid == NIGHT_STRETCHER:
            disc = discard_ids(obs)
            line_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
            mirror_rebuild = detect_matchup(obs) == "archaludon" and (
                (DURALUDON in disc and DURALUDON not in ids and line_count <= 2)
                or (
                    ARCHALUDON_EX in disc
                    and ARCHALUDON_EX not in ids
                    and has_in_play(obs, DURALUDON)
                    and count_in_play(obs, ARCHALUDON_EX) <= 1
                )
            )
            has_urgent = (
                (DURALUDON in disc and DURALUDON not in ids and count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX) <= 1)
                or (ARCHALUDON_EX in disc and ARCHALUDON_EX not in ids and has_in_play(obs, DURALUDON))
                or (METAL_ENERGY in disc and not obs.current.energyAttached
                    and sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY) == 0
                    and any(p and p.id in (DURALUDON, ARCHALUDON_EX) and energy_count(p) == 2 for p in all_my_pokemon(obs)))
                or mirror_rebuild
            )
            if not has_urgent:
                return -500, "save Night Stretcher"
        if cid == ULTRA_BALL:
            bench_empty = len([p for p in my_state(obs).bench if p]) == 0
            if bench_empty:
                return 300, "Ultra Ball: bench empty (donk risk)"
            metal_in_hand = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)
            metal_in_trash = metal_in_discard(obs)
            if metal_in_trash == 0 and metal_in_hand >= 1:
                return 20000, "Ultra Ball: fuel Alloy"
            if safe_discard_count(obs) >= 2 and (need_archaludon(obs) or need_duraludon(obs)):
                return 20000, "Ultra Ball: search line"
            return -1000, "skip Ultra Ball"
        return 20000, "play item"

    if cid == EXPLORER:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        return 16000, "play Explorer"

    if cid == LILLIE:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if detect_matchup(obs) == "chandelure":
            dc = my_state(obs).deckCount
            if dc <= 8 and my_state(obs).handCount >= dc + 6:
                return 26000, "Chandelure: Lillie refills low deck"
        if detect_matchup(obs) == "chandelure" and my_state(obs).handCount >= 7:
            return 17500, "Chandelure: Lillie lowers Mind Ruler damage"
        if BOSS in ids and planned_archaludon_attacks(obs):
            return -500, "save Lillie: Boss in hand with attacker ready"
        return 5000, "play Lillie"

    if cid == BOSS:
        if obs.current.supporterPlayed:
            return -1000, "Supporter already used"
        if detect_matchup(obs) == "ogerpon":
            opp_act = opp_active_pokemon(obs)
            attacks = planned_archaludon_attacks(obs)
            if attacks and opp_act and opp_act.id == 117:
                if any(p.id != 117 for p in opp_bench_pokemon(obs)):
                    return 26000, "Boss: bypass Cornerstone Ogerpon"
        # vs Hop: Boss Snorlax to remove Extra Helpings (+30) ASAP
        if detect_matchup(obs) == "hop":
            active = active_pokemon(obs)
            opp_has_snorlax = any(p.id == HOP_SNORLAX for p in opp_bench_pokemon(obs))
            if opp_has_snorlax and active:
                # Case 1: Cinderace active + bench has Duraludon → Turbo Flare Snorlax
                if active.id == CINDERACE:
                    has_dura_bench = any(p.id in {DURALUDON, ARCHALUDON_EX}
                                        for p in my_state(obs).bench if p)
                    if has_dura_bench:
                        return 16500, "Boss: pull Snorlax (Cinderace Turbo Flare)"
                # Case 2: Archaludon active, HP > 220, can attack → Boss Snorlax
                if active.id == ARCHALUDON_EX and active.hp > 220:
                    ok, _ = attack_energy_route(obs, active)
                    if ok:
                        return 16500, "Boss: pull Snorlax (Arch can tank Revenge 220)"
        if detect_matchup(obs) == "archaludon":
            active = active_pokemon(obs)
            opp_act = opp_active_pokemon(obs)
            attacks = planned_archaludon_attacks(obs)
            can_ko_active = opp_act and any(
                effective_damage(atk["damage"], opp_act) >= opp_act.hp for atk in attacks)
            remaining = len(my_state(obs).prize)
            if active and attacks and not can_ko_active:
                lethal_bench = any(
                    prize_value(target) >= remaining
                    and any(effective_damage(atk["damage"], target) >= target.hp for atk in attacks)
                    for target in opp_bench_pokemon(obs)
                )
                relcanth_ko = any(
                    p.id == RELICANTH
                    and any(effective_damage(atk["damage"], p) >= p.hp for atk in attacks)
                    for p in opp_bench_pokemon(obs)
                )
                if relcanth_ko and not lethal_bench:
                    return 15500, "Boss: remove mirror Relicanth"
        if _opp_last_attack_id == MEGA_BRAVE:
            return -500, "save Boss: Mega Brave stuck"
        attacks = planned_archaludon_attacks(obs)
        if not attacks:
            return -500, "save Boss: no attacker"
        opp_act = opp_active_pokemon(obs)
        can_ko_active = opp_act and any(
            effective_damage(atk["damage"], opp_act) >= opp_act.hp for atk in attacks)
        remaining = len(my_state(obs).prize)
        if can_ko_active:
            if prize_value(opp_act) >= remaining:
                return -500, "save Boss: Active KO wins"
            for target in opp_bench_pokemon(obs):
                for atk in attacks:
                    if effective_damage(atk["damage"], target) >= target.hp:
                        if prize_value(target) >= remaining:
                            return 20000, "LETHAL Boss"
                        break
            return -500, "save Boss: can KO Active"
        best_score = -500
        best_reason = "save Boss"
        for target in opp_bench_pokemon(obs):
            for atk in attacks:
                if effective_damage(atk["damage"], target) >= target.hp:
                    pv = prize_value(target)
                    if pv >= remaining:
                        return 20000, "LETHAL Boss"
                    s = 4000 + pv * 200 + energy_count(target) * 100
                    if s > best_score:
                        best_score = s
                        best_reason = "Boss: pull bench target"
                    break
        if best_score <= 0:
            metal_total = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)
            metal_total += sum(energy_count(p) for p in all_my_pokemon(obs) if p)
            has_cind = has_in_play(obs, CINDERACE)
            draw_in_hand = any(c and c.id in (EXPLORER, LILLIE) for c in (my_state(obs).hand or []) if c)
            if metal_total <= 2 and not has_cind and not draw_in_hand:
                best_stall = -500
                stall_reason = "save Boss"
                for target in opp_bench_pokemon(obs):
                    te = energy_count(target)
                    cd = CARD_DB.get(target.id)
                    rc = cd.retreatCost if cd else 0
                    min_atk = 99
                    if cd and cd.attacks:
                        for aid in cd.attacks:
                            atk = ALL_ATTACKS.get(aid)
                            if atk:
                                min_atk = min(min_atk, len(atk.energies))
                    if min_atk == 99:
                        min_atk = 1
                    ss = 4000 + rc * 1000 + min_atk * 500 - te * 800
                    if ss > best_stall:
                        best_stall = ss
                        stall_reason = "Boss stall"
                return best_stall, stall_reason
        return best_score, best_reason

    return 1000, "generic play"


def score_evolve(obs, opt):
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = card.id if card else None
    tid = target.id if target else None
    if cid == ARCHALUDON and tid == DURALUDON:
        if final_prize_nonex_no_backup(obs):
            if target and energy_count(target) >= 3:
                return 32000, "Endgame: evolve ready non-ex Archaludon"
            return 24000, "Endgame: evolve non-ex prize wall"
        if detect_matchup(obs) == "ogerpon":
            if target and energy_count(target) >= 3:
                return 30000, "Ogerpon: evolve non-ex Archaludon ready"
            return 18000, "Ogerpon: evolve non-ex Archaludon"
        return -1000, "hold non-ex Archaludon outside Ogerpon"
    if cid == ARCHALUDON_EX and tid == DURALUDON:
        if final_prize_nonex_no_backup(obs):
            return -8000, "Endgame: avoid final-prize ex evolve"
        target_is_active = opt.inPlayArea == AreaType.ACTIVE
        mc = metal_in_discard(obs)
        if target_is_active:
            if (
                detect_matchup(obs) == "lucario"
                and target.hp <= 70
                and any(p and p.id == DURALUDON for p in my_state(obs).bench)
            ):
                return 6000, "Lucario: preserve low-HP active, evolve bench"
            if energy_count(target) >= 3 and not has_in_play(obs, ARCHALUDON_EX):
                return 17000, "evolve Active 3-energy Duraludon"
            if mc >= 2:
                return 28000 + mc * 2000, "evolve Active Duraludon"
            if mc == 1:
                return 8000, "delay Active evolve: 1 Metal"
            return -500, "hold: no Metal in discard"
        if mc >= 2:
            return 14000 + mc * 1000, "evolve Bench Duraludon"
        return -1000, "hold: evolve Active first"
    return 10000, "generic evolution"


def attach_target_score(obs, target, area):
    if target is None:
        return 0
    cid = target.id
    e = energy_count(target)

    if e >= 3:
        return -5000
    if cid == CINDERACE and e >= 1:
        return -3000

    score = 0
    if cid == CINDERACE:
        score = 3000
        if e == 0:
            score += 7000 + (12000 if area == AreaType.ACTIVE else 5000)
    elif cid in {DURALUDON, ARCHALUDON, ARCHALUDON_EX}:
        score = 6000 if cid == ARCHALUDON_EX else 5500
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            score += 5000
        score += {2: 12000, 1: 7000, 0: 4000}.get(e, -1000)
        score += 1000 if area == AreaType.ACTIVE else 500
    else:
        score = 1000 + (1000 if e == 0 else 0)

    # HP-based adjustment
    if target.hp > 0:
        max_hp = getattr(target, "maxHp", target.hp)
        ratio = target.hp / max_hp if max_hp > 0 else 1
        if ratio <= 0.25:
            score -= 1500
        elif ratio <= 0.50:
            score -= 500
        else:
            score += min(1000, target.hp // 40 * 100)
    return score


def score_attach(obs, opt):
    card = option_card(obs, opt)
    target = option_target(obs, opt)
    cid = card.id if card else None
    tid = target.id if target else None

    if cid == HERO_CAPE:
        if tid == ARCHALUDON_EX and target and not has_tool(target):
            return 11000, "Hero's Cape on Archaludon ex"
        if tid == DURALUDON and target and not has_tool(target) and energy_count(target) >= 1:
            return 8000, "Hero's Cape on Duraludon"
        return -1000, "save Hero's Cape"

    if cid != METAL_ENERGY:
        return -500, "skip non-Metal"
    if obs.current.energyAttached:
        return -1000, "already attached"

    return attach_target_score(obs, target, opt.inPlayArea), "attach Metal"


def score_retreat(obs, opt):
    active = active_pokemon(obs)
    if active and active.id == ARCHALUDON_EX and has_tool(active) and active.hp > 200:
        return -5000, "don't retreat HP400 tank"
    route = archaludon_ex_attack_route(obs)
    if route and route["needs_retreat"]:
        return 13000, "retreat to attack-ready ex"
    return -100, "avoid retreat"


_MAIN_DISPATCH = {
    OptionType.PLAY: score_play, OptionType.EVOLVE: score_evolve,
    OptionType.ATTACH: score_attach, OptionType.RETREAT: score_retreat,
}


def score_option(obs, opt):
    ctx = obs.select.context

    if ctx in {SelectContext.IS_FIRST, SelectContext.MULLIGAN,
               SelectContext.SETUP_ACTIVE_POKEMON, SelectContext.SETUP_BENCH_POKEMON}:
        return score_setup(obs, opt)

    if opt.type in {OptionType.YES, OptionType.NO}:
        if ctx == SelectContext.IS_FIRST:
            return score_setup(obs, opt)
        if ctx == SelectContext.ACTIVATE:
            return (100000, "Explosiveness") if opt.type == OptionType.YES else (-100000, "never decline")
        return (1, "yes") if opt.type == OptionType.YES else (0, "no")

    if opt.type == OptionType.NUMBER:
        return (opt.number or 0), "number"

    if ctx == SelectContext.MAIN:
        fn = _MAIN_DISPATCH.get(opt.type)
        if fn:
            score, reason = fn(obs, opt)
        elif opt.type == OptionType.ABILITY:
            score, reason = 1, "ability"
        elif opt.type == OptionType.ATTACK:
            score, reason = best_attack_damage(obs, opt.attackId), "attack"
        elif opt.type == OptionType.END:
            score, reason = 0, "end turn"
        else:
            score, reason = 500, "generic MAIN"
    elif ctx == SelectContext.TO_HAND:
        score, reason = score_to_hand(obs, opt)
    elif ctx in {SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD}:
        score, reason = score_discard(obs, opt)
    elif ctx in {SelectContext.ATTACH_TO, SelectContext.TO_FIELD, SelectContext.TO_BENCH,
                 SelectContext.ATTACH_FROM, SelectContext.SWITCH, SelectContext.TO_ACTIVE,
                 SelectContext.HEAL, SelectContext.DAMAGE}:
        score, reason = score_target(obs, opt)
    elif ctx == SelectContext.ATTACK:
        score, reason = best_attack_damage(obs, opt.attackId), "attack"
    elif opt.type == OptionType.CARD:
        score, reason = score_to_hand(obs, opt)
    elif opt.type == OptionType.ENERGY:
        score, reason = 1000, "energy"
    elif opt.type == OptionType.END:
        score, reason = 0, "end"
    else:
        score, reason = 100, "fallback"

    return apply_overrides(obs, opt, score, reason)


def score_to_hand(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

    if effect_id == EXPLORER:
        has_ready = any(p and p.id in (DURALUDON, ARCHALUDON_EX) and energy_count(p) >= 3
                        for p in all_my_pokemon(obs))
        metal_in_hand = sum(1 for c in (my_state(obs).hand or []) if c and c.id == METAL_ENERGY)

        if cid == HERO_CAPE:
            has_target = any(p.id == ARCHALUDON_EX and not has_tool(p) for p in all_my_pokemon(obs))
            return (27000 if has_target else 22000), "Explorer: Hero's Cape"
        if cid == METAL_ENERGY:
            if has_ready or metal_in_hand > 0:
                return 0, "Explorer: skip energy"
            if getattr(opt, 'index', 0) == _first_option_index(obs, METAL_ENERGY):
                return 25000, "Explorer: take 1st energy"
            return 0, "Explorer: skip 2nd energy"
        if cid == ARCHALUDON_EX and need_archaludon(obs):
            return 20000, "Explorer: take Archaludon ex"
        if cid == ARCHALUDON and need_nonex_archaludon(obs):
            return 19000, "Explorer: take non-ex Archaludon"
        if cid == DURALUDON and need_duraludon(obs):
            return 18000, "Explorer: take Duraludon"
        if cid == RELICANTH and not has_in_play(obs, RELICANTH) and RELICANTH not in ids:
            return 15000, "Explorer: take Relicanth"
        sup_count = sum(1 for c in (my_state(obs).hand or []) if c and c.id in (EXPLORER, LILLIE))
        if cid in (EXPLORER, LILLIE) and sup_count == 0:
            return 12000, "Explorer: take supporter"
        return 0, "Explorer: let discard"

    if effect_id == NIGHT_STRETCHER and detect_matchup(obs) == "archaludon":
        line_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
        if cid == ARCHALUDON_EX and has_in_play(obs, DURALUDON) and count_in_play(obs, ARCHALUDON_EX) <= 1:
            return 24000, "Stretcher mirror: take Archaludon ex"
        if cid == DURALUDON and DURALUDON not in ids and line_count <= 2:
            return 23000, "Stretcher mirror: take Duraludon"
        if cid == METAL_ENERGY:
            return 9000, "Stretcher mirror: take Metal fallback"

    dura_ex_count = count_in_play(obs, DURALUDON) + count_in_play(obs, ARCHALUDON_EX)
    if cid == DURALUDON and DURALUDON not in ids and dura_ex_count <= 1:
        return 22000, "take Duraludon: backup"
    if cid == ARCHALUDON and need_nonex_archaludon(obs):
        return 21000, "take non-ex Archaludon"
    if cid == ARCHALUDON_EX and need_archaludon(obs):
        return 20000, "take Archaludon ex"
    if cid == DURALUDON and need_duraludon(obs):
        return 18000, "take Duraludon"
    if cid == CINDERACE:
        return -2000, "skip Cinderace"
    if cid == RELICANTH and not has_in_play(obs, RELICANTH):
        return 9000, "take Relicanth"
    if cid == METAL_ENERGY:
        return 8000, "take Metal Energy"
    if cid == EXPLORER and not obs.current.supporterPlayed:
        return 7500, "take Explorer"
    if cid == LILLIE and not obs.current.supporterPlayed:
        return 6500, "take Lillie"
    if cid == HERO_CAPE:
        has_target = any(p.id == ARCHALUDON_EX and not has_tool(p) for p in all_my_pokemon(obs))
        return (6000, "take Hero's Cape") if has_target else (1000, "generic take")
    if cid == FULL_METAL_LAB:
        return 5000, "take Full Metal Lab"
    if cid == BOSS:
        return 2500, "take Boss"
    return 1000, "generic take"


def score_discard(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ids = hand_ids(obs)
    mt = metal_in_discard(obs)
    effect = getattr(obs.select, "effect", None)
    effect_id = effect.id if effect else None

    if effect_id == ULTRA_BALL:
        mh = ids.count(METAL_ENERGY)
        if cid == METAL_ENERGY:
            if mt < 2 and mh >= 1:
                if getattr(opt, 'index', None) == _first_option_index(obs, METAL_ENERGY):
                    return 20000, "UB: 1st Metal"
                return 8000, "UB: 2nd Metal"
            return 8000, "UB: Metal"
        if cid == CINDERACE:
            return (18000, "UB: Cinderace") if (mt >= 2 or mh == 0) else (14000, "UB: Cinderace")
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            return -5000, "UB: keep non-ex Archaludon"
        draw_count = ids.count(LILLIE) + ids.count(EXPLORER)
        if cid in (LILLIE, EXPLORER) and draw_count >= 2:
            return (12000 if cid == LILLIE else 11000), "UB: surplus supporter"
        if cid == ULTRA_BALL and ids.count(ULTRA_BALL) > 1:
            return 10000, "UB: duplicate"
        if cid in (LILLIE, EXPLORER) and draw_count <= 1:
            return -3000, "UB: keep last supporter"

    if cid == METAL_ENERGY:
        if mt < 2:
            return 15000, "discard Metal"
        return (12000, "discard extra Metal") if ids.count(METAL_ENERGY) > 1 else (-1000, "keep last Metal")
    if cid == CINDERACE:
        return 10000, "discard Cinderace"
    if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
        return -5000, "keep non-ex Archaludon"
    if cid in {BOSS, FULL_METAL_LAB, POKEGEAR}:
        return 8500, "discard utility"
    if cid in {LILLIE, EXPLORER} and ids.count(cid) > 1:
        return 8000, "discard duplicate supporter"
    if cid == RELICANTH and (has_in_play(obs, RELICANTH) or ids.count(RELICANTH) > 1):
        return 6500, "discard extra Relicanth"
    if cid == ARCHALUDON_EX:
        return -5000, "keep Archaludon ex"
    if cid == DURALUDON:
        return -4000, "keep Duraludon"
    return 1000, "generic discard"


def score_target(obs, opt):
    card = option_card(obs, opt)
    cid = card.id if card else opt.cardId
    ctx = obs.select.context

    if ctx == SelectContext.ATTACH_TO:
        return (5000, "Metal") if cid == METAL_ENERGY else (1000, "attach")

    if ctx == SelectContext.ATTACH_FROM:
        if card and energy_count(card) >= 3:
            return -5000, "skip: 3+ energy"
        if card and cid == CINDERACE and energy_count(card) >= 1:
            return -3000, "skip: Cinderace ready"
        return attach_target_score(obs, card, opt.area), "effect attach"

    if ctx in {SelectContext.TO_FIELD, SelectContext.TO_BENCH}:
        if cid == ARCHALUDON and detect_matchup(obs) == "ogerpon":
            return 20000, "target non-ex Archaludon"
        if cid == ARCHALUDON_EX:
            return 18000, "target Archaludon ex"
        if cid == DURALUDON:
            return 16000, "target Duraludon"
        if cid == CINDERACE:
            return 3000, "avoid Cinderace"

    if ctx == SelectContext.HEAL:
        return (20000 + damage_on(card), "heal Archaludon ex") if cid == ARCHALUDON_EX else (damage_on(card), "heal")

    if ctx in {SelectContext.SWITCH, SelectContext.TO_ACTIVE}:
        yi = obs.current.yourIndex
        pi = getattr(opt, 'playerIndex', yi)
        if pi != yi and card:
            if detect_matchup(obs) == "archaludon" and cid == RELICANTH:
                killable = any(effective_damage(a["damage"], card) >= card.hp
                               for a in planned_archaludon_attacks(obs))
                if killable:
                    return 22500 + energy_count(card) * 100, "Boss: mirror Relicanth"
            if detect_matchup(obs) == "ogerpon":
                if cid == 117:
                    return -2000, "Boss: avoid Cornerstone blocker"
                priority = {
                    1051: 36000,
                    112: 34000,
                    675: 33000,
                    676: 33000,
                    116: 32000,
                    1052: 30000,
                }.get(cid, 22000)
                return priority - card.hp + energy_count(card) * 300, "Boss: Ogerpon non-blocker"
            # vs Hop: prioritize Snorlax (remove Extra Helpings)
            if detect_matchup(obs) == "hop" and cid == HOP_SNORLAX and card:
                active = active_pokemon(obs)
                e = energy_count(card)
                tools = len(getattr(card, 'tools', None) or [])
                if active and active.id == CINDERACE:
                    # Cinderace: pull the least mobile Snorlax (low energy, no tools, high HP)
                    return 30000 - e * 100 - tools * 50 + card.hp, "Boss: Snorlax (immobile target)"
                else:
                    # Archaludon: pull the most threatening Snorlax (high energy, tools, high HP)
                    return 30000 + e * 100 + tools * 50 + card.hp, "Boss: Snorlax (biggest threat)"
            pv = prize_value(card)
            te = energy_count(card)
            killable = any(effective_damage(a["damage"], card) >= card.hp
                           for a in planned_archaludon_attacks(obs))
            if killable:
                return 20000 + pv * 3000 + te * 100, "Boss: KO"
            return 5000 + pv * 1000 + te * 200, "Boss: drag"
        if cid == CINDERACE:
            return 16000, "promote Cinderace (retreat 0)"
        if cid == ARCHALUDON:
            return 15500, "promote non-ex Archaludon"
        if cid == ARCHALUDON_EX:
            return 15000, "promote Archaludon ex"
        if cid == DURALUDON:
            return 8000, "promote Duraludon"
        return 1000, "generic promote"

    if ctx == SelectContext.DAMAGE:
        hp = getattr(card, "hp", 999) if card else 999
        return 10000 - hp, "damage: lowest HP"

    return 1000, "generic target"


# ── Choose & Agent ──

def _choose_options_exact_parent(obs):
    scored = []
    for i, opt in enumerate(obs.select.option):
        try:
            score, reason = score_option(obs, opt)
        except Exception as e:
            score, reason = -999999, f"error {type(e).__name__}: {e}"
        scored.append((score, i, reason))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    selected = []
    for score, i, reason in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(i)

    if len(selected) < obs.select.minCount:
        selected = [i for _, i, _ in scored[:obs.select.minCount]]

    return selected


def _discard_semantic_groups(obs):
    """Return semantic hand-card options, collapsing exact duplicate encodings."""
    if obs.select.context != SelectContext.DISCARD:
        raise ValueError("not a discard callback")
    yi = obs.current.yourIndex
    groups = {}
    for position, option in enumerate(obs.select.option or ()):
        if (
            option.type != OptionType.CARD
            or option.area != AreaType.HAND
            or getattr(option, "playerIndex", yi) not in (None, yi)
            or not isinstance(option.index, int)
        ):
            raise ValueError("non-hand option in mandatory discard")
        card = option_card(obs, option)
        if not _valid_own_card(card, yi):
            raise ValueError("malformed discard option card")
        semantic = _card_semantic(card)
        groups.setdefault(semantic, []).append(position)
    hand_semantics = {
        _card_semantic(card) for card in my_state(obs).hand or ()
    }
    if set(groups) != hand_semantics:
        raise ValueError("discard option/hand mismatch")
    return groups


def _boss_guard_action_semantics(obs, action):
    result = []
    for position in action:
        option = obs.select.option[position]
        card = option_card(obs, option)
        target = option_target(obs, option)
        result.append(
            {
                "type": int(option.type),
                "card_id": getattr(card, "id", None),
                "serial": getattr(card, "serial", None),
                "target_id": getattr(target, "id", None),
                "target_serial": getattr(target, "serial", None),
                "attack_id": getattr(option, "attackId", None),
            }
        )
    return result


def _normalized_parent_discard_semantics(obs, groups):
    """Exact parent scoring over the unique semantic option universe."""
    scored = []
    for semantic, positions in groups.items():
        position = min(positions)
        option = obs.select.option[position]
        try:
            score, _ = score_option(obs, option)
        except Exception:
            score = -999999
        scored.append((score, position, semantic))
    scored.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    selected = []
    for score, _, semantic in scored:
        if len(selected) >= obs.select.maxCount:
            break
        if score < 0 and len(selected) >= obs.select.minCount:
            continue
        selected.append(semantic)
    if len(selected) < obs.select.minCount:
        selected = [row[2] for row in scored[:obs.select.minCount]]
    return selected


def _ultra_ball_text_is_exact():
    data = CARD_DB.get(ULTRA_BALL)
    if data is None or getattr(data, "name", None) != "Ultra Ball":
        return False
    skills = getattr(data, "skills", None) or ()
    return (
        len(skills) == 1
        and getattr(skills[0], "name", None) == "Ultra Ball"
        and getattr(skills[0], "text", None) == _ULTRA_BALL_PUBLIC_TEXT
    )


def _validate_public_board_for_guard(obs):
    """Validate public cards needed by the plan-equivalence certificate."""
    if len(obs.current.stadium or ()) > 1:
        return False
    seen = set()
    for player in obs.current.players:
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                return False
            semantic = _card_semantic(pokemon)
            if semantic is None or semantic[1] <= 0 or semantic[0] not in CARD_DB:
                return False
            owner_key = (getattr(pokemon, "playerIndex", None), semantic[1])
            if owner_key in seen:
                return False
            seen.add(owner_key)
            if (
                not isinstance(getattr(pokemon, "hp", None), int)
                or not isinstance(getattr(pokemon, "maxHp", None), int)
                or pokemon.hp <= 0
                or pokemon.maxHp <= 0
                or pokemon.hp > pokemon.maxHp
            ):
                return False
            for field in ("energyCards", "tools", "preEvolution"):
                for card in getattr(pokemon, field, None) or ():
                    item = _card_semantic(card)
                    if item is None or item[1] <= 0 or item[0] not in CARD_DB:
                        return False
                    card_owner_key = (
                        getattr(card, "playerIndex", None),
                        item[1],
                    )
                    if card_owner_key in seen:
                        return False
                    seen.add(card_owner_key)
    for card in obs.current.stadium or ():
        semantic = _card_semantic(card)
        if semantic is None or semantic[1] <= 0 or semantic[0] not in CARD_DB:
            return False
    return True


def _certified_current_attack_prefix(obs):
    active = active_pokemon(obs)
    if active is None:
        return None
    if (
        active.id == ARCHALUDON_EX
        and sum(
            1
            for card in getattr(active, "energyCards", None) or ()
            if card is not None and card.id == METAL_ENERGY
        )
        >= 3
    ):
        return {
            "attacker": _card_semantic(active),
            "attack_id": METAL_DEFENDER,
            "damage": 220,
        }
    if active.id == CINDERACE and energy_count(active) >= 1:
        return {
            "attacker": _card_semantic(active),
            "attack_id": 965,
            "damage": 50,
        }
    return None


def _positive_public_boss_target(obs, attack_prefix):
    """Require a visible Bench Prize route that beats the visible Active route."""
    opponent = opp_state(obs)
    if not opponent.active or opponent.active[0] is None:
        return False
    active_target = opponent.active[0]
    bench = [pokemon for pokemon in opponent.bench or () if pokemon is not None]
    if not bench:
        return False
    damage = attack_prefix["damage"]
    if not isinstance(damage, int) or damage <= 0:
        return False
    active_value = (
        prize_value(active_target)
        if effective_damage(damage, active_target) >= active_target.hp
        else 0
    )
    return any(
        effective_damage(damage, target) >= target.hp
        and prize_value(target) > active_value
        for target in bench
    )


def _boss_access_certificate(snapshot):
    if _PUBLIC_LEDGER_DECK_COUNTS.get(BOSS) != 4:
        return None
    rows = [
        (serial, row)
        for serial, row in _public_boss_ledger["cards"].items()
        if row["id"] == BOSS
    ]
    held = [serial for serial, row in rows if row["zone"] == "HAND"]
    discarded = [
        serial for serial, row in rows if row["zone"] == "PUBLIC_DISCARD"
    ]
    lost = [serial for serial, row in rows if row["zone"] == "PUBLIC_LOST"]
    revealed = [
        serial for serial, row in rows if row["zone"] == "CURRENT_REVEAL"
    ]
    unknown = [
        serial for serial, row in rows if row["zone"] == "UNKNOWN_HIDDEN"
    ]
    physical_boss = {
        serial: row
        for serial, row in snapshot["physical"].items()
        if row["id"] == BOSS
    }
    if (
        len(rows) != 4
        or len(held) != 1
        or len(discarded) != 3
        or lost
        or revealed
        or unknown
        or len(physical_boss) != 4
        or set(physical_boss) != set(held + discarded)
    ):
        return None
    return {
        "held": held[0],
        "discarded": sorted(discarded),
        "held_access_before": 1,
        "held_access_after": 1,
    }


def _plan_equivalent_archaludon_certificate(obs, groups, parent_semantics):
    """Prove the frozen current-plan identity without hidden-zone inference."""
    if len(parent_semantics) != 2:
        return None
    boss_rows = [row for row in parent_semantics if row[0] == BOSS]
    metal_rows = [row for row in parent_semantics if row[0] == METAL_ENERGY]
    if len(boss_rows) != 1 or len(metal_rows) != 1:
        return None
    boss_semantic = boss_rows[0]
    metal_semantic = metal_rows[0]

    nonex = [semantic for semantic in groups if semantic[0] == ARCHALUDON]
    bridges = [semantic for semantic in groups if semantic[0] == ARCHALUDON_EX]
    if len(nonex) != 1 or len(bridges) < 1:
        return None
    replacement = nonex[0]
    if replacement in parent_semantics or any(
        bridge in parent_semantics for bridge in bridges
    ):
        return None

    mine = my_state(obs)
    active = active_pokemon(obs)
    attack_prefix = _certified_current_attack_prefix(obs)
    if active is None or attack_prefix is None:
        return None
    if any(
        pokemon is not None and pokemon.id in {DURALUDON, ARCHALUDON}
        for pokemon in list(mine.active or ()) + list(mine.bench or ())
    ):
        return None
    if len(mine.bench or ()) >= mine.benchMax or mine.deckCount <= 0:
        return None

    opponent_active = opp_active_pokemon(obs)
    opponent_data = CARD_DB.get(opponent_active.id) if opponent_active else None
    if opponent_data is None or getattr(opponent_data, "basic", False):
        return None
    if not _positive_public_boss_target(obs, attack_prefix):
        return None
    if len(mine.prize or ()) <= 1:
        return None
    return {
        "boss": boss_semantic,
        "metal": metal_semantic,
        "replacement": replacement,
        "bridge": bridges[0],
        "attacker": attack_prefix["attacker"],
        "attack_id": attack_prefix["attack_id"],
        "bench_capacity": mine.benchMax - len(mine.bench or ()),
        "deck_count": mine.deckCount,
    }


def _propose_public_boss_guard(obs, parent_action, snapshot):
    select = obs.select
    effect = getattr(select, "effect", None)
    if (
        select.context != SelectContext.DISCARD
        or select.minCount != 2
        or select.maxCount != 2
        or effect is None
        or effect.id != ULTRA_BALL
        or getattr(effect, "playerIndex", None) != obs.current.yourIndex
        or not _ultra_ball_text_is_exact()
        or obs.current.supporterPlayed is not True
        or not _validate_public_board_for_guard(obs)
    ):
        return None, "CONTEXT_OR_PUBLIC_BOARD_GATE_INELIGIBLE"

    groups = _discard_semantic_groups(obs)
    parent_semantics = _normalized_parent_discard_semantics(obs, groups)
    if len(groups) == len(obs.select.option):
        actual_parent_semantics = [
            _card_semantic(option_card(obs, obs.select.option[position]))
            for position in parent_action
        ]
        if actual_parent_semantics != parent_semantics:
            raise ValueError("exact-parent semantic mismatch")

    access = _boss_access_certificate(snapshot)
    if access is None:
        return None, "FOUR_COPY_PUBLIC_BOSS_ACCESS_CERTIFICATE_INELIGIBLE"
    plan = _plan_equivalent_archaludon_certificate(
        obs, groups, parent_semantics
    )
    if plan is None or plan["boss"][1] != access["held"]:
        return None, "PLAN_EQUIVALENCE_OR_PUBLIC_TARGET_GATE_INELIGIBLE"

    replacement_positions = groups.get(plan["replacement"], ())
    metal_positions = groups.get(plan["metal"], ())
    if not replacement_positions or not metal_positions:
        return None, "SEMANTIC_ALTERNATE_BINDING_INELIGIBLE"
    action = [min(replacement_positions), min(metal_positions)]
    if len(set(action)) != 2:
        return None, "SEMANTIC_ALTERNATE_BINDING_INELIGIBLE"
    return (action, plan, access), None


def _choose_options_with_public_boss_guard(obs, parent_action):
    try:
        parent_semantics = _boss_guard_action_semantics(obs, parent_action)
        snapshot, fingerprint, ready, duplicate = _observe_public_ledger(obs)
        if duplicate:
            cached = _public_boss_ledger.get("last_action")
            if cached is None:
                raise ValueError("duplicate callback without cached action")
            return list(cached)
        if not ready or snapshot is None:
            _set_boss_guard_resolution(
                obs,
                owner="EXACT_HISTORICAL_SILVER",
                suppression_reason="LEDGER_RESET_OR_NOT_READY",
                parent_semantics=parent_semantics,
                final_semantics=parent_semantics,
                fail_closed_reason=_public_boss_ledger.get(
                    "last_reset_reason"
                ),
            )
            return parent_action

        confirmed_now = (
            _public_boss_ledger.get("transaction") is None
            and bool(_public_boss_ledger["events"])
            and _public_boss_ledger["events"][-1].get("kind")
            == "TRANSACTION_CONFIRMED"
            and _public_boss_ledger["events"][-1].get("turn")
            == obs.current.turn
            and _public_boss_ledger["events"][-1].get("action_count")
            == obs.current.turnActionCount
        )
        if confirmed_now:
            action = list(parent_action)
            _public_boss_ledger["last_action"] = action
            _public_boss_ledger["last_action_semantics"] = [
                _option_signature(obs, position, obs.select.option[position])
                for position in action
            ]
            _set_boss_guard_resolution(
                obs,
                owner="EXACT_HISTORICAL_SILVER",
                suppression_reason=(
                    "POST_EMISSION_CONFIRMED_CLEAR_AND_DELEGATE"
                ),
                parent_semantics=parent_semantics,
                final_semantics=parent_semantics,
            )
            return action

        proposal, suppression_reason = _propose_public_boss_guard(
            obs, parent_action, snapshot
        )
        if proposal is None:
            action = list(parent_action)
            _public_boss_ledger["last_action"] = action
            _public_boss_ledger["last_action_semantics"] = [
                _option_signature(obs, position, obs.select.option[position])
                for position in action
            ]
            _set_boss_guard_resolution(
                obs,
                owner="EXACT_HISTORICAL_SILVER",
                suppression_reason=suppression_reason,
                parent_semantics=parent_semantics,
                final_semantics=parent_semantics,
            )
            return action

        action, plan, access = proposal
        _public_boss_ledger["transaction"] = {
            "stage": "AWAIT_EXACT_DISCARD_CONFIRMATION",
            "boss": plan["boss"],
            "replacement": plan["replacement"],
            "metal": plan["metal"],
            "source_fingerprint": fingerprint,
            "source_turn": obs.current.turn,
            "source_action_count": obs.current.turnActionCount,
        }
        _public_boss_ledger["last_action"] = list(action)
        _public_boss_ledger["last_action_semantics"] = [
            plan["replacement"],
            plan["metal"],
        ]
        _ledger_event(
            "GUARD_EMITTED",
            turn=obs.current.turn,
            action_count=obs.current.turnActionCount,
            boss=list(plan["boss"]),
            replacement=list(plan["replacement"]),
            metal=list(plan["metal"]),
            bridge=list(plan["bridge"]),
            attacker=list(plan["attacker"]),
            attack_id=plan["attack_id"],
            bench_capacity=plan["bench_capacity"],
            deck_count=plan["deck_count"],
            public_discarded_boss_serials=access["discarded"],
            held_access_before=access["held_access_before"],
            held_access_after=access["held_access_after"],
        )
        final_semantics = _boss_guard_action_semantics(obs, action)
        _set_boss_guard_resolution(
            obs,
            owner=PUBLIC_BOSS_LEDGER_RULE_ID,
            suppression_reason=None,
            parent_semantics=parent_semantics,
            final_semantics=final_semantics,
            proposal=True,
        )
        return action
    except ValueError as error:
        reason = "fail_closed:" + str(error)
        _reset_public_boss_ledger(reason)
        _set_boss_guard_resolution(
            obs,
            owner="EXACT_HISTORICAL_SILVER",
            suppression_reason="FAIL_CLOSED_EXACT_PARENT",
            parent_semantics=(
                locals().get("parent_semantics")
                or _boss_guard_action_semantics(obs, parent_action)
            ),
            final_semantics=(
                locals().get("parent_semantics")
                or _boss_guard_action_semantics(obs, parent_action)
            ),
            fail_closed_reason=reason,
        )
        return parent_action
    except Exception as error:
        reason = "guard_exception:" + type(error).__name__
        _reset_public_boss_ledger(reason)
        _set_boss_guard_resolution(
            obs,
            owner="EXACT_HISTORICAL_SILVER",
            suppression_reason="FAIL_CLOSED_EXACT_PARENT",
            parent_semantics=locals().get("parent_semantics"),
            final_semantics=locals().get("parent_semantics"),
            fail_closed_reason=reason,
        )
        return parent_action


def choose_options(obs):
    parent_action = _choose_options_exact_parent(obs)
    return _choose_options_with_public_boss_guard(obs, parent_action)


def agent(obs_dict):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        global _opp_last_attack_id, _cur_turn_logs
        _opp_last_attack_id = None
        _cur_turn_logs.clear()
        _reset_public_boss_ledger("deck_request")
        return read_deck_csv()
    _update_opp_attack_tracking(obs)
    if not obs.select.option:
        return []
    try:
        return choose_options(obs)
    except Exception:
        _reset_public_boss_ledger("emergency_fallback")
        _set_boss_guard_resolution(
            obs,
            owner="EXACT_HISTORICAL_SILVER_EMERGENCY_FALLBACK",
            suppression_reason="EMERGENCY_FALLBACK",
            parent_semantics=None,
            final_semantics=None,
            fail_closed_reason="emergency_fallback",
        )
        return random.sample(list(range(len(obs.select.option))), obs.select.maxCount)
