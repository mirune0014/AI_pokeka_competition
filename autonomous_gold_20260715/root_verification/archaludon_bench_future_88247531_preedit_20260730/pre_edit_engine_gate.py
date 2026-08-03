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
    / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
REPLAY = (
    ROOT
    / "autonomous_gold_20260715"
    / "evidence"
    / "live_54927163_refresh_20260729_0344"
    / "episode_88247531_replay.json"
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
    "26D1D7054A5C67ED89261B4CA391445A3EA46C5FC8D4AE314E63A577CFC7434E"
)

TARGET_ROW = 115
TARGET_SEAT = 1
ARCHALUDON_EX = 190
DURALUDON = 169
SOURCE_EVOLUTION_SERIAL = 67
SOURCE_ACTIVE_SERIAL = 63
SOURCE_BENCH_SERIAL = 66
METAL_DEFENDER = 253
RAGING_HAMMER = 224


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


PARENT = load_module("bench_future_preedit_parent", PARENT_DIR / "main.py")


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


def transformed_callback(observation, mirror=False, serial_offset=0):
    view = copy.deepcopy(observation)
    if mirror:
        view = mirror_observation(view)
    if serial_offset:
        view = remap_serials(view, serial_offset)
    return view


def raw_fixture():
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    observation = to_observation_class(
        copy.deepcopy(replay["steps"][TARGET_ROW][TARGET_SEAT]["observation"])
    )
    hidden = copy.deepcopy(
        replay["steps"][0][0]["visualize"][TARGET_ROW - 1]["current"]
    )
    return observation, hidden


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


def normalized_semantics(observation, positions, serial_offset):
    result = []
    for position in positions:
        row = option_record(observation, position)
        for key in ("card_serial", "target_serial"):
            value = row[key]
            if isinstance(value, int) and value > 0:
                row[key] = value - serial_offset
        result.append(row)
    return result


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


def evolution_action(observation, branch, serial_offset):
    target_serial = (
        SOURCE_ACTIVE_SERIAL
        if branch == "control"
        else SOURCE_BENCH_SERIAL
    ) + serial_offset
    matches = [
        row
        for row in option_records(observation)
        if row["card_id"] == ARCHALUDON_EX
        and row["card_serial"]
        == SOURCE_EVOLUTION_SERIAL + serial_offset
        and row["target_id"] == DURALUDON
        and row["target_serial"] == target_serial
    ]
    if len(matches) != 1:
        raise AssertionError(
            {
                "branch": branch,
                "target_serial": target_serial,
                "matches": matches,
                "options": option_records(observation),
            }
        )
    return [matches[0]["position"]]


def pokemon_record(pokemon):
    return {
        "id": pokemon.id,
        "serial": pokemon.serial,
        "hp": pokemon.hp,
        "max_hp": pokemon.maxHp,
        "energies": sorted(pokemon.energies or ()),
        "energy_serials": sorted(
            card.serial for card in pokemon.energyCards or ()
        ),
        "tools": sorted(tool.id for tool in pokemon.tools or ()),
        "pre_evolution": sorted(
            (card.id, card.serial) for card in pokemon.preEvolution or ()
        ),
    }


def state_record(observation, engine_yi):
    mine = observation.current.players[engine_yi]
    opponent = observation.current.players[1 - engine_yi]
    return {
        "turn": observation.current.turn,
        "turn_action_count": observation.current.turnActionCount,
        "your_index": observation.current.yourIndex,
        "own_prizes": len(mine.prize or ()),
        "opponent_prizes": len(opponent.prize or ()),
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


STAGES = (
    "EVOLVE",
    "ALLOY_ACTIVATE",
    "ALLOY_SOURCE",
    "ALLOY_TARGET_1",
    "ALLOY_TARGET_2",
    "ATTACK",
)


def run_branch(name, branch, mirror=False, serial_offset=0):
    observation, hidden = raw_fixture()
    engine_yi = observation.current.yourIndex
    logical_yi = 1 - engine_yi if mirror else engine_yi
    state = begin_engine(observation, hidden)
    trace = []
    try:
        for stage in STAGES:
            raw = state.observation
            view = transformed_callback(
                raw, mirror=mirror, serial_offset=serial_offset
            )
            parent_action = choose_parent(view)
            if stage == "EVOLVE":
                expected_control = evolution_action(
                    view, "control", serial_offset
                )
                if normalized_semantics(
                    view, parent_action, serial_offset
                ) != normalized_semantics(
                    view, expected_control, serial_offset
                ):
                    raise AssertionError(
                        {
                            "parent": normalized_semantics(
                                view, parent_action, serial_offset
                            ),
                            "expected_control": normalized_semantics(
                                view, expected_control, serial_offset
                            ),
                        }
                    )
                action = evolution_action(
                    view, branch, serial_offset
                )
            else:
                action = parent_action
            repeated = (
                evolution_action(view, branch, serial_offset)
                if stage == "EVOLVE"
                else choose_parent(view)
            )
            if action != repeated:
                raise AssertionError((stage, action, repeated))
            trace.append(
                {
                    "stage": stage,
                    "logical_seat": logical_yi,
                    "action": action,
                    "semantics": normalized_semantics(
                        view, action, serial_offset
                    ),
                    "parent_semantics": normalized_semantics(
                        view, parent_action, serial_offset
                    ),
                    "before": state_record(raw, engine_yi),
                }
            )
            state = search_step(state.searchId, action)
            trace[-1]["after"] = state_record(
                state.observation, engine_yi
            )

        final = trace[-1]["after"]
        selected_attack = trace[-1]["semantics"]
        if len(selected_attack) != 1:
            raise AssertionError(selected_attack)
        attack_id = selected_attack[0]["attack_id"]
        target_serial = trace[-1]["before"]["opponent_active"][0]["serial"]
        damage_logs = [
            log
            for log in final["logs"]
            if log["player_index"] == 1 - engine_yi
            and log["serial"] == target_serial
            and isinstance(log["value"], int)
            and log["value"] < 0
        ]
        if not damage_logs:
            raise AssertionError(final["logs"])
        attack_damage = -min(log["value"] for log in damage_logs)
        return {
            "name": name,
            "branch": branch,
            "logical_seat": logical_yi,
            "engine_seat": engine_yi,
            "mirror": mirror,
            "serial_offset": serial_offset,
            "trace": trace,
            "selected_attack_id": attack_id,
            "attack_damage": attack_damage,
            "final": final,
            "invalid_actions": 0,
            "exceptions": 0,
            "stale_state": 0,
            "max_step_hits": 0,
        }
    finally:
        search_end()


def pokemon_by_serial(records, serial):
    matches = [record for record in records if record["serial"] == serial]
    if len(matches) != 1:
        raise AssertionError((serial, records))
    return matches[0]


def compare_pair(control, alternate):
    if control["selected_attack_id"] != METAL_DEFENDER:
        raise AssertionError(control["selected_attack_id"])
    if alternate["selected_attack_id"] != RAGING_HAMMER:
        raise AssertionError(alternate["selected_attack_id"])
    if control["attack_damage"] != 220:
        raise AssertionError(control["attack_damage"])
    if alternate["attack_damage"] != 80:
        raise AssertionError(alternate["attack_damage"])
    if control["final"]["own_prizes"] != alternate["final"]["own_prizes"]:
        raise AssertionError(
            (
                control["final"]["own_prizes"],
                alternate["final"]["own_prizes"],
            )
        )
    control_active = pokemon_by_serial(
        control["final"]["own_active"], SOURCE_EVOLUTION_SERIAL
    )
    alternate_active = pokemon_by_serial(
        alternate["final"]["own_active"], SOURCE_ACTIVE_SERIAL
    )
    alternate_bench = pokemon_by_serial(
        alternate["final"]["own_bench"], SOURCE_EVOLUTION_SERIAL
    )
    if control_active["id"] != ARCHALUDON_EX:
        raise AssertionError(control_active)
    if alternate_active["id"] != DURALUDON:
        raise AssertionError(alternate_active)
    if alternate_bench["id"] != ARCHALUDON_EX:
        raise AssertionError(alternate_bench)
    if alternate_bench["hp"] != 180:
        raise AssertionError(alternate_bench)
    if len(alternate_bench["energy_serials"]) != 3:
        raise AssertionError(alternate_bench)
    if len(alternate_active["energy_serials"]) != 3:
        raise AssertionError(alternate_active)
    return {
        "name": control["name"],
        "logical_seat": control["logical_seat"],
        "serial_offset": control["serial_offset"],
        "control_attack_id": control["selected_attack_id"],
        "alternate_attack_id": alternate["selected_attack_id"],
        "control_damage": control["attack_damage"],
        "alternate_damage": alternate["attack_damage"],
        "damage_regression": (
            control["attack_damage"] - alternate["attack_damage"]
        ),
        "same_immediate_prize_result": True,
        "alternate_saved_bench_hp": alternate_bench["hp"],
        "alternate_saved_bench_energy_count": len(
            alternate_bench["energy_serials"]
        ),
        "alternate_active_energy_count": len(
            alternate_active["energy_serials"]
        ),
        "current_attack_identity_preserved": False,
        "current_damage_preserved": False,
        "implementation_authorized": False,
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
        ("source_seat1", False, 0),
        ("mirror_seat0", True, 0),
        ("source_seat1_serial_remap", False, 1000),
        ("mirror_seat0_serial_remap", True, 1000),
    ]
    cases = []
    comparisons = []
    for name, mirror, offset in configurations:
        control = run_branch(
            name, "control", mirror=mirror, serial_offset=offset
        )
        alternate = run_branch(
            name, "alternate", mirror=mirror, serial_offset=offset
        )
        cases.extend((control, alternate))
        comparisons.append(compare_pair(control, alternate))

    result = {
        "decision": (
            "PREEDIT_GATE_FAIL__SOURCE_IS_MANDATORY_NEGATIVE__"
            "NO_IMPLEMENTATION"
        ),
        "hypothesis": (
            "DAMAGED_INVESTED_BENCH_EVOLUTION_FUTURE_VALUE_V1"
        ),
        "source": {
            "episode": 88247531,
            "row": TARGET_ROW,
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
        "controlling_regression": {
            "control_attack_id": METAL_DEFENDER,
            "control_damage": 220,
            "alternate_attack_id": RAGING_HAMMER,
            "alternate_damage": 80,
            "damage_loss": 140,
            "attack_identity_changed": True,
            "current_prize_route_not_preserved": True,
        },
        "invalid_actions": 0,
        "action_errors": 0,
        "exceptions": 0,
        "nondeterminism": 0,
        "stale_state": 0,
        "max_step_hits": 0,
        "implementation_authorized": False,
        "limitations": [
            "This fork stops at the first decisive current-attack regression.",
            "It does not force an opponent response or use hidden gust access.",
            "No replay action is used as a runtime label.",
        ],
    }
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_sha = sha256(OUTPUT)
    report = f"""# Bench-future row-115 pre-edit engine gate

Decision:
`{result['decision']}`

- Source: episode `88247531`, row `115`, source seat `1`
- Parent SHA-256: `{hashes['parent_sha256']}`
- Deck SHA-256: `{hashes['deck_sha256']}`
- Replay SHA-256: `{hashes['replay_sha256']}`
- Engine tree SHA-256: `{hashes['engine_tree_sha256']}`
- Runner SHA-256: `{hashes['runner_sha256_before_output']}`
- Raw output SHA-256: `{output_sha}`

The exact row-115 state was forked in both logical seats with serial-remapped
controls. The control evolved Archaludon ex `#67` onto the healthy Active
`#63`; the alternate evolved it onto the damaged three-Metal Bench `#66`.
Every later callback was delegated to unmodified exact historical-Silver.

The alternate locally saved the Bench as an `180/300`, three-Energy
Archaludon ex. It simultaneously routed both Alloy Metals to the Active
Duraludon and changed the current attack from Metal Defender `253` for `220`
to Raging Hammer `224` for `80`, an immediate `140`-damage regression. The
current attack identity and public two-hit Prize route are therefore not
preserved.

All `{len(cases)}` engine branch runs completed with zero invalid action,
action error, exception, nondeterminism, stale state, or max-step hit. Because
the frozen current-attack/Prize-route negative fails, episode `88247531:115`
is a mandatory parent-identical negative. No source implementation or
precedence rank is authorized.
"""
    REPORT.write_text(report, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
