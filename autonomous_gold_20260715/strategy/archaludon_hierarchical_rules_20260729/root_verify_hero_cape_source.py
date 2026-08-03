from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
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
    / "episode_88643491_replay.json"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_parent():
    for key in list(sys.modules):
        if key == "cg" or key.startswith("cg."):
            del sys.modules[key]
    sys.path.insert(0, str(PARENT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "root_hero_cape_parent",
            PARENT_DIR / "main.py",
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("parent import failed")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(PARENT_DIR))


def public_fields(obj):
    result = {}
    for name in dir(obj):
        if name.startswith("_"):
            continue
        try:
            value = getattr(obj, name)
        except Exception:
            continue
        if callable(value):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            result[name] = value
        elif isinstance(value, (list, tuple)):
            result[name] = [
                item
                if isinstance(item, (str, int, float, bool)) or item is None
                else str(item)
                for item in value
            ]
        else:
            result[name] = str(value)
    return result


def main() -> None:
    expected_parent = (
        "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
    )
    expected_replay = (
        "5C385365DBCA461A5E99B633E00C011CFDCE18ADD7EB0E9DECAF6F4A2FD16DDF"
    )
    assert sha256(PARENT_DIR / "main.py") == expected_parent
    assert sha256(REPLAY) == expected_replay

    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    assert replay["info"]["EpisodeId"] == 88643491
    assert replay["info"]["TeamNames"][0] == "rurumi"
    obs = replay["steps"][77][0]["observation"]
    assert obs["current"]["yourIndex"] == 0
    assert obs["current"]["turn"] == 8

    parent = load_parent()
    action = parent.agent(copy.deepcopy(obs))
    selected = [obs["select"]["option"][index] for index in action]
    parsed = parent.to_observation_class(copy.deepcopy(obs))
    parsed_options = []
    for index, option in enumerate(parsed.select.option):
        card = parent.option_card(parsed, option)
        target = parent.option_target(parsed, option)
        parsed_options.append(
            {
                "index": index,
                "type": int(option.type),
                "card_id": getattr(card, "id", None),
                "card_serial": getattr(card, "serial", None),
                "target_id": getattr(target, "id", None),
                "target_serial": getattr(target, "serial", None),
                "attack_id": getattr(option, "attackId", None),
                "score": parent.score_option(parsed, option),
            }
        )
    players = obs["current"]["players"]
    result = {
        "action": action,
        "parsed_options": parsed_options,
        "card_169": public_fields(parent.CARD_DB[169]),
        "card_678": public_fields(parent.CARD_DB[678]),
        "card_1159": public_fields(parent.CARD_DB[1159]),
        "attack_224": public_fields(parent.ALL_ATTACKS[224]),
        "attack_982": public_fields(parent.ALL_ATTACKS[982]),
        "selected": selected,
        "active": players[0]["active"][0],
        "hand": players[0]["hand"],
        "opponent_active": players[1]["active"][0],
        "opponent_bench": players[1]["bench"],
        "option_count": len(obs["select"]["option"]),
        "parent_main_sha256": expected_parent,
        "replay_sha256": expected_replay,
        "row": 77,
        "seat": 0,
        "turn": 8,
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
