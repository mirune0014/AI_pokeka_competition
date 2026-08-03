import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve()
CANDIDATE = HERE.parents[1]
ISOLATED = HERE.parents[3]
REPO = HERE.parents[4]
BASELINE = ISOLATED / "candidates" / "alakazam_neutralization_v0_public_best5_exact"
NOTEBOOK = ISOLATED / "evidence" / "public_code" / "alakazam_best5" / "rule-based-not-psychic-alakazam-best-5th.ipynb"
ENGINE = REPO  / "_local_generated" / "analysis_outputs" / "cynthia_v9_vs_v11_poffin_role_selection_20260713" / "seeded_engine"
sys.path.insert(0, str(ENGINE))

from cg.api import EnergyType, Pokemon, all_card_data  # noqa: E402


def load_module(agent_dir: Path, name: str):
    previous = Path.cwd()
    try:
        os.chdir(agent_dir)
        spec = importlib.util.spec_from_file_location(name, agent_dir / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous)


def test_exact_public_materialization():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    expected_deck = "".join(notebook["cells"][2]["source"]).split("\n", 1)[1]
    expected_main = "".join(notebook["cells"][3]["source"]).split("\n", 1)[1]
    # apply_patch preserves the cell text and adds one conventional terminal newline.
    assert (BASELINE / "deck.csv").read_text(encoding="utf-8") == expected_deck + "\n"
    assert (BASELINE / "main.py").read_text(encoding="utf-8") == expected_main + "\n"


def test_candidate_deck_exact_counts_and_ace_spec():
    deck = [int(line) for line in (CANDIDATE / "deck.csv").read_text().splitlines()]
    expected = Counter({
        741: 4, 742: 4, 743: 3, 305: 3, 66: 2, 140: 1, 142: 1, 858: 1, 343: 1,
        1086: 4, 1152: 4, 1079: 3, 1097: 1, 1129: 1, 1156: 3, 1081: 3,
        1182: 2, 1225: 4, 1231: 4, 1264: 4, 1247: 1, 5: 2, 19: 4,
    })
    assert len(deck) == 60
    assert Counter(deck) == expected
    cards = {card.cardId: card for card in all_card_data()}
    assert [card_id for card_id in deck if cards[card_id].aceSpec] == [1247]


def test_import_deck_return_and_determinism():
    module = load_module(CANDIDATE, "zone_candidate_import_test")
    observation = {"select": None, "logs": [], "current": None}
    expected = [int(line) for line in (CANDIDATE / "deck.csv").read_text().splitlines()]
    assert module.agent(observation) == expected
    assert module.agent(observation) == expected


def test_zone_public_state_gates():
    module = load_module(CANDIDATE, "zone_candidate_helper_test")
    dragapult = Pokemon(
        id=121, serial=1, hp=320, maxHp=320, appearThisTurn=False,
        energies=[EnergyType.FIRE], energyCards=[], tools=[], preEvolution=[],
    )
    assert module._public_ready_attacks(dragapult)  # ready now or after one attachment

    common = dict(
        visible_ready_ex=True, active_non_rule_box=True, zone_active=False,
        immediate_active_ko_before=False, immediate_active_ko_after=False,
        final_prize_ex_ko_threat=False, ready_non_ex_attacker=False,
        boss_ko_ready=False,
    )
    assert module._should_play_zone(**common)

    ko_veto = dict(common, immediate_active_ko_before=True, immediate_active_ko_after=False)
    assert not module._should_play_zone(**ko_veto)
    assert module._should_play_zone(**dict(ko_veto, final_prize_ex_ko_threat=True))

    non_ex_only = dict(common, visible_ready_ex=False, ready_non_ex_attacker=True)
    assert not module._should_play_zone(**non_ex_only)

    assert not module._should_play_battle_cage(
        stadium_id=1247, dragapult_pressure=True, zone_play_available=False,
    )
    assert not module._should_play_battle_cage(
        stadium_id=0, dragapult_pressure=True, zone_play_available=True,
    )
    assert module._should_play_battle_cage(
        stadium_id=0, dragapult_pressure=True, zone_play_available=False,
    )
    assert not module._should_play_battle_cage(
        stadium_id=0, dragapult_pressure=False, zone_play_available=False,
    )


if __name__ == "__main__":
    test_exact_public_materialization()
    test_candidate_deck_exact_counts_and_ace_spec()
    test_import_deck_return_and_determinism()
    test_zone_public_state_gates()
    print("zone candidate focused tests: PASS")
