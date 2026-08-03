"""Summarize public Daily Top Episode deck composition without replay inflation.

The input deck classification must come from tools/extract_episode_decks.py.
This script does not fetch data and does not infer hidden decks.  It produces
three views:

1. episode-seat appearances in the top-K episodes by average participant score;
2. one modal exact deck list per covered current-Leaderboard team;
3. unique (team, exact deck list) and globally unique exact-list views.

Daily Top Episodes are a biased public sample, so shares are descriptive of
the supplied snapshot only.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


COARSE_CATEGORY = {
    "alakazam_psychic": "ALAKAZAM",
    "kangaskhan_crustle": "CRUSTLE",
    "great_tusk_crustle": "CRUSTLE",
    "teal_ogerpon_clefairy_crustle": "CRUSTLE",
    "crustle_munkidori_control": "CRUSTLE",
    "crustle_control": "CRUSTLE",
    "rocket_mewtwo_spidops": "ROCKET_MEWTWO_SPIDOPS",
    "starmie_froslass": "BENCH_EFFECT",
    "dragapult": "BENCH_EFFECT",
    "chandelure_psychic_control": "CONTROL_OR_STALL",
    "cubchoo_articuno_control": "CONTROL_OR_STALL",
    "hop_trevenant": "SINGLE_PRIZE_OTHER",
    "okidogi_barbaracle": "SINGLE_PRIZE_OTHER",
    "mega_abomasnow_kyogre": "EX_AGGRO",
    "mega_lucario": "EX_AGGRO",
    "cynthia_garchomp": "EX_AGGRO",
    "charizard": "EX_AGGRO",
    "marnie_grimmsnarl": "EX_MIDRANGE",
    "archaludon_metal": "EX_MIDRANGE",
    "iono_bellibolt": "EX_MIDRANGE",
    "ogerpon_toolbox": "EX_MIDRANGE",
    "gardevoir": "EX_MIDRANGE",
    "festival_lead_dipplin": "SINGLE_PRIZE_OTHER",
    "unknown": "UNKNOWN",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def canonical_deck(deck_text: str) -> tuple[str, int, set[int]]:
    card_ids = [int(value) for value in deck_text.split()]
    counts = Counter(card_ids)
    signature = ";".join(f"{card_id}:{counts[card_id]}" for card_id in sorted(counts))
    return signature, len(card_ids), set(card_ids)


def refine_archetype(archetype: str, card_ids: set[int]) -> tuple[str, str]:
    if archetype == "unknown" and {90, 93, 1245}.issubset(card_ids):
        return "festival_lead_dipplin", "root_full_deck_rule_ids_90_93_1245"
    return archetype, "extract_episode_decks_full_60_card_ids_marker_rule"


def build_leaderboard_identity(
    rows: list[dict[str, str]],
) -> tuple[dict[str, tuple[int, str]], dict[str, list[int]]]:
    team_names: dict[str, set[int]] = defaultdict(set)
    member_names: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        rank = int(row["Rank"])
        team_names[row["TeamName"]].add(rank)
        for member in row.get("TeamMemberUserNames", "").split(","):
            if member.strip():
                member_names[member.strip()].add(rank)

    identity: dict[str, tuple[int, str]] = {}
    ambiguous: dict[str, list[int]] = {}
    for alias in sorted(set(team_names) | set(member_names)):
        ranks = team_names[alias] | member_names[alias]
        if len(ranks) != 1:
            ambiguous[alias] = sorted(ranks)
            continue
        rank = next(iter(ranks))
        sources = []
        if rank in team_names[alias]:
            sources.append("team_name")
        if rank in member_names[alias]:
            sources.append("member_username")
        identity[alias] = (rank, "+".join(sources))
    return identity, ambiguous


def broad_category(archetype: str) -> str:
    if archetype in COARSE_CATEGORY:
        return COARSE_CATEGORY[archetype]
    if "crustle" in archetype:
        return "CRUSTLE"
    return "UNKNOWN"


def aggregate(
    rows: list[dict[str, str]],
    *,
    population: str,
    unit: str,
) -> list[dict[str, object]]:
    denominator = len(rows)
    detailed = Counter(row["archetype"] for row in rows)
    broad = Counter(row["broad_category"] for row in rows)
    output: list[dict[str, object]] = []
    for level, counts in (("detailed", detailed), ("coarse", broad)):
        for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
            output.append(
                {
                    "population": population,
                    "unit": unit,
                    "classification_level": level,
                    "archetype": label,
                    "count": count,
                    "denominator": denominator,
                    "share": f"{count / denominator:.8f}" if denominator else "",
                }
            )
    return output


def choose_modal_rows(
    rows: list[dict[str, str]],
    leaderboard_cutoff: int,
) -> tuple[list[dict[str, str]], int, int]:
    eligible = [
        row
        for row in rows
        if row["leaderboard_rank"] and int(row["leaderboard_rank"]) <= leaderboard_cutoff
    ]
    by_team: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        by_team[row["leaderboard_rank"]].append(row)

    selected: list[dict[str, str]] = []
    for team, team_rows in sorted(by_team.items()):
        signature_counts = Counter(row["deck_signature"] for row in team_rows)
        modal_signature = sorted(
            signature_counts,
            key=lambda signature: (-signature_counts[signature], signature),
        )[0]
        candidates = [
            row for row in team_rows if row["deck_signature"] == modal_signature
        ]
        selected.append(
            sorted(
                candidates,
                key=lambda row: (int(row["daily_episode_rank"]), int(row["player_index"])),
            )[0]
        )
    unique_team_decks = len(
        {(row["leaderboard_rank"], row["deck_signature"]) for row in eligible}
    )
    unique_exact_decks = len({row["deck_signature"] for row in eligible})
    return selected, unique_team_decks, unique_exact_decks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decks-csv", type=Path, required=True)
    parser.add_argument("--leaderboard-csv", type=Path, required=True)
    parser.add_argument("--daily-manifest-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--episode-cutoffs", default="20,50,100")
    parser.add_argument("--leaderboard-cutoffs", default="20,50,100")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    episode_cutoffs = [int(value) for value in args.episode_cutoffs.split(",")]
    leaderboard_cutoffs = [int(value) for value in args.leaderboard_cutoffs.split(",")]
    if any(value <= 0 for value in episode_cutoffs + leaderboard_cutoffs):
        raise ValueError("cutoffs must be positive")

    decks = read_rows(args.decks_csv)
    leaderboard = read_rows(args.leaderboard_csv)
    daily_manifest = read_rows(args.daily_manifest_csv)

    ranked_manifest = sorted(
        daily_manifest,
        key=lambda row: (float(row["avg_score"]), int(row["episode_id"])),
        reverse=True,
    )
    daily_rank = {
        row["episode_id"]: index
        for index, row in enumerate(ranked_manifest, start=1)
    }
    daily_score = {
        row["episode_id"]: row["avg_score"]
        for row in ranked_manifest
    }
    leaderboard_identity, ambiguous_leaderboard_aliases = build_leaderboard_identity(
        leaderboard
    )

    enriched: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    for source in decks:
        episode_id = source["episode_id"]
        key = (episode_id, source["player_index"])
        if key in seen_keys:
            raise ValueError(f"duplicate episode-seat key: {key}")
        seen_keys.add(key)
        signature, card_count, card_ids = canonical_deck(source["deck"])
        if card_count != 60:
            raise ValueError(f"deck is not 60 cards: {key} has {card_count}")
        if episode_id not in daily_rank:
            raise ValueError(f"episode missing from daily manifest: {episode_id}")
        archetype, classification_basis = refine_archetype(
            source["archetype"], card_ids
        )
        leaderboard_match = leaderboard_identity.get(source["team"])
        enriched.append(
            {
                **source,
                "extractor_archetype": source["archetype"],
                "archetype": archetype,
                "daily_episode_rank": str(daily_rank[episode_id]),
                "daily_avg_score": daily_score[episode_id],
                "leaderboard_rank": str(leaderboard_match[0]) if leaderboard_match else "",
                "leaderboard_match": leaderboard_match[1] if leaderboard_match else "",
                "deck_signature": signature,
                "broad_category": broad_category(archetype),
                "classification_basis": classification_basis,
            }
        )

    max_episode_cutoff = max(episode_cutoffs)
    expected_ids = {
        row["episode_id"] for row in ranked_manifest[:max_episode_cutoff]
    }
    observed_ids = {
        row["episode_id"]
        for row in enriched
        if int(row["daily_episode_rank"]) <= max_episode_cutoff
    }
    if observed_ids != expected_ids:
        missing = sorted(expected_ids - observed_ids)
        extra = sorted(observed_ids - expected_ids)
        raise ValueError(
            f"top-{max_episode_cutoff} schedule mismatch: "
            f"missing={missing[:10]} extra={extra[:10]}"
        )
    for episode_id in expected_ids:
        count = sum(row["episode_id"] == episode_id for row in enriched)
        if count != 2:
            raise ValueError(f"episode {episode_id} has {count} deck rows, expected 2")

    aggregate_rows: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []

    for cutoff in episode_cutoffs:
        population_rows = [
            row for row in enriched if int(row["daily_episode_rank"]) <= cutoff
        ]
        aggregate_rows.extend(
            aggregate(
                population_rows,
                population=f"daily_top_{cutoff}_episodes",
                unit="episode_seat_appearance",
            )
        )
        team_deck_rows: dict[tuple[str, str], dict[str, str]] = {}
        exact_deck_rows: dict[str, dict[str, str]] = {}
        for row in population_rows:
            team_deck_rows.setdefault((row["team"], row["deck_signature"]), row)
            exact_deck_rows.setdefault(row["deck_signature"], row)
        aggregate_rows.extend(
            aggregate(
                list(team_deck_rows.values()),
                population=f"daily_top_{cutoff}_episodes",
                unit="unique_team_exact_deck",
            )
        )
        aggregate_rows.extend(
            aggregate(
                list(exact_deck_rows.values()),
                population=f"daily_top_{cutoff}_episodes",
                unit="unique_exact_deck",
            )
        )

    sample_rows = [
        row for row in enriched if int(row["daily_episode_rank"]) <= max_episode_cutoff
    ]
    for cutoff in leaderboard_cutoffs:
        modal_rows, unique_team_decks, unique_exact_decks = choose_modal_rows(
            sample_rows, cutoff
        )
        aggregate_rows.extend(
            aggregate(
                modal_rows,
                population=f"current_leaderboard_top_{cutoff}_covered_by_daily_top_{max_episode_cutoff}",
                unit="covered_team_modal_exact_deck",
            )
        )
        coverage_rows.append(
            {
                "population": f"current_leaderboard_top_{cutoff}",
                "target_teams": cutoff,
                "covered_teams": len(modal_rows),
                "coverage_share": f"{len(modal_rows) / cutoff:.8f}",
                "unique_team_exact_decks": unique_team_decks,
                "unique_exact_decks": unique_exact_decks,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    enriched_fields = list(enriched[0]) if enriched else []
    write_rows(args.out_dir / "enriched_decks.csv", enriched_fields, enriched)
    write_rows(
        args.out_dir / "deck_archetype_counts.csv",
        [
            "population",
            "unit",
            "classification_level",
            "archetype",
            "count",
            "denominator",
            "share",
        ],
        aggregate_rows,
    )
    write_rows(
        args.out_dir / "coverage.csv",
        [
            "population",
            "target_teams",
            "covered_teams",
            "coverage_share",
            "unique_team_exact_decks",
            "unique_exact_decks",
        ],
        coverage_rows,
    )
    summary = {
        "daily_manifest_rows": len(daily_manifest),
        "leaderboard_rows": len(leaderboard),
        "extracted_deck_rows": len(enriched),
        "unique_episode_seat_keys": len(seen_keys),
        "top_episode_schedule_verified": max_episode_cutoff,
        "unknown_rows_in_top_schedule": sum(
            row["archetype"] == "unknown" for row in sample_rows
        ),
        "ambiguous_leaderboard_aliases": len(ambiguous_leaderboard_aliases),
        "sample_rows_with_ambiguous_or_unmatched_alias": sum(
            not row["leaderboard_rank"] for row in sample_rows
        ),
        "notes": [
            "Shares describe the supplied public Daily Top snapshot, not all competitors.",
            "Team matching uses unambiguous exact TeamName or member username aliases.",
            "Coarse categories are an explicit heuristic map; detailed marker classes are primary.",
        ],
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
