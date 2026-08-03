"""Build deterministic seven-day matchup and action-history evidence.

This is an observational replay analysis.  It does not create policy labels,
train a model, or modify any agent.  Public Daily Top episodes are a selected,
dependent sample; every reported rate is descriptive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import statistics
import subprocess
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path


DATES = tuple(f"2026-07-{day:02d}" for day in range(19, 26))
SOURCE_POPULATION = "daily_top50_avg_score_2026-07-19_to_2026-07-25"
CANDIDATES = (
    "rocket_mewtwo_spidops",
    "alakazam_psychic",
    "kangaskhan_crustle",
    "marnie_grimmsnarl",
)
MAJOR_MATCHUPS = (
    "marnie_grimmsnarl",
    "alakazam_psychic",
    "cynthia_garchomp",
    "rocket_mewtwo_spidops",
    "kangaskhan_crustle",
)
SELECTED_ALAKAZAM_HASH = (
    "4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69"
)


ARCHETYPE_MARKERS: tuple[tuple[str, frozenset[int]], ...] = (
    ("marnie_grimmsnarl", frozenset({646, 647, 648, 1259})),
    ("starmie_froslass", frozenset({1030, 1031, 860, 861})),
    ("archaludon_metal", frozenset({169, 190, 666, 1244})),
    ("kangaskhan_crustle", frozenset({756})),
    ("great_tusk_crustle", frozenset({58})),
    ("mega_abomasnow_kyogre", frozenset({721, 722, 723})),
    ("mega_lucario", frozenset({677, 678})),
    ("hop_trevenant", frozenset({288, 289, 299, 304, 307, 308, 309, 310, 878, 879})),
    ("chandelure_psychic_control", frozenset({97, 98, 164, 494})),
    ("alakazam_psychic", frozenset({245, 743})),
    ("rocket_mewtwo_spidops", frozenset({400, 401, 431, 434})),
    ("okidogi_barbaracle", frozenset({116, 675, 676, 1051, 1052})),
    ("iono_bellibolt", frozenset({265, 266, 268, 269, 270, 271})),
    ("ogerpon_toolbox", frozenset({95, 96, 99, 108, 117, 349, 358, 370, 386})),
    ("dragapult", frozenset({120, 121})),
    ("cynthia_garchomp", frozenset({341, 342, 379, 380, 381})),
    ("gardevoir", frozenset({747})),
    ("charizard", frozenset({790, 928})),
)
SPECIAL_RULES: tuple[tuple[str, str, frozenset[int]], ...] = (
    ("KANGASKHAN_PRIORITY", "kangaskhan_crustle", frozenset({756})),
    ("GREAT_TUSK_PRIORITY", "great_tusk_crustle", frozenset({58})),
    ("OGERPON_CLEFAIRY_CRUSTLE_REQUIRED", "teal_ogerpon_clefairy_crustle", frozenset({96, 272, 344, 345})),
    ("MUNKIDORI_CRUSTLE_REQUIRED", "crustle_munkidori_control", frozenset({112, 344, 345})),
    ("CUBCHOO_ARTICUNO_REQUIRED", "cubchoo_articuno_control", frozenset({414, 506})),
    ("CRUSTLE_REQUIRED", "crustle_control", frozenset({344, 345})),
)
FESTIVAL_RULE = ("FESTIVAL_FULL_DECK_IDS_90_93_1245", "festival_lead_dipplin", frozenset({90, 93, 1245}))

ENRICHED_FIELDS = [
    "date", "episode_id", "file", "player_index", "team", "team_id", "reward",
    "archetype", "archetype_classification_basis", "classification_rule_id",
    "classification_evidence_card_ids", "classification_notes", "deck", "deck_hash",
    "deck_signature", "leaderboard_rank", "daily_episode_rank", "daily_avg_score",
    "opponent_team", "opponent_team_id", "opponent_archetype", "opponent_deck_hash",
    "starting_order", "first_or_second_known", "source_population",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def as_int(value: Any, default: int | None = None) -> int | None:
    try:
        if isinstance(value, bool):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def deck_signature(cards: Sequence[int]) -> str:
    counts = Counter(cards)
    return ";".join(f"{card_id}:{counts[card_id]}" for card_id in sorted(counts))


def deck_hash(cards: Sequence[int]) -> str:
    payload = " ".join(str(card_id) for card_id in sorted(cards)) + "\n"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def classify_deck(cards: Sequence[int]) -> dict[str, str]:
    ids = set(cards)
    matches: list[tuple[int, int, str, str, set[int]]] = []
    for priority, (rule_id, archetype, required) in enumerate(SPECIAL_RULES):
        if required.issubset(ids):
            matches.append((1000, -priority, rule_id, archetype, set(required)))
    marker_hits: list[tuple[int, int, str, str, set[int]]] = []
    for order, (archetype, markers) in enumerate(ARCHETYPE_MARKERS):
        evidence = ids & set(markers)
        if evidence:
            marker_hits.append((len(evidence), -order, f"MARKER_{archetype.upper()}", archetype, evidence))
    if marker_hits:
        top_hit = max(row[0] for row in marker_hits)
        matches.extend(row for row in marker_hits if row[0] == top_hit)
    if not matches and FESTIVAL_RULE[2].issubset(ids):
        rule_id, archetype, evidence = FESTIVAL_RULE
        return {
            "archetype": archetype,
            "archetype_classification_basis": "FULL_DECK_REFINED",
            "classification_rule_id": rule_id,
            "classification_evidence_card_ids": " ".join(map(str, sorted(evidence))),
            "classification_notes": "Previously extractor-unknown; refined only from complete 60-card marker conjunction.",
        }
    if not matches:
        return {
            "archetype": "unknown",
            "archetype_classification_basis": "UNKNOWN",
            "classification_rule_id": "",
            "classification_evidence_card_ids": "",
            "classification_notes": "No checked classification rule matched.",
        }
    selected = sorted(matches, reverse=True)[0]
    selected_rule, selected_archetype, evidence = selected[2], selected[3], selected[4]
    distinct_rules = {(row[2], row[3]) for row in matches}
    ambiguous = len(distinct_rules) > 1
    return {
        "archetype": selected_archetype,
        "archetype_classification_basis": "AMBIGUOUS" if ambiguous else "EXACT_MARKER",
        "classification_rule_id": selected_rule,
        "classification_evidence_card_ids": " ".join(map(str, sorted(evidence))),
        "classification_notes": (
            "Multiple rules matched; deterministic checked priority selected "
            + selected_rule
            + "; matches="
            + "|".join(f"{rule}:{arch}" for rule, arch in sorted(distinct_rules))
            if ambiguous
            else "Single highest-priority checked rule matched."
        ),
    }


def build_leaderboard_aliases(rows: Sequence[Mapping[str, str]]) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    by_alias: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        aliases = {row.get("TeamName", "").strip()}
        aliases.update(part.strip() for part in row.get("TeamMemberUserNames", "").split(","))
        for alias in aliases:
            if alias:
                by_alias[alias].append(dict(row))
    resolved: dict[str, dict[str, str]] = {}
    ambiguous: dict[str, list[str]] = {}
    for alias, candidates in by_alias.items():
        team_ids = {row["TeamId"] for row in candidates}
        if len(team_ids) == 1:
            resolved[alias] = sorted(candidates, key=lambda row: int(row["Rank"]))[0]
        else:
            ambiguous[alias] = sorted(team_ids)
    return resolved, ambiguous


def find_first_player(doc: Mapping[str, Any]) -> int | None:
    for step in items(doc.get("steps")):
        for record in items(step):
            observation = record.get("observation") if isinstance(record, Mapping) else None
            current = observation.get("current") if isinstance(observation, Mapping) else None
            first = as_int(current.get("firstPlayer")) if isinstance(current, Mapping) else None
            if first in (0, 1):
                return first
    return None


def own_turn_number(global_turn: int | None, seat: int, first_player: int | None) -> int | None:
    if global_turn is None or global_turn <= 0 or first_player not in (0, 1):
        return None
    offset = 0 if seat == first_player else 1
    if global_turn <= offset:
        return None
    return ((global_turn - 1 - offset) // 2) + 1


def card_from_state(current: Mapping[str, Any], seat: int, area: int | None, index: int | None) -> Mapping[str, Any] | None:
    players = items(current.get("players"))
    if area == 7:
        cards = items(current.get("stadium"))
    elif 0 <= seat < len(players) and isinstance(players[seat], Mapping):
        player = players[seat]
        zone = {2: "hand", 3: "discard", 4: "active", 5: "bench", 6: "prize"}.get(area)
        cards = items(player.get(zone)) if zone else []
    else:
        return None
    return cards[index] if index is not None and 0 <= index < len(cards) and isinstance(cards[index], Mapping) else None


def resolve_option(observation: Mapping[str, Any], option: Mapping[str, Any]) -> dict[str, Any]:
    current = observation.get("current") or {}
    select = observation.get("select") or {}
    actor = as_int(current.get("yourIndex"), 0) or 0
    option_type = as_int(option.get("type"), -1)
    area = as_int(option.get("area"))
    if option_type == 7 and area is None:
        area = 2
    owner = as_int(option.get("playerIndex"), actor)
    source: Mapping[str, Any] | None = None
    if area == 1:
        deck = items(select.get("deck"))
        index = as_int(option.get("index"))
        source = deck[index] if index is not None and 0 <= index < len(deck) and isinstance(deck[index], Mapping) else None
    elif area == 12:
        looking = items(current.get("looking"))
        index = as_int(option.get("index"))
        source = looking[index] if index is not None and 0 <= index < len(looking) and isinstance(looking[index], Mapping) else None
    else:
        source = card_from_state(current, owner if owner is not None else actor, area, as_int(option.get("index")))
    if option_type in (4, 5, 6) and isinstance(source, Mapping):
        attached_key = "tools" if option_type == 4 else "energyCards"
        attached_index_key = "toolIndex" if option_type == 4 else "energyIndex"
        attached = items(source.get(attached_key))
        attached_index = as_int(option.get(attached_index_key))
        source = (
            attached[attached_index]
            if attached_index is not None
            and 0 <= attached_index < len(attached)
            and isinstance(attached[attached_index], Mapping)
            else None
        )
    source_id = as_int(source.get("id")) if isinstance(source, Mapping) else as_int(option.get("cardId"))
    target_area = as_int(option.get("inPlayArea", option.get("targetArea")))
    target_owner = as_int(option.get("inPlayPlayerIndex", option.get("targetPlayerIndex")), actor)
    target = card_from_state(
        current,
        target_owner if target_owner is not None else actor,
        target_area,
        as_int(option.get("inPlayIndex", option.get("targetIndex"))),
    )
    target_id = as_int(target.get("id")) if isinstance(target, Mapping) else as_int(option.get("targetCardId"))
    relation = "SELF" if owner == actor else "OPPONENT"
    target_relation = "SELF" if target_owner == actor else "OPPONENT"
    context_card = select.get("contextCard") or select.get("effect")
    effect_source = as_int(context_card.get("id")) if isinstance(context_card, Mapping) else None
    return {
        "option_type": option_type,
        "selection_context": as_int(select.get("context"), -1),
        "source_area": area,
        "select_deck_present": isinstance(select.get("deck"), list),
        "source_card_id": source_id,
        "source_relation": relation,
        "target_card_id": target_id,
        "target_relation": target_relation,
        "attack_id": as_int(option.get("attackId")),
        "effect_source_id": effect_source,
        "number": as_int(option.get("number")),
    }


def is_main_prompt(observation: Mapping[str, Any]) -> bool:
    select = observation.get("select") or {}
    options = items(select.get("option"))
    return (
        as_int(select.get("context")) == 0
        and as_int(select.get("type")) == 0
        and not select.get("effect")
        and not select.get("contextCard")
        and any(as_int(option.get("type")) == 14 for option in options if isinstance(option, Mapping))
    )


def valid_decision(observation: Any, action: Any, seat: int, status: Any) -> bool:
    if status != "ACTIVE" or not isinstance(observation, Mapping) or not isinstance(action, list):
        return False
    current = observation.get("current") or {}
    select = observation.get("select") or {}
    options = items(select.get("option"))
    if as_int(current.get("yourIndex")) != seat or not options or current.get("result") not in (None, -1):
        return False
    if len(set(action)) != len(action) or any(as_int(index) != index or not 0 <= index < len(options) for index in action):
        return False
    minimum = as_int(select.get("minCount"), 0) or 0
    maximum = as_int(select.get("maxCount"), len(options))
    return maximum is not None and minimum <= len(action) <= maximum


def semantic_complete_action_count(
    observation: Mapping[str, Any],
    options: Sequence[Mapping[str, Any]],
    minimum: int,
    maximum: int,
) -> int:
    canonical_options = [stable_json(resolve_option(observation, option)) for option in options]
    complete_actions: set[str] = set()
    for count in range(max(0, minimum), min(len(options), maximum) + 1):
        for indexes in itertools.combinations(range(len(options)), count):
            complete_actions.add(stable_json(sorted(canonical_options[index] for index in indexes)))
    return len(complete_actions)


def normalize_choice(
    resolved: Mapping[str, Any],
    *,
    main_prompt: bool,
    card_types: Mapping[int, int],
    parent_action: str,
) -> str:
    option_type = resolved["option_type"]
    context = resolved["selection_context"]
    source_id = resolved["source_card_id"]
    if option_type == -1:
        return "decline_optional"
    if main_prompt:
        if option_type == 7:
            return {
                0: "play_basic",
                1: "play_item",
                2: "attach_tool",
                3: "play_supporter",
                4: "play_stadium",
            }.get(card_types.get(source_id, -1), "play_item")
        return {
            8: "attach_energy" if card_types.get(source_id) in (5, 6) else "attach_tool",
            9: "evolve",
            10: "use_ability",
            11: "discard",
            12: "retreat",
            13: "attack",
            14: "pass",
        }.get(option_type, "effect_choice")
    if context == 1:
        return "initial_active"
    if context == 2:
        return "initial_bench"
    if resolved.get("source_area") == 1 and resolved.get("select_deck_present"):
        return "search_target"
    if context == 7 and resolved.get("source_area") == 6:
        return "prize_take"
    if context == 24:
        return "search_target"
    if context in {8, 26, 27, 29, 30}:
        if resolved.get("source_relation") == "OPPONENT":
            return "effect_target"
        if parent_action in {"play_item", "play_supporter", "use_ability", "attack"}:
            return "discard_cost"
        return "discard_effect"
    if context in {3, 4, 5, 6}:
        return "gust" if resolved.get("source_relation") == "OPPONENT" else "switch"
    if context in {18, 19, 37}:
        return "evolve"
    if context in {21, 22, 28, 31, 32, 33}:
        return "attach_energy"
    if context == 35 and option_type == 13:
        return "attack"
    if context in {13, 14, 15, 25, 36}:
        return "attack_target"
    return "effect_choice"


def result_label(reward: int | None) -> str:
    if reward is None or reward == 0:
        return "DRAW"
    return "WIN" if reward > 0 else "LOSS"


def result_value(reward: int | None) -> float:
    return 0.5 if reward is None or reward == 0 else (1.0 if reward > 0 else 0.0)


def prize_count(current: Mapping[str, Any], seat: int) -> int | None:
    players = items(current.get("players"))
    if not 0 <= seat < len(players) or not isinstance(players[seat], Mapping):
        return None
    prize = players[seat].get("prize")
    return len(prize) if isinstance(prize, list) else None


def board_bucket(current: Mapping[str, Any], seat: int, attack_ready: Any) -> str:
    players = items(current.get("players"))
    if not 0 <= seat < len(players) or not isinstance(players[seat], Mapping):
        return "UNKNOWN"
    bench = items(players[seat].get("bench"))
    if not bench:
        return "EMPTY_BENCH"
    return "READY_BACKUP" if any(attack_ready(card) for card in bench if isinstance(card, Mapping)) else "DEVELOPING"


def prize_bucket(current: Mapping[str, Any], seat: int) -> str:
    mine, opponent = prize_count(current, seat), prize_count(current, 1 - seat)
    return f"SELF_{mine}_OPP_{opponent}" if mine is not None and opponent is not None else "UNKNOWN"


def phase_for_decision(
    current: Mapping[str, Any],
    seat: int,
    normalized_action: str,
    first_player: int | None,
    has_attacked: bool,
    attack_ready: Any,
    remaining_overage: float | None,
) -> tuple[str, str, str]:
    turn = as_int(current.get("turn"))
    own_turn = own_turn_number(turn, seat, first_player)
    pb = prize_bucket(current, seat)
    bb = board_bucket(current, seat, attack_ready)
    players = items(current.get("players"))
    deck_count = None
    appear = False
    if 0 <= seat < len(players) and isinstance(players[seat], Mapping):
        deck_count = as_int(players[seat].get("deckCount"))
        active = items(players[seat].get("active"))
        appear = bool(active and isinstance(active[0], Mapping) and active[0].get("appearThisTurn"))
    mine, opponent = prize_count(current, seat), prize_count(current, 1 - seat)
    if turn is None or turn <= 0:
        phase = "SETUP"
    elif (deck_count is not None and deck_count <= 5) or (remaining_overage is not None and remaining_overage <= 30):
        phase = "DECKOUT_OR_TIME"
    elif (mine is not None and mine <= 1) or (opponent is not None and opponent <= 1):
        phase = "CHECKMATE"
    elif normalized_action == "attack" and not has_attacked:
        phase = "FIRST_ATTACK"
    elif appear and own_turn is not None and own_turn > 1 and has_attacked:
        phase = "RECOVERY"
    elif own_turn is not None and own_turn <= 2 and not has_attacked:
        phase = "EARLY"
    elif (mine is not None and mine < 6) or (opponent is not None and opponent < 6):
        phase = "PRIZE_RACE"
    else:
        phase = "MIDGAME"
    return phase, pb, bb


@dataclass
class SeatFeatures:
    episode_id: str
    seat: int
    team: str
    team_id: str
    archetype: str
    deck_hash: str
    opponent_team: str
    opponent_team_id: str
    opponent_archetype: str
    opponent_deck_hash: str
    reward: int | None
    starting_order: str
    initial_active_card_id: int | None = None
    initial_bench_ids: tuple[int, ...] = ()
    bench_count_end_turn1: int | None = None
    bench_count_end_turn2: int | None = None
    first_evolution_turn: int | None = None
    first_attack_turn: int | None = None
    first_prize_turn: int | None = None
    first_prize_replay_step: int | None = None
    first_supporter_card_id: int | None = None
    first_stadium_card_id: int | None = None
    first_energy_target_card_id: int | None = None
    completed_own_turns: int = 0
    no_attack_turns: int = 0
    second_attacker_ready: bool | None = None
    first_attack_decision_step: int | None = None
    first_attack_snapshot_hash: str = ""
    first_attacker_card_id: int | None = None
    next_attacker_action_distance_lower_bound: int | None = None
    next_attacker_action_distance_certified_upper_bound: int | None = None
    next_attacker_action_distance: int | None = None
    next_attacker_action_distance_bucket: str = "UNKNOWN"
    next_attacker_action_distance_status: str = "UNKNOWN_NO_FIRST_ATTACK"
    next_attacker_action_path: str = ""
    next_attacker_distance_model_version: str = "KNOWN_HAND_BOARD_SELF_ACTIONS_V1"
    action_history_present: bool = False
    decision_count: int = 0


def attack_energy_gap(card: Any, provided: Sequence[int], attacks: Mapping[int, Any]) -> int | None:
    """Minimum additional energy attachments needed for any printed attack."""
    best: int | None = None
    for attack_id in getattr(card, "attacks", []) or []:
        attack = attacks.get(int(attack_id))
        if attack is None:
            continue
        costs = [int(value) for value in (getattr(attack, "energies", []) or [])]
        remaining = [int(value) for value in provided]
        missing = 0
        colored = [value for value in costs if value != 0]
        colorless = sum(value == 0 for value in costs)
        for need in colored:
            if need in remaining:
                remaining.remove(need)
            elif 10 in remaining:
                remaining.remove(10)
            elif need in (5, 7) and 11 in remaining:
                remaining.remove(11)
            else:
                missing += 1
        missing += max(0, colorless - len(remaining))
        best = missing if best is None else min(best, missing)
    return best


def make_attack_ready(cards: Mapping[int, Any], attacks: Mapping[int, Any]):
    def ready(pokemon: Mapping[str, Any]) -> bool:
        card_id = as_int(pokemon.get("id"))
        card = cards.get(card_id)
        if card is None:
            return False
        return attack_energy_gap(card, list(pokemon.get("energies") or []), attacks) == 0
    return ready


def make_next_attacker_distance(cards: Mapping[int, Any], attacks: Mapping[int, Any]):
    """Return a deterministic, capped same-printed-attacker known-hand/board action-path evaluator.

    This v1 model counts only self root actions supported directly by card/state
    metadata: bench a Basic, evolve, use Rare Candy, and attach one Energy.
    It excludes future draws, search/recovery/acceleration effects, opponent
    interference, knockout promotion, retreat/switch, and turn-legality timing.
    A found path is therefore a model-scoped minimum, not a guaranteed future
    game path. No supported path is reported as UNKNOWN rather than False.
    """
    evolves_from_name: dict[str, list[Any]] = defaultdict(list)
    cards_by_name: dict[str, list[Any]] = defaultdict(list)
    rare_candy_ids: set[int] = set()
    for card_id, card in cards.items():
        name = str(getattr(card, "name", ""))
        cards_by_name[name].append(card)
        parent_name = getattr(card, "evolvesFrom", None)
        if parent_name:
            evolves_from_name[str(parent_name)].append(card)
        if name.strip().lower() == "rare candy":
            rare_candy_ids.add(int(card_id))

    rare_candy_targets: dict[str, list[Any]] = defaultdict(list)
    for card in cards.values():
        if not bool(getattr(card, "stage2", False)):
            continue
        for stage1 in cards_by_name.get(str(getattr(card, "evolvesFrom", "")), []):
            basic_name = getattr(stage1, "evolvesFrom", None)
            if basic_name:
                rare_candy_targets[str(basic_name)].append(card)

    def hand_key(counts: Counter[int]) -> tuple[tuple[int, int], ...]:
        return tuple(sorted((card_id, count) for card_id, count in counts.items() if count > 0))

    def consume(counts: Counter[int], *card_ids: int) -> Counter[int] | None:
        updated = counts.copy()
        for card_id in card_ids:
            if updated[card_id] <= 0:
                return None
            updated[card_id] -= 1
        return updated

    def evolution_action_steps(start_card_id: int, target_card_id: int) -> int | None:
        if start_card_id == target_card_id:
            return 0
        start_card = cards.get(start_card_id)
        target_card = cards.get(target_card_id)
        if start_card is None or target_card is None:
            return None
        queue: deque[tuple[int, int]] = deque([(start_card_id, 0)])
        seen = {start_card_id}
        while queue:
            card_id, steps = queue.popleft()
            card = cards.get(card_id)
            if card is None:
                continue
            successors = list(evolves_from_name.get(str(getattr(card, "name", "")), []))
            if bool(getattr(card, "basic", False)):
                successors.extend(rare_candy_targets.get(str(getattr(card, "name", "")), []))
            for evolution in successors:
                evolution_id = int(getattr(evolution, "cardId"))
                if evolution_id == target_card_id:
                    return steps + 1
                if evolution_id not in seen:
                    seen.add(evolution_id)
                    queue.append((evolution_id, steps + 1))
        return None

    def structural_lower_bound(
        player_state: Mapping[str, Any],
        target_card_id: int,
    ) -> int | None:
        target_card = cards.get(target_card_id)
        bench = player_state.get("bench")
        hand = player_state.get("hand")
        if target_card is None or not isinstance(bench, list) or not isinstance(hand, list):
            return None
        candidates: list[tuple[int, tuple[int, ...], int]] = []
        for pokemon in bench:
            if not isinstance(pokemon, Mapping):
                continue
            card_id = as_int(pokemon.get("id"))
            if card_id is not None:
                candidates.append((
                    card_id,
                    tuple(int(value) for value in items(pokemon.get("energies"))),
                    0,
                ))
        bench_max = as_int(player_state.get("benchMax"))
        if bench_max is None or len(bench) < bench_max:
            for card in hand:
                if not isinstance(card, Mapping):
                    continue
                card_id = as_int(card.get("id"))
                card_data = cards.get(card_id)
                if card_id is not None and card_data is not None and bool(getattr(card_data, "basic", False)):
                    candidates.append((card_id, (), 1))
        bounds = []
        for card_id, provided, bench_action in candidates:
            evolution_steps = evolution_action_steps(card_id, target_card_id)
            energy_steps = attack_energy_gap(target_card, provided, attacks)
            if evolution_steps is not None and energy_steps is not None:
                bounds.append(bench_action + evolution_steps + energy_steps)
        return min(bounds) if bounds else None
    def evaluate(player_state: Mapping[str, Any], target_card_id: int | None) -> tuple[int | None, int | None, int | None, str, str, str]:
        bench = player_state.get("bench")
        hand = player_state.get("hand")
        if target_card_id is None or target_card_id not in cards:
            return None, None, None, "UNKNOWN", "UNKNOWN_TARGET_ATTACKER", "first_attacker_card_unresolved"
        if not isinstance(bench, list) or not isinstance(hand, list):
            return None, None, None, "UNKNOWN", "UNKNOWN_STATE", "bench_or_hand_not_exposed"

        lower_bound = structural_lower_bound(player_state, target_card_id)
        hand_ids = [
            card_id
            for card_id in (as_int(card.get("id")) for card in hand if isinstance(card, Mapping))
            if card_id is not None
        ]
        hand_counts = Counter(hand_ids)
        queue: deque[tuple[int, tuple[int, ...], tuple[tuple[int, int], ...], int, tuple[str, ...]]] = deque()

        for pokemon in bench:
            if not isinstance(pokemon, Mapping):
                continue
            card_id = as_int(pokemon.get("id"))
            if card_id is None or card_id not in cards:
                continue
            queue.append((
                card_id,
                tuple(int(value) for value in items(pokemon.get("energies"))),
                hand_key(hand_counts),
                0,
                (),
            ))

        bench_max = as_int(player_state.get("benchMax"))
        if bench_max is None or len(bench) < bench_max:
            for card_id in sorted(set(hand_ids)):
                card = cards.get(card_id)
                if card is None or not bool(getattr(card, "basic", False)):
                    continue
                updated = consume(hand_counts, card_id)
                if updated is not None:
                    queue.append((card_id, (), hand_key(updated), 1, (f"BENCH:{card_id}",)))

        best_seen: dict[tuple[int, tuple[int, ...], tuple[tuple[int, int], ...]], int] = {}
        while queue:
            card_id, provided, frozen_hand, distance, path = queue.popleft()
            state_key = (card_id, tuple(sorted(provided)), frozen_hand)
            if best_seen.get(state_key, 999) <= distance:
                continue
            best_seen[state_key] = distance
            card = cards.get(card_id)
            if card is None:
                continue
            if card_id == target_card_id and attack_energy_gap(card, provided, attacks) == 0:
                detail = ">".join(path) if path else f"READY_BENCH:{card_id}"
                if lower_bound is not None and lower_bound == distance:
                    bucket = str(distance) if distance <= 2 else "3_PLUS"
                    return (
                        distance,
                        lower_bound,
                        distance,
                        bucket,
                        "EXACT_BOUNDS_MATCH_WITHIN_SUPPORTED_MODEL",
                        detail,
                    )
                return (
                    None,
                    lower_bound,
                    distance,
                    "UNKNOWN",
                    "UNKNOWN_INTERVAL_MODEL_UPPER_ONLY",
                    detail,
                )
            if distance >= 8:
                continue

            current_hand = Counter(dict(frozen_hand))
            for evolution in sorted(
                evolves_from_name.get(str(getattr(card, "name", "")), []),
                key=lambda value: int(getattr(value, "cardId")),
            ):
                evolution_id = int(getattr(evolution, "cardId"))
                updated = consume(current_hand, evolution_id)
                if updated is not None:
                    queue.append((
                        evolution_id,
                        provided,
                        hand_key(updated),
                        distance + 1,
                        path + (f"EVOLVE:{card_id}->{evolution_id}",),
                    ))

            if bool(getattr(card, "basic", False)):
                for candy_id in sorted(rare_candy_ids):
                    for evolution in sorted(
                        rare_candy_targets.get(str(getattr(card, "name", "")), []),
                        key=lambda value: int(getattr(value, "cardId")),
                    ):
                        evolution_id = int(getattr(evolution, "cardId"))
                        updated = consume(current_hand, candy_id, evolution_id)
                        if updated is not None:
                            queue.append((
                                evolution_id,
                                provided,
                                hand_key(updated),
                                distance + 1,
                                path + (f"RARE_CANDY:{card_id}->{evolution_id}",),
                            ))

            for energy_id in sorted(current_hand):
                if current_hand[energy_id] <= 0:
                    continue
                energy = cards.get(energy_id)
                if energy is None or as_int(getattr(energy, "cardType", None)) not in (5, 6):
                    continue
                energy_type = as_int(getattr(energy, "energyType", None))
                updated = consume(current_hand, energy_id)
                if energy_type is not None and updated is not None:
                    queue.append((
                        card_id,
                        provided + (energy_type,),
                        hand_key(updated),
                        distance + 1,
                        path + (f"ATTACH:{energy_id}",),
                    ))

        return (
            None,
            lower_bound,
            None,
            "UNKNOWN",
            "LOWER_BOUND_ONLY_NO_SUPPORTED_UPPER" if lower_bound is not None else "UNKNOWN_NO_SUPPORTED_PATH",
            "future_or_unmodeled_resource_required",
        )

    return evaluate

def visual_features(
    doc: Mapping[str, Any],
    seat_features: dict[int, SeatFeatures],
    card_types: Mapping[int, int],
    attack_ready: Any,
    first_player: int | None,
) -> None:
    steps = items(doc.get("steps"))
    visualize = []
    if steps and items(steps[0]) and isinstance(items(steps[0])[0], Mapping):
        visualize = items(items(steps[0])[0].get("visualize"))
    turn_had_attack = {0: False, 1: False}
    latest_current: dict[int, Mapping[str, Any]] = {}
    for replay_step, frame in enumerate(visualize):
        if not isinstance(frame, Mapping):
            continue
        current = frame.get("current") or {}
        turn = as_int(current.get("turn"))
        for seat in (0, 1):
            latest_current[seat] = current
        for log in items(frame.get("logs")):
            if not isinstance(log, Mapping):
                continue
            kind = str(log.get("type"))
            seat = as_int(log.get("playerIndex"))
            if seat not in (0, 1):
                continue
            feature = seat_features[seat]
            own_turn = own_turn_number(turn, seat, first_player)
            if kind == "TurnStart":
                turn_had_attack[seat] = False
                if own_turn == 1:
                    players = items(current.get("players"))
                    if 0 <= seat < len(players) and isinstance(players[seat], Mapping):
                        active = items(players[seat].get("active"))
                        bench = items(players[seat].get("bench"))
                        feature.initial_active_card_id = as_int(active[0].get("id")) if active and isinstance(active[0], Mapping) else None
                        feature.initial_bench_ids = tuple(
                            card_id for card_id in (as_int(card.get("id")) for card in bench if isinstance(card, Mapping))
                            if card_id is not None
                        )
            elif kind == "TurnEnd" and own_turn is not None:
                players = items(current.get("players"))
                bench_count = None
                if 0 <= seat < len(players) and isinstance(players[seat], Mapping):
                    bench_count = len(items(players[seat].get("bench")))
                if own_turn == 1:
                    feature.bench_count_end_turn1 = bench_count
                elif own_turn == 2:
                    feature.bench_count_end_turn2 = bench_count
                feature.completed_own_turns += 1
                if not turn_had_attack[seat]:
                    feature.no_attack_turns += 1
            elif kind == "Evolve" and feature.first_evolution_turn is None:
                feature.first_evolution_turn = own_turn
            elif kind == "Attack":
                turn_had_attack[seat] = True
                if feature.first_attack_turn is None:
                    feature.first_attack_turn = own_turn
                    players = items(current.get("players"))
                    if 0 <= seat < len(players) and isinstance(players[seat], Mapping):
                        feature.second_attacker_ready = any(
                            attack_ready(card)
                            for card in items(players[seat].get("bench"))
                            if isinstance(card, Mapping)
                        )
            elif kind == "Play":
                card_id = as_int(log.get("cardId"))
                card_type = card_types.get(card_id, -1)
                if card_type == 3 and feature.first_supporter_card_id is None:
                    feature.first_supporter_card_id = card_id
                elif card_type == 4 and feature.first_stadium_card_id is None:
                    feature.first_stadium_card_id = card_id
            elif kind == "Attach" and card_types.get(as_int(log.get("cardId")), -1) in (5, 6):
                if feature.first_energy_target_card_id is None:
                    feature.first_energy_target_card_id = as_int(log.get("cardIdTarget"))
            elif (
                kind == "MoveCard"
                and as_int(log.get("fromArea")) == 6
                and as_int(log.get("toArea")) == 2
                and feature.first_prize_turn is None
            ):
                feature.first_prize_turn = own_turn
                feature.first_prize_replay_step = replay_step
    for seat, feature in seat_features.items():
        if feature.initial_active_card_id is None:
            current = latest_current.get(seat) or {}
            players = items(current.get("players"))
            if 0 <= seat < len(players) and isinstance(players[seat], Mapping):
                active = items(players[seat].get("active"))
                feature.initial_active_card_id = as_int(active[0].get("id")) if active and isinstance(active[0], Mapping) else None


def decision_events(
    doc: Mapping[str, Any],
    features: dict[int, SeatFeatures],
    card_types: Mapping[int, int],
    attack_ready: Any,
    next_attacker_distance: Any,
    first_player: int | None,
) -> list[dict[str, Any]]:
    steps = items(doc.get("steps"))
    events: list[dict[str, Any]] = []
    has_attacked = {0: False, 1: False}
    parent_action: dict[int, str] = {0: "", 1: ""}
    for replay_step in range(max(0, len(steps) - 1)):
        current_step, action_step = items(steps[replay_step]), items(steps[replay_step + 1])
        for seat in (0, 1):
            if seat >= len(current_step) or seat >= len(action_step):
                continue
            current_record, following_record = current_step[seat], action_step[seat]
            observation = current_record.get("observation") if isinstance(current_record, Mapping) else None
            action = following_record.get("action") if isinstance(following_record, Mapping) else None
            if not valid_decision(observation, action, seat, current_record.get("status")):
                continue
            feature = features[seat]
            feature.action_history_present = True
            feature.decision_count += 1
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            options = items(select.get("option"))
            players = items(current.get("players"))
            player_state = players[seat] if 0 <= seat < len(players) and isinstance(players[seat], Mapping) else {}
            deck_remaining = as_int(player_state.get("deckCount"))
            hand_count = as_int(player_state.get("handCount"))
            prize_remaining = (
                len(player_state.get("prize"))
                if isinstance(player_state.get("prize"), list) else None
            )
            main = is_main_prompt(observation)
            resolved_options = [resolve_option(observation, option) for option in options]
            selected = [resolved_options[index] for index in action] or [{
                "option_type": -1,
                "selection_context": as_int(select.get("context"), -1),
                "source_area": None,
                "select_deck_present": isinstance(select.get("deck"), list),
                "source_card_id": None,
                "source_relation": "SELF",
                "target_card_id": None,
                "target_relation": "SELF",
                "attack_id": None,
                "effect_source_id": None,
            }]
            semantic_options = {
                stable_json(resolved) for resolved in resolved_options
            }
            minimum = as_int(select.get("minCount"), 0) or 0
            maximum = as_int(select.get("maxCount"), len(options))
            semantic_action_count = semantic_complete_action_count(
                observation,
                options,
                minimum,
                maximum if maximum is not None else len(options),
            )
            forced = semantic_action_count == 1
            turn = as_int(current.get("turn"))
            remaining = as_float(observation.get("remainingOverageTime"))
            following_observation = (
                following_record.get("observation")
                if isinstance(following_record, Mapping)
                else None
            )
            next_current = following_observation.get("current") if isinstance(following_observation, Mapping) else None
            next_remaining = as_float(following_observation.get("remainingOverageTime")) if isinstance(following_observation, Mapping) else None
            next_turn = as_int(next_current.get("turn")) if isinstance(next_current, Mapping) else None
            timing_delta: float | None = None
            timing_quality = "MISSING"
            if not isinstance(following_record, Mapping) or following_record.get("status") != "ACTIVE":
                timing_quality = "PLAYER_SWITCH_OR_INACTIVE"
            elif not isinstance(next_current, Mapping):
                timing_quality = "MISSING_NEXT_OBSERVATION"
            elif as_int(next_current.get("yourIndex")) != seat:
                timing_quality = "PLAYER_SWITCH"
            elif turn != next_turn:
                timing_quality = "TURN_BOUNDARY"
            elif remaining is None or next_remaining is None:
                timing_quality = "MISSING"
            elif next_remaining > remaining:
                timing_quality = "RESET_OR_INCREASE"
            else:
                timing_delta = remaining - next_remaining
                if timing_delta <= 60:
                    timing_quality = "CONTIGUOUS_SAME_PLAYER_APPROX"
                else:
                    timing_quality = "CLOCK_DISCONTINUITY"
                    timing_delta = None
            for resolved in selected:
                current_parent = parent_action[seat]
                normalized = normalize_choice(
                    resolved,
                    main_prompt=main,
                    card_types=card_types,
                    parent_action=current_parent,
                )
                if main:
                    parent_action[seat] = normalized
                phase, pb, bb = phase_for_decision(
                    current,
                    seat,
                    normalized,
                    first_player,
                    has_attacked[seat],
                    attack_ready,
                    remaining,
                )
                source_id = resolved.get("source_card_id")
                target_id = resolved.get("target_card_id")
                token = normalized
                if source_id is not None:
                    token += f":{source_id}"
                if target_id is not None:
                    token += f">{target_id}"
                if resolved.get("attack_id") is not None:
                    token += f"@{resolved['attack_id']}"
                events.append({
                    "date": "",
                    "episode_id": feature.episode_id,
                    "player_index": seat,
                    "team": feature.team,
                    "team_id": feature.team_id,
                    "archetype": feature.archetype,
                    "deck_hash": feature.deck_hash,
                    "opponent_team": feature.opponent_team,
                    "opponent_team_id": feature.opponent_team_id,
                    "opponent_archetype": feature.opponent_archetype,
                    "opponent_deck_hash": feature.opponent_deck_hash,
                    "reward": feature.reward,
                    "outcome": result_label(feature.reward),
                    "starting_order": feature.starting_order,
                    "replay_step": replay_step,
                    "global_turn": turn,
                    "own_turn": own_turn_number(turn, seat, first_player),
                    "game_phase": phase,
                    "prize_state_bucket": pb,
                    "board_completion_bucket": bb,
                    "deck_remaining": deck_remaining,
                    "hand_count": hand_count,
                    "prize_remaining": prize_remaining,
                    "selected_action_count": len(action),
                    "decision_type": "MAIN_MENU" if main else f"PROMPT_CONTEXT_{resolved['selection_context']}",
                    "normalized_action": normalized,
                    "normalized_token": token,
                    "parent_normalized_action": "" if main else current_parent,
                    "source_card_id": source_id,
                    "source_area": resolved.get("source_area"),
                    "target_card_id": target_id,
                    "attack_id": resolved.get("attack_id"),
                    "effect_source_id": resolved.get("effect_source_id"),
                    "forced_choice": forced,
                    "strategic_choice": not forced,
                    "legal_option_count": len(options),
                    "semantic_option_count": len(semantic_options),
                    "semantic_legal_action_count": semantic_action_count,
                    "recorded_action_valid": "TRUE",
                    "fallback": "UNKNOWN",
                    "invalid_action": "UNKNOWN",
                    "observed_overage_delta_sec": (
                        f"{timing_delta:.6f}" if timing_delta is not None else ""
                    ),
                    "timing_source": "REMAINING_OVERAGE_TIME_DELTA",
                    "timing_quality_flag": timing_quality,
                })
                if normalized == "attack" and feature.first_attack_decision_step is None:
                    feature.first_attack_decision_step = replay_step
                    active = items(player_state.get("active"))
                    feature.first_attacker_card_id = (
                        as_int(source_id)
                        if as_int(source_id) is not None
                        else as_int(active[0].get("id")) if active and isinstance(active[0], Mapping) else None
                    )
                    snapshot_payload = {
                        "turn": turn,
                        "energyAttached": current.get("energyAttached"),
                        "retreated": current.get("retreated"),
                        "supporterPlayed": current.get("supporterPlayed"),
                        "active": player_state.get("active"),
                        "bench": player_state.get("bench"),
                        "hand": player_state.get("hand"),
                        "discard": player_state.get("discard"),
                        "deckCount": player_state.get("deckCount"),
                        "prizeCount": prize_remaining,
                    }
                    feature.first_attack_snapshot_hash = hashlib.sha256(
                        (stable_json(snapshot_payload) + "\n").encode("utf-8")
                    ).hexdigest()
                    (
                        feature.next_attacker_action_distance,
                        feature.next_attacker_action_distance_lower_bound,
                        feature.next_attacker_action_distance_certified_upper_bound,
                        feature.next_attacker_action_distance_bucket,
                        feature.next_attacker_action_distance_status,
                        feature.next_attacker_action_path,
                    ) = next_attacker_distance(player_state, feature.first_attacker_card_id)
                if normalized == "attack":
                    has_attacked[seat] = True
    return events


def end_turn_feature(feature: SeatFeatures, name: str) -> Any:
    return getattr(feature, name)


def sequence_windows(feature: SeatFeatures, events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    strategic = [row for row in events if row["strategic_choice"]]
    windows: list[tuple[str, list[Mapping[str, Any]], bool]] = []
    windows.append(("SETUP", [row for row in strategic if row["game_phase"] == "SETUP"], True))
    windows.append(("OWN_TURN_1", [row for row in strategic if row["own_turn"] == 1], True))
    windows.append(("OWN_TURN_2", [row for row in strategic if row["own_turn"] == 2], feature.completed_own_turns >= 2))
    attack_rows = [row for row in strategic if row["normalized_action"] == "attack"]
    if attack_rows:
        stop = int(attack_rows[0]["replay_step"])
        windows.append(("TO_FIRST_ATTACK", [row for row in strategic if int(row["replay_step"]) <= stop], True))
    else:
        windows.append(("TO_FIRST_ATTACK", strategic, False))
    if feature.first_prize_replay_step is not None:
        windows.append((
            "TO_FIRST_PRIZE",
            [row for row in strategic if int(row["replay_step"]) <= feature.first_prize_replay_step],
            True,
        ))
    else:
        windows.append(("TO_FIRST_PRIZE", strategic, False))
    output = []
    for name, rows, complete in windows:
        tokens = [str(row["normalized_token"]) for row in rows]
        sequence = "|".join(tokens)
        sequence_id = hashlib.sha256((sequence + "\n").encode("utf-8")).hexdigest()
        output.append({
            "sequence_window": name,
            "normalized_sequence_id": sequence_id,
            "normalized_sequence": sequence,
            "window_complete": complete,
        })
    return output


def warning_fields(rows: Sequence[Mapping[str, Any]], raw_games: int, unique_team_pairs: int) -> dict[str, Any]:
    dates = Counter(str(row["date"]) for row in rows)
    teams = Counter(str(row["team_id"]) for row in rows)
    hashes = Counter(str(row["deck_hash"]) for row in rows)
    single_date = len(dates) <= 1
    single_team = bool(raw_games and teams and max(teams.values()) / raw_games > 0.5)
    repeated_hash = bool(raw_games and hashes and max(hashes.values()) > 1)
    warnings = []
    if single_date:
        warnings.append("SINGLE_DATE")
    if single_team:
        warnings.append("SINGLE_TEAM_DOMINANCE")
    if repeated_hash:
        warnings.append("REPEATED_EXACT_DECK")
    return {
        "low_sample_flag": raw_games < 5 or unique_team_pairs < 3,
        "single_date_warning": single_date,
        "single_team_dominance_warning": single_team,
        "repeated_exact_deck_warning": repeated_hash,
        "dependence_warning": "|".join(warnings),
    }


def aggregate_units(
    games: Sequence[Mapping[str, Any]],
    aggregation_unit: str,
) -> tuple[int, float]:
    if aggregation_unit == "episode_raw":
        return len(games), sum(float(row["result_value"]) for row in games) / len(games) if games else math.nan
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in games:
        if aggregation_unit == "team_pair_day":
            key = (
                row["date"], row["team_id"], row["opponent_team_id"],
                row["deck_hash"], row["opponent_deck_hash"],
            )
        elif aggregation_unit == "exact_deck_pair_day":
            key = (row["date"], row["deck_hash"], row["opponent_deck_hash"])
        else:
            raise ValueError(aggregation_unit)
        grouped[key].append(row)
    rates = [
        sum(float(row["result_value"]) for row in unit) / len(unit)
        for unit in grouped.values()
    ]
    return len(grouped), statistics.fmean(rates) if rates else math.nan


def matchup_rows(enriched: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_episode: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in enriched:
        by_episode[str(row["episode_id"])].append(row)
    perspective_games: list[dict[str, Any]] = []
    special_mirrors: list[dict[str, Any]] = []
    for episode_rows in by_episode.values():
        if len(episode_rows) != 2:
            continue
        a, b = sorted(episode_rows, key=lambda row: int(row["player_index"]))
        same_arch = a["archetype"] == b["archetype"]
        same_hash = a["deck_hash"] == b["deck_hash"]
        if same_arch and same_hash:
            winner = a if int(a["reward"]) > int(b["reward"]) else b
            special_mirrors.append({
                **a,
                "opponent_team": b["team"],
                "opponent_team_id": b["team_id"],
                "opponent_archetype": b["archetype"],
                "opponent_deck_hash": b["deck_hash"],
                "result_value": "",
                "matchup_type": "SAME_HASH_MIRROR",
                "physical_winner_starting_order": winner["starting_order"],
            })
            continue
        if same_arch:
            low, high = sorted((a, b), key=lambda row: str(row["deck_hash"]))
            special_mirrors.append({
                **low,
                "opponent_team": high["team"],
                "opponent_team_id": high["team_id"],
                "opponent_archetype": high["archetype"],
                "opponent_deck_hash": high["deck_hash"],
                "result_value": result_value(as_int(low["reward"])),
                "matchup_type": "DIFFERENT_HASH_MIRROR",
                "physical_winner_starting_order": (
                    low["starting_order"] if int(low["reward"]) > int(high["reward"]) else high["starting_order"]
                ),
            })
            continue
        for row, opponent in ((a, b), (b, a)):
            perspective_games.append({
                **row,
                "opponent_team": opponent["team"],
                "opponent_team_id": opponent["team_id"],
                "opponent_archetype": opponent["archetype"],
                "opponent_deck_hash": opponent["deck_hash"],
                "result_value": result_value(as_int(row["reward"])),
                "matchup_type": "NON_MIRROR",
                "physical_winner_starting_order": (
                    row["starting_order"] if int(row["reward"]) > int(opponent["reward"]) else opponent["starting_order"]
                ),
            })
    output: list[dict[str, Any]] = []
    aggregation_units = ("episode_raw", "team_pair_day", "exact_deck_pair_day")
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in perspective_games + special_mirrors:
        key = (
            row["archetype"], row["deck_hash"], row["opponent_archetype"],
            row["opponent_deck_hash"], row["matchup_type"],
        )
        grouped[key].append(row)
    for key, games in sorted(grouped.items()):
        row_arch, row_hash, opp_arch, opp_hash, matchup_type = key
        team_pairs = {
            tuple(sorted((str(row["team_id"]), str(row["opponent_team_id"]))))
            for row in games
        }
        physical_first = sum(row["physical_winner_starting_order"] == "FIRST" for row in games)
        physical_second = sum(row["physical_winner_starting_order"] == "SECOND" for row in games)
        physical_unknown = sum(row["physical_winner_starting_order"] == "UNKNOWN" for row in games)
        for unit in aggregation_units:
            raw_games = len(games)
            if matchup_type == "SAME_HASH_MIRROR":
                raw_wins = raw_losses = raw_draws = ""
                raw_rate = descriptive = ""
                aggregated_units = (
                    raw_games if unit == "episode_raw"
                    else len({
                        (row["date"], tuple(sorted((str(row["team_id"]), str(row["opponent_team_id"])))))
                        if unit == "team_pair_day"
                        else (row["date"], row_hash)
                        for row in games
                    })
                )
                unit_rate = ""
            else:
                values = [float(row["result_value"]) for row in games]
                raw_wins = sum(value == 1.0 for value in values)
                raw_losses = sum(value == 0.0 for value in values)
                raw_draws = sum(value == 0.5 for value in values)
                raw_rate = (raw_wins + 0.5 * raw_draws) / raw_games if raw_games else ""
                aggregated_units, unit_rate_value = aggregate_units(games, unit)
                unit_rate = unit_rate_value
                descriptive = raw_rate if unit == "episode_raw" else unit_rate_value
            warnings = warning_fields(games, raw_games, len(team_pairs))
            output.append({
                "population": SOURCE_POPULATION,
                "aggregation_unit": unit,
                "matchup_type": matchup_type,
                "row_archetype": row_arch,
                "row_deck_hash": row_hash,
                "opponent_archetype": opp_arch,
                "opponent_deck_hash": opp_hash,
                "deck_hash_a": row_hash if matchup_type == "DIFFERENT_HASH_MIRROR" else "",
                "deck_hash_b": opp_hash if matchup_type == "DIFFERENT_HASH_MIRROR" else "",
                "raw_games": raw_games,
                "raw_wins": raw_wins,
                "raw_losses": raw_losses,
                "raw_draws": raw_draws,
                "raw_result_rate": f"{raw_rate:.8f}" if isinstance(raw_rate, float) else raw_rate,
                "aggregated_units": aggregated_units,
                "unit_equal_weight_result_rate": (
                    f"{unit_rate:.8f}" if isinstance(unit_rate, float) else unit_rate
                ),
                "descriptive_win_rate": (
                    f"{descriptive:.8f}" if isinstance(descriptive, float) else descriptive
                ),
                "wins": raw_wins,
                "losses": raw_losses,
                "draws": raw_draws,
                "unique_row_teams": len({str(row["team_id"]) for row in games}),
                "unique_opponent_teams": len({str(row["opponent_team_id"]) for row in games}),
                "unique_teams": len({
                    str(team_id) for row in games
                    for team_id in (row["team_id"], row["opponent_team_id"])
                }),
                "unique_team_pairs": len(team_pairs),
                "unique_dates": len({str(row["date"]) for row in games}),
                "first_games": (
                    raw_games if matchup_type == "SAME_HASH_MIRROR"
                    else sum(row["starting_order"] == "FIRST" for row in games)
                ),
                "first_wins": (
                    physical_first if matchup_type == "SAME_HASH_MIRROR"
                    else sum(row["starting_order"] == "FIRST" and float(row["result_value"]) == 1 for row in games)
                ),
                "second_games": (
                    raw_games if matchup_type == "SAME_HASH_MIRROR"
                    else sum(row["starting_order"] == "SECOND" for row in games)
                ),
                "second_wins": (
                    physical_second if matchup_type == "SAME_HASH_MIRROR"
                    else sum(row["starting_order"] == "SECOND" and float(row["result_value"]) == 1 for row in games)
                ),
                "unknown_order_games": physical_unknown if matchup_type == "SAME_HASH_MIRROR" else sum(
                    row["starting_order"] == "UNKNOWN" for row in games
                ),
                "deck_hash_a_wins": raw_wins if matchup_type == "DIFFERENT_HASH_MIRROR" else "",
                "deck_hash_b_wins": raw_losses if matchup_type == "DIFFERENT_HASH_MIRROR" else "",
                "deck_hash_a_result_rate": (
                    f"{raw_rate:.8f}" if matchup_type == "DIFFERENT_HASH_MIRROR" and isinstance(raw_rate, float) else ""
                ),
                **warnings,
            })
    return output


def aggregate_openings(
    enriched: Sequence[Mapping[str, Any]],
    features: Mapping[tuple[str, int], SeatFeatures],
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_seat: dict[tuple[str, int], list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        by_seat[(str(event["episode_id"]), int(event["player_index"]))].append(event)
    instances = []
    for row in enriched:
        key = (str(row["episode_id"]), int(row["player_index"]))
        feature = features[key]
        for window in sequence_windows(feature, by_seat.get(key, [])):
            instances.append({
                **row,
                **window,
                "outcome": result_label(feature.reward),
                "initial_active_card_id": feature.initial_active_card_id,
                "bench_count_end_turn1": feature.bench_count_end_turn1,
                "bench_count_end_turn2": feature.bench_count_end_turn2,
                "first_evolution_turn": feature.first_evolution_turn,
                "first_attack_turn": feature.first_attack_turn,
                "first_supporter_card_id": feature.first_supporter_card_id,
                "first_stadium_card_id": feature.first_stadium_card_id,
                "first_energy_target_card_id": feature.first_energy_target_card_id,
                "fallback_in_sequence": "UNKNOWN",
            })
    group_fields = (
        "archetype", "deck_hash", "opponent_archetype", "starting_order",
        "sequence_window", "normalized_sequence_id", "normalized_sequence", "window_complete",
        "initial_active_card_id", "bench_count_end_turn1", "bench_count_end_turn2",
        "first_evolution_turn", "first_attack_turn", "first_supporter_card_id",
        "first_stadium_card_id", "first_energy_target_card_id", "fallback_in_sequence",
    )
    groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in instances:
        groups[tuple(row.get(field, "") for field in group_fields)].append(row)
    output = []
    for key, rows in groups.items():
        base = dict(zip(group_fields, key))
        wins = sum(row["outcome"] == "WIN" for row in rows)
        losses = sum(row["outcome"] == "LOSS" for row in rows)
        draws = sum(row["outcome"] == "DRAW" for row in rows)
        team_pairs = {
            tuple(sorted((str(row["team_id"]), str(row["opponent_team_id"]))))
            for row in rows
        }
        output.append({
            **base,
            "episodes": len(rows),
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "descriptive_win_rate": f"{(wins + 0.5 * draws) / len(rows):.8f}",
            "unique_teams": len({str(row["team_id"]) for row in rows}),
            "unique_team_pairs": len(team_pairs),
            **warning_fields(rows, len(rows), len(team_pairs)),
        })
    return sorted(output, key=lambda row: (
        row["archetype"], row["deck_hash"], row["opponent_archetype"],
        row["sequence_window"], -int(row["episodes"]), row["normalized_sequence_id"],
    ))


def feature_tokens(feature: SeatFeatures) -> list[tuple[str, str, str, str]]:
    rows = [
        ("SETUP", "initial_active", f"card_id={feature.initial_active_card_id}", "SETUP_BOARD"),
        ("EARLY", "bench_count_end_turn1", str(feature.bench_count_end_turn1), "EARLY_BOARD"),
        ("EARLY", "bench_count_end_turn2", str(feature.bench_count_end_turn2), "EARLY_BOARD"),
        ("EARLY", "first_evolution_turn", str(feature.first_evolution_turn), "EARLY_TEMPO"),
        ("FIRST_ATTACK", "first_attack_turn", str(feature.first_attack_turn), "ATTACK_TEMPO"),
        ("FIRST_ATTACK", "second_attacker_ready", str(feature.second_attacker_ready), "ATTACK_CONTINUITY"),
        ("EARLY", "first_supporter_card_id", str(feature.first_supporter_card_id), "RESOURCE_USE"),
        ("EARLY", "first_stadium_card_id", str(feature.first_stadium_card_id), "RESOURCE_USE"),
        ("EARLY", "first_energy_target_card_id", str(feature.first_energy_target_card_id), "RESOURCE_USE"),
        ("MIDGAME", "no_attack_turns", str(feature.no_attack_turns), "ATTACK_CONTINUITY"),
        ("MIDGAME", "fallback", "UNKNOWN", "RUNTIME"),
        ("MIDGAME", "invalid_action", "UNKNOWN", "RUNTIME"),
    ]
    return rows


def observational_bucket(name: str, value: Any) -> str:
    if value in (None, ""):
        return "UNKNOWN"
    if name in {"prize_remaining", "selected_action_count", "prize_take_count"}:
        return str(int(value))
    number = float(value)
    if name == "deck_remaining":
        if number <= 5: return "0_5"
        if number <= 10: return "6_10"
        if number <= 20: return "11_20"
        if number <= 30: return "21_30"
        return "31_PLUS"
    if name == "hand_count":
        if number == 0: return "0"
        if number <= 3: return "1_3"
        if number <= 6: return "4_6"
        return "7_PLUS"
    if name == "observed_time_proxy":
        if number <= 0.1: return "LE_0_1_SEC"
        if number <= 0.5: return "LE_0_5_SEC"
        if number <= 1: return "LE_1_SEC"
        if number <= 2: return "LE_2_SEC"
        if number <= 5: return "LE_5_SEC"
        return "GT_5_SEC"
    return str(value)


def winner_loser_diff(
    enriched: Sequence[Mapping[str, Any]],
    features: Mapping[tuple[str, int], SeatFeatures],
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    seat_rows = {(str(row["episode_id"]), int(row["player_index"])): row for row in enriched}
    presence: dict[tuple[Any, ...], dict[str, set[tuple[str, int]]]] = defaultdict(lambda: defaultdict(set))
    strata_seats: dict[tuple[Any, ...], set[tuple[str, int]]] = defaultdict(set)
    for event in events:
        seat_key = (str(event["episode_id"]), int(event["player_index"]))
        row = seat_rows[seat_key]
        stratum = (
            row["archetype"], row["opponent_archetype"], row["deck_hash"], row["opponent_deck_hash"],
            row["starting_order"], event["game_phase"], event["prize_state_bucket"],
            event["board_completion_bucket"],
        )
        strata_seats[stratum].add(seat_key)
        action_key = f"{event['normalized_action']}|{event['normalized_token']}"
        presence[stratum][f"ACTION::{event['decision_type']}::{action_key}"].add(seat_key)
        state_values = {
            "deck_remaining": event.get("deck_remaining"),
            "hand_count": event.get("hand_count"),
            "prize_remaining": event.get("prize_remaining"),
        }
        if event["normalized_action"] == "prize_take":
            state_values["prize_take_count"] = event.get("selected_action_count")
        if event["timing_quality_flag"] == "CONTIGUOUS_SAME_PLAYER_APPROX":
            state_values["observed_time_proxy"] = event.get("observed_overage_delta_sec")
        for feature_name, value in state_values.items():
            bucket = observational_bucket(feature_name, value)
            presence[stratum][f"STATE::OBSERVATION::{feature_name}={bucket}"].add(seat_key)
    for seat_key, row in seat_rows.items():
        feature = features[seat_key]
        for phase, action, value, decision_type in feature_tokens(feature):
            stratum = (
                row["archetype"], row["opponent_archetype"], row["deck_hash"], row["opponent_deck_hash"],
                row["starting_order"], phase, "EPISODE_LEVEL", "EPISODE_LEVEL",
            )
            strata_seats[stratum].add(seat_key)
            presence[stratum][f"FEATURE::{decision_type}::{action}={value}"].add(seat_key)
    output = []
    for stratum, action_map in sorted(presence.items()):
        seats = strata_seats[stratum]
        winners = {seat for seat in seats if result_label(features[seat].reward) == "WIN"}
        losers = {seat for seat in seats if result_label(features[seat].reward) == "LOSS"}
        winner_teams = {features[seat].team_id for seat in winners}
        loser_teams = {features[seat].team_id for seat in losers}
        team_counts = Counter(features[seat].team_id for seat in seats)
        date_count = len({str(seat_rows[seat]["date"]) for seat in seats})
        hash_counts = Counter(features[seat].deck_hash for seat in seats)
        single_date = date_count <= 1
        single_team = bool(seats and team_counts and max(team_counts.values()) / len(seats) > 0.5)
        repeated_hash = bool(hash_counts and max(hash_counts.values()) > 1)
        for encoded, present in action_map.items():
            kind, decision_type, action = encoded.split("::", 2)
            winner_count = len(present & winners)
            loser_count = len(present & losers)
            winner_rate = winner_count / len(winners) if winners else math.nan
            loser_rate = loser_count / len(losers) if losers else math.nan
            difference = winner_rate - loser_rate if winners and losers else math.nan
            comparable = len(winners) + len(losers)
            low = comparable < 10 or len(winner_teams) < 2 or len(loser_teams) < 2
            warnings = []
            if len(team_counts) <= 2:
                warnings.append("FEW_TEAMS")
            if single_date:
                warnings.append("SINGLE_DATE")
            if single_team:
                warnings.append("SINGLE_TEAM_DOMINANCE")
            if repeated_hash:
                warnings.append("REPEATED_EXACT_DECK")
            warnings.append("OBSERVATIONAL_ASSOCIATION_NOT_CAUSAL")
            output.append({
                "row_archetype": stratum[0],
                "opponent_archetype": stratum[1],
                "row_deck_hash": stratum[2],
                "opponent_deck_hash": stratum[3],
                "starting_order": stratum[4],
                "game_phase": stratum[5],
                "prize_state_bucket": stratum[6],
                "board_completion_bucket": stratum[7],
                "decision_type": f"{kind}:{decision_type}",
                "action_or_feature": action,
                "winner_count": winner_count,
                "winner_rate": f"{winner_rate:.8f}" if math.isfinite(winner_rate) else "",
                "loser_count": loser_count,
                "loser_rate": f"{loser_rate:.8f}" if math.isfinite(loser_rate) else "",
                "difference": f"{difference:.8f}" if math.isfinite(difference) else "",
                "winner_unique_teams": len(winner_teams),
                "loser_unique_teams": len(loser_teams),
                "comparable_state_count": comparable,
                "low_sample_flag": low,
                "single_date_warning": single_date,
                "single_team_dominance_warning": single_team,
                "repeated_exact_deck_warning": repeated_hash,
                "confounding_warning": "|".join(warnings),
                "interpretation": (
                    "WINNER_MORE_OBSERVED" if math.isfinite(difference) and difference > 0
                    else "LOSER_MORE_OBSERVED" if math.isfinite(difference) and difference < 0
                    else "NO_OBSERVED_DIFFERENCE" if math.isfinite(difference)
                    else "INSUFFICIENT_COMPARISON"
                ),
            })
    return output


def estimate_card_role(card: Any) -> str:
    if card is None:
        return "UNRESOLVED_CARD"
    card_type = int(getattr(card, "cardType", -1))
    name = str(getattr(card, "name", ""))
    text = " ".join(f"{getattr(skill, 'name', '')} {getattr(skill, 'text', '')}" for skill in (getattr(card, "skills", []) or [])).lower()
    if card_type == 0:
        stage = "BASIC" if getattr(card, "basic", False) else "STAGE1" if getattr(card, "stage1", False) else "STAGE2"
        if getattr(card, "ex", False) or getattr(card, "megaEx", False):
            return f"{stage}_POKEMON_EX_ATTACKER"
        if getattr(card, "skills", None):
            return f"{stage}_ABILITY_POKEMON"
        return f"{stage}_POKEMON_ATTACKER_OR_SETUP"
    if card_type in (5, 6):
        return "BASIC_ENERGY" if card_type == 5 else "SPECIAL_ENERGY"
    if card_type == 2:
        return "POKEMON_TOOL"
    if card_type == 4:
        return "STADIUM_BOARD_MODIFIER"
    if card_type == 3:
        if "draw" in text or "search your deck" in text or "look at" in text:
            return "SUPPORTER_DRAW_OR_SEARCH"
        if "opponent" in text or "switch" in text or "discard" in text:
            return "SUPPORTER_DISRUPTION_OR_GUST"
        return "SUPPORTER_UTILITY"
    if card_type == 1:
        if "search your deck" in text or "look at" in text:
            return "ITEM_SEARCH_OR_DRAW"
        if "discard pile" in text or "energy" in text:
            return "ITEM_RESOURCE_OR_RECOVERY"
        if "switch" in text or "active spot" in text:
            return "ITEM_SWITCH_OR_GUST"
        return "ITEM_UTILITY"
    return f"OTHER_CARD_TYPE_{card_type}:{name}"


def exact_deck_outputs(
    enriched: Sequence[Mapping[str, Any]],
    card_names: Mapping[int, str],
    card_types: Mapping[int, int],
    card_roles: Mapping[int, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    candidate_rows = [row for row in enriched if row["archetype"] in CANDIDATES]
    by_variant: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        by_variant[(str(row["archetype"]), str(row["deck_hash"]))].append(row)
    variant_cards: dict[tuple[str, str], Counter[int]] = {}
    variants_output = []
    for key, rows in sorted(by_variant.items()):
        archetype, digest = key
        cards = [int(value) for value in str(rows[0]["deck"]).split()]
        counts = Counter(cards)
        variant_cards[key] = counts
        matchup = defaultdict(lambda: [0, 0, 0])
        for row in rows:
            bucket = matchup[str(row["opponent_archetype"])]
            reward = as_int(row["reward"], 0) or 0
            bucket[0 if reward > 0 else 1 if reward < 0 else 2] += 1
        matchup_json = {
            opponent: {
                "wins": values[0], "losses": values[1], "draws": values[2],
                "games": sum(values),
                "result_rate": (values[0] + 0.5 * values[2]) / sum(values),
            }
            for opponent, values in sorted(matchup.items())
        }
        for card_id, count in sorted(counts.items()):
            variants_output.append({
                "archetype": archetype,
                "deck_hash": digest,
                "card_id": card_id,
                "card_name": card_names.get(card_id, ""),
                "card_type": card_types.get(card_id, ""),
                "estimated_role": card_roles.get(card_id, "UNRESOLVED_CARD"),
                "count": count,
                "observed_teams": "|".join(sorted({str(row["team"]) for row in rows})),
                "observed_team_ids": "|".join(sorted({str(row["team_id"]) for row in rows})),
                "observed_dates": "|".join(sorted({str(row["date"]) for row in rows})),
                "leaderboard_ranks": "|".join(sorted({str(row["leaderboard_rank"]) for row in rows}, key=lambda v: int(v) if v else 999999)),
                "observed_games": len(rows),
                "matchup_results_json": json.dumps(matchup_json, ensure_ascii=False, sort_keys=True),
                "sample_bias": "PUBLIC_DAILY_TOP_HIGH_SCORE_SELECTED_DEPENDENT",
            })
    core_output = []
    markdown = ["# 完全一致デッキ構築差", "", "公開Daily Topの観測リストであり、提出デッキ全体の分布ではない。", ""]
    for archetype in CANDIDATES:
        variants = {digest: cards for (arch, digest), cards in variant_cards.items() if arch == archetype}
        markdown.extend([f"## {archetype}", "", f"観測した完全一致60枚リスト：{len(variants)}種類。", ""])
        markdown.append("| deck_hash | games | teams | dates | sample_bias |")
        markdown.append("|---|---:|---:|---:|---|")
        for digest in sorted(variants):
            variant_rows = by_variant[(archetype, digest)]
            markdown.append(f"| `{digest}` | {len(variant_rows)} | {len({str(row['team_id']) for row in variant_rows})} | {len({str(row['date']) for row in variant_rows})} | PUBLIC_DAILY_TOP_HIGH_SCORE_SELECTED_DEPENDENT |")
        markdown.append("")
        all_ids = sorted({card_id for cards in variants.values() for card_id in cards})
        markdown.append("| card_id | name | min | max | variants | classification |")
        markdown.append("|---:|---|---:|---:|---:|---|")
        for card_id in all_ids:
            values = [cards.get(card_id, 0) for cards in variants.values()]
            present = sum(value > 0 for value in values)
            minimum, maximum = min(values), max(values)
            classification = (
                "COMMON_FIXED" if minimum > 0 and minimum == maximum
                else "COMMON_VARIABLE" if minimum > 0
                else "VARIANT_ONLY" if present == 1
                else "OPTIONAL_SHARED"
            )
            core_output.append({
                "archetype": archetype,
                "card_id": card_id,
                "card_name": card_names.get(card_id, ""),
                "card_type": card_types.get(card_id, ""),
                "min_count": minimum,
                "max_count": maximum,
                "present_variant_count": present,
                "total_variant_count": len(variants),
                "classification": classification,
                "estimated_role": card_roles.get(card_id, "UNRESOLVED_CARD"),
            })
            markdown.append(
                f"| {card_id} | {card_names.get(card_id, '')} | {minimum} | {maximum} | {present}/{len(variants)} | {classification} |"
            )
        markdown.append("")
    return variants_output, core_output, "\n".join(markdown) + "\n"


TEAM_PAIR_DAY_KEY_FIELDS = (
    "date", "team_id", "opponent_team_id", "deck_hash", "opponent_deck_hash",
)


def team_pair_day_key(row: Mapping[str, Any]) -> tuple[str, str, str, str, str]:
    return tuple(str(row[field]) for field in TEAM_PAIR_DAY_KEY_FIELDS)  # type: ignore[return-value]


def result_groups(
    rows: Sequence[Mapping[str, Any]],
    key_fn: Any,
) -> dict[tuple[Any, ...], list[Mapping[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(key_fn(row))].append(row)
    return grouped


def row_result_rate(rows: Sequence[Mapping[str, Any]]) -> float | None:
    return statistics.fmean(result_value(as_int(row["reward"])) for row in rows) if rows else None


def equal_group_result(groups: Mapping[tuple[Any, ...], Sequence[Mapping[str, Any]]]) -> float | None:
    rates = [row_result_rate(rows) for rows in groups.values() if rows]
    return statistics.fmean(float(rate) for rate in rates if rate is not None) if rates else None


def team_pair_result(rows: Sequence[Mapping[str, Any]]) -> float | None:
    """Canonical team-pair-day result using the same five-field key as the matrix."""
    return equal_group_result(result_groups(rows, team_pair_day_key)) if rows else None


AGGREGATION_SENSITIVITY_METHODS = (
    "EPISODE_RAW",
    "TEAM_PAIR_DAY_EQUAL",
    "TEAM_PAIR_DAY_LEGACY_THREE_KEY",
    "TEAM_PAIR_DAY_EXCLUDE_SINGLE_GAME_UNITS",
    "TEAM_PAIR_DAY_MIN_5_GAMES",
    "EXACT_PAIR_DAY_EPISODE_WITHIN",
    "EXACT_PAIR_DAY_TEAM_PAIR_WITHIN",
    "DATE_OUTER_EQUAL",
    "EXACT_PAIR_OUTER_EQUAL",
)


def aggregation_method_result(
    rows: Sequence[Mapping[str, Any]],
    method: str,
) -> dict[str, Any]:
    if not rows:
        return {
            "result_rate": None,
            "aggregated_units": 0,
            "included_games": 0,
            "unit_sizes": [],
            "unit_key": "",
        }
    if method == "EPISODE_RAW":
        return {
            "result_rate": row_result_rate(rows),
            "aggregated_units": len(rows),
            "included_games": len(rows),
            "unit_sizes": [1] * len(rows),
            "unit_key": "episode_id+player_index",
        }
    if method == "TEAM_PAIR_DAY_EQUAL":
        groups = result_groups(rows, team_pair_day_key)
        return {
            "result_rate": equal_group_result(groups),
            "aggregated_units": len(groups),
            "included_games": sum(len(unit) for unit in groups.values()),
            "unit_sizes": sorted(len(unit) for unit in groups.values()),
            "unit_key": "+".join(TEAM_PAIR_DAY_KEY_FIELDS),
        }
    if method == "TEAM_PAIR_DAY_LEGACY_THREE_KEY":
        groups = result_groups(
            rows,
            lambda row: (row["date"], row["team_id"], row["opponent_team_id"]),
        )
        return {
            "result_rate": equal_group_result(groups),
            "aggregated_units": len(groups),
            "included_games": sum(len(unit) for unit in groups.values()),
            "unit_sizes": sorted(len(unit) for unit in groups.values()),
            "unit_key": "date+team_id+opponent_team_id",
        }
    if method in ("TEAM_PAIR_DAY_EXCLUDE_SINGLE_GAME_UNITS", "TEAM_PAIR_DAY_MIN_5_GAMES"):
        minimum = 2 if method == "TEAM_PAIR_DAY_EXCLUDE_SINGLE_GAME_UNITS" else 5
        groups = {
            key: unit
            for key, unit in result_groups(rows, team_pair_day_key).items()
            if len(unit) >= minimum
        }
        return {
            "result_rate": equal_group_result(groups),
            "aggregated_units": len(groups),
            "included_games": sum(len(unit) for unit in groups.values()),
            "unit_sizes": sorted(len(unit) for unit in groups.values()),
            "unit_key": "+".join(TEAM_PAIR_DAY_KEY_FIELDS) + f";min_games={minimum}",
        }
    if method == "EXACT_PAIR_DAY_EPISODE_WITHIN":
        groups = result_groups(
            rows,
            lambda row: (row["date"], row["deck_hash"], row["opponent_deck_hash"]),
        )
        return {
            "result_rate": equal_group_result(groups),
            "aggregated_units": len(groups),
            "included_games": len(rows),
            "unit_sizes": sorted(len(unit) for unit in groups.values()),
            "unit_key": "date+deck_hash+opponent_deck_hash",
        }
    if method == "EXACT_PAIR_DAY_TEAM_PAIR_WITHIN":
        outer = result_groups(
            rows,
            lambda row: (row["date"], row["deck_hash"], row["opponent_deck_hash"]),
        )
        rates = []
        for unit in outer.values():
            rate = equal_group_result(result_groups(unit, team_pair_day_key))
            if rate is not None:
                rates.append(rate)
        return {
            "result_rate": statistics.fmean(rates) if rates else None,
            "aggregated_units": len(rates),
            "included_games": len(rows),
            "unit_sizes": sorted(len(unit) for unit in outer.values()),
            "unit_key": "date+deck_hash+opponent_deck_hash;team_pair_day_within",
        }
    if method == "DATE_OUTER_EQUAL":
        dates = result_groups(rows, lambda row: (row["date"],))
        rates = []
        for unit in dates.values():
            rate = equal_group_result(result_groups(unit, team_pair_day_key))
            if rate is not None:
                rates.append(rate)
        return {
            "result_rate": statistics.fmean(rates) if rates else None,
            "aggregated_units": len(rates),
            "included_games": len(rows),
            "unit_sizes": sorted(len(unit) for unit in dates.values()),
            "unit_key": "date_outer;team_pair_day_within",
        }
    if method == "EXACT_PAIR_OUTER_EQUAL":
        exact_pairs = result_groups(
            rows,
            lambda row: (row["deck_hash"], row["opponent_deck_hash"]),
        )
        rates = []
        for unit in exact_pairs.values():
            days = result_groups(unit, lambda row: (row["date"],))
            day_rates = [row_result_rate(day_rows) for day_rows in days.values()]
            present = [float(rate) for rate in day_rates if rate is not None]
            if present:
                rates.append(statistics.fmean(present))
        return {
            "result_rate": statistics.fmean(rates) if rates else None,
            "aggregated_units": len(rates),
            "included_games": len(rows),
            "unit_sizes": sorted(len(unit) for unit in exact_pairs.values()),
            "unit_key": "deck_hash+opponent_deck_hash_outer;date_within",
        }
    raise ValueError(method)


def leave_one_out_range(
    rows: Sequence[Mapping[str, Any]],
    method: str,
    key_fn: Any,
) -> tuple[float | None, float | None]:
    values = sorted({tuple(key_fn(row)) for row in rows})
    rates: list[float] = []
    for value in values:
        subset = [row for row in rows if tuple(key_fn(row)) != value]
        rate = aggregation_method_result(subset, method)["result_rate"]
        if rate is not None:
            rates.append(float(rate))
    return (min(rates), max(rates)) if rates else (None, None)


def candidate_matchup_sensitivity(
    enriched: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_variant: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in enriched:
        if row["archetype"] in CANDIDATES:
            by_variant[(str(row["archetype"]), str(row["deck_hash"]))].append(row)
    output: list[dict[str, Any]] = []
    for (archetype, digest), variant_rows in sorted(by_variant.items()):
        for opponent in MAJOR_MATCHUPS:
            rows = [row for row in variant_rows if row["opponent_archetype"] == opponent]
            method_results = {
                method: aggregation_method_result(rows, method)
                for method in AGGREGATION_SENSITIVITY_METHODS
            }
            present_rates = [
                float(result["result_rate"])
                for result in method_results.values()
                if result["result_rate"] is not None
            ]
            method_min = min(present_rates) if present_rates else None
            method_max = max(present_rates) if present_rates else None
            physical_pairs = {
                tuple(sorted((str(row["team_id"]), str(row["opponent_team_id"]))))
                for row in rows
            }
            evidence_status = (
                "UNOBSERVED"
                if not rows
                else "OBSERVED_ADEQUATE"
                if len(rows) >= 5 and len(physical_pairs) >= 3
                else "OBSERVED_LOW_SAMPLE"
            )
            ranking_stability = (
                "UNOBSERVED"
                if not present_rates
                else "SENSITIVE"
                if method_min is not None and method_max is not None and method_min <= 0.5 <= method_max
                else "STABLE_ABOVE_0_5"
                if method_min is not None and method_min > 0.5
                else "STABLE_BELOW_0_5"
            )
            wins = sum(as_int(row["reward"]) == 1 for row in rows)
            losses = sum(as_int(row["reward"]) == -1 for row in rows)
            draws = len(rows) - wins - losses
            for method in AGGREGATION_SENSITIVITY_METHODS:
                result = method_results[method]
                loo_date = leave_one_out_range(rows, method, lambda row: (row["date"],))
                loo_team = leave_one_out_range(rows, method, lambda row: (row["team_id"],))
                loo_opponent_team = leave_one_out_range(
                    rows, method, lambda row: (row["opponent_team_id"],)
                )
                loo_pair = leave_one_out_range(
                    rows,
                    method,
                    lambda row: (row["team_id"], row["opponent_team_id"]),
                )
                sizes = list(result["unit_sizes"])
                included_games = int(result["included_games"])
                output.append({
                    "candidate_archetype": archetype,
                    "exact_deck_hash": digest,
                    "opponent_archetype": opponent,
                    "aggregation_method": method,
                    "unit_key": result["unit_key"],
                    "raw_games": len(rows),
                    "raw_wins": wins,
                    "raw_losses": losses,
                    "raw_draws": draws,
                    "raw_result_rate": f"{row_result_rate(rows):.8f}" if rows else "",
                    "included_games": included_games,
                    "aggregated_units": int(result["aggregated_units"]),
                    "unit_games_min": min(sizes) if sizes else "",
                    "unit_games_median": f"{statistics.median(sizes):.8f}" if sizes else "",
                    "unit_games_max": max(sizes) if sizes else "",
                    "max_unit_game_share": (
                        f"{max(sizes) / included_games:.8f}" if sizes and included_games else ""
                    ),
                    "result_rate": (
                        f"{float(result['result_rate']):.8f}"
                        if result["result_rate"] is not None else ""
                    ),
                    "method_envelope_min": f"{method_min:.8f}" if method_min is not None else "",
                    "method_envelope_max": f"{method_max:.8f}" if method_max is not None else "",
                    "method_envelope_width": (
                        f"{method_max - method_min:.8f}"
                        if method_min is not None and method_max is not None else ""
                    ),
                    "loo_date_min": f"{loo_date[0]:.8f}" if loo_date[0] is not None else "",
                    "loo_date_max": f"{loo_date[1]:.8f}" if loo_date[1] is not None else "",
                    "loo_team_min": f"{loo_team[0]:.8f}" if loo_team[0] is not None else "",
                    "loo_team_max": f"{loo_team[1]:.8f}" if loo_team[1] is not None else "",
                    "loo_opponent_team_min": (
                        f"{loo_opponent_team[0]:.8f}" if loo_opponent_team[0] is not None else ""
                    ),
                    "loo_opponent_team_max": (
                        f"{loo_opponent_team[1]:.8f}" if loo_opponent_team[1] is not None else ""
                    ),
                    "loo_team_pair_min": f"{loo_pair[0]:.8f}" if loo_pair[0] is not None else "",
                    "loo_team_pair_max": f"{loo_pair[1]:.8f}" if loo_pair[1] is not None else "",
                    "ranking_stability": ranking_stability,
                    "cell_evidence_status": evidence_status,
                })
    return output

def candidate_scorecard(
    enriched: Sequence[Mapping[str, Any]],
    features: Mapping[tuple[str, int], SeatFeatures],
    events: Sequence[Mapping[str, Any]],
    cards: Mapping[int, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_variant: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in enriched:
        if row["archetype"] in CANDIDATES:
            by_variant[(str(row["archetype"]), str(row["deck_hash"]))].append(row)
    team_days = {
        (str(row["date"]), str(row["team_id"]), str(row["archetype"]))
        for row in enriched
    }
    meta_counts = Counter(archetype for _, _, archetype in team_days)
    major_total = sum(meta_counts[opponent] for opponent in MAJOR_MATCHUPS)
    major_weights = {opponent: meta_counts[opponent] / major_total for opponent in MAJOR_MATCHUPS} if major_total else {}
    events_by_variant: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        if event["archetype"] in CANDIDATES:
            events_by_variant[(str(event["archetype"]), str(event["deck_hash"]))].append(event)
    variant_count = Counter(arch for arch, _ in by_variant)
    output = []
    scenario_output: list[dict[str, Any]] = []
    for key, rows in sorted(by_variant.items()):
        archetype, digest = key
        seat_features = [features[(str(row["episode_id"]), int(row["player_index"]))] for row in rows]
        results = [result_value(feature.reward) for feature in seat_features]
        canonical_unit_count = len(result_groups(rows, team_pair_day_key))
        unit_result = team_pair_result(rows)
        matchup_rows_by_opponent = {
            opponent: [row for row in rows if row["opponent_archetype"] == opponent]
            for opponent in MAJOR_MATCHUPS
        }
        matchup_results = {
            opponent: team_pair_result(cell_rows)
            for opponent, cell_rows in matchup_rows_by_opponent.items()
        }
        matchup_evidence = {}
        for opponent, cell_rows in matchup_rows_by_opponent.items():
            physical_pairs = {
                tuple(sorted((str(row["team_id"]), str(row["opponent_team_id"]))))
                for row in cell_rows
            }
            matchup_evidence[opponent] = (
                "UNOBSERVED"
                if not cell_rows
                else "OBSERVED_ADEQUATE"
                if len(cell_rows) >= 5 and len(physical_pairs) >= 3
                else "OBSERVED_LOW_SAMPLE"
            )
        observed_major = [value for value in matchup_results.values() if value is not None]
        observed_meta_weight = sum(
            major_weights.get(opponent, 0.0)
            for opponent, value in matchup_results.items()
            if value is not None
        )
        observed_contribution = sum(
            major_weights.get(opponent, 0.0) * float(value)
            for opponent, value in matchup_results.items()
            if value is not None
        )
        meta_weighted = (
            observed_contribution / observed_meta_weight if observed_meta_weight else None
        )
        adequate_opponents = [
            opponent
            for opponent, status in matchup_evidence.items()
            if status == "OBSERVED_ADEQUATE"
        ]
        low_sample_opponents = [
            opponent
            for opponent, status in matchup_evidence.items()
            if status == "OBSERVED_LOW_SAMPLE"
        ]
        unobserved_opponents = [
            opponent
            for opponent, status in matchup_evidence.items()
            if status == "UNOBSERVED"
        ]
        adequate_weight = sum(major_weights.get(opponent, 0.0) for opponent in adequate_opponents)
        low_sample_weight = sum(major_weights.get(opponent, 0.0) for opponent in low_sample_opponents)
        unobserved_weight = sum(major_weights.get(opponent, 0.0) for opponent in unobserved_opponents)
        uncertain_weight = low_sample_weight + unobserved_weight
        adequate_contribution = sum(
            major_weights.get(opponent, 0.0) * float(matchup_results[opponent])
            for opponent in adequate_opponents
            if matchup_results[opponent] is not None
        )
        adequate_values = [
            float(matchup_results[opponent])
            for opponent in adequate_opponents
            if matchup_results[opponent] is not None
        ]
        scenario_values = {
            "UNOBSERVED_ONLY_AS_0": observed_contribution,
            "UNOBSERVED_ONLY_AS_0_25": observed_contribution + 0.25 * unobserved_weight,
            "UNOBSERVED_ONLY_AS_0_50": observed_contribution + 0.50 * unobserved_weight,
            "UNCERTAIN_AS_0": adequate_contribution,
            "UNCERTAIN_AS_0_25": adequate_contribution + 0.25 * uncertain_weight,
            "UNCERTAIN_AS_0_50": adequate_contribution + 0.50 * uncertain_weight,
            "UNCERTAIN_AS_1": adequate_contribution + uncertain_weight,
            "OBSERVED_WORST_FILL": (
                adequate_contribution + min(adequate_values) * uncertain_weight
                if adequate_values else None
            ),
            "OBSERVED_ONLY_RENORMALIZED_LEGACY": meta_weighted,
        }
        first_turns = [feature.first_attack_turn for feature in seat_features if feature.first_attack_turn is not None]
        no_attack_numerator = sum(feature.no_attack_turns for feature in seat_features)
        no_attack_denominator = sum(feature.completed_own_turns for feature in seat_features)
        ready = [feature.second_attacker_ready for feature in seat_features if feature.second_attacker_ready is not None]
        first_attack_decisions = [
            feature for feature in seat_features if feature.first_attack_decision_step is not None
        ]
        known_distances = [
            int(feature.next_attacker_action_distance)
            for feature in first_attack_decisions
            if feature.next_attacker_action_distance is not None
        ]
        distance_lower_bounds = [
            int(feature.next_attacker_action_distance_lower_bound)
            for feature in first_attack_decisions
            if feature.next_attacker_action_distance_lower_bound is not None
        ]
        distance_upper_bounds = [
            int(feature.next_attacker_action_distance_certified_upper_bound)
            for feature in first_attack_decisions
            if feature.next_attacker_action_distance_certified_upper_bound is not None
        ]
        distance_denominator = len(first_attack_decisions)
        distance_coverage = (
            len(known_distances) / distance_denominator if distance_denominator else None
        )
        distance_lower_bound_coverage = (
            len(distance_lower_bounds) / distance_denominator if distance_denominator else None
        )
        distance_upper_bound_coverage = (
            len(distance_upper_bounds) / distance_denominator if distance_denominator else None
        )
        order_results = {
            order: [result_value(feature.reward) for feature in seat_features if feature.starting_order == order]
            for order in ("FIRST", "SECOND")
        }
        variant_events = events_by_variant[key]
        timing_by_decision = {
            (event["episode_id"], event["player_index"], event["replay_step"]): float(event["observed_overage_delta_sec"])
            for event in variant_events
            if event["timing_quality_flag"] == "CONTIGUOUS_SAME_PLAYER_APPROX" and event["observed_overage_delta_sec"] != ""
        }
        timing = list(timing_by_decision.values())
        root_choices = [
            int(event["semantic_legal_action_count"])
            for event in variant_events if event["decision_type"] == "MAIN_MENU"
        ]
        deck_ids = {int(value) for value in str(rows[0]["deck"]).split()}
        unresolved = sorted(deck_ids - set(cards))
        text_effect_cards = sum(
            bool(getattr(cards.get(card_id), "skills", None) or getattr(cards.get(card_id), "attacks", None))
            for card_id in deck_ids if card_id in cards
        )
        team_pairs = {
            tuple(sorted((str(row["team_id"]), str(row["opponent_team_id"]))))
            for row in rows
        }
        warnings = warning_fields(rows, len(rows), len(team_pairs))
        complexity = (
            f"OBSERVED_MEDIAN_ROOT_SEMANTIC_COMPLETE_ACTIONS="
            f"{statistics.median(root_choices):.2f}" if root_choices else "NO_ACTION_HISTORY"
        )
        implementation = (
            f"UNRESOLVED_CARD_IDS={','.join(map(str, unresolved))}"
            if unresolved else f"ALL_CARD_IDS_RESOLVED;EFFECT_BEARING_UNIQUE_CARDS={text_effect_cards}"
        )
        scenario_assumptions = {
            "UNOBSERVED_ONLY_AS_0": 0.0,
            "UNOBSERVED_ONLY_AS_0_25": 0.25,
            "UNOBSERVED_ONLY_AS_0_50": 0.50,
            "UNCERTAIN_AS_0": 0.0,
            "UNCERTAIN_AS_0_25": 0.25,
            "UNCERTAIN_AS_0_50": 0.50,
            "UNCERTAIN_AS_1": 1.0,
            "OBSERVED_WORST_FILL": min(adequate_values) if adequate_values else None,
            "OBSERVED_ONLY_RENORMALIZED_LEGACY": None,
        }
        for scenario_name, scenario_result in scenario_values.items():
            scenario_output.append({
                "candidate_archetype": archetype,
                "exact_deck_hash": digest,
                "scenario": scenario_name,
                "assumed_uncertain_result": (
                    f"{scenario_assumptions[scenario_name]:.8f}"
                    if scenario_assumptions[scenario_name] is not None else ""
                ),
                "major_meta_weight_total": f"{sum(major_weights.values()):.8f}",
                "adequately_observed_weight": f"{adequate_weight:.8f}",
                "low_sample_weight": f"{low_sample_weight:.8f}",
                "unobserved_weight": f"{unobserved_weight:.8f}",
                "uncertain_weight": f"{uncertain_weight:.8f}",
                "adequate_observed_contribution": f"{adequate_contribution:.8f}",
                "observed_all_weight": f"{observed_meta_weight:.8f}",
                "observed_all_contribution": f"{observed_contribution:.8f}",
                "scenario_result": (
                    f"{float(scenario_result):.8f}" if scenario_result is not None else ""
                ),
                "scenario_is_assumption": scenario_name != "OBSERVED_ONLY_RENORMALIZED_LEGACY",
                "adequate_major_matchups": "|".join(adequate_opponents),
                "low_sample_major_matchups": "|".join(low_sample_opponents),
                "unobserved_major_matchups": "|".join(unobserved_opponents),
                "meta_weight_basis": "UNIQUE_TEAM_DAY_SHARE_WITHIN_MAJOR_MATCHUPS",
                "interpretation": (
                    "ASSUMPTION_NOT_POINT_ESTIMATE"
                    if scenario_name != "OBSERVED_ONLY_RENORMALIZED_LEGACY"
                    else "OBSERVED_CELLS_ONLY_RENORMALIZED_NOT_FULL_META_ESTIMATE"
                ),
            })
        output.append({
            "candidate_archetype": archetype,
            "exact_deck_hash": digest,
            "observed_games": len(rows),
            "unique_teams": len({str(row["team_id"]) for row in rows}),
            "unique_team_pairs": len(team_pairs),
            "unique_dates": len({str(row["date"]) for row in rows}),
            "raw_result_rate": f"{statistics.fmean(results):.8f}",
            "unit_equal_weight_result_rate": f"{unit_result:.8f}" if unit_result is not None else "",
            "unit_equal_weight_aggregated_units": canonical_unit_count,
            "result_aggregation_basis": "date+team_id+opponent_team_id+deck_hash+opponent_deck_hash",
            "result_vs_marnie": f"{matchup_results['marnie_grimmsnarl']:.8f}" if matchup_results["marnie_grimmsnarl"] is not None else "",
            "result_vs_alakazam": f"{matchup_results['alakazam_psychic']:.8f}" if matchup_results["alakazam_psychic"] is not None else "",
            "result_vs_cynthia_garchomp": f"{matchup_results['cynthia_garchomp']:.8f}" if matchup_results["cynthia_garchomp"] is not None else "",
            "result_vs_rocket": f"{matchup_results['rocket_mewtwo_spidops']:.8f}" if matchup_results["rocket_mewtwo_spidops"] is not None else "",
            "result_vs_kangaskhan_crustle": f"{matchup_results['kangaskhan_crustle']:.8f}" if matchup_results["kangaskhan_crustle"] is not None else "",
            "worst_major_matchup_result": f"{min(observed_major):.8f}" if observed_major else "",
            "meta_weighted_major_matchup_result": f"{meta_weighted:.8f}" if meta_weighted is not None else "",
            "meta_observed_only_renormalized_legacy": f"{meta_weighted:.8f}" if meta_weighted is not None else "",
            "meta_unobserved_only_as_0_result": f"{scenario_values['UNOBSERVED_ONLY_AS_0']:.8f}",
            "meta_unobserved_only_as_0_25_result": f"{scenario_values['UNOBSERVED_ONLY_AS_0_25']:.8f}",
            "meta_unobserved_only_as_0_50_result": f"{scenario_values['UNOBSERVED_ONLY_AS_0_50']:.8f}",
            "meta_loss_bound": f"{scenario_values['UNCERTAIN_AS_0']:.8f}",
            "meta_neutral_scenario": f"{scenario_values['UNCERTAIN_AS_0_50']:.8f}",
            "meta_win_bound": f"{scenario_values['UNCERTAIN_AS_1']:.8f}",
            "meta_observed_worst_fill": (
                f"{scenario_values['OBSERVED_WORST_FILL']:.8f}"
                if scenario_values["OBSERVED_WORST_FILL"] is not None else ""
            ),
            "meta_scenario_width": f"{uncertain_weight:.8f}",
            "meta_weight_coverage": f"{observed_meta_weight:.8f}",
            "meta_adequately_observed_weight": f"{adequate_weight:.8f}",
            "meta_low_sample_weight": f"{low_sample_weight:.8f}",
            "meta_unobserved_weight": f"{unobserved_weight:.8f}",
            "meta_uncertain_weight": f"{uncertain_weight:.8f}",
            "meta_weight_basis": "UNIQUE_TEAM_DAY_SHARE_WITHIN_MAJOR_MATCHUPS",
            "meta_weighted_interpretation": "OBSERVED_ONLY_RENORMALIZED_LEGACY_NOT_FULL_META_ESTIMATE",
            "adequate_major_matchups": "|".join(adequate_opponents),
            "low_sample_major_matchups": "|".join(low_sample_opponents),
            "unobserved_major_matchups": "|".join(unobserved_opponents),
            "scenario_is_assumption": True,
            "first_attack_turn": f"{statistics.fmean(first_turns):.8f}" if first_turns else "",
            "no_attack_turn_rate": f"{no_attack_numerator / no_attack_denominator:.8f}" if no_attack_denominator else "",
            "second_attacker_ready_rate": f"{sum(ready) / len(ready):.8f}" if ready else "",
            "second_attacker_ready_definition": "LEGACY_V1_ANY_BENCH_PRINTED_ATTACK_COST_READY",
            "second_attacker_ready_deprecated_for_selection": True,
            "next_attacker_distance_lower_bound_coverage": (
                f"{distance_lower_bound_coverage:.8f}"
                if distance_lower_bound_coverage is not None else ""
            ),
            "next_attacker_distance_lower_bound_median": (
                f"{statistics.median(distance_lower_bounds):.8f}"
                if distance_lower_bounds else ""
            ),
            "next_attacker_distance_certified_upper_bound_coverage": (
                f"{distance_upper_bound_coverage:.8f}"
                if distance_upper_bound_coverage is not None else ""
            ),
            "next_attacker_distance_certified_upper_bound_median": (
                f"{statistics.median(distance_upper_bounds):.8f}"
                if distance_upper_bounds else ""
            ),            "next_attacker_distance_known_coverage": (
                f"{distance_coverage:.8f}" if distance_coverage is not None else ""
            ),
            "next_attacker_distance_zero_rate_known": (
                f"{sum(value == 0 for value in known_distances) / len(known_distances):.8f}"
                if known_distances else ""
            ),
            "next_attacker_distance_le_1_rate_known": (
                f"{sum(value <= 1 for value in known_distances) / len(known_distances):.8f}"
                if known_distances else ""
            ),
            "next_attacker_distance_le_2_rate_known": (
                f"{sum(value <= 2 for value in known_distances) / len(known_distances):.8f}"
                if known_distances else ""
            ),
            "next_attacker_distance_3_plus_rate_known": (
                f"{sum(value >= 3 for value in known_distances) / len(known_distances):.8f}"
                if known_distances else ""
            ),
            "next_attacker_distance_median_known": (
                f"{statistics.median(known_distances):.8f}" if known_distances else ""
            ),
            "next_attacker_distance_mean_known": (
                f"{statistics.fmean(known_distances):.8f}" if known_distances else ""
            ),
            "next_attacker_distance_unknown_rate": (
                f"{1.0 - distance_coverage:.8f}" if distance_coverage is not None else ""
            ),
            "next_attacker_distance_model_version": "KNOWN_HAND_BOARD_SELF_ACTIONS_V1",
            "next_attacker_distance_interpretation": "PROVISIONAL_MODEL_SCOPE_NOT_SELECTION_GRADE",
            "opening_failure_rate": f"{sum(feature.first_attack_turn is None or feature.first_attack_turn > 2 for feature in seat_features) / len(seat_features):.8f}",
            "first_player_result": f"{statistics.fmean(order_results['FIRST']):.8f}" if order_results["FIRST"] else "",
            "second_player_result": f"{statistics.fmean(order_results['SECOND']):.8f}" if order_results["SECOND"] else "",
            "unknown_order_rate": f"{sum(feature.starting_order == 'UNKNOWN' for feature in seat_features) / len(seat_features):.8f}",
            "exact_deck_variant_count": variant_count[archetype],
            "action_history_coverage": f"{sum(feature.action_history_present for feature in seat_features) / len(seat_features):.8f}",
            "deck_legality_and_engine_certainty": f"OBSERVED_60_CARDS={len(str(rows[0]['deck']).split()) == 60};UNRESOLVED_CARD_IDS={len(unresolved)}",
            "runtime_evidence": "RECORDED_ACTION_VALID;FALLBACK_UNKNOWN;INVALID_ACTION_UNKNOWN;TIMING_IS_APPROXIMATION",
            "card_effect_implementation_risk": implementation,
            "rule_based_policy_complexity": complexity,
            "observed_time_proxy": f"{statistics.fmean(timing):.8f}" if timing else "",
            "low_sample_flag": warnings["low_sample_flag"],
            "single_date_warning": warnings["single_date_warning"],
            "single_team_dominance_warning": warnings["single_team_dominance_warning"],
            "repeated_exact_deck_warning": warnings["repeated_exact_deck_warning"],
            "dependence_warning": warnings["dependence_warning"],
            "data_limitations": "PUBLIC_DAILY_TOP_SELECTED;DEPENDENT_REPEATED_TEAMS;NO_CAUSAL_ACTION_EFFECT",
        })
    return output, scenario_output


def build_sensitivity_markdown(
    scorecard: Sequence[Mapping[str, Any]],
    sensitivity: Sequence[Mapping[str, Any]],
    meta_scenarios: Sequence[Mapping[str, Any]],
) -> str:
    def percent(value: Any) -> str:
        parsed = as_float(value)
        return f"{parsed * 100:.2f}%" if parsed is not None else "-"

    selected_score = next(
        (
            row for row in scorecard
            if row["exact_deck_hash"] == SELECTED_ALAKAZAM_HASH
        ),
        None,
    )
    matchup_rows = {
        str(row["aggregation_method"]): row
        for row in sensitivity
        if row["exact_deck_hash"] == SELECTED_ALAKAZAM_HASH
        and row["opponent_archetype"] == "marnie_grimmsnarl"
    }
    scenario_rows = {
        str(row["scenario"]): row
        for row in meta_scenarios
        if row["exact_deck_hash"] == SELECTED_ALAKAZAM_HASH
    }
    method_order = (
        "EPISODE_RAW",
        "TEAM_PAIR_DAY_EQUAL",
        "TEAM_PAIR_DAY_EXCLUDE_SINGLE_GAME_UNITS",
        "TEAM_PAIR_DAY_MIN_5_GAMES",
        "EXACT_PAIR_DAY_EPISODE_WITHIN",
        "EXACT_PAIR_DAY_TEAM_PAIR_WITHIN",
        "DATE_OUTER_EQUAL",
        "EXACT_PAIR_OUTER_EQUAL",
    )
    scenario_order = (
        "UNOBSERVED_ONLY_AS_0",
        "UNOBSERVED_ONLY_AS_0_25",
        "UNOBSERVED_ONLY_AS_0_50",
        "OBSERVED_ONLY_RENORMALIZED_LEGACY",
        "UNCERTAIN_AS_0",
        "UNCERTAIN_AS_0_50",
        "UNCERTAIN_AS_1",
        "OBSERVED_WORST_FILL",
    )
    lines = [
        "# デッキ選定感度分析",
        "",
        f"対象はフーディン exact hash `{SELECTED_ALAKAZAM_HASH}` である。",
        "公開Daily Topの選択標本に対する記述的な感度分析であり、母集団勝率の推定ではない。",
        "",
        "## フーディン対マーニーの集約感度",
        "",
        "| 集約方法 | 対象試合 | unit数 | 結果率 | leave-one-team範囲 | 最大unit試合比率 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in method_order:
        row = matchup_rows.get(method)
        if row is None:
            continue
        loo_range = (
            f"{percent(row['loo_team_min'])}–{percent(row['loo_team_max'])}"
            if row["loo_team_min"] != "" and row["loo_team_max"] != "" else "-"
        )
        lines.append(
            f"| `{method}` | {row['included_games']} | {row['aggregated_units']} | "
            f"{percent(row['result_rate'])} | {loo_range} | {percent(row['max_unit_game_share'])} |"
        )
    lines.extend([
        "",
        "`TEAM_PAIR_DAY_EQUAL` の正規キーは "
        "`(date, team_id, opponent_team_id, deck_hash, opponent_deck_hash)` である。",
        "集約方式またはleave-one-outで50%の上下が変わる場合、対マーニー優位は `SENSITIVE` と扱う。",
        "",
        "## 未観測・low-sample主要対面のシナリオ",
        "",
        "| シナリオ | 仮定値 | 結果 | 解釈 |",
        "|---|---:|---:|---|",
    ])
    for scenario in scenario_order:
        row = scenario_rows.get(scenario)
        if row is None:
            continue
        lines.append(
            f"| `{scenario}` | {percent(row['assumed_uncertain_result'])} | "
            f"{percent(row['scenario_result'])} | {row['interpretation']} |"
        )
    if selected_score is not None:
        lines.extend([
            "",
            f"観測済み主要対面weightは {percent(selected_score['meta_weight_coverage'])}、"
            f"未観測weightは {percent(selected_score['meta_unobserved_weight'])} である。",
            "観測済みだけを再正規化した値は、全メタ推定値ではなくlegacy比較値としてのみ残す。",
            "",
            "## 次アタッカー距離",
            "",
            f"- legacy即時準備率: {percent(selected_score['second_attacker_ready_rate'])}",
            f"- v1距離点値coverage: {percent(selected_score['next_attacker_distance_known_coverage'])}",
            f"- 構造下限coverage: {percent(selected_score['next_attacker_distance_lower_bound_coverage'])}",
            f"- 構造下限中央値: {selected_score['next_attacker_distance_lower_bound_median'] or '-'}",
            f"- 既知手札経路上限coverage: {percent(selected_score['next_attacker_distance_certified_upper_bound_coverage'])}",
            f"- 既知手札経路上限中央値: {selected_score['next_attacker_distance_certified_upper_bound_median'] or '-'}",
            f"- 距離0率（既知分母）: {percent(selected_score['next_attacker_distance_zero_rate_known'])}",
            f"- 距離1以下率（既知分母）: {percent(selected_score['next_attacker_distance_le_1_rate_known'])}",
            f"- 距離2以下率（既知分母）: {percent(selected_score['next_attacker_distance_le_2_rate_known'])}",
            f"- 距離中央値（既知分母）: {selected_score['next_attacker_distance_median_known'] or '-'}",
            "",
            "v1距離は最初の攻撃直前observationだけを使い、場出し・進化・Rare Candy・手張りの既知手札経路を数える。",
            "将来ドロー、検索・回収・加速効果、相手干渉、KO昇格、交代、ターン待ちはモデル外であり、"
            "経路が証明できない席は数値へ丸めずUNKNOWNにする。",
        ])
    lines.extend([
        "",
        "## 判定",
        "",
        "フーディンは最小実装で検証する暫定候補として維持する。",
        "ただし、集約方式・チーム除外・未観測対面仮定に敏感なため、最終採用デッキとは確定しない。",
        "150～300ルールの大規模化には進まず、ローカル両席同一seed比較を先に行う。",
        "",
    ])
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    args = parser.parse_args()
    root = args.root.resolve()
    raw_root = root  / "_local_generated" / "analysis_outputs" / "rocket_preimplementation_meta_20260727" / "raw"
    verified = root  / "_local_generated" / "analysis_outputs" / "rocket_preimplementation_meta_20260727" / "verified_top_band_7d"
    work = root  / "_local_generated" / "analysis_outputs" / "rocket_preimplementation_meta_20260727" / "deck_selection_analysis"
    reports = root / "reports"
    work.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    ensure_engine_on_path((root / args.engine_dir).resolve() if not args.engine_dir.is_absolute() else args.engine_dir)
    from cg.api import all_attack, all_card_data
    cards = {int(card.cardId): card for card in all_card_data()}
    attacks = {int(attack.attackId): attack for attack in all_attack()}
    card_names = {card_id: card.name for card_id, card in cards.items()}
    card_types = {card_id: int(card.cardType) for card_id, card in cards.items()}
    card_roles = {card_id: estimate_card_role(card) for card_id, card in cards.items()}
    attack_ready = make_attack_ready(cards, attacks)
    next_attacker_distance = make_next_attacker_distance(cards, attacks)

    leaderboard_path = raw_root / "full_leaderboard.csv"
    leaderboard = read_csv(leaderboard_path)
    aliases, ambiguous_aliases = build_leaderboard_aliases(leaderboard)
    missing_rows: list[dict[str, Any]] = []
    source_files: set[Path] = {leaderboard_path}
    enriched: list[dict[str, Any]] = []
    features: dict[tuple[str, int], SeatFeatures] = {}
    events: list[dict[str, Any]] = []
    selected_episode_ids: set[str] = set()
    read_failures = 0
    action_episode_ids: set[str] = set()
    known_order_episode_ids: set[str] = set()

    for date in DATES:
        if date == "2026-07-25":
            sample_dir = raw_root / "daily_top" / f"{date}-sample"
            decks_path = raw_root / "daily_top" / f"{date}-decks" / "decks.csv"
        else:
            sample_dir = raw_root / "daily_top_7d" / f"{date}-sample"
            decks_path = raw_root / "daily_top_7d" / f"{date}-decks" / "decks.csv"
        manifest_path = sample_dir / "manifest.csv"
        source_files.update({manifest_path, decks_path})
        manifest = read_csv(manifest_path)
        ranked = sorted(
            manifest,
            key=lambda row: (float(row["avg_score"]), int(row["episode_id"])),
            reverse=True,
        )
        selected = ranked[:50]
        ranks = {row["episode_id"]: index for index, row in enumerate(ranked, 1)}
        scores = {row["episode_id"]: row["avg_score"] for row in ranked}
        selected_ids = {row["episode_id"] for row in selected}
        deck_rows = [row for row in read_csv(decks_path) if row["episode_id"] in selected_ids]
        by_episode_deck: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in deck_rows:
            by_episode_deck[row["episode_id"]].append(row)
        for episode_id in sorted(selected_ids, key=int):
            selected_episode_ids.add(episode_id)
            json_path = sample_dir / f"{episode_id}.json"
            source_files.add(json_path)
            if not json_path.exists():
                missing_rows.append({"date": date, "episode_id": episode_id, "file": str(json_path.relative_to(root)), "issue": "MISSING_FILE", "details": ""})
                continue
            try:
                doc = json.loads(json_path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                read_failures += 1
                missing_rows.append({"date": date, "episode_id": episode_id, "file": str(json_path.relative_to(root)), "issue": "READ_FAILURE", "details": str(error)})
                continue
            episode_decks = sorted(by_episode_deck.get(episode_id, []), key=lambda row: int(row["player_index"]))
            if len(episode_decks) != 2:
                missing_rows.append({"date": date, "episode_id": episode_id, "file": str(json_path.relative_to(root)), "issue": "DECK_ROW_COUNT", "details": str(len(episode_decks))})
                continue
            first_player = find_first_player(doc)
            if first_player in (0, 1):
                known_order_episode_ids.add(episode_id)
            built_rows: list[dict[str, Any]] = []
            for source in episode_decks:
                seat = int(source["player_index"])
                cards_in_deck = [int(value) for value in source["deck"].split()]
                classification = classify_deck(cards_in_deck)
                leader = aliases.get(source["team"])
                reward = as_int(source["reward"])
                built_rows.append({
                    "date": date,
                    "episode_id": episode_id,
                    "file": str(json_path.relative_to(root)),
                    "player_index": seat,
                    "team": source["team"],
                    "team_id": leader["TeamId"] if leader else "",
                    "reward": reward if reward is not None else "",
                    **classification,
                    "deck": source["deck"],
                    "deck_hash": deck_hash(cards_in_deck),
                    "deck_signature": deck_signature(cards_in_deck),
                    "leaderboard_rank": leader["Rank"] if leader else "",
                    "daily_episode_rank": ranks[episode_id],
                    "daily_avg_score": scores[episode_id],
                    "starting_order": "FIRST" if first_player == seat else "SECOND" if first_player in (0, 1) else "UNKNOWN",
                    "first_or_second_known": first_player in (0, 1),
                    "source_population": SOURCE_POPULATION,
                })
            for seat in (0, 1):
                row, opponent = built_rows[seat], built_rows[1 - seat]
                row.update({
                    "opponent_team": opponent["team"],
                    "opponent_team_id": opponent["team_id"],
                    "opponent_archetype": opponent["archetype"],
                    "opponent_deck_hash": opponent["deck_hash"],
                })
                enriched.append(row)
                features[(episode_id, seat)] = SeatFeatures(
                    episode_id=episode_id,
                    seat=seat,
                    team=row["team"],
                    team_id=row["team_id"],
                    archetype=row["archetype"],
                    deck_hash=row["deck_hash"],
                    opponent_team=row["opponent_team"],
                    opponent_team_id=row["opponent_team_id"],
                    opponent_archetype=row["opponent_archetype"],
                    opponent_deck_hash=row["opponent_deck_hash"],
                    reward=reward if (reward := as_int(row["reward"])) is not None else None,
                    starting_order=row["starting_order"],
                )
            local_features = {seat: features[(episode_id, seat)] for seat in (0, 1)}
            visual_features(doc, local_features, card_types, attack_ready, first_player)
            episode_events = decision_events(
                doc, local_features, card_types, attack_ready, next_attacker_distance, first_player
            )
            for event in episode_events:
                event["date"] = date
            events.extend(episode_events)
            if episode_events:
                action_episode_ids.add(episode_id)

    enriched.sort(key=lambda row: (row["date"], int(row["episode_id"]), int(row["player_index"])))
    events.sort(key=lambda row: (row["date"], int(row["episode_id"]), int(row["replay_step"]), int(row["player_index"])))
    write_csv(verified / "enriched_decks_7d.csv", ENRICHED_FIELDS, enriched)
    action_fields = list(events[0]) if events else []
    write_csv(work / "action_events_7d.csv", action_fields, events)
    seat_feature_rows = []
    for feature_key in sorted(features):
        feature_row = dict(vars(features[feature_key]))
        feature_row["initial_bench_ids"] = " ".join(map(str, feature_row["initial_bench_ids"]))
        seat_feature_rows.append(feature_row)
    seat_feature_fields = list(seat_feature_rows[0]) if seat_feature_rows else []
    write_csv(work / "seat_features_7d.csv", seat_feature_fields, seat_feature_rows)

    matchups = matchup_rows(enriched)
    matchup_fields = list(matchups[0]) if matchups else []
    write_csv(reports / "matchup_matrix.csv", matchup_fields, matchups)
    openings = aggregate_openings(enriched, features, events)
    opening_fields = list(openings[0]) if openings else []
    write_csv(reports / "opening_sequence_patterns.csv", opening_fields, openings)
    diffs = winner_loser_diff(enriched, features, events)
    diff_fields = list(diffs[0]) if diffs else []
    write_csv(reports / "winner_loser_action_diff.csv", diff_fields, diffs)
    variants, common_core, comparison_md = exact_deck_outputs(enriched, card_names, card_types, card_roles)
    write_csv(reports / "exact_deck_variants.csv", list(variants[0]) if variants else [], variants)
    write_csv(reports / "deck_common_core.csv", list(common_core[0]) if common_core else [], common_core)
    (reports / "deck_variant_comparison.md").write_text(comparison_md, encoding="utf-8")
    scorecard, meta_scenarios = candidate_scorecard(enriched, features, events, cards)
    write_csv(reports / "candidate_deck_scorecard.csv", list(scorecard[0]) if scorecard else [], scorecard)
    sensitivity = candidate_matchup_sensitivity(enriched)
    write_csv(
        reports / "candidate_matchup_aggregation_sensitivity.csv",
        list(sensitivity[0]) if sensitivity else [],
        sensitivity,
    )
    write_csv(
        reports / "candidate_meta_scenarios.csv",
        list(meta_scenarios[0]) if meta_scenarios else [],
        meta_scenarios,
    )
    (reports / "deck_selection_sensitivity.md").write_text(
        build_sensitivity_markdown(scorecard, sensitivity, meta_scenarios),
        encoding="utf-8",
    )

    write_csv(
        reports / "missing_or_invalid_episodes.csv",
        ["date", "episode_id", "file", "issue", "details"],
        missing_rows,
    )

    by_episode: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in enriched:
        by_episode[str(row["episode_id"])].append(row)
    reward_pair_failures = sum(
        sorted(as_int(row["reward"]) for row in rows) != [-1, 1]
        for rows in by_episode.values() if len(rows) == 2
    )
    deck_size_failures = sum(len(str(row["deck"]).split()) != 60 for row in enriched)
    unknown = sum(row["archetype"] == "unknown" for row in enriched)
    missing_hash = sum(not row["deck_hash"] for row in enriched)
    duplicate_keys = len(enriched) - len({(row["episode_id"], row["player_index"]) for row in enriched})
    opponent_mismatch = sum(
        len(rows) != 2 or any(
            row["opponent_team"] != rows[1 - int(row["player_index"])]["team"]
            for row in rows
        )
        for rows in by_episode.values()
    )
    validation_text = f"""# Episode解析検証

## 対象

- 期間：{DATES[0]} から {DATES[-1]}
- 選択：各日 `avg_score` 上位50試合
- 期待episode数：350
- 読み込み済みepisode数：{len(by_episode)}
- 期待席数：700
- 出力席数：{len(enriched)}

## 完全性

| 検査 | 結果 |
|---|---:|
| episode種類数 | {len(by_episode)} |
| 2席でないepisode | {sum(len(rows) != 2 for rows in by_episode.values())} |
| 60枚でないデッキ | {deck_size_failures} |
| rewardが-1/+1でないepisode | {reward_pair_failures} |
| 未分類 | {unknown} |
| deck_hash欠損 | {missing_hash} |
| opponent対応不一致 | {opponent_mismatch} |
| episode-seat重複 | {duplicate_keys} |
| 元JSON欠損・読込失敗 | {len(missing_rows)} |

## 行動履歴

- 行動履歴を復元できたepisode：{len(action_episode_ids)} / {len(by_episode)}
- `current.firstPlayer`を確認できたepisode：{len(known_order_episode_ids)} / {len(by_episode)}
- fallback：明示証拠がないため `UNKNOWN`
- invalid action：完全記録の保証がないため `UNKNOWN`
- 処理時間：同一席・同一ターン内の `remainingOverageTime` 差分だけを近似値として使用

## 集約定義

`raw_result_rate = (wins + 0.5 * draws) / raw_games`。

`team_pair_day` と `exact_deck_pair_day` は、各ユニット内のresult rateを計算し、ユニットを等加重平均する。

`descriptive_win_rate` は `episode_raw` ではraw result rate、集約単位ではunit-equal-weight result rateを格納する。

通常の二項信頼区間と有意差検定は使用しない。
"""
    validation_text += (
        "\n## \u884c\u52d5\u30fb\u72b6\u614b\u6307\u6a19\u306e\u64cd\u4f5c\u7684\u5b9a\u7fa9\n\n"
        "- `recorded_action_valid=TRUE` \u306f\u8a18\u9332action\u306eoption index\u3068\u9078\u629e\u679a\u6570\u304clegal action\u306e\u7bc4\u56f2\u5185\u3060\u3063\u305f\u3053\u3068\u3060\u3051\u3092\u8868\u3057\u3001fallback\u3084invalid action\u304c\u4e0d\u5b58\u5728\u3060\u3063\u305f\u3053\u3068\u306f\u8868\u3055\u306a\u3044\u3002\n"
        "- `forced_choice=TRUE` \u306f `minCount..maxCount` \u306e\u5168\u9078\u629e\u6570\u3092\u5c55\u958b\u3057\u3001\u610f\u5473\u4e0a\u91cd\u8907\u3059\u308b\u5019\u88dc\u3092\u9664\u3044\u305f\u5b8c\u5168action\u304c1\u901a\u308a\u3060\u3051\u3060\u3063\u305f\u3053\u3068\u3092\u8868\u3059\u3002\n"
        "- `opening_failure_rate` \u306f\u6700\u521d\u306e\u653b\u6483\u304c\u81ea\u5206\u306e\u7b2c2\u30bf\u30fc\u30f3\u307e\u3067\u306b\u8a18\u9332\u3055\u308c\u306a\u304b\u3063\u305f\u5e2d\u306e\u6bd4\u7387\u3067\u3042\u308b\u3002\n"
        "- `second_attacker_ready` \u306f\u6700\u521d\u306e\u653b\u6483\u6642\u70b9\u3067\u30d9\u30f3\u30c1\u306b\u653b\u6483\u53ef\u80fd\u306a\u5225\u30dd\u30b1\u30e2\u30f3\u304c\u5b58\u5728\u3057\u305f\u304b\u3092\u8868\u3059\u3002\n"
        "- `no_attack_turns` \u306f\u5e2d\u3054\u3068\u306b `TurnStart` \u3067\u653b\u6483\u30d5\u30e9\u30b0\u3092\u521d\u671f\u5316\u3057\u3001`Attack` \u3067\u7acb\u3066\u3001`TurnEnd` \u3067\u672a\u653b\u6483\u306a\u3089\u52a0\u7b97\u3059\u308b\u72b6\u614b\u8ffd\u8de1\u3067\u7b97\u51fa\u3059\u308b\u3002\n"
        "- \u6700\u521d\u306e\u30b5\u30a4\u30c9\u53d6\u5f97\u306f `MoveCard(fromArea=6,toArea=2)` \u3068visualizer frame\u306e\u53cc\u65b9\u304b\u3089\u7167\u5408\u3057\u3001frame\u756a\u53f7\u3092\u4fdd\u5b58\u3059\u308b\u3002\n"
        "- \u51e6\u7406\u6642\u9593\u8fd1\u4f3c\u306f\u9023\u7d9a\u3059\u308bACTIVE\u89b3\u6e2c\u3067 `current.yourIndex` \u304c\u540c\u3058\u5e2d\u3001\u304b\u3064global turn\u304c\u540c\u3058\u5834\u5408\u3060\u3051\u3092 `CONTIGUOUS_SAME_PLAYER_APPROX` \u3068\u3059\u308b\u3002\n"
        "- low sample\u306fraw games\u304c5\u672a\u6e80\u3001unique team pair\u304c3\u672a\u6e80\u3001\u307e\u305f\u306f\u5404\u96c6\u7d04unit\u304c10\u672a\u6e80\u306e\u3044\u305a\u308c\u304b\u306b\u52a0\u3048\u3001\u6bd4\u8f03\u8868\u3067\u306f\u5404\u7fa4\u30fb\u5404team\u304c2\u672a\u6e80\u306e\u5834\u5408\u306b\u3082\u4ed8\u4e0e\u3059\u308b\u3002\n"
        "- single date\u3001single team dominance\u3001repeated exact deck\u306flow sample\u3068\u306f\u5225\u306e\u4f9d\u5b58\u6027\u8b66\u544a\u3068\u3057\u3066\u4fdd\u6301\u3059\u308b\u3002\n"
    )
    validation_text += (
        "\n## 集約感度・シナリオ・次アタッカー距離\n\n"
        "- candidate scorecard の正規 `team_pair_day` キーは "
        "`(date, team_id, opponent_team_id, deck_hash, opponent_deck_hash)` とし、"
        "matchup matrix と統一する。\n"
        "- `candidate_matchup_aggregation_sensitivity.csv` はraw、正規unit等加重、"
        "単試合unit除外、5試合以上unit、exact-pair階層、date外側等加重、"
        "exact-pair外側等加重とleave-one-out範囲を併記する。\n"
        "- `candidate_meta_scenarios.csv` の0/0.25/0.5/1およびworst-fillは仮定であり、"
        "母集団勝率の点推定ではない。observed-only再正規化値はlegacy比較値である。\n"
        "- `second_attacker_ready` は `LEGACY_V1_ANY_BENCH_PRINTED_ATTACK_COST_READY` として"
        "再現確認用に残し、デッキ選定には使用しない。\n"
        "- `next_attacker_action_distance` v1は最初の攻撃直前ACTIVE observationだけを使い、"
        "最初の攻撃カードと同じprinted card IDへ至る既知の場・手札からのBasic場出し、進化、Rare Candy、Energy装着の自己root actionを"
        "幅優先探索したmodel-scope値である。\n"
        "- 将来ドロー、検索・回収・加速効果、相手干渉、KO昇格、retreat/switch、"
        "ターン待ちはv1の範囲外である。supported pathがない席はFalseや3へ丸めずUNKNOWNにする。\n"
        "- 距離値は勝敗や最初の攻撃後の行動を参照しない。"
        "`first_attack_snapshot_hash` と証明pathをseat featuresへ保存する。\n"
    )
    (reports / "episode_analysis_validation.md" ).write_text(validation_text, encoding="utf-8")

    output_paths = [
        verified / "enriched_decks_7d.csv",
        work / "action_events_7d.csv",
        work / "seat_features_7d.csv",
        reports / "episode_analysis_validation.md",
        reports / "missing_or_invalid_episodes.csv",
        reports / "matchup_matrix.csv",
        reports / "opening_sequence_patterns.csv",
        reports / "winner_loser_action_diff.csv",
        reports / "exact_deck_variants.csv",
        reports / "deck_common_core.csv",
        reports / "deck_variant_comparison.md",
        reports / "candidate_deck_scorecard.csv",
        reports / "candidate_matchup_aggregation_sensitivity.csv",
        reports / "candidate_meta_scenarios.csv",
        reports / "deck_selection_sensitivity.md",
    ]
    manifest = {
        "schema_version": "top_band_episode_history.v2",
        "period": {"start": DATES[0], "end": DATES[-1]},
        "episodes": len(by_episode),
        "seats": len(enriched),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_script": "infrastructure/tools/analyze_top_band_episode_history.py",
        "generation_script_sha256": sha256_file(Path(__file__).resolve()),
        "git_commit": git_commit(root),
        "ambiguous_leaderboard_alias_count": len(ambiguous_aliases),
        "inputs": [
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(source_files)
            if path.exists()
        ],
        "outputs": [
            {
                "path": str(path.relative_to(root)),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in output_paths
        ],
    }
    manifest_path = work / "analysis_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "episodes": len(by_episode),
        "seats": len(enriched),
        "events": len(events),
        "matchup_rows": len(matchups),
        "opening_rows": len(openings),
        "diff_rows": len(diffs),
        "variant_rows": len(variants),
        "scorecard_rows": len(scorecard),
        "missing_or_invalid": len(missing_rows),
        "manifest": str(manifest_path),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
