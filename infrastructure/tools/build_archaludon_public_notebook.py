from __future__ import annotations

import argparse
import csv
import json
import tarfile
from pathlib import Path

import nbformat


REQUIRED_MEMBERS = {"main.py", "deck.csv", "requirements.txt"}


def read_archive(archive: Path) -> tuple[str, str, str]:
    with tarfile.open(archive, "r:gz") as bundle:
        names = set(bundle.getnames())
        missing = REQUIRED_MEMBERS - names
        if missing:
            raise ValueError(f"archive is missing required members: {sorted(missing)}")
        main_source = bundle.extractfile("main.py").read().decode("utf-8")
        deck_source = bundle.extractfile("deck.csv").read().decode("utf-8-sig")
        requirements = bundle.extractfile("requirements.txt").read().decode("utf-8")
    cards = [int(value) for value in deck_source.split()]
    if len(cards) != 60:
        raise ValueError(f"expected 60 deck rows, found {len(cards)}")
    compile(main_source, "main.py", "exec")
    return main_source, deck_source, requirements


def read_deck_summary(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if sum(int(row["count"]) for row in rows) != 60:
        raise ValueError("deck summary does not total 60 cards")
    return rows


def source_literal(value: str) -> str:
    return repr(value)


def build_notebook(
    *,
    main_source: str,
    deck_source: str,
    requirements: str,
    deck_summary: list[dict[str, str]],
    archive_sha256: str,
    revalidation_submission_id: int,
) -> nbformat.NotebookNode:
    notebook = nbformat.v4.new_notebook()
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3"},
    }

    rows_json = json.dumps(deck_summary, ensure_ascii=False)
    notebook["cells"] = [
        nbformat.v4.new_markdown_cell(
            "# Archaludon rule agent: reproducible silver recheck\n\n"
            "This notebook exposes the complete rule policy and 60-card deck of an "
            "Archaludon agent that previously reached **1045.58** in the live arena. "
            "It repeatedly crossed 1000 during the same run and was 18-8 after 26 "
            "public games. The score later declined, so the peak is not presented as "
            "a stable final estimate.\n\n"
            f"A fresh live revalidation is running as submission `{revalidation_submission_id}`. "
            "This draft must not be described as a current silver agent until that "
            "submission reaches the live silver range with enough public games."
        ),
        nbformat.v4.new_markdown_cell(
            "## What is rule based here\n\n"
            "The policy scores every legal option and then applies narrow public-state "
            "guards. It does not use a neural network. The main components are:\n\n"
            "- board setup and Duraludon/Archaludon evolution planning;\n"
            "- discard-aware energy acceleration and attachment routing;\n"
            "- matchup detection from visible cards only;\n"
            "- Great Tusk/Crustle deck-preservation rules;\n"
            "- non-ex Archaludon routes for Cornerstone Ogerpon and one-prize endgames;\n"
            "- damage-aware healing, retreat, Boss targeting, and prize mapping;\n"
            "- conservative fallbacks when no matchup-specific condition is proven.\n\n"
            "Opponent hands, prize cards, future logs, and hidden deck order are not "
            "used by the policy."
        ),
        nbformat.v4.new_code_cell(
            "from pathlib import Path\n"
            "import json\n"
            "import pandas as pd\n\n"
            f"deck_rows = json.loads({rows_json!r})\n"
            "deck = pd.DataFrame(deck_rows)\n"
            "deck['count'] = deck['count'].astype(int)\n"
            "display(deck[['count', 'name', 'card_id']])\n"
            "assert deck['count'].sum() == 60"
        ),
        nbformat.v4.new_markdown_cell(
            "## Deck construction\n\n"
            "The list uses four Duraludon, four Archaludon ex, four Cinderace, and two "
            "non-ex Archaludon. Cinderace supplies an early one-prize attacker and "
            "energy bridge. The non-ex line handles ability denial and selected final-"
            "prize states. Three Night Stretcher, three Jumbo Ice Cream, and three Full "
            "Metal Lab balance recovery, healing, and damage reduction without cutting "
            "the 12-Energy core."
        ),
        nbformat.v4.new_markdown_cell(
            "## Complete policy source\n\n"
            "The policy below is the exact `main.py` from the historically tested "
            "archive.\n\n```python\n"
            + main_source
            + "\n```"
        ),
        nbformat.v4.new_code_cell(
            "# Materialize the complete source-only agent.\n"
            "WORK = Path('/kaggle/working/archaludon_rule_agent')\n"
            "WORK.mkdir(parents=True, exist_ok=True)\n\n"
            f"MAIN_SOURCE = {source_literal(main_source)}\n"
            f"DECK_SOURCE = {source_literal(deck_source)}\n"
            f"REQUIREMENTS = {source_literal(requirements)}\n\n"
            "(WORK / 'main.py').write_text(MAIN_SOURCE, encoding='utf-8')\n"
            "(WORK / 'deck.csv').write_text(DECK_SOURCE, encoding='utf-8')\n"
            "(WORK / 'requirements.txt').write_text(REQUIREMENTS, encoding='utf-8')\n"
            "compile(MAIN_SOURCE, 'main.py', 'exec')\n"
            "assert len([line for line in DECK_SOURCE.splitlines() if line.strip()]) == 60\n"
            "print(f'Wrote source agent to {WORK}')"
        ),
        nbformat.v4.new_markdown_cell(
            "## Build a submission archive\n\n"
            "The competition input supplies the official `cg` runtime. The following "
            "cell locates that runtime rather than embedding or modifying the game "
            "engine. It then creates the same archive layout expected by the simulator."
        ),
        nbformat.v4.new_code_cell(
            "import shutil\n"
            "import tarfile\n\n"
            "input_root = Path('/kaggle/input')\n"
            "engine_candidates = [\n"
            "    path.parent for path in input_root.rglob('libcg.so')\n"
            "    if path.parent.name == 'cg'\n"
            "    and (path.parent / 'api.py').is_file()\n"
            "    and (path.parent / 'sim.py').is_file()\n"
            "]\n"
            "if not engine_candidates:\n"
            "    raise FileNotFoundError('Attach the Pokemon TCG AI Battle competition data.')\n"
            "engine_dir = sorted(engine_candidates, key=lambda path: str(path))[0]\n"
            "target_cg = WORK / 'cg'\n"
            "if target_cg.exists():\n"
            "    shutil.rmtree(target_cg)\n"
            "shutil.copytree(\n"
            "    engine_dir, target_cg,\n"
            "    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),\n"
            ")\n\n"
            "archive = Path('/kaggle/working/submission_archaludon_rule_agent.tar.gz')\n"
            "with tarfile.open(archive, 'w:gz') as bundle:\n"
            "    for name in ('main.py', 'deck.csv', 'requirements.txt', 'cg'):\n"
            "        bundle.add(WORK / name, arcname=name)\n"
            "print(archive)"
        ),
        nbformat.v4.new_code_cell(
            "# Import the generated package with the official Linux runtime.\n"
            "import importlib.util\n"
            "import sys\n\n"
            "sys.path.insert(0, str(WORK))\n"
            "spec = importlib.util.spec_from_file_location('archaludon_rule_agent', WORK / 'main.py')\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "assert callable(module.agent)\n"
            "print('agent entrypoint import: OK')"
        ),
        nbformat.v4.new_code_cell(
            "# Structural verification without running a match.\n"
            "import hashlib\n\n"
            "with tarfile.open(archive, 'r:gz') as bundle:\n"
            "    names = bundle.getnames()\n"
            "    packaged_deck = bundle.extractfile('deck.csv').read().decode('utf-8-sig')\n"
            "assert {'main.py', 'deck.csv', 'requirements.txt', 'cg'} <= set(names)\n"
            "assert len([line for line in packaged_deck.splitlines() if line.strip()]) == 60\n"
            "print({'members': len(names), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})"
        ),
        nbformat.v4.new_markdown_cell(
            "## Interpreting the result\n\n"
            f"The original tested archive has SHA256 `{archive_sha256.lower()}`. A newly "
            "built archive can have a different gzip hash while preserving the same "
            "source policy and deck because the official runtime files and archive "
            "metadata may differ.\n\n"
            "The useful result is not the historical peak alone. Before publishing this "
            "draft, add the fresh score trajectory, number of public games, matchup "
            "record, and the current silver cutoff. Report regressions as well as wins."
        ),
    ]
    return notebook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the public Archaludon notebook draft.")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--deck-summary", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--submission-id", type=int, required=True)
    parser.add_argument(
        "--kernel-id",
        default="rurururumi/ptcg-archaludon-rule-agent-silver-recheck",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    main_source, deck_source, requirements = read_archive(args.archive)
    deck_summary = read_deck_summary(args.deck_summary)
    notebook = build_notebook(
        main_source=main_source,
        deck_source=deck_source,
        requirements=requirements,
        deck_summary=deck_summary,
        archive_sha256=args.archive_sha256,
        revalidation_submission_id=args.submission_id,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, args.out_dir / "notebook.ipynb")
    metadata = {
        "id": args.kernel_id,
        "title": "PTCG Archaludon Rule Agent - Silver Recheck",
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_internet": False,
        "dataset_sources": [],
        "competition_sources": ["pokemon-tcg-ai-battle"],
        "kernel_sources": [],
    }
    (args.out_dir / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.out_dir / 'notebook.ipynb'}")


if __name__ == "__main__":
    main()
