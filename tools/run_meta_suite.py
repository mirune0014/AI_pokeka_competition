from __future__ import annotations

import argparse
import csv
from pathlib import Path
from types import SimpleNamespace

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path
from run_local_battle import run_game


META_OPPONENTS: dict[str, Path] = {
    "marnie": Path("submission_marnie_grimmsnarl"),
    "marnie_kei_live": Path("meta_agents/marnie_kei_live_84983053_simple"),
    "marnie_shota_live": Path("meta_agents/marnie_shota_live_85029339_simple"),
    "marnie_sota_live": Path("meta_agents/marnie_sota_live_85033057_simple"),
    "marnie_gonsaku_live": Path("meta_agents/marnie_gonsaku_live_85034863_simple"),
    "marnie_srmeg_live": Path("meta_agents/marnie_srmeg_live_85037325_simple"),
    "marnie_shardul_live": Path("meta_agents/marnie_shardul_live_85037813_simple"),
    "marnie_shishio_live": Path("meta_agents/marnie_shishio_live_85041778_simple"),
    "marnie_ysakuragi_live": Path("meta_agents/marnie_ysakuragi_live_85050361_simple"),
    "marnie_arsnoveau_live": Path("meta_agents/marnie_arsnoveau_live_85053222_simple"),
    "marnie_mykhailo_live": Path("meta_agents/marnie_mykhailo_live_85075581_simple"),
    "marnie_kazuki_live": Path("meta_agents/marnie_kazuki_live_85083586_simple"),
    "marnie_yushin_2026_07_08": Path("meta_agents/marnie_yushin_84743048_simple"),
    "marnie_gonsaku_2026_07_08": Path("meta_agents/marnie_gonsaku_84743055_simple"),
    "alakazam": Path("meta_agents/alakazam_psychic_public_simple"),
    "alakazam_noor_live": Path("meta_agents/alakazam_noor_live_84982062_simple"),
    "alakazam_tubotu_live": Path("meta_agents/alakazam_tubotu_live_84569848_simple"),
    "alakazam_kohenyan_live": Path("meta_agents/alakazam_kohenyan_live_85026363_simple"),
    "alakazam_kisamaki_live": Path("meta_agents/alakazam_kisamaki_live_85027847_simple"),
    "alakazam_ebisu_live": Path("meta_agents/alakazam_ebisu_live_85029849_simple"),
    "alakazam_capbloo_live": Path("meta_agents/alakazam_capbloo_live_85030556_simple"),
    "alakazam_capbloo2_live": Path("meta_agents/alakazam_capbloo2_live_85036033_simple"),
    "alakazam_oselcoun_live": Path("meta_agents/alakazam_oselcoun_live_85035844_simple"),
    "alakazam_abhyuday_live": Path("meta_agents/alakazam_abhyuday_live_85036339_simple"),
    "alakazam_tsukammo_live": Path("meta_agents/alakazam_tsukammo_live_85030817_simple"),
    "alakazam_55_live": Path("meta_agents/alakazam_55_live_85032356_simple"),
    "alakazam_ebi_live": Path("meta_agents/alakazam_ebi_live_85042306_simple"),
    "alakazam_kusui_live": Path("meta_agents/alakazam_kusui_live_85044440_simple"),
    "alakazam_ant_live": Path("meta_agents/alakazam_ant_live_85044679_simple"),
    "alakazam_pompom_live": Path("meta_agents/alakazam_pompom_live_85046024_simple"),
    "alakazam_matsurih_live": Path("meta_agents/alakazam_matsurih_live_85056873_simple"),
    "alakazam_ketchum_alt_live": Path("meta_agents/alakazam_ketchum_alt_live_85072862_simple"),
    "alakazam_rmy_live": Path("meta_agents/alakazam_rmy_live_85082271_simple"),
    "alakazam_majkel1337_2026_07_08": Path("meta_agents/alakazam_majkel1337_84743025_simple"),
    "alakazam_third_ptcg_2026_07_08": Path("meta_agents/alakazam_third_ptcg_84743063_simple"),
    "alakazam_55_2026_07_08": Path("meta_agents/alakazam_55_84743065_simple"),
    "archaludon": Path("meta_agents/archaludon_public"),
    "archaludon_ezreal77": Path("meta_agents/archaludon_ezreal77_83190494_simple"),
    "archaludon_ezreal77_live": Path("meta_agents/archaludon_ezreal77_live_85013912_simple"),
    "archaludon_ozanm_live": Path("meta_agents/archaludon_ozanm_live_85014881_simple"),
    "archaludon_victorvv_live": Path("meta_agents/archaludon_victorvv_live_85044984_simple"),
    "archaludon_toru_live": Path("meta_agents/archaludon_toru_live_85048021_simple"),
    "archaludon_shumpei_2026_07_08": Path("meta_agents/archaludon_shumpei_84743052_simple"),
    "great_tusk": Path("meta_agents/great_tusk_crustle_public"),
    "great_tusk_evan2_live": Path("meta_agents/great_tusk_evan2_live_85029139_simple"),
    "great_tusk_liamk_2026_07_08": Path("meta_agents/great_tusk_liamk_84743031_simple"),
    "great_tusk_bono_junlee_2026_07_08": Path("meta_agents/great_tusk_bono_junlee_84743036_simple"),
    "kangaskhan_crustle_dung_2026_07_08": Path("meta_agents/kangaskhan_crustle_dung_84743044_simple"),
    "ogerpon": Path("meta_agents/ogerpon_toolbox_monnosuke_simple"),
    "ogerpon_btk15049_2026_07_08": Path("meta_agents/ogerpon_btk15049_84743052_simple"),
    "ogerpon_zoroark190_2026_07_08": Path("meta_agents/ogerpon_zoroark190_84743095_simple"),
    "okidogi_majkel1337_2026_07_08": Path("meta_agents/okidogi_majkel1337_84743042_simple"),
    "lucario": Path("meta_agents/mega_lucario_public_simple"),
    "lucario_live": Path("meta_agents/mega_lucario_live_simple"),
    "lucario_aib4_live": Path("meta_agents/mega_lucario_aib4_live_84983544_simple"),
    "lucario_fujiborozoukin_live": Path("meta_agents/mega_lucario_fujiborozoukin_live_85033862_simple"),
    "lucario_mekeh_live": Path("meta_agents/mega_lucario_mekeh_live_85036843_simple"),
    "lucario_hamu_live": Path("meta_agents/mega_lucario_hamu_live_85060465_simple"),
    "lucario_genki_live": Path("meta_agents/mega_lucario_genki_live_85069777_simple"),
    "lucario_akira_2026_07_08": Path("meta_agents/mega_lucario_akira_84743057_simple"),
    "dragapult": Path("meta_agents/dragapult_live_simple"),
    "dragapult_lumen_live": Path("meta_agents/dragapult_lumen_live_85038765_simple"),
    "dragapult_rojiomote_live": Path("meta_agents/dragapult_rojiomote_live_85060632_simple"),
    "dragapult_bigbug_2026_07_08": Path("meta_agents/dragapult_bigbug_84743038_simple"),
    "rocket_mewtwo_spidops": Path("meta_agents/rocket_mewtwo_spidops_kashiwashira_20260703_simple"),
    "hop": Path("meta_agents/hop_trevenant_public_simple"),
    "starmie": Path("meta_agents/starmie_public_simple"),
    "starmie_windecks_2026_07_08": Path("meta_agents/starmie_windecks_84743054_simple"),
    "starmie_yushin_2026_07_08": Path("meta_agents/starmie_yushin_84743057_simple"),
    "chandelure": Path("meta_agents/chandelure_psychic_control_simple"),
    "chandelure_dick": Path("meta_agents/chandelure_psychic_control_dick"),
    "chandelure_koga_2026_07_08": Path("meta_agents/chandelure_koga_84743037_simple"),
    "chandelure_starmine_2026_07_08": Path("meta_agents/chandelure_starmine_84743078_simple"),
    "cubchoo_senkin13_live": Path("meta_agents/cubchoo_senkin13_live_85057952_simple"),
    "comfey_yveltal_koga_live": Path("meta_agents/comfey_yveltal_koga_live_85012465_simple"),
    "cynthia_garchomp_nasuo_live": Path("meta_agents/cynthia_garchomp_nasuo445_live_85023194_simple"),
    "cynthia_garchomp_topdecking_live": Path("meta_agents/cynthia_garchomp_topdecking_live_85038290_simple"),
    "cynthia_garchomp_jason_live": Path("meta_agents/cynthia_garchomp_jason_live_85074031_simple"),
    "alakazam_ketchum_alt": Path("meta_agents/alakazam_ketchum_alt_83700054_simple"),
    "iono_bellibolt": Path("meta_agents/iono_bellibolt_live_wasabi_simple"),
    "iono_bellibolt_alghital_live": Path("meta_agents/iono_bellibolt_alghital_live_85067649_simple"),
    "ogerpon_raging_bolt": Path("meta_agents/ogerpon_raging_bolt_public_simple"),
    "ogerpon_cornerstone": Path("meta_agents/ogerpon_cornerstone_public_simple"),
    "ogerpon_clefairy": Path("meta_agents/ogerpon_clefairy_public_simple"),
    "ogerpon_hydrapple": Path("meta_agents/ogerpon_hydrapple_public_simple"),
    "ogerpon_meganium": Path("meta_agents/ogerpon_meganium_public_simple"),
    "ogerpon_meganium_arboliva": Path("meta_agents/ogerpon_meganium_arboliva_public_simple"),
    "ogerpon_meganium_hydrapple": Path("meta_agents/ogerpon_meganium_hydrapple_public_simple"),
    "ogerpon_multi_mask": Path("meta_agents/ogerpon_multi_mask_public_simple"),
    "ogerpon_sinistcha": Path("meta_agents/ogerpon_sinistcha_public_simple"),
}

SCENARIOS: dict[str, dict[str, float]] = {
    "public_sample_2026_07_02": {
        "marnie": 11,
        "alakazam": 10,
        "archaludon": 6,
        "ogerpon": 4,
        "lucario": 2,
        "hop": 2,
        "chandelure": 2,
        "starmie": 1,
    },
    "public_sample_2026_07_02_top20": {
        "marnie": 12,
        "alakazam": 11,
        "archaludon": 6,
        "ogerpon": 4,
        "lucario": 2,
        "hop": 2,
        "chandelure": 2,
        "starmie": 1,
    },
    "public_sample_2026_07_03_top20": {
        "marnie": 12,
        "ogerpon": 7,
        "lucario": 4,
        "alakazam": 3,
        "archaludon": 3,
        "starmie": 3,
        "great_tusk": 2,
        "rocket_mewtwo_spidops": 2,
        "hop": 1,
        "chandelure": 1,
    },
    "public_sample_2026_07_08_top20": {
        "alakazam_majkel1337_2026_07_08": 3,
        "alakazam_third_ptcg_2026_07_08": 1,
        "alakazam_55_2026_07_08": 1,
        "great_tusk_liamk_2026_07_08": 1,
        "great_tusk_bono_junlee_2026_07_08": 3,
        "marnie_yushin_2026_07_08": 1,
        "marnie_gonsaku_2026_07_08": 1,
        "chandelure_koga_2026_07_08": 1,
        "chandelure_starmine_2026_07_08": 1,
        "okidogi_majkel1337_2026_07_08": 2,
        "dragapult_bigbug_2026_07_08": 1,
        "ogerpon_btk15049_2026_07_08": 1,
        "ogerpon_zoroark190_2026_07_08": 1,
        "archaludon_shumpei_2026_07_08": 1,
        "starmie_windecks_2026_07_08": 1,
        "starmie_yushin_2026_07_08": 1,
    },
    "live_alakazam_ketchum_alt_2026_07_04": {
        "alakazam_ketchum_alt": 1,
    },
    "discussion_starmie_heavy_2026_06_28": {
        "starmie": 5,
        "archaludon": 3,
        "alakazam": 2,
    },
    "discussion_ogerpon_toolbox_2026_07_04": {
        "ogerpon_raging_bolt": 4,
        "ogerpon_cornerstone": 3,
        "ogerpon": 2,
        "archaludon": 2,
        "starmie": 1,
        "alakazam": 1,
    },
    "discussion_ogerpon_public_variants_2026_07_09": {
        "ogerpon_raging_bolt": 1,
        "ogerpon_cornerstone": 1,
        "ogerpon_clefairy": 1,
        "ogerpon_hydrapple": 1,
        "ogerpon_meganium": 1,
        "ogerpon_meganium_arboliva": 1,
        "ogerpon_meganium_hydrapple": 1,
        "ogerpon_multi_mask": 1,
        "ogerpon_sinistcha": 1,
    },
    "live_chandelure_control_2026_07_04": {
        "chandelure": 1,
        "chandelure_dick": 1,
    },
    "live_dragapult_2026_07_09": {
        "dragapult": 1,
    },
    "live_lucario_2026_07_09": {
        "lucario_live": 1,
    },
    "live_aib4_lucario_2026_07_09": {
        "lucario_aib4_live": 1,
    },
    "live_fujiborozoukin_lucario_2026_07_09": {
        "lucario_fujiborozoukin_live": 1,
    },
    "live_hamu_lucario_2026_07_10": {
        "lucario_hamu_live": 1,
    },
    "live_genki_lucario_2026_07_10": {
        "lucario_genki_live": 1,
    },
    "public_akira_lucario_2026_07_08": {
        "lucario_akira_2026_07_08": 1,
    },
    "live_noor_alakazam_2026_07_09": {
        "alakazam_noor_live": 1,
    },
    "live_rojiomote_dragapult_2026_07_10": {
        "dragapult_rojiomote_live": 1,
    },
    "live_capbloo2_alakazam_2026_07_10": {
        "alakazam_capbloo2_live": 1,
    },
    "live_ketchum_alt_alakazam_2026_07_10": {
        "alakazam_ketchum_alt_live": 1,
    },
    "live_rmy_alakazam_2026_07_10": {
        "alakazam_rmy_live": 1,
    },
    "live_kei_marnie_2026_07_09": {
        "marnie_kei_live": 1,
    },
    "live_gonsaku_marnie_2026_07_09": {
        "marnie_gonsaku_live": 1,
    },
    "live_mykhailo_marnie_2026_07_10": {
        "marnie_mykhailo_live": 1,
    },
    "live_kazuki_marnie_2026_07_10": {
        "marnie_kazuki_live": 1,
    },
    "live_alghital_iono_2026_07_10": {
        "iono_bellibolt_alghital_live": 1,
    },
    "live_jason_cynthia_2026_07_10": {
        "cynthia_garchomp_jason_live": 1,
    },
    "public_dung_kangaskhan_crustle_2026_07_08": {
        "kangaskhan_crustle_dung_2026_07_08": 1,
    },
    "equal_public_buckets": {name: 1 for name in META_OPPONENTS},
}


def parse_agent(value: str) -> tuple[str, Path]:
    if "=" in value:
        name, path = value.split("=", 1)
        return name, Path(path)
    path = Path(value)
    return path.name, path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run candidate agents against local mimics of public top-side meta buckets."
    )
    parser.add_argument(
        "--candidate",
        action="append",
        required=True,
        help="Candidate spec. Use name=path or just path. Repeat for multiple candidates.",
    )
    parser.add_argument(
        "--opponent",
        action="append",
        choices=sorted(META_OPPONENTS),
        help="Limit to specific public-meta bucket(s). Defaults to all buckets.",
    )
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--games", type=int, default=2, help="Games per seat and matchup.")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--seed-base", type=int, help="Seed Python-side randomness as seed_base + game_id.")
    parser.add_argument("--out", type=Path, default=Path("analysis_outputs/meta_suite_results.csv"))
    parser.add_argument("--summary-out", type=Path, default=Path("analysis_outputs/meta_suite_summary.csv"))
    parser.add_argument("--game-out", type=Path, help="Optional per-game result CSV for loss analysis.")
    parser.add_argument("--trace-root", type=Path, default=Path("analysis_outputs/meta_suite_traces"))
    parser.add_argument("--trace-scores", action="store_true", help="Include score/reason data in trace JSONL files.")
    parser.add_argument("--trace-score-limit", type=int, default=8, help="Number of top scored options to store per step.")
    parser.add_argument(
        "--fair-seeds",
        action="store_true",
        help="Reuse the same game_id schedule for every candidate within each bucket/seat order.",
    )
    return parser.parse_args()


def check_agent_dir(path: Path) -> None:
    missing = [name for name in ("main.py", "deck.csv") if not (path / name).exists()]
    if missing:
        raise FileNotFoundError(f"{path} is missing {', '.join(missing)}")


def run_ordered_matchup(
    *,
    engine_dir: Path,
    name_a: str,
    path_a: Path,
    name_b: str,
    path_b: Path,
    games: int,
    max_steps: int,
    trace_root: Path | None,
    game_id_start: int,
    seed_base: int | None,
    trace_scores: bool = False,
    trace_score_limit: int = 8,
) -> tuple[dict[str, object], int, list[dict[str, object]]]:
    wins_a = 0
    wins_b = 0
    draws_or_unknown = 0
    errors = 0
    total_steps = 0
    game_id = game_id_start
    trace_dir = trace_root / f"{name_a}_vs_{name_b}" if trace_root is not None else None
    game_rows: list[dict[str, object]] = []

    for local_game in range(games):
        ns = SimpleNamespace(
            engine_dir=engine_dir,
            agent_a=path_a,
            agent_b=path_b,
            deck_a=None,
            deck_b=None,
            games=1,
            max_steps=max_steps,
            trace_dir=trace_dir,
            trace_scores=trace_scores,
            trace_score_limit=trace_score_limit,
            summary=None,
            seed_base=seed_base,
        )
        try:
            result = run_game(ns, game_id)
        except Exception as exc:
            errors += 1
            print(f"ERROR {name_a} vs {name_b} game {local_game}: {exc}")
            game_rows.append(
                {
                    "agent_a": name_a,
                    "agent_b": name_b,
                    "local_game": local_game,
                    "game_id": game_id,
                    "seed": "" if seed_base is None else int(seed_base) + int(game_id),
                    "result": "",
                    "winner": "",
                    "error": type(exc).__name__,
                    "steps": "",
                    "turn": "",
                    "trace": "",
                    "p0_prizes": "",
                    "p1_prizes": "",
                    "p0_active": "",
                    "p1_active": "",
                }
            )
            game_id += 1
            continue

        total_steps += int(result.get("steps") or 0)
        winner = result.get("result")
        if winner == 0:
            wins_a += 1
        elif winner == 1:
            wins_b += 1
        else:
            draws_or_unknown += 1
        game_rows.append(
            {
                "agent_a": name_a,
                "agent_b": name_b,
                "local_game": local_game,
                "game_id": game_id,
                "seed": result.get("seed", ""),
                "result": winner,
                "winner": name_a if winner == 0 else name_b if winner == 1 else "",
                "error": "",
                "steps": result.get("steps", ""),
                "turn": result.get("turn", ""),
                "trace": result.get("trace", ""),
                "p0_prizes": result.get("p0_prizes", ""),
                "p1_prizes": result.get("p1_prizes", ""),
                "p0_active": result.get("p0_active", ""),
                "p1_active": result.get("p1_active", ""),
            }
        )
        game_id += 1

    played = wins_a + wins_b + draws_or_unknown
    return (
        {
            "agent_a": name_a,
            "agent_b": name_b,
            "games": played,
            "agent_a_wins": wins_a,
            "agent_b_wins": wins_b,
            "draws_or_unknown": draws_or_unknown,
            "errors": errors,
            "agent_a_win_rate": round(wins_a / played, 4) if played else "",
            "avg_steps": round(total_steps / played, 2) if played else "",
        },
        game_id,
        game_rows,
    )


def candidate_bucket_rates(rows: list[dict[str, object]], candidate: str) -> dict[str, tuple[int, int, int]]:
    rates: dict[str, tuple[int, int, int]] = {}
    for bucket in META_OPPONENTS:
        wins = 0
        games = 0
        errors = 0
        for row in rows:
            row_games = int(row["games"])
            row_errors = int(row["errors"])
            if row["agent_a"] == candidate and row["agent_b"] == bucket:
                wins += int(row["agent_a_wins"])
                games += row_games
                errors += row_errors
            elif row["agent_b"] == candidate and row["agent_a"] == bucket:
                wins += int(row["agent_b_wins"])
                games += row_games
                errors += row_errors
        if games:
            rates[bucket] = (wins, games, errors)
    return rates


def build_summary(rows: list[dict[str, object]], candidates: list[str]) -> list[dict[str, object]]:
    summary_rows: list[dict[str, object]] = []
    for candidate in candidates:
        rates = candidate_bucket_rates(rows, candidate)
        for bucket, (wins, games, errors) in rates.items():
            summary_rows.append(
                {
                    "candidate": candidate,
                    "scenario": f"bucket:{bucket}",
                    "wins": wins,
                    "games": games,
                    "win_rate": round(wins / games, 4) if games else "",
                    "errors": errors,
                }
            )
        for scenario, weights in SCENARIOS.items():
            numerator = 0.0
            denominator = 0.0
            games = 0
            errors = 0
            for bucket, weight in weights.items():
                if bucket not in rates:
                    continue
                wins, bucket_games, bucket_errors = rates[bucket]
                numerator += (wins / bucket_games) * weight
                denominator += weight
                games += bucket_games
                errors += bucket_errors
            summary_rows.append(
                {
                    "candidate": candidate,
                    "scenario": scenario,
                    "wins": "",
                    "games": games,
                    "win_rate": round(numerator / denominator, 4) if denominator else "",
                    "errors": errors,
                }
            )
    return summary_rows


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)

    candidates = [parse_agent(value) for value in args.candidate]
    candidate_names = [name for name, _ in candidates]
    duplicate_names = sorted({name for name in candidate_names if candidate_names.count(name) > 1})
    if duplicate_names:
        raise ValueError(f"Duplicate candidate name(s): {', '.join(duplicate_names)}")
    bucket_name_collisions = sorted(set(candidate_names) & set(META_OPPONENTS))
    if bucket_name_collisions:
        raise ValueError(
            "Candidate names must not match public-meta bucket names: "
            + ", ".join(bucket_name_collisions)
            + ". Use an alias such as cand_marnie=path."
        )
    opponents = {
        name: path
        for name, path in META_OPPONENTS.items()
        if not args.opponent or name in set(args.opponent)
    }
    for _, path in [*candidates, *opponents.items()]:
        check_agent_dir(path)

    rows: list[dict[str, object]] = []
    game_rows: list[dict[str, object]] = []
    game_id = 0
    for candidate_name, candidate_path in candidates:
        for bucket_index, (bucket_name, bucket_path) in enumerate(opponents.items()):
            first_game_id = bucket_index * args.games * 2 if args.fair_seeds else game_id
            row, next_game_id, matchup_game_rows = run_ordered_matchup(
                engine_dir=args.engine_dir,
                name_a=candidate_name,
                path_a=candidate_path,
                name_b=bucket_name,
                path_b=bucket_path,
                games=args.games,
                max_steps=args.max_steps,
                trace_root=args.trace_root,
                game_id_start=first_game_id,
                seed_base=args.seed_base,
                trace_scores=args.trace_scores,
                trace_score_limit=args.trace_score_limit,
            )
            rows.append(row)
            game_rows.extend(matchup_game_rows)
            if not args.fair_seeds:
                game_id = next_game_id

            second_game_id = bucket_index * args.games * 2 + args.games if args.fair_seeds else game_id
            row, next_game_id, matchup_game_rows = run_ordered_matchup(
                engine_dir=args.engine_dir,
                name_a=bucket_name,
                path_a=bucket_path,
                name_b=candidate_name,
                path_b=candidate_path,
                games=args.games,
                max_steps=args.max_steps,
                trace_root=args.trace_root,
                game_id_start=second_game_id,
                seed_base=args.seed_base,
                trace_scores=args.trace_scores,
                trace_score_limit=args.trace_score_limit,
            )
            rows.append(row)
            game_rows.extend(matchup_game_rows)
            if not args.fair_seeds:
                game_id = next_game_id

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "agent_a",
            "agent_b",
            "games",
            "agent_a_wins",
            "agent_b_wins",
            "draws_or_unknown",
            "errors",
            "agent_a_win_rate",
            "avg_steps",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary_rows = build_summary(rows, [name for name, _ in candidates])
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    with args.summary_out.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["candidate", "scenario", "wins", "games", "win_rate", "errors"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    if args.game_out:
        args.game_out.parent.mkdir(parents=True, exist_ok=True)
        with args.game_out.open("w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "agent_a",
                "agent_b",
                "local_game",
                "game_id",
                "seed",
                "result",
                "winner",
                "error",
                "steps",
                "turn",
                "trace",
                "p0_prizes",
                "p1_prizes",
                "p0_active",
                "p1_active",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(game_rows)

    print(f"Wrote {args.out}")
    print(f"Wrote {args.summary_out}")
    if args.game_out:
        print(f"Wrote {args.game_out}")


if __name__ == "__main__":
    main()
