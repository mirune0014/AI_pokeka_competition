from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
TEST = HERE / "test_focused_h6.py"
CANDIDATE = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_attack_completing_energy_reservation_v2"
    / "main.py"
)
EXPECTED_CANDIDATE_SHA256 = (
    "C2B2E6E2A3170A1E90853CD0128075EA023831C17F2B7263744E371FC826E530"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    if sha256(CANDIDATE) != EXPECTED_CANDIDATE_SHA256:
        raise AssertionError("candidate source identity changed")
    spec = importlib.util.spec_from_file_location("h6_v2_focused", TEST)
    if spec is None or spec.loader is None:
        raise RuntimeError(TEST)
    focused = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(focused)
    agent = focused.AGENT

    focused.reset()
    arm_state = focused.observation(90)
    arm_action = agent.choose_options(arm_state)
    transaction = copy.deepcopy(agent._h6_transaction)
    if transaction is None or transaction["stage"] != "RESERVED_PRE_ATTACH":
        raise AssertionError("H6 v2 failed to arm")

    changed = focused.observation(90)
    mine = agent.my_state(changed)
    metals_before = [
        card.serial
        for card in mine.hand
        if card is not None and card.id == agent.METAL_ENERGY
    ]
    extra = copy.deepcopy(
        next(
            card
            for card in mine.hand
            if card is not None and card.id == agent.METAL_ENERGY
        )
    )
    extra.serial = 998
    mine.hand.append(extra)
    mine.handCount = len(mine.hand)
    metals_after = [
        card.serial
        for card in mine.hand
        if card is not None and card.id == agent.METAL_ENERGY
    ]

    core_valid = agent._h6_core_valid(
        changed,
        transaction,
        after_attach=False,
    )
    parent = agent._historical_silver_choose_options(changed)
    candidate = agent.choose_options(changed)
    result = {
        "arm_action": arm_action,
        "candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "metals_before": metals_before,
        "metals_after": metals_after,
        "reserved_energy_serial": transaction["energy_serial"],
        "stage": transaction["stage"],
        "core_valid_after_uniqueness_change": core_valid,
        "contract_expected_core_valid": False,
        "parent_semantic": focused.semantic(changed, parent),
        "candidate_semantic": focused.semantic(changed, candidate),
        "exact_parent_action": focused.semantic(changed, parent)
        == focused.semantic(changed, candidate),
        "transaction_clear": agent._h6_transaction is None,
        "defect_closed": core_valid is False,
    }
    if not (
        result["defect_closed"]
        and result["exact_parent_action"]
        and result["transaction_clear"]
    ):
        raise AssertionError(result)
    output = HERE / "h6_uniqueness_reproducer_v2.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
