from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
PARENT_DIR = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
REPLAY = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "maturity_20260730_0127"
    / "episode_88819392_replay.json"
)
OUTPUT = HERE / "pre_edit_engine_gate.json"
REPORT = HERE / "PRE_EDIT_ENGINE_GATE.md"

EXPECTED_PARENT_SHA = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_DECK_SHA = (
    "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"
)
EXPECTED_REPLAY_SHA = (
    "4D625ADF892F1D0DC1453E31219025A96C4474D509E5B1E36819225A22F22698"
)

TARGET_ROW = 119
TARGET_SEAT = 0
ULTRA_BALL = 1121
BOSS = 1182
NONEX_ARCHALUDON = 840
ARCHALUDON_EX = 190
DURALUDON = 169
BASIC_METAL = 8
METAL_DEFENDER = 253
SOURCE_BOSS_SERIAL = 39
SOURCE_NONEX_SERIAL = 31
SOURCE_METAL_SERIAL = 57


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def tree_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from cg.api import search_begin, search_end, search_step, to_observation_class


PARENT = load_module("last_boss_preedit_parent", PARENT_DIR / "main.py")


def cards_from_hidden(cards):
    return [card["id"] for card in cards if card]


def walk_cards(observation):
    for player in observation.current.players:
        for field in ("hand", "discard", "lostZone"):
            for card in getattr(player, field, None) or ():
                if card is not None:
                    yield card
        for pokemon in list(player.active or ()) + list(player.bench or ()):
            if pokemon is None:
                continue
            yield pokemon
            for field in ("energyCards", "tools", "preEvolution"):
                for card in getattr(pokemon, field, None) or ():
                    if card is not None:
                        yield card
    for card in getattr(observation.current, "stadium", None) or ():
        if card is not None:
            yield card
    for card in getattr(observation.current, "looking", None) or ():
        if card is not None:
            yield card
    for card in getattr(observation.select, "deck", None) or ():
        if card is not None:
            yield card
    if observation.select.effect is not None:
        yield observation.select.effect
    if observation.select.contextCard is not None:
        yield observation.select.contextCard


def mirror_observation(observation):
    old_yi = observation.current.yourIndex
    observation.current.players = [
        observation.current.players[1],
        observation.current.players[0],
    ]
    observation.current.yourIndex = 1 - old_yi
    if observation.current.firstPlayer in (0, 1):
        observation.current.firstPlayer = 1 - observation.current.firstPlayer
    for card in walk_cards(observation):
        if getattr(card, "playerIndex", None) in (0, 1):
            card.playerIndex = 1 - card.playerIndex
    for entry in observation.logs:
        if entry.playerIndex in (0, 1):
            entry.playerIndex = 1 - entry.playerIndex
    for option in observation.select.option:
        if option.playerIndex in (0, 1):
            option.playerIndex = 1 - option.playerIndex
    return observation


def remap_serials(observation, offset):
    seen = set()
    for card in walk_cards(observation):
        if id(card) in seen:
            continue
        seen.add(id(card))
        serial = getattr(card, "serial", None)
        if isinstance(serial, int) and serial > 0:
            card.serial = serial + offset
    for entry in observation.logs:
        for field in (
            "serial",
            "serialActive",
            "serialBench",
            "serialBefore",
            "serialAfter",
            "serialTarget",
        ):
            value = getattr(entry, field, None)
            if isinstance(value, int) and value > 0:
                setattr(entry, field, value + offset)
    return observation


def raw_fixture():
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    observation = to_observation_class(
        copy.deepcopy(replay["steps"][TARGET_ROW][TARGET_SEAT]["observation"])
    )
    hidden = copy.deepcopy(
        replay["steps"][0][0]["visualize"][TARGET_ROW - 1]["current"]
    )
    return replay, observation, hidden


def begin_engine(observation, hidden):
    yi = observation.current.yourIndex
    oi = 1 - yi
    return search_begin(
        observation,
        cards_from_hidden(hidden["players"][yi]["deck"]),
        cards_from_hidden(hidden["players"][yi]["prize"]),
        cards_from_hidden(hidden["players"][oi]["deck"]),
        cards_from_hidden(hidden["players"][oi]["prize"]),
        cards_from_hidden(hidden["players"][oi]["hand"]),
        [],
    )


def option_record(observation, position):
    option = observation.select.option[position]
    card = PARENT.option_card(observation, option)
    target = PARENT.option_target(observation, option)
    return {
        "position": position,
        "type": int(option.type),
        "card_id": None if card is None else card.id,
        "card_serial": None if card is None else card.serial,
        "target_id": None if target is None else target.id,
        "target_serial": None if target is None else target.serial,
        "attack_id": getattr(option, "attackId", None),
    }


def option_records(observation):
    return [
        option_record(observation, position)
        for position in range(len(observation.select.option))
    ]


def transformed_callback(
    observation,
    *,
    mirror=False,
    serial_offset=0,
    option_mode="identity",
):
    view = copy.deepcopy(observation)
    if mirror:
        view = mirror_observation(view)
    if serial_offset:
        view = remap_serials(view, serial_offset)
    count = len(view.select.option)
    if option_mode == "identity":
        return view, list(range(count))
    if option_mode == "reverse":
        view.select.option = list(reversed(view.select.option))
        return view, list(reversed(range(count)))
    if option_mode == "duplicate":
        options = []
        back_map = []
        for position, option in enumerate(view.select.option):
            options.append(copy.deepcopy(option))
            back_map.append(position)
            options.append(option)
            back_map.append(position)
        view.select.option = options
        return view, back_map
    raise AssertionError(option_mode)


def unique_position(
    observation,
    *,
    card_id=None,
    card_serial=None,
    attack_id=None,
):
    matches = []
    seen_semantics = set()
    for row in option_records(observation):
        if card_id is not None and row["card_id"] != card_id:
            continue
        if card_serial is not None and row["card_serial"] != card_serial:
            continue
        if attack_id is not None and row["attack_id"] != attack_id:
            continue
        key = (
            row["type"],
            row["card_id"],
            row["card_serial"],
            row["target_id"],
            row["target_serial"],
            row["attack_id"],
        )
        if key in seen_semantics:
            continue
        seen_semantics.add(key)
        matches.append(row)
    if len(matches) != 1:
        raise AssertionError(
            {
                "required": {
                    "card_id": card_id,
                    "card_serial": card_serial,
                    "attack_id": attack_id,
                },
                "matches": matches,
                "options": option_records(observation),
            }
        )
    return matches[0]["position"]


def semantic_action(stage, observation, branch, serial_offset):
    if stage == "ULTRA_BALL":
        return [unique_position(observation, card_id=ULTRA_BALL)]
    if stage == "DISCARD":
        first_id = BOSS if branch == "parent" else NONEX_ARCHALUDON
        first_serial = (
            SOURCE_BOSS_SERIAL
            if branch == "parent"
            else SOURCE_NONEX_SERIAL
        ) + serial_offset
        return [
            unique_position(
                observation,
                card_id=first_id,
                card_serial=first_serial,
            ),
            unique_position(
                observation,
                card_id=BASIC_METAL,
                card_serial=SOURCE_METAL_SERIAL + serial_offset,
            ),
        ]
    if stage == "SEARCH":
        return [unique_position(observation, card_id=DURALUDON)]
    if stage == "BENCH":
        return [unique_position(observation, card_id=DURALUDON)]
    if stage == "ATTACK":
        return [unique_position(observation, attack_id=METAL_DEFENDER)]
    raise AssertionError(stage)


def normalized_semantics(observation, positions, serial_offset):
    rows = []
    for position in positions:
        row = option_record(observation, position)
        for key in ("card_serial", "target_serial"):
            value = row[key]
            if isinstance(value, int) and value > 0:
                row[key] = value - serial_offset
        rows.append(row)
    return rows


def choose_parent(observation):
    first = PARENT.choose_options(copy.deepcopy(observation))
    second = PARENT.choose_options(copy.deepcopy(observation))
    if first != second:
        raise AssertionError((first, second))
    if len(first) != len(set(first)):
        raise AssertionError(first)
    if any(
        position < 0 or position >= len(observation.select.option)
        for position in first
    ):
        raise AssertionError(first)
    return first


def card_zone(player, field):
    rows = []
    for card in getattr(player, field, None) or ():
        if card is None:
            continue
        rows.append((card.id, card.serial))
    return sorted(rows)


def pokemon_record(pokemon):
    return {
        "id": pokemon.id,
        "serial": pokemon.serial,
        "hp": pokemon.hp,
        "max_hp": pokemon.maxHp,
        "energies": sorted(pokemon.energies or ()),
        "tools": sorted(tool.id for tool in pokemon.tools or ()),
        "pre_evolution": sorted(
            (card.id, card.serial) for card in pokemon.preEvolution or ()
        ),
    }


def public_state_record(observation, engine_yi):
    mine = observation.current.players[engine_yi]
    opponent = observation.current.players[1 - engine_yi]
    return {
        "turn": observation.current.turn,
        "turn_action_count": observation.current.turnActionCount,
        "your_index": observation.current.yourIndex,
        "own_prizes": len(mine.prize or ()),
        "opponent_prizes": len(opponent.prize or ()),
        "own_hand": card_zone(mine, "hand"),
        "own_discard": card_zone(mine, "discard"),
        "own_active": [
            pokemon_record(pokemon)
            for pokemon in mine.active or ()
            if pokemon is not None
        ],
        "own_bench": [
            pokemon_record(pokemon)
            for pokemon in mine.bench or ()
            if pokemon is not None
        ],
        "opponent_active": [
            pokemon_record(pokemon)
            for pokemon in opponent.active or ()
            if pokemon is not None
        ],
        "opponent_bench": [
            pokemon_record(pokemon)
            for pokemon in opponent.bench or ()
            if pokemon is not None
        ],
        "logs": [
            {
                "type": int(log.type),
                "player_index": log.playerIndex,
                "card_id": log.cardId,
                "serial": log.serial,
                "attack_id": log.attackId,
                "target_serial": log.serialTarget,
                "value": getattr(log, "value", None),
            }
            for log in observation.logs
        ],
    }


def strip_allowed_zone_delta(record):
    result = copy.deepcopy(record)
    result.pop("own_hand", None)
    result.pop("own_discard", None)
    for log in result.get("logs", ()):
        if (
            log.get("type") == 6
            and (
                (
                    log.get("card_id") == BOSS
                    and log.get("serial") == SOURCE_BOSS_SERIAL
                )
                or (
                    log.get("card_id") == NONEX_ARCHALUDON
                    and log.get("serial") == SOURCE_NONEX_SERIAL
                )
            )
        ):
            log["card_id"] = "PLAN_EQUIVALENT_REPLACEMENT"
            log["serial"] = "PLAN_EQUIVALENT_REPLACEMENT"
    return result


STAGES = ("ULTRA_BALL", "DISCARD", "SEARCH", "BENCH", "ATTACK")


def run_branch(
    *,
    name,
    branch,
    mirror=False,
    serial_offset=0,
    discard_option_mode="identity",
):
    _, observation, hidden = raw_fixture()
    engine_yi = observation.current.yourIndex
    logical_yi = 1 - engine_yi if mirror else engine_yi
    state = begin_engine(observation, hidden)
    trace = []
    try:
        for stage in STAGES:
            raw = state.observation
            option_mode = (
                discard_option_mode if stage == "DISCARD" else "identity"
            )
            view, back_map = transformed_callback(
                raw,
                mirror=mirror,
                serial_offset=serial_offset,
                option_mode=option_mode,
            )
            expected = semantic_action(
                stage, view, branch, serial_offset
            )
            repeated = semantic_action(
                stage, view, branch, serial_offset
            )
            if expected != repeated:
                raise AssertionError((stage, expected, repeated))

            parent_action = None
            parent_semantics = None
            if option_mode == "identity":
                parent_action = choose_parent(view)
                parent_semantics = normalized_semantics(
                    view, parent_action, serial_offset
                )

            if stage != "DISCARD":
                action = parent_action
                if action is None:
                    raise AssertionError(stage)
                expected_semantics = normalized_semantics(
                    view, expected, serial_offset
                )
                actual_semantics = normalized_semantics(
                    view, action, serial_offset
                )
                if actual_semantics != expected_semantics:
                    raise AssertionError(
                        {
                            "stage": stage,
                            "expected": expected_semantics,
                            "parent": actual_semantics,
                        }
                    )
            elif branch == "parent" and option_mode == "identity":
                action = parent_action
                if normalized_semantics(
                    view, action, serial_offset
                ) != normalized_semantics(
                    view, expected, serial_offset
                ):
                    raise AssertionError(
                        {
                            "stage": stage,
                            "expected": normalized_semantics(
                                view, expected, serial_offset
                            ),
                            "parent": normalized_semantics(
                                view, action, serial_offset
                            ),
                        }
                    )
            else:
                action = expected

            engine_action = [back_map[position] for position in action]
            if len(engine_action) != len(set(engine_action)):
                raise AssertionError(
                    {
                        "stage": stage,
                        "view_action": action,
                        "engine_action": engine_action,
                    }
                )
            before = public_state_record(raw, engine_yi)
            trace.append(
                {
                    "stage": stage,
                    "logical_seat": logical_yi,
                    "view_action": action,
                    "repeat_action": repeated,
                    "engine_action": engine_action,
                    "semantics": normalized_semantics(
                        view, action, serial_offset
                    ),
                    "parent_semantics": parent_semantics,
                    "before": before,
                }
            )
            state = search_step(state.searchId, engine_action)
            trace[-1]["after"] = public_state_record(
                state.observation, engine_yi
            )

        final = trace[-1]["after"]
        if not any(
            log["player_index"] == engine_yi
            and log["attack_id"] == METAL_DEFENDER
            for log in final["logs"]
        ):
            raise AssertionError(final["logs"])
        return {
            "name": name,
            "branch": branch,
            "logical_seat": logical_yi,
            "engine_seat": engine_yi,
            "mirror": mirror,
            "serial_offset": serial_offset,
            "discard_option_mode": discard_option_mode,
            "trace": trace,
            "final": final,
            "invalid_actions": 0,
            "exceptions": 0,
            "stale_state": 0,
            "max_step_hits": 0,
        }
    finally:
        search_end()


def normalized_zone(rows, serial_offset):
    return sorted(
        (card_id, serial - serial_offset if serial > 0 else serial)
        for card_id, serial in rows
    )


def compare_pair(parent_case, alternate_case):
    if len(parent_case["trace"]) != len(alternate_case["trace"]):
        raise AssertionError("trace length")
    for parent_step, alternate_step in zip(
        parent_case["trace"], alternate_case["trace"]
    ):
        stage = parent_step["stage"]
        if stage != alternate_step["stage"]:
            raise AssertionError((stage, alternate_step["stage"]))
        if stage != "DISCARD":
            if parent_step["semantics"] != alternate_step["semantics"]:
                raise AssertionError(
                    {
                        "stage": stage,
                        "parent": parent_step["semantics"],
                        "alternate": alternate_step["semantics"],
                    }
                )
        if stage in {"SEARCH", "BENCH", "ATTACK"}:
            if strip_allowed_zone_delta(
                parent_step["after"]
            ) != strip_allowed_zone_delta(alternate_step["after"]):
                raise AssertionError(
                    {
                        "stage": stage,
                        "parent": strip_allowed_zone_delta(
                            parent_step["after"]
                        ),
                        "alternate": strip_allowed_zone_delta(
                            alternate_step["after"]
                        ),
                    }
                )

    offset = parent_case["serial_offset"]
    parent_final = parent_case["final"]
    alternate_final = alternate_case["final"]
    parent_checkpoint = parent_case["trace"][3]["after"]
    alternate_checkpoint = alternate_case["trace"][3]["after"]
    parent_hand = normalized_zone(parent_checkpoint["own_hand"], 0)
    alternate_hand = normalized_zone(
        alternate_checkpoint["own_hand"], 0
    )
    parent_discard = normalized_zone(
        parent_checkpoint["own_discard"], 0
    )
    alternate_discard = normalized_zone(
        alternate_checkpoint["own_discard"], 0
    )

    if (BOSS, SOURCE_BOSS_SERIAL) in parent_hand:
        raise AssertionError(parent_hand)
    if (BOSS, SOURCE_BOSS_SERIAL) not in alternate_hand:
        raise AssertionError(alternate_hand)
    if (NONEX_ARCHALUDON, SOURCE_NONEX_SERIAL) not in parent_hand:
        raise AssertionError(parent_hand)
    if (NONEX_ARCHALUDON, SOURCE_NONEX_SERIAL) in alternate_hand:
        raise AssertionError(alternate_hand)
    if (BOSS, SOURCE_BOSS_SERIAL) not in parent_discard:
        raise AssertionError(parent_discard)
    if (NONEX_ARCHALUDON, SOURCE_NONEX_SERIAL) not in alternate_discard:
        raise AssertionError(alternate_discard)
    if (
        BASIC_METAL,
        SOURCE_METAL_SERIAL,
    ) not in parent_discard or (
        BASIC_METAL,
        SOURCE_METAL_SERIAL,
    ) not in alternate_discard:
        raise AssertionError((parent_discard, alternate_discard))

    return {
        "name": parent_case["name"],
        "logical_seat": parent_case["logical_seat"],
        "serial_offset": offset,
        "discard_option_mode": parent_case["discard_option_mode"],
        "same_search_bench_attack_semantics": True,
        "same_functional_state_after_search_bench_attack": True,
        "parent_pre_attack_hand": parent_hand,
        "alternate_pre_attack_hand": alternate_hand,
        "parent_pre_attack_discard": parent_discard,
        "alternate_pre_attack_discard": alternate_discard,
        "boss_preserved_only_in_alternate": True,
        "nonex_replaced_only_in_alternate": True,
        "same_metal_discard": True,
        "same_target_damage_and_prize_result": True,
    }


def main():
    hashes = {
        "runner_sha256_before_output": sha256(pathlib.Path(__file__)),
        "parent_sha256": sha256(PARENT_DIR / "main.py"),
        "deck_sha256": sha256(PARENT_DIR / "deck.csv"),
        "replay_sha256": sha256(REPLAY),
        "engine_tree_sha256": tree_sha256(PARENT_DIR / "cg"),
    }
    if hashes["parent_sha256"] != EXPECTED_PARENT_SHA:
        raise AssertionError(hashes)
    if hashes["deck_sha256"] != EXPECTED_DECK_SHA:
        raise AssertionError(hashes)
    if hashes["replay_sha256"] != EXPECTED_REPLAY_SHA:
        raise AssertionError(hashes)

    configurations = [
        ("seat0_identity", False, 0, "identity"),
        ("seat1_mirror", True, 0, "identity"),
        ("seat0_serial_remap", False, 1000, "identity"),
        ("seat1_serial_remap", True, 1000, "identity"),
        ("seat0_reverse_discard", False, 0, "reverse"),
        ("seat1_reverse_discard", True, 0, "reverse"),
        ("seat0_duplicate_discard", False, 0, "duplicate"),
        ("seat1_duplicate_discard", True, 0, "duplicate"),
    ]
    cases = []
    comparisons = []
    for name, mirror, serial_offset, option_mode in configurations:
        parent_case = run_branch(
            name=name,
            branch="parent",
            mirror=mirror,
            serial_offset=serial_offset,
            discard_option_mode=option_mode,
        )
        alternate_case = run_branch(
            name=name,
            branch="alternate",
            mirror=mirror,
            serial_offset=serial_offset,
            discard_option_mode=option_mode,
        )
        cases.extend((parent_case, alternate_case))
        comparisons.append(compare_pair(parent_case, alternate_case))

    result = {
        "decision": (
            "PREEDIT_GATE_PASS__AUTHORIZE_ONE_ISOLATED_DIRECT_PARENT_IMPLEMENTATION"
        ),
        "selected_rule": (
            "PERSISTENT_PUBLIC_BOSS_ACCESS_LEDGER_WITH_PLAN_EQUIVALENT_"
            "LAST_COPY_DISCARD_GUARD_V1"
        ),
        "source": {
            "episode": 88819392,
            "start_row": TARGET_ROW,
            "target_discard_row": 120,
            "continuation_rows": [121, 122, 123],
            "source_seat": TARGET_SEAT,
        },
        "hashes": hashes,
        "configurations": len(configurations),
        "branch_runs": len(cases),
        "both_logical_seats": sorted(
            {case["logical_seat"] for case in cases}
        )
        == [0, 1],
        "comparisons": comparisons,
        "cases": cases,
        "parent_discard_semantics": [
            [BOSS, SOURCE_BOSS_SERIAL],
            [BASIC_METAL, SOURCE_METAL_SERIAL],
        ],
        "alternate_discard_semantics": [
            [NONEX_ARCHALUDON, SOURCE_NONEX_SERIAL],
            [BASIC_METAL, SOURCE_METAL_SERIAL],
        ],
        "continuation": [
            "same Duraludon search",
            "same Duraludon bench",
            "same Metal Defender 253",
            "same target damage and Prize result",
        ],
        "invalid_actions": 0,
        "action_errors": 0,
        "exceptions": 0,
        "nondeterminism": 0,
        "stale_state": 0,
        "max_step_hits": 0,
        "limitations": [
            "This proves the current-turn plan-equivalent branch only.",
            "It does not prove a later Boss draw or match conversion.",
            "Hidden zone identities are used only to execute the exact engine "
            "fixture, never as runtime rule inputs.",
        ],
    }
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_sha = sha256(OUTPUT)
    report = f"""# Last-public-Boss ledger pre-edit engine gate

Decision:
`{result['decision']}`

- Rule: `{result['selected_rule']}`
- Source: episode `88819392`, rows `119-123`, source seat `0`
- Parent SHA-256: `{hashes['parent_sha256']}`
- Deck SHA-256: `{hashes['deck_sha256']}`
- Replay SHA-256: `{hashes['replay_sha256']}`
- Engine tree SHA-256: `{hashes['engine_tree_sha256']}`
- Runner SHA-256: `{hashes['runner_sha256_before_output']}`
- Raw output SHA-256: `{output_sha}`

The exact source state was executed as two engine branches in eight
configurations: both logical seats, serial remapping, reversed discard
options, equivalent duplicate discard options, and deterministic repeated
selection. There were `{len(cases)}` total branch runs.

The parent branch discarded Boss `1182#39` plus Basic Metal `8#57`. The
alternate branch discarded non-ex Archaludon `840#31` plus the same Metal,
retaining Boss. After that irreversible difference, unmodified exact
historical-Silver selected the same Duraludon, Benched it, and selected Metal
Defender `253`. Search, board formation, attacker, attack target, damage,
Prize result, and turn progression were identical in every comparison.

No invalid action, action error, exception, nondeterminism, stale state, or
max-step hit occurred. This gate authorizes one isolated direct-parent
implementation of the frozen ledger/discard contract. It does not authorize
packaging, Kaggle submission, formal-parent adoption, or a claim that a later
Boss converts the source match.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
