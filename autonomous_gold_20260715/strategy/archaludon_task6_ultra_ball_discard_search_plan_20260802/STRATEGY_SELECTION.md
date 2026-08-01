# Task 6 strategy selection: Declared Complete-Route Ultra Ball Transaction

Date: 2026-08-02 JST

## Decision

**SELECT for isolated implementation.**

Rule id:

`PUBLIC_ULTRA_BALL_DECLARED_COMPLETE_ROUTE_TRANSACTION_V1`

Replace the narrow PFC Ultra Ball planner and its legacy `ULTRA_*` callback
lifecycle. Do not append a competing outer wrapper. Task 4, Task 5 Poké Pad,
Turbo allocation, attack choice and the deck are invariant.

Frozen parent `main.py` SHA-256:
`2B23D3AFC63A5BDC4BC7765CE1656725ED01890D161E3D23DCC672BE7FCCCFF4`.

Frozen deck SHA-256:
`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

## Hypothesis

Before emitting Ultra Ball, declare one complete public-information route:

- role;
- target card id;
- two physical discard serials;
- placement or evolution destination;
- exact Assemble Alloy and manual-attachment variant;
- unchanged attack continuation;
- unchanged Turbo handoff where applicable.

Compare all complete routes lexicographically. Never choose the two costs and
the searched Pokémon as independent local-score decisions.

## Admitted roles and priority

1. `FINISH_NOW`
   - Search Archaludon ex, or non-ex Archaludon only for exact Coated Attack.
   - Evolution is legal now and the complete route wins the game from the
     current public state.
2. `ATTACK_NOW`
   - Archaludon ex legally evolves now and exact evolution, Alloy and optional
     manual attachment make the unchanged parent attack executable; or
   - non-ex Archaludon legally evolves now and exact Coated Attack is the
     same-turn continuation.
   - Never search non-ex Archaludon for generic or future-only value.
3. `TURBO_SUCCESSOR`
   - Search Duraludon, place it into a declared open Bench slot, preserve the
     current Turbo Flare, and hand the bound serial to the unchanged Turbo
     allocator.
4. `ARCH_EX_BACKUP`
   - Search Archaludon ex, evolve an eligible Duraludon now, and use exact Alloy
     attachments to create the first certified ready backup while preserving
     the current attack.
5. `BASIC_SUCCESSOR`
   - Search and immediately Bench Duraludon only when no usable Duraludon is in
     hand and no public executable successor already exists.
   - Preserve the current attack and minimum next-attack package.

A route dominated by an equal-or-better no-Ultra route is inadmissible. If no
role and safe pair exist, Task 6 owns no callback and returns the saved parent
action. It must not search a redundant Pokémon merely to fuel Alloy.

## Exhaustive discard and energy planning

Enumerate every unordered pair of distinct legal hand serials except the Ultra
Ball being played. Use no fixed discard whitelist.

For every role, target, destination and pair, enumerate:

- current attached Energy;
- every legal post-cost Assemble Alloy Metal selection and assignment from zero
  through the exact useful amount, capped at two;
- no manual attachment if the turn attachment is already used;
- otherwise every retained-hand Metal serial assigned to the attacker or a
  competing concrete target;
- unchanged attack continuation;
- unchanged Turbo allocation when the declared role uses Turbo.

Reject overattachment or wasted actions when a lower-cost exact variant exists.

### Controlling Alloy fuel rule

For each complete variant:

```text
exact_alloy_attachment_need =
    exact Alloy attachments required by the same-turn role
    after current attachments and the selected manual-to-attacker assignment

productive_metal_cap = max(
    0,
    min(2, exact_alloy_attachment_need)
      - usable_public_discard_metal_before_ultra_costs,
)
```

Only a cost Metal actually selected back from discard by this Alloy plan may
receive productive credit, and never above the cap.

- With two usable discard Metal, productive credit is zero.
- If the planned attacker needs only one Alloy attachment, the cap is one.
- Duraludon formation, Turbo-only plans and unsupported future Alloy ideas have
  cap zero.
- Metal above the cap is an ordinary resource, not `Alloy fuel`.

The cap does not force a Metal discard. For every pair recompute:

```text
attached_now
+ exact Alloy attachments available after the Ultra Ball costs
+ retained-hand manual attachment when unused
```

For `attached 1 / discard 1 / hand 1 / need 3`, compare both:

- retain Metal: Alloy one plus manual one;
- discard Metal: Alloy two.

Two redundant cards make retaining Metal preferable. A pair that would consume
a concretely bound Boss, evolution or recovery card can make the productive
Metal route preferable. Manual-already-used state and a competing attachment
target may reverse the result.

## Hard pair protections

Reject a pair if it:

- is not two distinct legal serials or contains the played Ultra Ball;
- makes the declared target, placement, evolution, ability, manual attachment,
  attack or Turbo continuation illegal;
- breaks a higher-priority public terminal, Prize, current-attack or minimum
  next-attack route;
- removes the exact Energy package bound to manual attachment, current attack,
  Turbo completion or one certified next attacker;
- removes the minimum physical copies bound to a specific Boss target, Night
  Stretcher recovery, evolution, Duraludon successor, parent-declared
  Supporter, required Stadium or required Tool;
- leaves no complete energy-allocation variant;
- relies on a publicly absent target, full Bench, ineligible evolution target,
  used manual attachment or invented hidden information.

Protection is by exact serial or minimum required count. Do not blanket-protect
every Boss, recovery card, Pokémon, Supporter, Stadium, Tool or Metal.

## Lexicographic plan choice

Among complete safe plans, minimize in this order:

1. admitted role priority;
2. worse public Prize or finish result under the unchanged parent attack;
3. loss of current attack legality;
4. fewer ready attackers after the turn;
5. larger exact Energy deficit on the best certified backup;
6. two discard opportunity levels, sorted worst-first;
7. number of lower-priority complete public routes removed;
8. nonproductive Metal discarded;
9. productive Metal discarded;
10. total Metal discarded;
11. wasted attachment or action count;
12. canonical target id, destination serial, sorted discard `(card_id, serial)`
    and attachment-recipient serials.

Recompute opportunity level counterfactually for each pair:

- `0`: true surplus; removal changes no complete public route;
- `1`: productive Metal reattached this turn within the cap;
- `2`: only redundant multiplicity is reduced;
- `3`: one optional setup, draw, search, Stadium or Tool line disappears;
- `4`: one optional attack, evolution, recovery, disruption or continuity line
  disappears;
- infinity: hard-protected or route-breaking.

This must select redundant Ultra Ball copies before Lillie and Explorer in the
89280661 anchor, while allowing productive Metal over a scarce bound card.

## State machine and ownership

Use one PFC owner and one immutable plan:

```text
IDLE
-> DECLARED
-> COSTS_EMITTED
-> SEARCH_EMITTED or WHIFF_EMITTED
-> TARGET_IN_HAND
-> PLACE_OR_EVOLVE_EMITTED
-> ALLOY_EMITTED
-> MANUAL_EMITTED
-> ATTACK_HANDOFF or TURBO_HANDOFF
-> DONE
```

Store the turn/action epoch, Ultra serial, role, target card id, ordered cost
serials, destination/evolution serial, Alloy/manual assignments, attack
continuation, Turbo handoff and public-state fingerprint.

- Bind no searched physical serial before reveal.
- At search reveal, select the lowest canonical matching serial.
- Advance only after the expected public zone or board transition.
- Identical duplicate prompts return the same semantic serials without stage
  advancement.
- Option permutations are canonicalized; raw positions are never identities.
- Empty search or a reveal without the declared target uses an explicit legal
  no-selection, chooses no substitute, marks `WHIFF`, and resumes the saved
  parent from the actual state when control returns.
- Before Ultra commits, mismatch clears and returns the saved parent action.
- After a cost commits, rollback only relinquishes ownership; it never invents
  an undo. Delegate unexpected legal continuation to the parent and record a
  transaction failure.
- Never leave both Task 6 and Task 5, PCRD/Turbo or another inherited owner
  active.

## Required focused fixtures

1. Episode 89280661: discard two canonical redundant Ultra Ball copies, retain
   Lillie and Explorer, search Duraludon.
2. Episode 89291523: no admitted role, no Task 6 ownership, no Metal/Boss cost,
   no redundant non-ex search.
3. Episode 89347400: Duraludon reveal, Bench and Turbo handoff; the other ten
   canonical decisions remain parent-identical.
4. `attached1/discard1/hand1/need3` with two redundant costs: retain Metal,
   Alloy one and manual one.
5. Same Energy state with bound Boss/evolution alternatives: discard one Metal
   within cap and Alloy two.
6. Two and three usable discard Metal: productive cap zero.
7. Zero discard Metal and exact need one/two: cap one/two, never above need.
8. Manual already used: remove all manual variants and decline Ultra if no
   complete route remains.
9. Competing attachment target: compare manual-to-attacker with
   Alloy-to-attacker/manual-to-backup by the same readiness ordering.
10. Non-ex exact Coated positive and future-only negative.
11. Both seats, permuted options, equivalent duplicates, conflicting duplicate
    semantics and identical callback retries.
12. Empty and wrong-target reveal: legal whiff, no substitution, no stale or
    double owner.
13. Final Prize and existing owner controls remain byte-identical to parent.

## Implementation safety gate

- Parent and deck hashes fixed.
- `main.py` is the only candidate package diff.
- Diff confined to the PFC Ultra planner and lifecycle.
- All focused fixtures pass.
- Exact multi-callback completion in both seats for each admitted role exercised
  by the fixture engine.
- Episode anchors and all first differences inspected.
- Compile/import, final callable, legal 60 cards, ACE SPEC one, cache-free.
- Both-seat checked-engine smoke: zero action errors and max-step hits.
- Zero stale, duplicate-divergent or double-owner states.

This is an implementation-safety selection, not a ladder win-rate claim.

## Controlling amendment: purposeless-Ultra fallback

The earlier phrase "returns the saved parent action" does not authorize a
purposeless Ultra Ball when the saved parent itself selected Ultra Ball without
an admitted complete route. In that case Task 6 owns no callback and chooses
the unique highest-scoring legal non-Ultra prefix under the inherited scoring
semantics only when that prefix preserves the certified current attack and
terminal floor. If uniqueness or preservation cannot be certified, fail closed
to the parent.

For episode 89291523 step 104, the required result is the manual Metal
attachment to the Bench Archaludon ex, with no Task 6 owner, followed by the
still-legal current Metal Defender attack. It must not discard Metal plus Boss
to search a redundant non-ex Archaludon, and it must not skip the productive
attachment merely to attack immediately.
