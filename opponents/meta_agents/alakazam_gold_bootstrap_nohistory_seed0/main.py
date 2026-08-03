from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any

from research.rl_ptcg.gold_prompt_policy import GoldPromptHybridPolicy
from research.rl_ptcg.gold_prompt_ranker import load_ranker


ROOT = Path(__file__).resolve().parent
FALLBACK_PATH = ROOT.parent / "alakazam_psychic_public_simple" / "main.py"


def _load_fallback():
    name = "ptcg_alakazam_gold_bootstrap_fallback"
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, FALLBACK_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("could not load Alakazam fallback policy")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FALLBACK = _load_fallback()
MODEL = load_ranker(
    ROOT / "gold_prompt_ranker.pt",
    ROOT / "gold_prompt_ranker_manifest.json",
)
POLICY = GoldPromptHybridPolicy(MODEL, FALLBACK.agent)


def agent(observation: dict[str, Any]) -> list[int]:
    return POLICY(observation)
