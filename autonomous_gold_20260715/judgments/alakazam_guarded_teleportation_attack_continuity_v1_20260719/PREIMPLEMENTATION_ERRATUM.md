# Pre-implementation erratum: Sacred Ash target and gates

- Recorded: 2026-07-19 JST
- Role: read-only Sol-Ultra rule-policy judge
- External write: none
- Governing judgment:
  `FINAL_STRATEGY_JUDGMENT.md`, SHA-256
  `9E8A062035FB2C991483A6D3126A5B7D1E2AF6957158F49165ACDF7DEC27AFB7`
- Scope: this erratum supersedes only the Sacred Ash target population,
  exposure requirements, and adoption gates. It does not silently modify the
  original artifact or change the public behavioral predicate and mandatory
  negatives.

## Root-verified contradiction

Root parsed all 144 exact-v3 `baseline_primary` traces, selected the evaluated
player by seat, found 72 finalized MAIN Sacred Ash plays, and paired each with
the immediate same-player context-9 option set to establish `N/R`.

The original `D/P/M/R` and board-sufficient predicate has exactly seven
preliminary positives:

1. `fresh_general|alakazam_oselcoun|p0|2026101803`, step 75, `R=1`;
2. `fresh_general|alakazam_rmy|p1|2026101804`, step 50, `R=1`;
3. `fresh_general|historical_silver|p0|2026101804`, step 93, `R=2`;
4. `known_target|alakazam_oselcoun|p0|2026071593`, step 57, `R=1`;
5. `known_target|dragapult|p1|2026071586`, step 142, `R=2`;
6. `known_target|kangaskhan_crustle|p1|2026071593`, step 55, `R=2`;
7. `known_target|starmie|p0|2026071593`, step 48, `R=2`.

They span both blocks, both seats, and six opponents. Great Tusk has zero
predicate-positive Sacred Ash plays: each of its five evaluated-player Ash
plays fails board sufficiency or `M>5`. Therefore a Great Tusk natural hold or
gain from this unchanged rule is structurally unreachable in the frozen
schedule. The prior Great Tusk target and gates are invalid and must not be
used to authorize implementation or judge evaluation.

## Exact revised decision

Choose **B: RETARGET BEFORE IMPLEMENTATION**.

Keep the unchanged hypothesis
`alakazam_public_sacred_ash_reserve_timing_v1`, forked only from exact-v3
source/runtime/deck SHA-256
`49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
`9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Its target is now **Alakazam-mirror and Historical-Silver resource
endurance**, not Great Tusk. This is coherent because four preliminary
positives are exactly in that population: two Oselcoun keys, one Rmy key, and
one Silver key, spanning both blocks and seats. Exact-v3 is only `7/16`
against Rmy and `8/16` against Historical Silver; the live causal anchor
`86778139` is an Alakazam-mirror loss by deck exhaustion. The remaining
Dragapult, Kangaskhan/Crustle, and Starmie positives are adjacent-population
safety/exposure controls, not new targets.

Root additionally certified replay `86778139` observation step 70, whose next
transition plays Sacred Ash serial 35, as contract-positive: `D=22`, `P=6`,
`M=15`, discard returnables Kadabra serial 9 plus Abra serial 4 (`N=R=2`),
three Abra-line bodies, attached Psychic Energy, and Alakazam in play/hand.
That same game later loses by own deck exhaustion. This is a valid live mirror
fixture for the retarget, while still being only one causal game.

Do not inherit guarded Teleportation or the rejected net-deck-delta Psychic
Draw, Lucky Helmet, Run Away, or clock rules. The public Sacred Ash predicate,
same-turn hold behavior, fail-closed clauses, and all mandatory negatives in
the governing judgment remain byte-for-byte the implementation contract.

## Final pre-edit exposure certificate

The seven rows are preliminary because root's census establishes the numeric
and board predicate, not yet every transaction/final-Prize exclusion. Before
any source edit, root must freeze the exact observation/action hashes and
verify the remaining clauses for all seven.

Implementation may proceed only if the fully certified positives still
include:

- `fresh_general|alakazam_rmy|p1|2026101804`;
- `fresh_general|historical_silver|p0|2026101804`;
- at least one of the two Oselcoun keys; and
- at least one known-block key.

This guarantees a minimum of four usable positives, both seats, both blocks,
and at least three opponents. Otherwise reject this hypothesis before editing
source. All other Sacred Ash plays are mandatory negative controls. In
particular, every Great Tusk primary trace must remain exact-v3-identical.

## Revised frozen adoption gates

Use the same 144-key both-seat schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
with primary and duplicate controls for both policies.

- candidate at least `89/144` and at least `3G/0R`;
- at least one gain in each seat and at least one gain in each block;
- Historical Silver at least `9/16`, with a gain at the certified Silver
  exposure;
- Rmy at least `8/16`, with a gain at its certified exposure;
- combined Oselcoun plus Rmy at least `16/32`, no mirror decline, and at least
  one mirror gain;
- P0 at least `45/72`, P1 at least `42/72`, known at least `44/72`, and fresh
  at least `43/72`;
- Great Tusk at least `4/16`, with all 16 Great Tusk baseline/candidate primary
  traces byte-identical; Kangaskhan/Crustle at least `10/16`; no opponent
  decline;
- at least four natural holds across both seats, both blocks, and at least
  three opponents, including Silver, Rmy, and one known-block key;
- every first difference is exact-v3 PLAY Sacred Ash versus the certified
  hold action on an identical pre-action state; every nonpositive Ash exposure
  preserves the parent Ash decision;
- at least the Silver and Rmy gains begin causally at the intended hold, and
  each later realizes the reserve mechanism through a higher-yield use of the
  same Ash serial, a preserved required start-of-turn draw, or an additional
  attack/Prize attributable to the retained hand/deck resource;
- zero mechanism-first regression, execution failure, action error,
  max-step hit, duplicate mismatch, schedule defect, hash defect, cache file,
  or semantic defect; exact source/runtime parity and the byte-identical legal
  deck remain mandatory.

The unchanged rule is not accepted merely for activating seven times or for a
small aggregate delta. Packaging requires the complete revised gate: practical
absolute strength, Silver anchor movement, Rmy-floor movement, both-seat and
both-block gains, adjacent-population safety, repeated mechanism behavior, and
causal confirmation. Great Tusk is now a strict negative control, not a target.

## Next evidence

The exact next discriminating evidence is the root-completed seven-row
transaction certificate. If it passes, one isolated Sol-xhigh implementation
may be evaluated on the frozen schedule. If it fails the minimum exposure set
or any later revised gate, reject the candidate and retain exact-v3. No
packaging or live submission is authorized by this erratum.
