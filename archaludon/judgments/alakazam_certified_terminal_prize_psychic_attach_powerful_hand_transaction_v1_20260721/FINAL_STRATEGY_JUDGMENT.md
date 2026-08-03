# Final strategy judgment: certified terminal Prize transaction v1

Recorded: 2026-07-21 JST  
Scope: one exploratory live probe only; this is not formal adoption

## Verdict

**REJECT_AND_DO_NOT_SUBMIT** candidate source
`1D01BC4796D39E4CEF82CC3A309947347A0968F20612E3CB43A926DAF708FEC0`
and clean archive
`704129B27280467668728DB33B4BA6EA802CBBED217401652D8B34F711CE421C`.

The exact recorded S124 mechanism is valid, but the implemented eligibility
certificate is wider than the proved mechanism and omits a public damage
modifier. A live refresh, remaining quota, or urgency cannot waive this source
safety failure. The exact live parent remains `23B89E...CBE9`; formal rollback
remains `4A95DCE0...AE16`.

## Verified facts used

- Candidate, frozen strategy, root evidence, and implementation receipt match
  the supplied SHA-256 values: `1D01BC47...FEC0`, `C58675DD...2BD2`,
  `862D917C...AFAFA`, and `73609870...F05C` respectively. Candidate deck and
  runtime are byte-identical to the live parent; only `main.py` adds 919 lines.
- The raw current-42 shadow
  `18291C9629C273FE4D739F843E0B851D1CED5475BC54F31F41D777EF5E7BBE96`
  has 2,593 callbacks, exactly one classified difference at
  `87139766/S124`, zero invalid actions, and zero duplicate mismatches.
- The raw formal shadow
  `97DD6A8CBC32A6CBB550B8DA3191E72C23F748D67F9838D68B5A6337BB26769C`
  has the four inherited live/formal differences plus S124, all classified,
  with zero invalid actions and zero duplicate mismatches.
- The raw historical shadow
  `06D5EBEFD931B656E1045FAF1E357F706CA6A90298516988AB2BF3D150B7B57B`
  covers 136 manifest rows, 186 seat-runs, and 11,866 callbacks with zero
  differences, invalid actions, or duplicate mismatches.
- Both source and clean-package checked-engine artifacts pass in both semantic
  seats: Basic Psychic, Powerful Hand, two Prize cards, zero own Prizes,
  correct winner, duplicate-identical callbacks, and cleared latch. Thus the
  observed anchor mechanism matches the intended rule.
- The root package report, SHA-256
  `C776500E5A6DE6B10FC045C8BA68CB46557A648FAEA94E4305DDD96C3389A7BF`,
  verifies compile/import, legal deterministic deck, one loader entrypoint,
  clean re-extraction, 9/9 focused tests, and duplicate Historical-Silver
  wins in both seats with zero action errors and no max-step hit.

These are meaningful major-break and packaging positives, but they do not
override a false-positive lethal certificate.

## Blocking source counterexample

The candidate's `_terminal_two_prize_target_is_clear` checks the opponent's
Active card, its own skills, Tool, Prize value, Resistance, and attached Basic
Energy. `_terminal_full_metal_lab_reduction` then accounts only for absent
Stadium or exact Full Metal Lab. The start path fingerprints the opponent
Bench for continuation equality but never checks Bench skills that modify
damage to the Active.

Runtime card metadata confirms Klinklang `623` has **Gear Coating**: all of its
controller's Pokemon with Metal Energy attached take 20 less attack damage.
That public Bench effect applies to the certified Metal-energized target.

A direct anchor-derived mutation demonstrates the false start:

- retain the exact 300-HP, two-Prize Active Archaludon ex with three Basic
  Metal Energy and Full Metal Lab;
- reduce the fully visible starting hand from 21 to 18 by removing three
  unrelated cards, retaining the unique Basic Psychic and Enriching Energy;
- place a serial-complete Klink `621` -> Klang `622` -> Klinklang `623` on the
  opponent Bench.

The live parent still selects semantic Enriching-to-Bench. The candidate
instead selects semantic Basic-Psychic-to-Active, opens its latch, and stores
`damage_floor = 310`: `20 * 17 - 30`. Gear Coating supplies the omitted second
reduction, so the public conservative result is `340 - 30 - 20 = 290`, below
the target's 300 HP. The candidate can therefore spend the Basic Psychic and
force a nonlethal attack while believing the game is certified terminal.

This directly violates frozen contract clause 7 (every unresolved public
damage modifier must veto the start) and implementation/mechanism gate 1. The
focused mutation matrix contains Stadium, Tool, special-Energy, and below-floor
cases, but no opponent-field damage-modifier case. Historical zero-diff is no
coverage of this branch; the one activation had no Klinklang.

## Integrated judgment

At the exact anchor, setup, board formation, attacker readiness, Energy/hand
spend, attack continuity, final two-Prize exchange, and finishing are all
proved. In the counterexample, however, the same Energy spend is no longer
terminal: it abandons the parent's four-card Enriching draw, consumes the turn's
attachment, exposes the Active, and leaves future attack and Prize continuity
uncertified. That is a material resource, continuity, and finishing regression,
not a cosmetic conservatism issue. Both-seat anchor success and adjacent
historical equality cannot establish safety in an uncovered activation bucket.

## Hard live stops

1. Do not submit, upload, or repackage source hash `1D01BC47...FEC0` or archive
   hash `704129B2...421C` for a live probe.
2. Do not override this rejection because S124 flips to a win, smoke wins both
   seats, the live score is weak, reset is near, or a slot remains.
3. Any archive containing the same candidate source hash remains rejected.
4. A probe may be reconsidered only for a new frozen source and archive hash,
   followed by a fresh independent judgment. This report grants no permission
   to a later patch and no formal adoption.

## Exact evidence needed next

1. A minimal fail-closed hardening diff that either accounts for every exact
   public field modifier or rejects any opponent Bench/Active/Stadium effect
   not explicitly proved irrelevant. It must not broaden H0/H1, Helmet,
   Teleportation, scoring, or deck behavior.
2. Focused both-seat, option-permuted, serial-distinct mutations for Klinklang
   Gear Coating with a Metal-energized target. The near-margin `310 -> 290`
   case must return byte-identical live-parent behavior, create no latch, and
   remain duplicate-idempotent. The original S124 anchor must still complete
   the full terminal transaction in both seats.
3. Fresh source/deck/runtime hashes, static diff, focused results, checked-engine
   artifact, complete current-42/formal/historical shadows, and root-recomputed
   counts. Require zero invalid actions, duplicate mismatches, unclassified
   differences, mechanism-first losses, and max-step hits.
4. A newly built and re-extracted clean archive with matching source, legal
   deck, loader/import checks, both-seat duplicate Historical-Silver smoke, and
   exact archive hash.
5. Only after those gates and a new Sol-Ultra accept/reject ruling: a fresh
   root-authenticated live status, replay-delta, execution-error, quota, and
   intended-hash check immediately before any Kaggle write.

Uncertainty remains about how often the hardened generic rule will activate,
so any later permission would still be for one exploratory probe only. There
is no uncertainty about the current decision: the demonstrated public-state
false positive is sufficient to reject this build.
