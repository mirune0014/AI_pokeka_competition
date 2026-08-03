from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1" / "run_fixed160.py"
SPEC = importlib.util.spec_from_file_location("_checked_fixed160", BASE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load checked fixed160 runner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MODULE.SPEC_PATH = HERE / "fixed160_spec.json"


if __name__ == "__main__":
    MODULE.main()
