from __future__ import annotations

import argparse
import csv
from pathlib import Path


SCENARIO_BUCKETS: dict[str, set[str]] = {
    "public_sample_2026_07_02": {
        "marnie",
        "alakazam",
        "archaludon",
        "ogerpon",
        "lucario",
        "hop",
        "chandelure",
        "starmie",
    },
    "public_sample_2026_07_02_top20": {
        "marnie",
        "alakazam",
        "archaludon",
        "ogerpon",
        "lucario",
        "hop",
        "chandelure",
        "starmie",
    },
    "public_sample_2026_07_03_top20": {
        "marnie",
        "ogerpon",
        "lucario",
        "alakazam",
        "archaludon",
        "starmie",
        "great_tusk",
        "rocket_mewtwo_spidops",
        "hop",
        "chandelure",
    },
    "public_sample_2026_07_08_top20": {
        "alakazam_majkel1337_2026_07_08",
        "alakazam_third_ptcg_2026_07_08",
        "alakazam_55_2026_07_08",
        "great_tusk_liamk_2026_07_08",
        "great_tusk_bono_junlee_2026_07_08",
        "marnie_yushin_2026_07_08",
        "marnie_gonsaku_2026_07_08",
        "chandelure_koga_2026_07_08",
        "chandelure_starmine_2026_07_08",
        "okidogi_majkel1337_2026_07_08",
        "dragapult_bigbug_2026_07_08",
        "ogerpon_btk15049_2026_07_08",
        "ogerpon_zoroark190_2026_07_08",
        "starmie_windecks_2026_07_08",
        "starmie_yushin_2026_07_08",
        "archaludon_shumpei_2026_07_08",
    },
    "live_alakazam_ketchum_alt_2026_07_04": {"alakazam_ketchum_alt"},
    "discussion_starmie_heavy_2026_06_28": {"starmie", "archaludon", "alakazam"},
    "discussion_ogerpon_toolbox_2026_07_04": {
        "ogerpon_raging_bolt",
        "ogerpon_cornerstone",
        "ogerpon",
        "archaludon",
        "starmie",
        "alakazam",
    },
    "discussion_ogerpon_public_variants_2026_07_09": {
        "ogerpon_raging_bolt",
        "ogerpon_cornerstone",
        "ogerpon_clefairy",
        "ogerpon_hydrapple",
        "ogerpon_meganium",
        "ogerpon_meganium_arboliva",
        "ogerpon_meganium_hydrapple",
        "ogerpon_multi_mask",
        "ogerpon_sinistcha",
    },
    "live_chandelure_control_2026_07_04": {"chandelure", "chandelure_dick"},
    "live_dragapult_2026_07_09": {"dragapult"},
    "live_lucario_2026_07_09": {"lucario_live"},
    "live_aib4_lucario_2026_07_09": {"lucario_aib4_live"},
    "live_fujiborozoukin_lucario_2026_07_09": {"lucario_fujiborozoukin_live"},
    "live_hamu_lucario_2026_07_10": {"lucario_hamu_live"},
    "live_genki_lucario_2026_07_10": {"lucario_genki_live"},
    "public_akira_lucario_2026_07_08": {"lucario_akira_2026_07_08"},
    "live_noor_alakazam_2026_07_09": {"alakazam_noor_live"},
    "live_rojiomote_dragapult_2026_07_10": {"dragapult_rojiomote_live"},
    "live_capbloo2_alakazam_2026_07_10": {"alakazam_capbloo2_live"},
    "live_ketchum_alt_alakazam_2026_07_10": {"alakazam_ketchum_alt_live"},
    "live_rmy_alakazam_2026_07_10": {"alakazam_rmy_live"},
    "live_kei_marnie_2026_07_09": {"marnie_kei_live"},
    "live_gonsaku_marnie_2026_07_09": {"marnie_gonsaku_live"},
    "live_mykhailo_marnie_2026_07_10": {"marnie_mykhailo_live"},
    "live_kazuki_marnie_2026_07_10": {"marnie_kazuki_live"},
    "live_alghital_iono_2026_07_10": {"iono_bellibolt_alghital_live"},
    "live_jason_cynthia_2026_07_10": {"cynthia_garchomp_jason_live"},
    "public_dung_kangaskhan_crustle_2026_07_08": {"kangaskhan_crustle_dung_2026_07_08"},
    "equal_public_buckets": {
        "marnie",
        "marnie_kei_live",
        "marnie_gonsaku_live",
        "marnie_mykhailo_live",
        "marnie_kazuki_live",
        "marnie_yushin_2026_07_08",
        "marnie_gonsaku_2026_07_08",
        "alakazam",
        "alakazam_noor_live",
        "alakazam_tubotu_live",
        "alakazam_ketchum_alt",
        "alakazam_ketchum_alt_live",
        "alakazam_rmy_live",
        "alakazam_majkel1337_2026_07_08",
        "alakazam_third_ptcg_2026_07_08",
        "alakazam_55_2026_07_08",
        "archaludon",
        "archaludon_shumpei_2026_07_08",
        "great_tusk",
        "great_tusk_liamk_2026_07_08",
        "great_tusk_bono_junlee_2026_07_08",
        "kangaskhan_crustle_dung_2026_07_08",
        "rocket_mewtwo_spidops",
        "ogerpon",
        "ogerpon_btk15049_2026_07_08",
        "ogerpon_zoroark190_2026_07_08",
        "okidogi_majkel1337_2026_07_08",
        "lucario",
        "lucario_live",
        "lucario_aib4_live",
        "lucario_hamu_live",
        "lucario_genki_live",
        "lucario_akira_2026_07_08",
        "dragapult",
        "dragapult_rojiomote_live",
        "dragapult_bigbug_2026_07_08",
        "hop",
        "starmie",
        "starmie_windecks_2026_07_08",
        "starmie_yushin_2026_07_08",
        "chandelure",
        "chandelure_dick",
        "chandelure_koga_2026_07_08",
        "chandelure_starmine_2026_07_08",
        "iono_bellibolt",
        "iono_bellibolt_alghital_live",
        "cynthia_garchomp_jason_live",
        "ogerpon_raging_bolt",
        "ogerpon_cornerstone",
        "ogerpon_clefairy",
        "ogerpon_hydrapple",
        "ogerpon_meganium",
        "ogerpon_meganium_arboliva",
        "ogerpon_meganium_hydrapple",
        "ogerpon_multi_mask",
        "ogerpon_sinistcha",
    },
}


def parse_float(value: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def iter_summary_rows(root: Path):
    for path in sorted(root.rglob("*summary.csv")):
        if not path.is_file():
            continue
        try:
            with path.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or not {"candidate", "scenario", "win_rate"} <= set(reader.fieldnames):
                    continue
                for row in reader:
                    rate = parse_float(row.get("win_rate", ""))
                    if rate is None:
                        continue
                    yield {
                        "source": str(path),
                        "candidate": row.get("candidate", ""),
                        "scenario": row.get("scenario", ""),
                        "wins": row.get("wins", ""),
                        "games": parse_int(row.get("games", "")),
                        "win_rate": rate,
                        "errors": parse_int(row.get("errors", "")),
                    }
        except UnicodeDecodeError:
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate local meta-suite summary CSVs.")
    parser.add_argument("--root", type=Path, default=Path("analysis_outputs"))
    parser.add_argument("--scenario", action="append", help="Scenario substring filter. Repeatable.")
    parser.add_argument("--candidate", action="append", help="Candidate substring filter. Repeatable.")
    parser.add_argument("--source", action="append", help="Source path substring filter. Repeatable.")
    parser.add_argument("--min-games", type=int, default=40)
    parser.add_argument(
        "--min-buckets",
        type=int,
        default=0,
        help="Minimum distinct bucket rows present for the same candidate/source.",
    )
    parser.add_argument(
        "--require-full-scenario",
        action="store_true",
        help="Keep only scenario rows whose source covers every bucket in that scenario.",
    )
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    all_rows = list(iter_summary_rows(args.root))
    bucket_map: dict[tuple[str, str], set[str]] = {}
    for row in all_rows:
        scenario = row["scenario"]
        if not scenario.startswith("bucket:"):
            continue
        key = (row["source"], row["candidate"])
        bucket_map.setdefault(key, set()).add(scenario.split(":", 1)[1])

    rows = []
    for row in all_rows:
        if row["games"] < args.min_games:
            continue
        if args.scenario and not any(s in row["scenario"] for s in args.scenario):
            continue
        if args.candidate and not any(c in row["candidate"] for c in args.candidate):
            continue
        if args.source and not any(s in row["source"] for s in args.source):
            continue
        source_buckets = bucket_map.get((row["source"], row["candidate"]), set())
        expected_buckets = SCENARIO_BUCKETS.get(row["scenario"])
        if row["scenario"].startswith("bucket:"):
            expected_buckets = {row["scenario"].split(":", 1)[1]}
        covered = len(source_buckets & expected_buckets) if expected_buckets else len(source_buckets)
        expected = len(expected_buckets) if expected_buckets else ""
        coverage = round(covered / expected, 4) if expected_buckets else ""
        if args.min_buckets and len(source_buckets) < args.min_buckets:
            continue
        if args.require_full_scenario and expected_buckets and covered < len(expected_buckets):
            continue
        row = {
            **row,
            "bucket_count": len(source_buckets),
            "scenario_buckets": expected,
            "scenario_coverage": coverage,
        }
        rows.append(row)

    rows.sort(key=lambda r: (r["win_rate"], r["games"]), reverse=True)
    rows = rows[: args.top]

    fieldnames = [
        "win_rate",
        "games",
        "wins",
        "errors",
        "bucket_count",
        "scenario_buckets",
        "scenario_coverage",
        "candidate",
        "scenario",
        "source",
    ]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    writer = csv.DictWriter(__import__("sys").stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
