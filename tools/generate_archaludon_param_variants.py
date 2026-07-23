from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Replacement:
    old: str
    new: str


@dataclass(frozen=True)
class Recipe:
    suffix: str
    replacements: tuple[Replacement, ...]


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        "takeboss6500",
        (
            Replacement(
                'if cid == BOSS:\n        return 2500, "take Boss"',
                'if cid == BOSS:\n        return 6500, "take Boss"',
            ),
        ),
    ),
    Recipe(
        "takefml8000",
        (
            Replacement(
                'if cid == FULL_METAL_LAB:\n        return 5000, "take Full Metal Lab"',
                'if cid == FULL_METAL_LAB:\n        return 8000, "take Full Metal Lab"',
            ),
        ),
    ),
    Recipe(
        "ubempty1500",
        (
            Replacement(
                'if bench_empty:\n                return 300, "Ultra Ball: bench empty (donk risk)"',
                'if bench_empty:\n                return 1500, "Ultra Ball: bench empty (donk risk)"',
            ),
        ),
    ),
    Recipe(
        "ubempty3500",
        (
            Replacement(
                'if bench_empty:\n                return 300, "Ultra Ball: bench empty (donk risk)"',
                'if bench_empty:\n                return 3500, "Ultra Ball: bench empty (donk risk)"',
            ),
        ),
    ),
    Recipe(
        "benchboss8500",
        (
            Replacement(
                "s = 4000 + pv * 200 + energy_count(target) * 100",
                "s = 8500 + pv * 400 + energy_count(target) * 200",
            ),
        ),
    ),
    Recipe(
        "lillie7500",
        (
            Replacement(
                'return 5000, "play Lillie"',
                'return 7500, "play Lillie"',
            ),
        ),
    ),
)


def apply_recipe(text: str, recipe: Recipe) -> str:
    for replacement in recipe.replacements:
        count = text.count(replacement.old)
        if count != 1:
            raise ValueError(
                f"{recipe.suffix}: expected exactly one match for {replacement.old!r}, found {count}"
            )
        text = text.replace(replacement.old, replacement.new)
    return text


def generate(base: Path, out_root: Path, prefix: str, recipes: tuple[Recipe, ...]) -> list[Path]:
    created: list[Path] = []
    base = base.resolve()
    if not (base / "main.py").exists():
        raise FileNotFoundError(f"missing main.py under {base}")
    for recipe in recipes:
        target = out_root / f"{prefix}_{recipe.suffix}"
        if target.exists():
            raise FileExistsError(f"{target} already exists")
        shutil.copytree(base, target)
        main_path = target / "main.py"
        text = main_path.read_text(encoding="utf-8")
        main_path.write_text(apply_recipe(text, recipe), encoding="utf-8")
        created.append(target)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate small Archaludon score-sweep variants.")
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("submission_archaludon_safe_gt58guard_strict4_oger_lowdeck_t14_l7"),
    )
    parser.add_argument("--out-root", type=Path, default=Path("."))
    parser.add_argument("--prefix", default="submission_archaludon_param")
    parser.add_argument(
        "--recipe",
        action="append",
        choices=[recipe.suffix for recipe in RECIPES],
        help="Generate only selected recipe(s). Defaults to all recipes.",
    )
    args = parser.parse_args()

    selected = RECIPES
    if args.recipe:
        selected = tuple(recipe for recipe in RECIPES if recipe.suffix in set(args.recipe))
    created = generate(args.base, args.out_root, args.prefix, selected)
    for path in created:
        print(path)


if __name__ == "__main__":
    main()
