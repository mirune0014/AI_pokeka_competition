import importlib.util
import os
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve()
CANDIDATE = HERE.parents[1]
ISOLATED = HERE.parents[3]
REPO = HERE.parents[4]
PARENT = ISOLATED / "candidates" / "alakazam_neutralization_v0_public_best5_exact"
ENGINE = REPO  / "_local_generated" / "analysis_outputs" / "cynthia_v9_vs_v11_poffin_role_selection_20260713" / "seeded_engine"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(ENGINE))

from cg.api import EnergyType, Pokemon, all_card_data  # noqa: E402
from infrastructure.tools.ptcg_common import ensure_engine_on_path, load_agent  # noqa: E402


def load_source(agent_dir: Path, name: str):
    previous = Path.cwd()
    try:
        os.chdir(agent_dir)
        spec = importlib.util.spec_from_file_location(name, agent_dir / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        os.chdir(previous)


def card(card_id, serial, player_index):
    return {"id": card_id, "serial": serial, "playerIndex": player_index}


def pokemon(card_id, serial, hp, max_hp, energies, player_index):
    energy_cards = [card(int(energy), serial * 10 + i, player_index) for i, energy in enumerate(energies)]
    return {
        "id": card_id, "serial": serial, "hp": hp, "maxHp": max_hp,
        "appearThisTurn": False, "energies": list(energies),
        "energyCards": energy_cards, "tools": [], "preEvolution": [],
    }


def player(active, bench, hand, prizes):
    return {
        "active": [active] if active is not None else [], "bench": bench,
        "benchMax": 5, "deckCount": 30, "discard": [], "prize": [None] * prizes,
        "handCount": len(hand) if hand is not None else 5, "hand": hand,
        "poisoned": False, "burned": False, "asleep": False,
        "paralyzed": False, "confused": False,
    }


def state(my_player, opponent, supporter_played=False):
    return {
        "turn": 6, "turnActionCount": 0, "yourIndex": 0, "firstPlayer": 0,
        "supporterPlayed": supporter_played, "stadiumPlayed": False,
        "energyAttached": False, "retreated": False, "result": -1,
        "stadium": [], "looking": None, "players": [my_player, opponent],
    }


def select_data(options, context=0, select_type=0, effect=None):
    return {
        "type": select_type, "context": context, "minCount": 1, "maxCount": 1,
        "remainDamageCounter": 0, "remainEnergyCost": 0, "option": options,
        "deck": None, "contextCard": None, "effect": effect,
    }


def positive_main_observation(include_acerola=True):
    alakazam = pokemon(743, 10, 140, 140, [5], 0)
    abra = pokemon(741, 11, 50, 50, [], 0)
    eevee_ex = pokemon(249, 20, 180, 200, [2, 3], 1)
    hand_ids = [1228, 1156, 1156, 1081, 1086, 1097] if include_acerola else [1225, 1156, 1156, 1081, 1086, 1097]
    hand = [card(card_id, 100 + i, 0) for i, card_id in enumerate(hand_ids)]
    my_player = player(alakazam, [abra], hand, prizes=2)
    opponent = player(eevee_ex, [], None, prizes=2)
    options = [
        {"type": 7, "index": 0, "playerIndex": 0},
        {"type": 13, "attackId": 1072},
        {"type": 14},
    ]
    return {"current": state(my_player, opponent), "logs": [], "select": select_data(options)}


def target_observation():
    obs = positive_main_observation()
    obs["current"]["supporterPlayed"] = True
    obs["current"]["players"][0]["hand"] = obs["current"]["players"][0]["hand"][1:]
    obs["current"]["players"][0]["handCount"] = 5
    options = [
        {"type": 3, "area": 5, "index": 0, "playerIndex": 0},
        {"type": 3, "area": 4, "index": 0, "playerIndex": 0},
    ]
    obs["select"] = select_data(
        options, context=25, select_type=1, effect=card(1228, 100, 0),
    )
    return obs


def test_deck_legality_and_exact_diff():
    parent = [int(line) for line in (PARENT / "deck.csv").read_text().splitlines()]
    candidate = [int(line) for line in (CANDIDATE / "deck.csv").read_text().splitlines()]
    assert len(candidate) == 60
    expected = Counter(parent)
    expected[1264] -= 1
    expected[1228] += 1
    assert Counter(candidate) == expected
    assert Counter(candidate)[1264] == 3
    assert Counter(candidate)[1228] == 1
    assert Counter(candidate)[13] == 1
    cards = {item.cardId: item for item in all_card_data()}
    assert [card_id for card_id in candidate if cards[card_id].aceSpec] == [13]
    assert (CANDIDATE / "runtime" / "deck.csv").read_bytes() == (CANDIDATE / "deck.csv").read_bytes()


def test_fixed_public_ko_certificate_is_fail_closed():
    module = load_source(CANDIDATE, "acerola_certificate_test")
    alakazam = Pokemon(743, 1, 140, 140, False, [EnergyType.PSYCHIC], [], [], [])
    eevee_ex = Pokemon(249, 2, 180, 200, False, [EnergyType.FIRE, EnergyType.WATER], [], [], [])
    assert module._certified_fixed_ko_attacks(eevee_ex, alakazam, max_missing=1)
    eevee_ex.energies = [EnergyType.FIRE]
    assert not module._certified_fixed_ko_attacks(eevee_ex, alakazam, max_missing=1)
    dragapult = Pokemon(121, 3, 320, 320, False, [EnergyType.FIRE, EnergyType.PSYCHIC], [], [], [])
    assert not module._certified_fixed_ko_attacks(dragapult, alakazam, max_missing=1)


def test_non_ex_veto_requires_current_attack_readiness():
    module = load_source(CANDIDATE, "acerola_non_ex_readiness_test")
    alakazam = Pokemon(743, 1, 140, 140, False, [EnergyType.PSYCHIC], [], [], [])
    carracosta = Pokemon(155, 2, 150, 170, False, [EnergyType.WATER], [], [], [])
    # Tidal Wave costs two Water: one attached is one missing and must not veto Acerola.
    assert not module._certified_fixed_ko_attacks(carracosta, alakazam, max_missing=0)
    carracosta.energies = [EnergyType.WATER, EnergyType.WATER]
    assert module._certified_fixed_ko_attacks(carracosta, alakazam, max_missing=0)


def test_immediate_damage_uses_only_current_hand_and_required_hammers():
    module = load_source(CANDIDATE, "acerola_immediate_damage_test")
    assert module._acerola_immediate_damage(
        hand_size=6, defense_energy_count=0, enhanced_hammer_count=0,
    ) == 100
    damage_with_hammer = module._acerola_immediate_damage(
        hand_size=6, defense_energy_count=1, enhanced_hammer_count=1,
    )
    assert damage_with_hammer == 80

    bridge = dict(
        acerola_in_hand=True, supporter_unused=True, opponent_prizes=2,
        active_is_alakazam=True, active_has_psychic=True, powerful_hand_legal=True,
        opponent_active_is_ex=True, opponent_ex_ready_ko=True,
        ready_non_ex_ko=False, immediate_winning_ko=False,
        projected_damage=damage_with_hammer, opponent_active_hp=150,
        ex_takes_all_prizes=True, bench_has_two_prize_rule_box=False,
        bench_empty=False,
    )
    assert module._acerola_final_bridge(**bridge)
    assert not module._acerola_final_bridge(**dict(bridge, opponent_active_hp=170))

    unpaid = module._acerola_immediate_damage(
        hand_size=8, defense_energy_count=2, enhanced_hammer_count=1,
    )
    assert unpaid == -1
    assert not module._acerola_final_bridge(**dict(bridge, projected_damage=unpaid))


def test_pure_predicate_positive_and_each_bounded_negative():
    module = load_source(CANDIDATE, "acerola_predicate_test")
    common = dict(
        acerola_in_hand=True, supporter_unused=True, opponent_prizes=2,
        active_is_alakazam=True, active_has_psychic=True, powerful_hand_legal=True,
        opponent_active_is_ex=True, opponent_ex_ready_ko=True,
        ready_non_ex_ko=False, immediate_winning_ko=False,
        projected_damage=100, opponent_active_hp=180, ex_takes_all_prizes=True,
        bench_has_two_prize_rule_box=False, bench_empty=False,
    )
    assert module._acerola_final_bridge(**common)
    negatives = [
        {"acerola_in_hand": False}, {"supporter_unused": False},
        {"opponent_prizes": 3}, {"active_is_alakazam": False},
        {"active_has_psychic": False}, {"powerful_hand_legal": False},
        {"opponent_active_is_ex": False}, {"opponent_ex_ready_ko": False},
        {"ready_non_ex_ko": True}, {"immediate_winning_ko": True},
        {"projected_damage": 180}, {"opponent_active_hp": 201},
        {"ex_takes_all_prizes": False}, {"bench_has_two_prize_rule_box": True},
        {"opponent_prizes": 1, "bench_empty": False},
    ]
    for change in negatives:
        case = dict(common)
        case.update(change)
        assert not module._acerola_final_bridge(**case), change


def test_agent_positive_target_determinism_and_unchanged_fallback():
    candidate = load_source(CANDIDATE, "acerola_action_test")
    parent = load_source(PARENT, "acerola_parent_fallback_test")
    positive = positive_main_observation()
    assert candidate.agent(positive) == [0]
    assert candidate.agent(positive) == [0]
    assert candidate.agent(target_observation()) == [1]

    fallback = positive_main_observation(include_acerola=False)
    assert candidate.agent(fallback) == parent.agent(fallback)

    # A bench Kadabra plus Alakazam in hand offers a future +2 maximum draw,
    # but the immediate four-card hand gives D=(4-1)*20=60 and must not bridge.
    unused_draw = positive_main_observation()
    unused_draw["current"]["players"][0]["hand"] = [
        card(1228, 100, 0), card(743, 101, 0), card(1156, 102, 0), card(1081, 103, 0),
    ]
    unused_draw["current"]["players"][0]["handCount"] = 4
    unused_draw["current"]["players"][0]["bench"].append(
        pokemon(742, 12, 80, 80, [], 0)
    )
    assert candidate.agent(unused_draw) == [1]


def test_repo_root_runtime_import_and_deck_return():
    ensure_engine_on_path(ENGINE)
    runtime = CANDIDATE / "runtime"
    agent = load_agent(runtime, "acerola_runtime_root_import_test")
    observation = {"select": None, "logs": [], "current": None}
    expected = [int(line) for line in (runtime / "deck.csv").read_text().splitlines()]
    assert agent(observation) == expected
    assert agent(observation) == expected


if __name__ == "__main__":
    test_deck_legality_and_exact_diff()
    test_fixed_public_ko_certificate_is_fail_closed()
    test_non_ex_veto_requires_current_attack_readiness()
    test_immediate_damage_uses_only_current_hand_and_required_hammers()
    test_pure_predicate_positive_and_each_bounded_negative()
    test_agent_positive_target_determinism_and_unchanged_fallback()
    test_repo_root_runtime_import_and_deck_return()
    print("acerola final bridge focused tests: PASS")
