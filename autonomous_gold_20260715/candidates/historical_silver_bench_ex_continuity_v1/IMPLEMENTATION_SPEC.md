# Implementation specification: certified Bench Archaludon ex continuity v1

This directory is an isolated copy of
`historical_silver_alakazam_prize_exchange_v1`.  The frozen parent hashes are:

- `main.py`: `01469A3B9241F8ADA535AED11E264F8821886321ACC2E3162A6354DED8E57C1F`
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

The deck, bundled engine, Alakazam prize-exchange rule, and Lucario Pokegear
rule remain unchanged.  No Kaggle write is authorized by this implementation.

## One rule hypothesis

The parent incorrectly leaves a legal Bench Duraludon-to-Archaludon ex
evolution at `-1000` (`hold: evolve Active first`) after the Active is already
the only in-play Archaludon ex.  The candidate scores exactly one certified
backup evolution at `19000`, after ordinary `20000` item plays and before
supporters, attacks, or ending the turn.

The stateless certificate requires every condition below:

1. MAIN offers a legal Archaludon ex evolution of a Bench Duraludon.
2. Active is Archaludon ex and is the only in-play Archaludon ex.
3. The target has maximum attached Energy among such legal Bench evolutions.
   Maximum Energy, Bench order, target serial, hand-card serial, and option
   order produce one deterministic winner even when duplicate hand cards
   expose equivalent options.
4. The target is the only Bench member of the Archaludon line, or it has at
   least two attached Energy.
5. The opponent has at least three remaining Prize cards.
6. The opponent Active's printed Prize value is strictly below our remaining
   Prize count, certifying that current Metal Defender cannot be an immediate
   prize win.  Less certain cases retain the parent score.
7. Cornerstone Mask Ogerpon ex is absent from all visible opponent cards,
   `detect_matchup(obs)` is not `crustle`, and
   `final_prize_nonex_no_backup(obs)` is false.

Absent public fields, malformed options, and all exceptions fail closed to the
parent score.  The rule has no memory and does not inspect hidden cards,
episode IDs, steps, opponents, or future actions.

## Explicit exclusions

This candidate does not add Night Stretcher, Cinderace, survival-resource,
final-prize, attack, gust, attachment, or deck rules.  In particular,
Cinderace is not treated as a legal midgame Bench Basic.

## Point controls

- Episode `86278699`: retain Jumbo Ice Cream at step 59 (`20000`), then choose
  the certified Bench evolution at step 60 (`19000`).
- Episode `86279220`: retain the Active evolution at step 40, then choose the
  certified Bench evolution before Lillie at step 44 (`19000` versus `5000`).
- `test_bench_ex_continuity.py` covers the live positive, duplicate-option
  uniqueness, maximum-Energy target selection, and fail-closed negatives for
  every safety family.
