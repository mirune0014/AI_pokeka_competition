"""Build a deterministic residual-policy submission without mutating the baseline."""
from __future__ import annotations

import argparse
import ast
import copy
import io
import json
import math
import py_compile
import re
import shutil
import tarfile
from pathlib import Path


def safe_extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
                raise ValueError("unsafe archive member: " + member.name)
        tar.extractall(destination)


def rename_choose_options(source):
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "choose_options"]
    if len(matches) != 1:
        raise ValueError("main.py must contain exactly one top-level choose_options")
    node = matches[0]
    lines = source.splitlines(keepends=True)
    line = lines[node.lineno - 1]
    replacement, count = re.subn(r"\bchoose_options\b", "choose_options_rule", line, count=1)
    if count != 1:
        raise ValueError("could not safely rename choose_options definition")
    lines[node.lineno - 1] = replacement
    result = "".join(lines)
    check = ast.parse(result)
    if sum(isinstance(n, ast.FunctionDef) and n.name == "choose_options_rule" for n in check.body) != 1:
        raise ValueError("rename validation failed")
    return result


def move_agent_last(source):
    """Move the sole top-level agent definition to the end of main.py."""
    tree = ast.parse(source)
    matches = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "agent"
    ]
    if len(matches) != 1:
        raise ValueError("main.py must contain exactly one top-level agent")
    node = matches[0]
    lines = source.splitlines(keepends=True)
    start = node.lineno - 1
    end = node.end_lineno
    agent_block = "".join(lines[start:end])
    remainder = "".join(lines[:start] + lines[end:]).rstrip() + "\n\n"
    result = remainder + agent_block
    check = ast.parse(result)
    functions = [
        item for item in check.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if sum(item.name == "agent" for item in functions) != 1 or functions[-1].name != "agent":
        raise ValueError("agent relocation validation failed")
    return result


def write_preserving_archive(baseline_archive, output_dir, archive_path):
    """Copy the proven archive layout verbatim, replacing only root main.py."""
    replacement = (Path(output_dir) / "main.py").read_bytes()
    found_main = False
    with tarfile.open(baseline_archive, "r:gz") as source, tarfile.open(archive_path, "w:gz") as target:
        for member in source.getmembers():
            info = copy.copy(member)
            if member.name == "main.py":
                found_main = True
                info.size = len(replacement)
                target.addfile(info, io.BytesIO(replacement))
            elif member.isfile():
                payload = source.extractfile(member)
                if payload is None:
                    raise ValueError("could not read archive member: " + member.name)
                target.addfile(info, payload)
            else:
                target.addfile(info)
    if not found_main:
        raise ValueError("baseline archive has no root main.py member")


WRAPPER = r'''

# Added by rl_ptcg.build_submission.  The baseline remains the error fallback.
import random as _residual_random
_RESIDUAL_WEIGHTS = __RESIDUAL_WEIGHTS__

def choose_options(obs):
    try:
        return choose_residual(obs, score_option, option_card, option_target, detect_matchup,
                               choose_options_rule(obs), _RESIDUAL_WEIGHTS,
                               rng=_residual_random.Random(0), top_n=__RESIDUAL_TOP_N__, training=False,
                               residual_cap=__RESIDUAL_CAP__)[0]
    except Exception:
        return choose_options_rule(obs)
'''


def build(baseline_archive, weights_json, output_dir, archive_path, top_n=3, residual_cap=0.35):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(str(output_dir) + " already exists")
    safe_extract(Path(baseline_archive), output_dir)
    main = output_dir / "main.py"
    deck = output_dir / "deck.csv"
    if not main.exists() or not deck.exists() or not (output_dir / "cg").is_dir():
        raise ValueError("baseline must contain main.py, deck.csv, and cg/")
    cards = [line.strip() for line in deck.read_text(encoding="ascii").splitlines() if line.strip()]
    if len(cards) != 60 or not all(card.lstrip("-").isdigit() for card in cards):
        raise ValueError("deck.csv must contain exactly 60 integer card ids")
    if int(top_n) < 1 or float(residual_cap) < 0.0:
        raise ValueError("top_n must be positive and residual_cap must be non-negative")
    weights = json.loads(Path(weights_json).read_text(encoding="ascii"))
    if not isinstance(weights, dict) or not all(
        isinstance(key, str) and isinstance(value, (int, float)) and math.isfinite(value)
        for key, value in weights.items()
    ):
        raise ValueError("weights JSON must be a finite string-to-number object")
    residual_source = Path(__file__).with_name("residual_policy.py").read_text(encoding="utf-8")
    residual_source = re.sub(
        r"^from __future__ import annotations\s*\n", "", residual_source,
        count=1, flags=re.MULTILINE,
    )
    wrapper = WRAPPER.replace("__RESIDUAL_TOP_N__", str(int(top_n)))
    wrapper = wrapper.replace("__RESIDUAL_CAP__", repr(float(residual_cap)))
    wrapper = wrapper.replace("__RESIDUAL_WEIGHTS__", json.dumps(weights, sort_keys=True))
    combined = rename_choose_options(main.read_text(encoding="utf-8"))
    combined += "\n\n# Embedded dependency-free residual runtime.\n" + residual_source + wrapper
    combined = move_agent_last(combined)
    main.write_text(combined, encoding="utf-8")
    for stale in (output_dir / "residual_weights.json", output_dir / "residual_policy.py"):
        stale.unlink(missing_ok=True)
    for path in list(output_dir.rglob("__pycache__")):
        shutil.rmtree(path)
    for path in output_dir.rglob("*.pyc"):
        path.unlink()
    for path in output_dir.rglob("*.py"):
        py_compile.compile(str(path), doraise=True)
    for path in list(output_dir.rglob("__pycache__")):
        shutil.rmtree(path)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    write_preserving_archive(Path(baseline_archive), output_dir, archive_path)
    return archive_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--residual-cap", type=float, default=0.35)
    args = parser.parse_args()
    print(build(args.baseline, args.weights, args.output_dir, args.archive,
                args.top_n, args.residual_cap))


if __name__ == "__main__":
    main()
