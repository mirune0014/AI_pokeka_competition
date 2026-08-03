# Night Stretcher post-shadow causal repair amendment

## Status and authority

This amendment is rooted in direct replay-state inspection of the rejected
`8232D0AD...555B` shadow source and its immutable raw rows.  It narrows the
implementation meaning of the existing purpose-bound Night Stretcher contract;
it does not authorize episode-specific branches or hidden-state use.

The current `47BF05DE...3428` source already repairs the false active-evolution
liability comparison observed twice in episode `87738210`.  It is not eligible
for fixed evaluation because the target and route audits found additional
causal failures.

## Root-verified failure classes

1. **Exact current KO was erased by an incomplete reply graph.**
   At `87659504 / seat 0 / effect step 57`, Duraludon's payable Raging Hammer
   deals exact 80 into a 70-HP Crustle.  `_pbns_current_attack` returned no row
   because reply-graph construction was incomplete, so the transaction evolved
   the Active and converted an exact KO into zero damage.
2. **Payable was mistaken for useful.**
   At `87664300 / seat 1 / step 96`, recovered Metal made a Duraludon attack
   payable but its certified final damage was zero.  Recovering Archaludon ex,
   evolving Duraludon, and resolving Assemble Alloy made a 190-damage Metal
   Defender KO instead.
3. **Recovery was not tested for necessity.**
   At `87842092 / seat 0 / step 96`, a visible hand Metal already enabled the
   same active KO.  Recovering another Metal consumed Night Stretcher and left
   the bench empty.
4. **Immediate attackability outranked exact terminal-loss avoidance.**
   At `88293552 / seat 1 / step 113`, a zero-damage attack was followed by the
   opponent's exact terminal KO.  Recovering and evolving Archaludon ex plus
   public Alloy energies survived that same reply even though it could not
   attack immediately.
5. **A saved route pre-empted a productive parent sequence without proof.**
   At `87651381 / seat 0 / step 97`, the parent attached to an established
   Archaludon ex and later attacked for 190; the candidate redirected the Metal
   to a new Duraludon and attacked for 20.  At `88507294 / seat 0 / step 53`,
   the parent used Poke Pad, created two bodies, and reached the same attack;
   the candidate forced the shorter route and lost the extra body.
6. **Semantically equal copy selection created noise.**
   Three target changes differed only by serial and had no policy advantage.

The inherited-owner handoff at `87662159 / seat 0 / step 135` is safe: PBNS
clears before the exact parent resolves Assemble Alloy, and no PBNS action or
state survives.

## Controlling repair contract

### 1. Independent current-attack certificate

Enumerate legal, payable attacks and obtain their exact attack certificates
independently from opponent-reply graph availability.  An exact current KO,
Prize gain, or terminal win must not disappear merely because a later reply is
unknown.  The controlling precedence is:

1. exact current win;
2. exact avoidance of an otherwise certain terminal loss;
3. nonterminal exact current KO and Prize gain;
4. all continuity and resource comparisons.

Therefore no Stretcher route may lower a certified current KO or Prize gain
unless the route satisfies the stricter whole-board terminal-loss-avoidance
certificate below.  A merely safer or higher-HP route does not qualify.

### 2. Meaningful Stretcher-enabled attack certificate

`ready` and `payable` are necessary but not sufficient.  This requirement
governs every attack made possible or selected by the Stretcher route, including
`ATTACK_NOW`, `EVOLVE_ATTACK_NOW`, Active evolution, and backup continuity.
Against the current public opposing Active, the attack must certify at least
one of:

- positive final damage;
- exact KO or Prize gain;
- a necessary, deterministic non-damage effect that advances the certified
  route.

A non-damage effect must be named and have an exact public postcondition that
the certified route actually needs.  A generic `persistent_progress` flag,
unresolved callback, hypothetical target, or future possibility is insufficient.
For example, zero-damage Turbo Flare is meaningful only when its acceleration
callback and an eligible public target/capacity are both exact and needed by the
saved route.  Otherwise zero damage fails closed.

The post-reply state must be nonterminal.  Unknown future promotion does not
justify inventing damage or rejecting an otherwise exact current KO.

### 3. Recovery necessity

Before recovering Metal, simulate visible hand Metals and compare the semantic
host/attachment role plus the complete post-route board and resource ledger,
not the physical Energy serial alone.

- In `OVERRIDE_TO_STRETCHER` mode, when a hand Metal produces the same full
  attach, meaningful-attack, KO, and Prize outcome, do not start a
  Stretcher-to-Metal route.
- In `PARENT_ALREADY_STRETCHER` mode, the Item use is a sunk cost.  Remove the
  redundant Metal target from candidate improvements, recompute non-Metal
  recovery targets using the legal hand Metal, and preserve the exact parent's
  mandatory recovery selection unless an alternative is exact and Pareto
  nonworse at every higher-priority layer **and strictly better in at least one
  exact board, attack, or resource layer**.  Equality, incomparability, or any
  `UNKNOWN` field preserves the parent's mandatory selection.

The mandatory one-card recovery callback must always return one uniquely legal
selection.  Necessity filtering may never produce an empty or invalid action.

### 4. Exact defensive evolution

When the opponent has one Prize remaining and an exact visible reply wins the
game, allow a public Archaludon ex evolution plus exact Alloy resolution to
avoid that terminal reply even if the evolved Pokémon cannot attack now.  This
route is allowed below an exact current win but above a nonterminal current KO.
It must prove that **no exact public terminal reply remains against the entire
projected post-evolution board**, including a switch, gust, Bench target, attack
effect, or alternative ready attacker represented by the complete public reply
enumeration.  Merely surviving the previously selected reply or target is not
sufficient.  Unknown or incomplete reply coverage fails closed.

This is an explicit no-attack lifecycle.  After evolution and exact Alloy
resolution, re-certify the whole board, then complete through a currently legal
`END`, exact-parent action, or inherited-owner handoff.  The transaction must
not require an `ATTACK` step, exhaust an attack-only queue, or carry a stale
attack reservation into the next callback or turn.

### 5. Preserve the parent's semantic copy

If candidate targets are equal in semantic outcome and copy-isomorphic resource
ledger, retain the serial selected by the exact parent when it belongs to that
equivalence class.  Copy-isomorphic equality means exact equality after a
permutation of publicly identical same-ID physical copies, including their
locations, roles, attachments, and same-ID hosts; raw serial-keyed ledgers are
not sufficient.  The binding decision occurs at the Night Stretcher recovery
callback, where the exact parent's target is first observable; pre-Stretcher
planning must not guess that serial.  The callback must rebind the whole saved,
pre-certified semantic equivalence class to the parent target when uniquely
valid.  Lowest serial is only a deterministic fallback when the parent did not
select an equivalent member.

### 6. Do not pre-empt productive parent route steps

After the parent has already played the same Night Stretcher and selected the
same recovery target, every legal non-`END` parent action is preserved by
default.  A saved PBNS step may replace it only when both actions have complete
exact public projections and the candidate strictly dominates at the full
controlling hierarchy.  Search, draw, unresolved callbacks, hidden outcomes,
or any incomparable projection therefore return the parent action.  After
emitting a parent action, invalidate the old saved queue.  Any later candidate
route must be planned and certified anew from the actual next state; it may not
resume an old step index.  Clear and delegate on stale resources, filled bench
slots, or inherited callback owners.

Parent `END` conversions at `88035562` and `88660007` remain valid positive
controls.  The two harmful parent-sequence takeovers above are required
negative controls.

## Required focused evidence before a fresh full shadow

- Both seats for every repaired failure family.
- The four original positive purpose families.
- Duplicate callback rebinding and stale-state clearing.
- The safe inherited Alloy owner handoff.
- Exact current-KO preservation when the reply graph is unavailable.
- Zero-damage backup rejection and positive-damage/KO backup acceptance.
- Separate zero-damage rejection for `ATTACK_NOW`, Active
  `EVOLVE_ATTACK_NOW`, and `BACKUP_CONTINUITY`, so the guard cannot exist only
  in one helper.
- A named exact deterministic non-damage-effect positive and an unresolved or
  targetless non-damage-effect negative.
- Hand-Metal recovery-necessity negative.
- Exact terminal defensive evolution positive and nonterminal negative.
- A defensive-evolution negative with an alternate whole-board terminal target,
  plus an assertion that the successful no-attack route clears all saved state
  after its legal completion.
- Parent productive-step preservation and parent-END conversion retention.
- Copy-isomorphic parent-target preservation at `87663229 / seat 0 / step 121`,
  `87665900 / seat 1 / step 97`, and `87877210 / seat 1 / step 103`.
- Compile/import, legal 60-card deck with one ACE SPEC, last-callable loader
  behavior, deterministic valid actions, and a cache-free candidate tree.

Only a new complete full shadow from the repaired frozen source can satisfy the
original frequency and qualitative gates.  The interrupted `47BF` shadow and
the rejected `8232` shadow are diagnostic evidence only.
