from __future__ import annotations

import ast
import csv
import difflib
import hashlib
import importlib.util
import json
import os
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_attack_completing_energy_reservation_v2"
)
PARENT = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
ENGINE = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)

EXPECTED_PARENT_MAIN = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_DECK = (
    "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"
)
EXPECTED_ENGINE = (
    "466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF"
)
EXPECTED_MEMBERS = [
    "cg/__init__.py",
    "cg/api.py",
    "cg/cg.dll",
    "cg/game.py",
    "cg/libcg-arm64.so",
    "cg/libcg.dylib",
    "cg/libcg.so",
    "cg/sim.py",
    "cg/utils.py",
    "deck.csv",
    "main.py",
    "requirements.txt",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engine_manifest() -> tuple[list[dict[str, object]], str]:
    files = sorted(
        path
        for path in ENGINE.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )
    rows = [
        {
            "relative_path": path.relative_to(ENGINE).as_posix(),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in files
    ]
    canonical = "".join(
        f"{row['relative_path']}|{row['sha256']}\n" for row in rows
    ).encode("ascii")
    return rows, hashlib.sha256(canonical).hexdigest().upper()


def main() -> None:
    parent_main = PARENT / "main.py"
    candidate_main = CANDIDATE / "main.py"
    parent_bytes = parent_main.read_bytes()
    candidate_bytes = candidate_main.read_bytes()
    candidate_text = candidate_bytes.decode("utf-8")
    parent_text = parent_bytes.decode("utf-8")

    actual_members = sorted(
        path.relative_to(CANDIDATE).as_posix()
        for path in CANDIDATE.rglob("*")
        if path.is_file()
    )
    cache_members = [
        member
        for member in actual_members
        if "__pycache__" in member or member.endswith((".pyc", ".pyo"))
    ]
    non_main_mismatches = [
        member
        for member in EXPECTED_MEMBERS
        if member != "main.py"
        and (
            not (PARENT / member).is_file()
            or not (CANDIDATE / member).is_file()
            or sha256(PARENT / member) != sha256(CANDIDATE / member)
        )
    ]

    changed_python = [candidate_main, *sorted(HERE.glob("*.py"))]
    compile_results = []
    for path in changed_python:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        compile_results.append(path.relative_to(ROOT).as_posix())

    prior_cwd = pathlib.Path.cwd()
    sys.path.insert(0, str(CANDIDATE))
    os.chdir(CANDIDATE)
    try:
        candidate_module = load_module("h6_structure_candidate", candidate_main)
        deck_one = candidate_module.agent(
            {"select": None, "logs": [], "current": None}
        )
        deck_two = candidate_module.agent(
            {"select": None, "logs": [], "current": None}
        )

        loader_namespace = {
            "__file__": str(candidate_main),
            "__name__": "h6_exact_loader_namespace",
        }
        exec(compile(candidate_text, str(candidate_main), "exec"), loader_namespace)
        callables = [
            (name, value)
            for name, value in loader_namespace.items()
            if callable(value)
        ]
        loader_name, loader_callable = callables[-1]
        loader_deck = loader_callable(
            {"select": None, "logs": [], "current": None}
        )
        ace_spec_count = sum(
            1
            for card_id in deck_one
            if candidate_module.CARD_DB[card_id].aceSpec
        )
    finally:
        os.chdir(prior_cwd)
        sys.path.remove(str(CANDIDATE))

    tree = ast.parse(candidate_text)
    top_level_agent_defs = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "agent"
        for node in tree.body
    )

    diff_text = "".join(
        difflib.unified_diff(
            parent_text.splitlines(keepends=True),
            candidate_text.splitlines(keepends=True),
            fromfile="historical_silver_archaludon_54495224/main.py",
            tofile="archaludon_attack_completing_energy_reservation_v2/main.py",
        )
    )
    diff_path = HERE / "direct_main.diff"
    diff_path.write_text(diff_text, encoding="utf-8", newline="\n")

    engine_rows, engine_hash = engine_manifest()
    engine_manifest_path = HERE / "engine_source_manifest.csv"
    with engine_manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["relative_path", "sha256", "bytes"]
        )
        writer.writeheader()
        writer.writerows(engine_rows)

    checks = {
        "parent_main_hash": sha256(parent_main) == EXPECTED_PARENT_MAIN,
        "parent_deck_hash": sha256(PARENT / "deck.csv") == EXPECTED_DECK,
        "candidate_deck_hash": sha256(CANDIDATE / "deck.csv") == EXPECTED_DECK,
        "runtime_members_exact": actual_members == EXPECTED_MEMBERS,
        "non_main_parent_identical": not non_main_mismatches,
        "no_cache_members": not cache_members,
        "parent_source_exact_prefix": candidate_bytes.startswith(parent_bytes),
        "h6_marker_immediately_after_parent": candidate_bytes[
            len(parent_bytes) :
        ].startswith(
            b"\n\n# H6_UNIQUE_ACTIVE_METAL_DEFENDER_CONTINUITY_RESERVATION"
        ),
        "last_inserted_callable_is_agent": loader_name == "agent"
        and loader_callable.__name__ == "agent",
        "loader_deck_legal": len(loader_deck) == 60,
        "deck_repeat_deterministic": deck_one == deck_two == loader_deck,
        "deck_card_count": len(deck_one) == 60,
        "deck_ace_spec_count": ace_spec_count == 1,
        "engine_file_count": len(engine_rows) == 11,
        "engine_canonical_hash": engine_hash == EXPECTED_ENGINE,
        "python_compile": len(compile_results) == len(changed_python),
    }
    if not all(checks.values()):
        raise AssertionError(
            {name: value for name, value in checks.items() if not value}
        )

    result = {
        "checks": checks,
        "candidate": {
            "path": CANDIDATE.relative_to(ROOT).as_posix(),
            "main_sha256": sha256(candidate_main),
            "deck_sha256": sha256(CANDIDATE / "deck.csv"),
            "runtime_file_count": len(actual_members),
            "runtime_members": actual_members,
            "cache_members": cache_members,
            "non_main_mismatches": non_main_mismatches,
            "top_level_agent_definitions": top_level_agent_defs,
            "last_inserted_callable": loader_name,
            "deck_card_count": len(deck_one),
            "ace_spec_count": ace_spec_count,
        },
        "parent": {
            "path": PARENT.relative_to(ROOT).as_posix(),
            "main_sha256": sha256(parent_main),
            "deck_sha256": sha256(PARENT / "deck.csv"),
        },
        "engine": {
            "path": ENGINE.relative_to(ROOT).as_posix(),
            "file_count": len(engine_rows),
            "canonical_sha256": engine_hash,
            "canonical_definition": (
                "sorted relative POSIX path + '|' + uppercase file SHA-256 "
                "+ LF; files exclude __pycache__ and .pyc"
            ),
            "manifest": engine_manifest_path.name,
        },
        "diff": {
            "path": diff_path.name,
            "sha256": sha256(diff_path),
            "bytes": diff_path.stat().st_size,
            "candidate_starts_with_exact_parent_bytes": True,
        },
        "compiled_python": compile_results,
    }
    result_path = HERE / "structural_results.json"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
