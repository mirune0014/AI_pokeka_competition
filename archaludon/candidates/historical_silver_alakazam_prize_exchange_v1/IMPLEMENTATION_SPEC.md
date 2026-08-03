# Immutable implementation specification: Alakazam strict prize exchange v1

Frozen by the root at 2026-07-16T16:57:52+09:00 before the destination source
was edited. This authorizes one isolated deterministic rule candidate only. It
does not authorize a deck change or a Kaggle write.

## Parent and destination

- exact parent:
  `autonomous_gold_20260715/candidates/historical_silver_lucario_pokegear_duplicate_boss_continuity_v1`;
- parent `main.py` SHA256:
  `A69E2C5915355D402B314AA4BC66D933B68A5C0E2976A86905238A97EB6093AE`;
- parent `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`;
- isolated destination:
  `autonomous_gold_20260715/candidates/historical_silver_alakazam_prize_exchange_v1`.

The destination was mechanically copied from the parent. `deck.csv`,
`requirements.txt`, and bundled `cg/` must remain byte-identical. Only
destination `main.py`, this specification, and isolated tests may differ.

## Root-verified evidence

- The rejected broad Continuity2 candidate is not a parent: it lost 440 wins
  over 2,400 paired games. Its Marnie traces show that wide callback ownership,
  rather than the frozen A69 baseline, caused the dominant regression.
- Live replay `86199864`, target step 66: ready Archaludon ex can KO the
  one-prize Active Alakazam; Fezandipiti ex id 140, HP 210 is on the Bench and
  the same Metal Defender 220 exactly KOs it. A69 scores Boss `-500` only
  because the Active is already KOable.
- Live replay `86202608`, target step 61 contains the same strict public
  one-prize Active KO versus two-prize Fezandipiti ex KO. A69 again scores Boss
  `-500` for the same reason.
- The risky new-loss Ultra Ball line is deliberately excluded. At replay
  `86246054`, step 52, the root recomputed the public Powerful Hand envelope as
  `(floor, ceiling, boss ceiling) = (220, 420, 360)`. A 300 HP Archaludon ex
  does not survive every public branch, so the actual later 220 damage cannot
  be used as an opponent-policy proxy.
- Read-only Sol-Ultra strategy judgment: `IMPLEMENT` this Boss-only strict
  public prize certificate; do not extend it to Ultra Ball, general Boss
  timing, future hands, or opponent-policy assumptions.

Replays are board-state and prize-sequencing evidence only, never action labels.

## One exact rule hypothesis

Add a stateless `ALAKAZAM_STRICT_PRIZE_EXCHANGE` certificate. Do not change
deck construction, setup, search, evolution, attachment, healing, attack,
promotion, retreat, discard, or any non-Alakazam score.

At a MAIN option to play Boss's Orders, override the legacy Boss score only if
every predicate is true in the current public observation:

1. `detect_matchup(obs) == "alakazam"`.
2. A Supporter has not already been played.
3. `planned_archaludon_attacks(obs)` contains at least one currently payable
   attack route.
4. At least one of those same routes exactly or over-KOs the visible opponent
   Active after the existing public weakness calculation.
5. Taking the Active's public prize value does not already win the game.
6. At least one visible opponent Bench Pokemon is exactly or over-KOable by a
   route from the same frozen attack set.
7. The maximum public prize value among those KOable Bench Pokemon is strictly
   greater than the Active's public prize value.

If all predicates hold, score Boss exactly `32000 + 100 * best_bench_prizes`
with reason `Alakazam exchange: Boss higher-prize exact KO`. This is above
ordinary items and the direct attack, but below existing setup invariants.

At Boss's opponent `SWITCH/TO_ACTIVE` target selection, independently
recompute the same certificate from that current public observation. Score only
KOable Bench targets whose prize value equals the certified maximum exactly
`40000 + parent_KO_target_score`; use reason
`Alakazam exchange: choose max-prize exact KO`. Other targets retain their
exact parent score and tie order. This preserves the parent target ordering
between equal-prize exact KOs before the stable option-index tie-break.

The subsequent Attack is not overridden. The unchanged parent policy must
still find and choose its legal attack after the switch.

## Safety and fail-closed invariants

- No card ID, player name, episode ID, step, seed, serial, hand ordering, or
  opponent action is used as a trigger. Fezandipiti is evidence, not a
  hard-coded target.
- Do not estimate hidden future draws or future opponent actions.
- Strictly greater immediate prize value is mandatory; equal-prize gusts fall
  back to A69.
- Direct match-winning Active KO is never displaced.
- A real legal Attack option is required at MAIN. Asleep, Paralyzed, Confused,
  unknown status, damage ranges, unsupported prevention, unsupported Stadium,
  Tool, or attachment effects fail closed.
- If the attack set, target legality, KO arithmetic, matchup, or prize value is
  absent or ambiguous at either stage, use exact A69 behavior.
- The certificate owns no callback and stores no pending state. Every step is
  revalidated from the current observation.
- If Boss resolves but the attack later becomes unavailable, do not invent a
  fallback transaction; unchanged A69 chooses from the actual legal options.

## Required local gates before exploratory submission

1. Source compiles/imports; agent and 60-card deck requests are valid and
   deterministic.
2. Synthetic positive controls for one-prize Active versus two-prize exact-KO
   Bench target pass at both Boss-play and target-selection stages.
3. Negative controls preserve exact parent scores for non-Alakazam, no ready
   attack, non-KOable Bench, equal/lower prize Bench, and match-winning Active.
4. Re-score the exact public decision observations from `86199864` step 66 and
   `86202608` step 61: candidate selects Boss while parent selects direct
   attack, with no exception or invalid action.
5. Public replay double-pass action validity and deterministic row hashes pass.
6. Run both seats on identical broad and fresh fixed seeds against the complete
   anti-overfitting population. Require no action errors, max-step hits, or
   schedule mismatches; nonnegative broad, fresh, and combined deltas; no
   opponent/seat floor breach; and positive or at least nonnegative Alakazam.
7. Inspect every changed position. At least one changed parent loss must follow
   the certified higher-prize line without unexplained regressions.

Only after these gates and a fresh Kaggle quota/episode check may the root use
one exploratory slot.
