from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE_RUNNER = HERE / "run_fixed160.py"


def main() -> None:
    module_spec = importlib.util.spec_from_file_location(
        "rule3_parent_prefix_checked_fixed760",
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
