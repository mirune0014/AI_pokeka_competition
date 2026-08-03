"""Replace coarse family labels in the frozen replay-shadow output."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "archaludon"
TASK9 = AUTO / "candidates/archaludon_public_prize_race_threat_control_t9_v1"
CURRENT = AUTO / "live/55155015/analysis_20260802/refresh"
HISTORICAL = AUTO / "live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new"
INPUT = Path(__file__).with_name("replay_first_differences.json")
OUTPUT = Path(__file__).with_name("replay_first_differences_classified.json")
sys.path[:0] = [str(TASK9), str(ROOT), str(ROOT / "infrastructure" / "tools")]
from research.rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


spec = importlib.util.spec_from_file_location("task9_family_parser", TASK9 / "main.py")
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)


def family(parsed, action):
    if not action:
        return "EMPTY"
    options = parsed.select.option if parsed.select is not None else []
    names = []
    for index in action:
        option = options[index]
        value = getattr(option, "type", None)
        name = getattr(value, "name", None)
        if name is None:
            try:
                name = module.OptionType(int(value)).name
            except (TypeError, ValueError):
                name = str(value)
        names.append(name)
    return "+".join(sorted(names))


payload = json.loads(INPUT.read_bytes())
for result in payload["results"]:
    grouped = {}
    for row in result["first_differences"]:
        grouped.setdefault((row["corpus"], row["episode"], row["seat"]), []).append(row)
    for (corpus, episode, seat), rows in grouped.items():
        root = CURRENT if corpus == "current" else HISTORICAL
        replay_path = root / f"{episode}.json"
        replay = json.loads(replay_path.read_bytes())
        wanted = {row["step"]: row for row in rows}
        for step, obs, _recorded in replay_decisions(replay, seat):
            row = wanted.get(step)
            if row is None:
                continue
            parsed = module.to_observation_class(obs)
            row["left_family"] = family(parsed, row["left_action"])
            row["right_family"] = family(parsed, row["right_action"])
    transitions = {}
    for row in result["first_differences"]:
        key = f"{row['left_family']}->{row['right_family']}"
        transitions[key] = transitions.get(key, 0) + 1
    result["family_transitions"] = dict(sorted(transitions.items()))

OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({
    result["pair"]: result["family_transitions"] for result in payload["results"]
}, indent=2, sort_keys=True))
