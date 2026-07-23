# Final strategy judgment: guarded Teleportation continuity

- Decision date: 2026-07-19 JST
- Role: read-only Sol-Ultra rule-policy judge
- Kaggle action: none

## Verified facts used

The frozen contract is
`decisions/20260719_1100_public_net_clock_reject_and_guarded_teleport_select.md`,
SHA-256
`FC0397EB673103F095650537C788385B38AB105CBD054F864B0AA593D196B9C7`.
Its final sentence permits packaging only after a **complete** Phase-0 pass.

Root final verification, independent numerical audit, and independent
qualitative audit have respective SHA-256 values
`3117228D0A94824E4FBCF103A4B47DFE9DF40709D11969D4780D7482642A707F`,
`3E9676DC8C78E26AB691232428D19BCEB96A6B2C0600187E4037340424F01A21`,
and
`95079DB80910E8273FF7ECFDC8EE6106DB89D9C180CD51E2DCF50A808F4B5F8C`.
They agree, and root found no discrepancy in the frozen raw rows.

Direct hash checks also match the supplied identities:

- exact-v3 parent source/runtime/deck:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- guarded-Teleport source/runtime/deck:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

The exact paired result is parent `86/144`, candidate `89/144`, `3G/0R`,
or `+2.08` percentage points. The paired 95% interval is
`[-0.28,+4.46]` points and exact two-sided McNemar `p=.25`. All `576`
ledger rows form four identical 144-key schedules; duplicate results match;
exit failures, action errors, max-step hits, missing/extra keys, and duplicate
keys are zero.

All six primary first differences are certified parent MAIN `RETREAT` versus
Abra Teleportation Attack `1070`; all immediately deal ten and switch to the
pre-certified unique zero-Energy Kadabra. There are three causal gains and no
binary mechanism-first regression or semantic defect. The four attack-ready
retreat negatives and two PLAY-bearing negatives remain parent-identical.
Every activation is in `known_target`; the only Silver activation remains a
loss.

## Final verdict

**REJECT this exact source for packaging and live submission.** It is not a
close discretionary call: the precommitted complete-pass condition is false.

| Frozen requirement | Observed | Verdict |
|---|---:|---|
| Historical Silver absolute | `8/16` vs `>=9/16` | fail |
| Historical Silver movement | `0` gain vs `>=1` | fail |
| P1 | `41/72` vs `>=42/72` | fail |
| fresh | `42/72` vs `>=43/72` | fail |
| Kangaskhan/Crustle | `10/16` vs `>=11/16` | fail |
| fresh natural activation | `0` | fail |

The mechanism improves known P0 positions, preserves Abra Energy, and creates
real later Powerful Hand continuity. That is useful causal evidence. It does
not establish both-seat strength, fresh-population behavior, primary-anchor
movement, or finishing improvement. Silver's altered line attacks earlier yet
reaches a worse prize endpoint before the same loss. The aggregate interval
still includes harm. Zero binary regressions and clean execution establish
local safety, not adoption.

Across the full game plan: setup and ordinary board formation are unchanged;
the six admitted boards and switch targets are correct; Energy conservation
and known-board attacker continuity improve; hand/deck and Night Stretcher
ordering can change downstream; prize conversion occurs only in three known
P0 games; Silver finishing does not improve; disruption/fresh behavior is
unexposed. Those coupled facts rule out promotion.

**Disposition:** retain the unstacked Teleportation mechanism as research
evidence only. Do not use this source as the parent of a sibling. Fork the next
candidate directly from exact-v3 so the known-only change is not stacked and
attribution remains paired and isolated.

## Selected next sibling: public Sacred Ash reserve timing v1

Select exactly one next direction:
`alakazam_public_sacred_ash_reserve_timing_v1`, forked only from exact-v3 at
the source/runtime/deck identities above.

Hypothesis: the deck's single Sacred Ash should not be cashed in early for only
one or two public discard Pokemon when the board is already sufficiently
formed and the public deck/prize reserve is larger than the card's maximum
five-card recovery. Holding it preserves Powerful Hand hand size and permits a
later, higher-yield deck replenishment. This is an opponent-agnostic resource
timing rule aimed at the verified exact-v3 Great Tusk floor (`4/16`) and the
root-verified deck-exhaustion loss in live episode `86778139` (replay SHA-256
`E81761637DE5281CFB03345F3E1C5576400ED5353334E7AB907C905A98B5271F`).
The live game is a causal lead, not population proof.

This is not the rejected public net-deck-delta source. It must inherit no
guarded Teleportation, Psychic Draw suppression, Lucky Helmet suppression,
Run Away override, net-clock threshold, or other rejected sibling code.

### Implementation-ready behavioral contract

Compute exact-v3's complete finalized choice first. Define from public own
state only:

- `D = deckCount`, `P = prizes remaining`, and reserve `M = D - P - 1`;
- `R = min(5, N)`, where `N` is the number of serial-distinct Pokemon in the
  own discard that Sacred Ash can legally select;
- board-sufficient means at least three in-play Abra/Kadabra/Alakazam bodies,
  at least one public Psychic Energy attached to one of them, and at least one
  Alakazam either in play or visible in hand.

Override only when all clauses hold:

1. Context is ordinary MAIN; exact-v3's unique finalized action is PLAY of the
   visible Sacred Ash serial; no parent transaction latch is active.
2. `1 <= R <= 2`, `M > 5`, and board-sufficient is true.
3. None of the returnable serials is required by a currently certified parent
   transaction, and no public same-turn final-Prize or board-out route is being
   executed.
4. Card/effect metadata, player, turn, serials, zones, and legal-option mapping
   are complete and unambiguous.

When admitted, mark only that Sacred Ash serial unavailable for the remainder
of the same player/turn and return exact-v3's next-ranked legal action under
its unchanged stable ordering. Recompute the public predicates at every MAIN
callback. Clear the hold on player/turn change, zone/serial loss, predicate
failure, or unexpected callback. Repeated identical callbacks return the same
action. When the hold clears, delegate fully; if Sacred Ash is later played,
all of its effect and TO_DECK choices remain exact-v3.

Mandatory negatives delegate bit-for-bit: `R=0`, `R>=3`, `M<=5`, fewer than
three Abra-line bodies, no attached public Psychic Energy, no visible/in-play
Alakazam, a final-Prize/board-out route, any active parent latch, parent top
action other than Sacred Ash, multiple/ambiguous Ash options, mandatory effect
callbacks, stale serials, malformed state, or unknown relevant text. Do not
change setup, evolution, attachment, Psychic Draw, Helmet, Run Away, recovery
selection, retreat, Boss, targeting, attacks, or the deck.

### Exposure controls before implementation/evaluation

Root must first freeze an exact-v3 exposure census over the 144-key schedule
and replay `86778139`, recording key/step, Sacred Ash serial, `D/P/M/R`, board,
hand/discard serials, finalized and next-ranked actions, and whether a returned
card is immediately required. The apparent early low-yield Ash state near
replay step 70 is only a locator until root certifies its action mapping; it
must not be treated as a positive fixture on this report alone.

Focused positives must include at least one root-certified `R<=2, M>5`
state with the board certificate. Focused negatives must cover every mandatory
negative above, especially `R=3`, `M=5`, missing backup structure, final-Prize
conversion, active parent latches, option-order permutations, repeated calls,
and a later released Sacred Ash transaction. If the census finds fewer than
four natural positives spanning both blocks and at least two opponents, stop
before implementation; the hypothesis lacks usable exposure.

### Frozen adoption gates

Use the same 144-key both-seat schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`
with primary and duplicate controls for both policies.

- at least `89/144`, at least `3G/0R`, with at least one gain in each seat;
- Historical Silver at least `9/16` with a Silver gain;
- Great Tusk at least `5/16` with a Great Tusk gain;
- P0 at least `45/72`, P1 at least `42/72`, known at least `44/72`, fresh at
  least `43/72`, Rmy at least `7/16`, Kangaskhan/Crustle at least `11/16`, and
  no opponent decline;
- at least four natural holds across both seats, both blocks, and two
  opponents, including Great Tusk and either Silver or an Alakazam mirror;
- every first difference is exact-v3 PLAY Sacred Ash versus the certified
  hold action on an identical pre-action state;
- at least one causal gain later realizes the intended reserve mechanism by
  playing the same Ash serial for `R>=3`, preserving an otherwise lost
  start-of-turn draw, or converting the retained hand/deck card into an
  additional attack or Prize; no mechanism-first regression;
- zero execution, action, max-step, duplicate, schedule, hash, cache, or
  semantic defect, plus exact source/runtime parity and a byte-identical legal
  deck.

Only a complete pass may return to a final rule-level adoption judgment.

## Regression risks and exact evidence needed next

Holding Sacred Ash may lose it to later hand disruption, delay access to a
recycled evolution line, alter Psychic Draw composition, or preserve deck at
the cost of immediate board rebuilding. It can also be too sparse to affect
the Great Tusk, P1, fresh, Silver, or Kangaskhan floors. These risks are why
board sufficiency, low current return, repeated exposure, both-seat movement,
primary-anchor movement, and no-regression gates are mandatory.

Next evidence, in order: (1) root-certified exposure census and replay-step
mapping; (2) focused transaction/negative fixtures and exact source/deck
hashes from one Sol-xhigh worker; (3) immutable paired raw rows with duplicate
controls; (4) Sol-Ultra numerical and qualitative audits; (5) root
recomputation of outcomes, keys, errors, max steps, floors, and the causal
first differences. If the census or any frozen gate fails, reject the sibling
and retain exact-v3.
