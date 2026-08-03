"""Update executable/configuration references after the 2026-08-04 move.

Historical Markdown, JSON evidence, frozen specifications, and archived agents are
intentionally not rewritten.  Their original hashes and paths remain evidence
for commit 3111ecf.  This migrator only touches code and active configuration.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELF = Path(__file__).resolve()
REPORT = ROOT / "docs" / "repository_workspace_rename_report_20260804.json"

DIRECTORY_MOVES = (
    ("autonomous_gold_20260715", "archaludon"),
    ("alakazam_staged_20260729", "alakazam"),
    ("submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v5_staticstruct_20260710", "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v5_staticstruct_20260710"),
    ("submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v4_static_20260710", "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v4_static_20260710"),
    ("submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v3_20260710", "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v3_20260710"),
    ("submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v2_20260710", "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_v2_20260710"),
    ("submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_20260710", "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_seededrl_archattach003_20260710"),
    ("submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710", "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710"),
    ("submission_archaludon_947base_iono_alaklive_line4markers", "archive/submissions/submission_archaludon_947base_iono_alaklive_line4markers"),
    ("submission_archaludon_shumpei_current_v3_runtime", "archive/submissions/submission_archaludon_shumpei_current_v3_runtime"),
    ("submission_archaludon_current_purecopy", "archive/submissions/submission_archaludon_current_purecopy"),
    ("submission_meta_archaludon", "archive/submissions/submission_meta_archaludon"),
    ("submission_archaludon", "archive/submissions/submission_archaludon"),
    ("isolated_rule_agents", "opponents/isolated_rule_agents"),
    ("meta_agents", "opponents/meta_agents"),
    ("experiments", "research/experiments"),
    ("rl_ptcg", "research/rl_ptcg"),
    ("reports", "research/reports"),
    ("apps", "infrastructure/apps"),
    ("tools", "infrastructure/tools"),
    ("external", "infrastructure/external"),
    ("data", "infrastructure/data"),
    ("vendor", "infrastructure/vendor"),
    ("analysis_outputs", "_local_generated/analysis_outputs"),
    ("deliverables", "_local_generated/deliverables"),
    ("notebook_output", "_local_generated/notebook_output"),
    ("share_packages", "_local_generated/share_packages"),
    ("metrics", "_local_generated/metrics"),
    ("logs", "_local_generated/logs"),
)

WORKSPACE_ROOT_MOVES = {
    "autonomous_gold_20260715",
    "alakazam_staged_20260729",
}
WORKSPACE_NEW_ROOTS = {"archaludon", "alakazam"}

CODE_SUFFIXES = {".py", ".ps1", ".sh", ".bat", ".cmd", ".toml", ".yaml", ".yml"}
FILE_MOVES = {
    "analyze_matches.py": "infrastructure/scripts/analyze_matches.py",
    "build_zoroark_deck.py": "infrastructure/scripts/build_zoroark_deck.py",
    "run_eval.py": "infrastructure/scripts/run_eval.py",
}

PYTHON_JOIN_MOVES = (
    ("tools", ("infrastructure", "tools")),
    ("rl_ptcg", ("research", "rl_ptcg")),
    ("meta_agents", ("opponents", "meta_agents")),
    ("isolated_rule_agents", ("opponents", "isolated_rule_agents")),
    ("experiments", ("research", "experiments")),
    ("apps", ("infrastructure", "apps")),
    ("external", ("infrastructure", "external")),
    ("data", ("infrastructure", "data")),
    ("vendor", ("infrastructure", "vendor")),
    ("analysis_outputs", ("_local_generated", "analysis_outputs")),
    ("deliverables", ("_local_generated", "deliverables")),
    ("notebook_output", ("_local_generated", "notebook_output")),
    ("share_packages", ("_local_generated", "share_packages")),
)

IMMUTABLE_EXECUTABLES = {
    "infrastructure/tools/audit_archaludon_iteration007_identifiability.py",
}


def candidate_files() -> list[Path]:
    directory_map = dict(DIRECTORY_MOVES)
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    result: set[Path] = set()
    for item in raw.split(b"\0"):
        if not item:
            continue
        relative = item.decode("utf-8")
        destination = FILE_MOVES.get(relative)
        if destination is None:
            parts = relative.split("/")
            moved_root = directory_map.get(parts[0])
            destination = "/".join((moved_root, *parts[1:])) if moved_root else relative
        path = ROOT / destination
        current_relative = path.relative_to(ROOT).as_posix()
        if (
            path.is_file()
            and path != SELF
            and current_relative not in IMMUTABLE_EXECUTABLES
            and path.suffix.lower() in CODE_SUFFIXES
        ):
            result.add(path)
    return sorted(result)


def protect_new_paths(data: bytes) -> tuple[bytes, list[tuple[bytes, bytes]]]:
    protected: list[tuple[bytes, bytes]] = []
    for index, (_, new) in enumerate(DIRECTORY_MOVES):
        if new in WORKSPACE_NEW_ROOTS:
            continue
        for variant_index, variant in enumerate((new, new.replace("/", "\\"))):
            raw = variant.encode("ascii")
            token = f"@@NEW_PATH_{index}_{variant_index}@@".encode("ascii")
            if raw in data:
                data = data.replace(raw, token)
                protected.append((token, raw))
    return data, protected


def rewrite_paths(data: bytes) -> tuple[bytes, int]:
    data, protected = protect_new_paths(data)
    count = 0
    for old, new in DIRECTORY_MOVES:
        raw_old = old.encode("ascii")
        if raw_old not in data:
            continue
        if old in WORKSPACE_ROOT_MOVES:
            pattern = re.compile(
                rb"(?<![A-Za-z0-9_])" + re.escape(raw_old) + rb"(?![A-Za-z0-9_])"
            )
        else:
            pattern = re.compile(
                rb"(?<![A-Za-z0-9_.\\/-])" + re.escape(raw_old) + rb"(?=[\\/])"
            )

        def replace(match: re.Match[bytes]) -> bytes:
            following = match.string[match.end() : match.end() + 1]
            value = new.replace("/", "\\") if following == b"\\" else new
            return value.encode("ascii")

        data, replacements = pattern.subn(replace, data)
        count += replacements
    for token, raw in reversed(protected):
        data = data.replace(token, raw)
    return data, count


def rewrite_python_structure(path: Path, data: bytes) -> bytes:
    if path.suffix.lower() != ".py":
        return data
    replacements = (
        (b"from tools.", b"from infrastructure.tools."),
        (b"from tools import", b"from infrastructure.tools import"),
        (b"from rl_ptcg.", b"from research.rl_ptcg."),
        (b"from rl_ptcg import", b"from research.rl_ptcg import"),
        (b'"tools.', b'"infrastructure.tools.'),
        (b"'tools.", b"'infrastructure.tools."),
        (b'"rl_ptcg.', b'"research.rl_ptcg.'),
        (b"'rl_ptcg.", b"'research.rl_ptcg."),
    )
    for old, new in replacements:
        data = data.replace(old, new)

    lines: list[bytes] = []
    for line in data.splitlines(keepends=True):
        for old, components in PYTHON_JOIN_MOVES:
            old_join = f'/ "{old}"'.encode("ascii")
            component_chain = b' / '.join(
                f'"{component}"'.encode("ascii") for component in components
            )
            new_join = b" / " + component_chain
            duplicated_chain = (
                f'"{components[0]}" / '.encode("ascii") + component_chain
            )
            while duplicated_chain in line:
                line = line.replace(duplicated_chain, component_chain)
            if new_join not in line:
                line = line.replace(old_join, new_join)
        lines.append(line)
    data = b"".join(lines)

    relative = path.relative_to(ROOT)
    if relative.parts[:2] == ("infrastructure", "tools") and len(relative.parts) == 3:
        data = data.replace(b"Path(__file__).resolve().parents[1]", b"Path(__file__).resolve().parents[2]")
    if relative.parts[:2] == ("research", "rl_ptcg"):
        if len(relative.parts) >= 3 and relative.parts[2] == "tests":
            data = data.replace(b"Path(__file__).resolve().parents[2]", b"Path(__file__).resolve().parents[3]")
            data = data.replace(b"Path(__file__).parents[2]", b"Path(__file__).parents[3]")
        elif len(relative.parts) == 3:
            data = data.replace(b"Path(__file__).resolve().parents[1]", b"Path(__file__).resolve().parents[2]")
    return data


def main() -> None:
    changed: list[dict[str, object]] = []
    for path in candidate_files():
        original = path.read_bytes()
        if b"\0" in original[:8192]:
            continue
        data, replacements = rewrite_paths(original)
        data = rewrite_python_structure(path, data)
        if data == original:
            continue
        path.write_bytes(data)
        changed.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "path_replacements": replacements,
                "before_sha256": hashlib.sha256(original).hexdigest().upper(),
                "after_sha256": hashlib.sha256(data).hexdigest().upper(),
            }
        )
    payload = {
        "base_commit": "0f22d49",
        "scope": "Archaludon and Alakazam executable code and active configuration",
        "historical_evidence_rewritten": False,
        "files_changed_this_run": len(changed),
        "idempotent": True,
        "directory_moves": dict(DIRECTORY_MOVES),
        "files": changed,
    }
    REPORT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files_changed_this_run": len(changed)}))


if __name__ == "__main__":
    main()
