from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPLAY_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "54757713"
    / "monitor_20260716_1926"
    / "replays_current_minus_prior"
)


def load_module():
    spec = importlib.util.spec_from_file_location("bench_ex_candidate", HERE / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def replay_observation(episode: int, step: int) -> dict:
    replay = json.loads(
        (REPLAY_DIR / f"episode_{episode}_replay.json").read_text(encoding="utf-8")
    )
    seat = replay["info"]["TeamNames"].index("rurumi")
    return copy.deepcopy(replay["steps"][step][seat]["observation"])


def as_active_archaludon(raw: dict) -> None:
    current = raw["current"]
    mine = current["players"][current["yourIndex"]]
    active = mine["active"][0]
    active.update({"id": 190, "hp": 300, "maxHp": 300})


def certified(module, raw: dict):
    obs = module.to_observation_class(raw)
    options = [
        option
        for option in obs.select.option
        if option.type == module.OptionType.EVOLVE
        and option.inPlayArea == module.AreaType.BENCH
        and (card := module.option_card(obs, option)) is not None
        and card.id == module.ARCHALUDON_EX
        and (target := module.option_target(obs, option)) is not None
        and target.id == module.DURALUDON
    ]
    return obs, options, [module._bench_ex_continuity_option(obs, option) for option in options]


def add_bench_duraludon(raw: dict, *, energy_count: int) -> None:
    current = raw["current"]
    yi = current["yourIndex"]
    mine = current["players"][yi]
    pokemon = copy.deepcopy(mine["bench"][0])
    pokemon.update({"id": 169, "serial": 9000, "hp": 130, "maxHp": 130})
    pokemon["energies"] = [8] * energy_count
    pokemon["energyCards"] = [
        {"id": 8, "serial": 9100 + index, "playerIndex": yi}
        for index in range(energy_count)
    ]
    mine["bench"].append(pokemon)
    existing = [
        option
        for option in raw["select"]["option"]
        if option["type"] == 9
        and option.get("inPlayArea") == 5
        and option.get("index") in {0, 2}
    ]
    for option in existing:
        duplicate = copy.deepcopy(option)
        duplicate["inPlayIndex"] = 1
        raw["select"]["option"].append(duplicate)


def main() -> None:
    module = load_module()

    # Exact live positive: one zero-Energy backup still qualifies because it is
    # the only Archaludon-line Pokemon on the Bench.
    marnie = replay_observation(86278699, 60)
    obs, options, flags = certified(module, marnie)
    assert len(options) == 1 and flags == [True]
    assert module.score_evolve(obs, options[0]) == (
        19000,
        "continuity: evolve certified bench backup",
    )

    # Duplicate Archaludon ex cards aimed at one target must yield exactly one
    # deterministic winner rather than two equal certified options.
    lucario = replay_observation(86279220, 40)
    as_active_archaludon(lucario)
    _, options, flags = certified(module, lucario)
    assert len(options) == 2 and sum(flags) == 1

    # A higher-Energy second target wins the ranking; only one hand-card/target
    # option is certified after the target and card-serial tie breaks.
    ranked = copy.deepcopy(lucario)
    add_bench_duraludon(ranked, energy_count=2)
    ranked_obs, ranked_options, ranked_flags = certified(module, ranked)
    assert len(ranked_options) == 4 and sum(ranked_flags) == 1
    winner = ranked_options[ranked_flags.index(True)]
    assert module.option_target(ranked_obs, winner).serial == 9000

    negatives = {}

    not_active_ex = replay_observation(86279220, 40)
    negatives["active_not_archaludon_ex"] = certified(module, not_active_ex)[2]

    extra_ex = copy.deepcopy(lucario)
    extra = copy.deepcopy(extra_ex["current"]["players"][0]["bench"][0])
    extra.update({"id": 190, "serial": 9200, "hp": 300, "maxHp": 300})
    extra_ex["current"]["players"][0]["bench"].append(extra)
    negatives["more_than_one_archaludon_ex"] = certified(module, extra_ex)[2]

    weak_multi_backup = copy.deepcopy(lucario)
    add_bench_duraludon(weak_multi_backup, energy_count=1)
    negatives["multi_backup_target_below_two_energy"] = certified(
        module, weak_multi_backup
    )[2]

    low_opp_prizes = copy.deepcopy(lucario)
    current = low_opp_prizes["current"]
    current["players"][1 - current["yourIndex"]]["prize"] = [None, None]
    negatives["opponent_below_three_prizes"] = certified(module, low_opp_prizes)[2]

    immediate_prize_win = copy.deepcopy(lucario)
    current = immediate_prize_win["current"]
    current["players"][current["yourIndex"]]["prize"] = [None]
    negatives["current_active_prize_wins"] = certified(module, immediate_prize_win)[2]

    cornerstone = copy.deepcopy(lucario)
    current = cornerstone["current"]
    opponent = current["players"][1 - current["yourIndex"]]
    visible = copy.deepcopy(opponent["bench"][0])
    visible.update({"id": 117, "serial": 9300, "hp": 210, "maxHp": 210})
    opponent["bench"].append(visible)
    negatives["cornerstone_visible"] = certified(module, cornerstone)[2]

    crustle = copy.deepcopy(lucario)
    current = crustle["current"]
    opponent = current["players"][1 - current["yourIndex"]]
    opponent["active"][0].update({"id": 345, "hp": 140, "maxHp": 140})
    negatives["crustle_matchup"] = certified(module, crustle)[2]

    unknown_serial = copy.deepcopy(lucario)
    current = unknown_serial["current"]
    current["players"][current["yourIndex"]]["bench"][0]["serial"] = None
    negatives["unknown_target_serial"] = certified(module, unknown_serial)[2]

    original_final_rule = module.final_prize_nonex_no_backup
    try:
        module.final_prize_nonex_no_backup = lambda _obs: True
        negatives["final_prize_nonex_no_backup"] = certified(module, lucario)[2]
    finally:
        module.final_prize_nonex_no_backup = original_final_rule

    assert all(not any(flags) for flags in negatives.values()), negatives
    print(
        json.dumps(
            {
                "positive_live_score": 19000,
                "duplicate_option_certified_count": sum(flags),
                "ranked_winner_serial": 9000,
                "negative_checks": {name: "fail_closed" for name in negatives},
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
