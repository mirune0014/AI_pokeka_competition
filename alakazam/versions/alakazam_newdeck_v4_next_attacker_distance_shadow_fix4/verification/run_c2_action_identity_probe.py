#!/usr/bin/env python3
"""Deterministic parent/candidate action identity probe over 700 callbacks."""

from __future__ import annotations

import argparse
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


CALLBACKS = 700
PARENT_NAME = "alakazam_newdeck_v3_exact_evolution_ko_fix2"
CANDIDATE_NAME = (
    "alakazam_newdeck_v4_next_attacker_distance_shadow_fix4"
)
RULE = "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4"


def _fixture_paths(repo_root: Path) -> list[Path]:
    root = (
        repo_root
        / "alakazam"
        / "fixtures"
        / "episode_88844273_public_observations"
    )
    return sorted(root.glob("step_*.json"))


def _base_observations(repo_root: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(path.read_text(encoding="utf-8"))["observation"]
        for path in _fixture_paths(repo_root)
    ]
    replay = Path(r"C:\Users\amuam\Downloads\88843743.json")
    if replay.is_file():
        value = json.loads(replay.read_text(encoding="utf-8"))
        rows.extend(
            (
                value["steps"][22][1]["observation"],
                value["steps"][23][1]["observation"],
            )
        )
    if not rows:
        raise ValueError("No frozen public observations")
    return rows


def _case(raw: dict[str, Any], ordinal: int) -> dict[str, Any]:
    value = copy.deepcopy(raw)
    options = value.get("select", {}).get("option")
    if isinstance(options, list):
        mode = ordinal % 7
        if mode in (1, 5):
            options.reverse()
        elif mode == 2 and options:
            options.append(copy.deepcopy(options[0]))
        elif mode == 3:
            options[:] = sorted(
                options,
                key=lambda row: json.dumps(
                    row, sort_keys=True, separators=(",", ":")
                ),
            )
    return value


def _reset_modules() -> None:
    deck = importlib.import_module("planner_deck_adaptation_v1")
    core = importlib.import_module("planner_policy")
    deck.reset()
    core.reset_integrated_state()
    parent = importlib.import_module("_cumulative_parent")
    parent.ability_used_dudunsparce = False
    parent.ability_used_fezandipiti = False


def worker(policy_dir: Path, repo_root: Path) -> dict[str, Any]:
    os.chdir(policy_dir)
    sys.path.insert(0, str(policy_dir))
    entrypoint = importlib.import_module("main")
    bases = _base_observations(repo_root)
    rows = []
    action_identity_failures = 0
    metric_exceptions = 0
    for ordinal in range(CALLBACKS):
        _reset_modules()
        raw = _case(bases[ordinal % len(bases)], ordinal)
        error = None
        action = None
        try:
            action = entrypoint.agent(raw)
        except BaseException as exc:
            error = type(exc).__name__
        trace = getattr(
            entrypoint, "LAST_STAGED_POLICY_TRACE", None
        )
        if policy_dir.name == CANDIDATE_NAME:
            identity = (
                trace.get("action_identity")
                if isinstance(trace, dict)
                else None
            )
            identity_ok = (
                isinstance(identity, dict)
                and all(
                    identity.get(key) is True
                    for key in (
                        "value_equal",
                        "type_equal",
                        "order_equal",
                        "returned_parent_object_unchanged",
                    )
                )
                and trace.get("rule_version") == RULE
                and trace.get("raw_parent_action") == action
                and trace.get("applied_action") == action
            )
            if not identity_ok:
                action_identity_failures += 1
            if (
                not isinstance(trace, dict)
                or trace.get("metric_exception") is not None
            ):
                metric_exceptions += 1
        rows.append(
            {
                "ordinal": ordinal,
                "action": action,
                "action_type": (
                    f"{type(action).__module__}."
                    f"{type(action).__qualname__}"
                ),
                "error": error,
            }
        )
    return {
        "policy": policy_dir.name,
        "callbacks": CALLBACKS,
        "rows": rows,
        "action_identity_failures": action_identity_failures,
        "metric_exceptions": metric_exceptions,
    }


def _subprocess_worker(
    script: Path,
    python: Path,
    engine: Path,
    policy_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(engine)
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        (
            str(python),
            "-B",
            str(script),
            "--worker",
            str(policy_dir),
            "--repo-root",
            str(repo_root),
        ),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"worker failed {policy_dir}: {completed.stderr}"
        )
    return json.loads(completed.stdout)


def _exception_probe(
    candidate_dir: Path,
    repo_root: Path,
) -> dict[str, Any]:
    os.chdir(candidate_dir)
    sys.path.insert(0, str(candidate_dir))
    entrypoint = importlib.import_module("main")
    _reset_modules()
    raw = copy.deepcopy(_base_observations(repo_root)[-1])
    ordinary = entrypoint.agent(copy.deepcopy(raw))
    _reset_modules()
    original = entrypoint._c2_shadow.analyze

    def explode(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("C2_IDENTITY_PROBE")

    entrypoint._c2_shadow.analyze = explode
    try:
        exceptional = entrypoint.agent(copy.deepcopy(raw))
        trace = entrypoint.LAST_STAGED_POLICY_TRACE
    finally:
        entrypoint._c2_shadow.analyze = original
    return {
        "ordinary_action": ordinary,
        "exceptional_action": exceptional,
        "ordinary_type": (
            f"{type(ordinary).__module__}."
            f"{type(ordinary).__qualname__}"
        ),
        "exceptional_type": (
            f"{type(exceptional).__module__}."
            f"{type(exceptional).__qualname__}"
        ),
        "action_equal": ordinary == exceptional,
        "type_equal": type(ordinary) is type(exceptional),
        "metric_exception": trace.get("metric_exception"),
    }


def run_probe(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    versions = repo_root / "alakazam" / "versions"
    parent_dir = versions / PARENT_NAME
    candidate_dir = versions / CANDIDATE_NAME
    engine = (
        repo_root
         / "_local_generated" / "analysis_outputs"
        / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
        / "seeded_engine"
    )
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    python = repo_root / ".venv-rl" / "Scripts" / "python.exe"
    script = Path(__file__).resolve()
    parent_rows = _subprocess_worker(
        script, python, engine, parent_dir, repo_root
    )
    candidate_rows = _subprocess_worker(
        script, python, engine, candidate_dir, repo_root
    )
    mismatches = [
        {
            "ordinal": parent_row["ordinal"],
            "parent": parent_row,
            "candidate": candidate_row,
        }
        for parent_row, candidate_row in zip(
            parent_rows["rows"], candidate_rows["rows"]
        )
        if (
            parent_row["action"] != candidate_row["action"]
            or parent_row["action_type"]
            != candidate_row["action_type"]
            or parent_row["error"] != candidate_row["error"]
        )
    ]
    exception = _exception_probe(candidate_dir, repo_root)
    return {
        "schema_version": "c2-action-identity-probe-v1",
        "callbacks": CALLBACKS,
        "parent": PARENT_NAME,
        "candidate": CANDIDATE_NAME,
        "action_mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "candidate_trace_action_identity_failures": candidate_rows[
            "action_identity_failures"
        ],
        "candidate_metric_exceptions": candidate_rows[
            "metric_exceptions"
        ],
        "analyzer_exception_probe": exception,
        "pass": (
            not mismatches
            and candidate_rows["action_identity_failures"] == 0
            and candidate_rows["metric_exceptions"] == 0
            and exception["action_equal"]
            and exception["type_equal"]
            and exception["metric_exception"] == "RuntimeError"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        print(
            json.dumps(
                worker(args.worker.resolve(), args.repo_root.resolve()),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0
    result = run_probe(args.repo_root)
    payload = (
        json.dumps(
            result,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
        )
        + "\n"
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            payload,
            encoding="utf-8",
            newline="\n",
        )
    print(payload, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
