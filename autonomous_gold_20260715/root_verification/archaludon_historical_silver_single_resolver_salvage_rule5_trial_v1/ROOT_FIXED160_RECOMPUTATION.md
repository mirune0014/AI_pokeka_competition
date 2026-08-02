# Rule 5 fixed160 root recomputation

Date: 2026-08-03 JST

## Immutable inputs

- Specification: `evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1/fixed160_spec.json`
- Specification SHA-256: `B9D6BEAC707B51C79D9EA42E5C00FCE0E4C85D8FA0F4A119EC39ACA032BAF258`
- Baseline: accepted Rule 4 parent
- Baseline `main.py` SHA-256: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- Candidate: Rule 5 trial
- Candidate `main.py` SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Shared deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Raw tree digest supplied by the deterministic runner: `4A89277BA250B25CA849B3868BEF80A268D36881A20E0CA9CD3698396E056B82`

## Root recomputation

The two checked `paired_results.csv` files contain exactly 160 unique
`(opponent, seat, seed)` keys: 40 Historical-Silver mirror games and 120
adjacent-population games.  The schedules are identical between baseline and
candidate.

| Cell | Games | Baseline wins | Candidate wins | Delta |
| --- | ---: | ---: | ---: | ---: |
| Historical-Silver, seat 0 | 20 | 11 | 11 | 0 |
| Historical-Silver, seat 1 | 20 | 9 | 9 | 0 |
| Alakazam, seat 0 | 20 | 16 | 16 | 0 |
| Alakazam, seat 1 | 20 | 13 | 13 | 0 |
| Arch Peak, seat 0 | 20 | 6 | 6 | 0 |
| Arch Peak, seat 1 | 20 | 14 | 14 | 0 |
| Marnie, seat 0 | 20 | 14 | 14 | 0 |
| Marnie, seat 1 | 20 | 17 | 17 | 0 |
| **Total** | **160** | **100** | **100** | **0** |

- Paired gains: 0
- Paired regressions: 0
- Paired ties: 160
- Action errors: 0
- Exceptions/start faults: 0
- Max-step hits: 0
- Duplicate mismatches: 0
- Outcome-discordant keys requiring first-difference classification: 0

The fixed160 panel therefore satisfies the numerical retention gates.  It is
neutral rather than evidence of a win-rate gain.

## Natural activation evidence outside fixed160

The callback-complete replay shadow inspected 4,262 callbacks from 77 readable
replays and produced two Rule 5 differences.  Both were
`DIRECT_EXACT_CURRENT_WIN`; both replaced nonterminal setup actions with an
exact, immediately terminal Metal Defender attack:

1. episode 89273754, seat 1, step 73: exact two-Prize terminal attack;
2. episode 89280169, seat 1, step 161: exact one-Prize terminal attack.

No invalid action or exception occurred.  No natural Boss transaction occurred
in this corpus.  The direct-win branch is therefore naturally exercised and
its two observed first differences are beneficial.  The Boss subroute remains
covered only by focused fixtures and must not be credited with a natural gain.

## Root conclusion before independent judgment

Rule 5 passes the stated stage gate as a safe-neutral rule: it preserves all
160 paired outcomes and corrects two naturally observed missed terminal wins.
Final adoption remains subject to the independent numerical audit and the
Sol-Ultra rule-level judgment.
