from __future__ import annotations

import importlib.util
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
BASE_RUNNER = (
    HERE.parent
    / "archaludon_explorer_certified_attack_deadline_productive_prefix_v1"
    / "run_fixed760.py"
)


def main() -> None:
    module_spec = importlib.util.spec_from_file_location(
        "historical_silver_single_resolver_checked_fixed760",
        BASE_RUNNER,
    )
    if module_spec is None or module_spec.loader is None:
        raise AssertionError(f"cannot load checked runner: {BASE_RUNNER}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    module.SPEC_PATH = HERE / "fixed760_spec.json"
    module.main()


if __name__ == "__main__":
    main()
