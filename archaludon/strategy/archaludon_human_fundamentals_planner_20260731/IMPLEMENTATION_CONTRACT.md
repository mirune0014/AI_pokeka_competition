# Archaludon human-fundamentals turn planner v1

## Frozen inputs

- Parent:
  `candidates/archaludon_integrated_public_turn_plan_transaction_v1`
- Parent `main.py` SHA256:
  `3E23CC048CF87E148ACA3E7B017B5B3AAA8C422BD1580BF553222CA79BB466A2`
- Parent `deck.csv` SHA256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Source-only audit SHA256:
  `07480151E49FC1D85D96A8A6B458EDDD6955CC4423C5143E50D549DD84F891A6`
- TODO SHA256:
  `F0FDECB14149E9DA55ACEACEC35A62C208FE74DC6CF8A4D8ED4946F487D2CACA`

## Candidate destination

`candidates/archaludon_human_fundamentals_turn_planner_v1`

Implementation evidence destination:

`implementation/archaludon_human_fundamentals_turn_planner_v1`

The parent and all other repository artifacts are read-only inputs.

## Single coherent hypothesis

Replace the final decision path with one deterministic public-state
human-fundamentals planner. The planner generates plans from board properties,
not from the action selected by the historical parent, and compares them by
terminal result, Prize clock, return threat, attack continuity, and essential
resources.

The old seventeen frozen rules may remain as inert source, but the new final
`agent` must not call `_CUM_RULES` or use fixed rule ranks. The historical parent
may be used only for truly unsupported mandatory engine contexts after the new
planner has produced no safe legal action.

## Phase-1 implementation scope

### Shared `PublicFacts`

Build one immutable per-callback facts object containing:

- both Active and Bench boards, HP, maximum HP, lineage, Energy, tools, status;
- our hand/discard and both Prize/deck counts;
- stadium and turn-action flags;
- public previous-attack effects;
- Prize value, Rule Box, stage, type, and public skills for each Pokémon.

Do not duplicate fact extraction for our and opponent damage.

### Shared combat resolver

Implement one resolver returning at least:

- `min_damage`, `max_damage`, `exact`;
- `ko_certain`, `ko_possible`;
- `prevented`, `persistent_damage`;
- `prize_delta`;
- uncertainty reasons.

The exact order is:

1. legality and Energy payment;
2. printed/formula damage or counter placement;
3. attacking modifiers;
4. Weakness;
5. Resistance `-30`;
6. defending/stadium reduction, with Full Metal Lab symmetric;
7. prevention/immunity;
8. KO replacement;
9. Prize modifiers.

Required exact Phase-1 semantics:

- every attack, ability, trainer, tool, and stadium in the fixed deck;
- Raging Hammer;
- Metal Defender;
- Coated Attack;
- Turbo Flare;
- Weakness and Resistance;
- Full Metal Lab;
- Hero's Cape;
- ex/mega Prize values;
- fixed additive/reductive public modifiers already represented in the card
  database;
- damage counters versus attack damage;
- public return-to-hand/deck effects that erase non-KO chip progress.

Unknown dynamic effects are not zero. They carry `UNKNOWN`; use the upper bound
for opponent threat and lower bound for our benefit. They cannot certify KO or
survival.

### Current plus one-resource threat model

For every public Pokémon enumerate:

- ready now;
- ready after one Basic Energy attachment;
- ready after one legal public evolution with current Energy;
- ready through one known public ability;
- Active retreat/switch into a ready Bench attacker;
- Bench promotion after Active KO.

Record evolution-plus-Energy and unknown hand combos as speculative only in v1.

### Plans

Generate deterministic plans for:

- terminal direct attack;
- terminal/high-Prize/threat-removal Boss;
- ex and non-ex evolution into attack;
- Duraludon direct attack;
- Turbo Flare formation;
- heal/Cape/FML continuity;
- retreat, rotation, and one-Prize sacrifice;
- Ultra Ball, Poké Pad, Pokégear, Night Stretcher, Explorer, and Lillie setup;
- no-current-attack next-attacker formation.

Each plan contains ordered action semantics, required callbacks, resulting
public-state deltas, immediate Prize, maximum return threat, next attackers,
important resources spent, and uncertainty.

### Hard branches

1. Engine result/deck/setup/mandatory contexts.
2. Duplicate callback replay.
3. Valid active transaction.
4. Exactly certified terminal win.
5. Filter plans that allow a preventable exactly certified terminal loss.
6. Reject loss of the only Pokémon, surrender of the opponent's final Prize,
   and attacks exactly known to be nullified.
7. Lexicographically compare remaining plans.

Do not use a weighted sum.

Required comparison tuple:

1. `opponent_turns_to_win - own_turns_to_win`;
2. our shortest win;
3. immediate certain Prizes;
4. maximum Prizes lost on the return;
5. ready next attackers;
6. one-resource next attackers;
7. certain survival margin;
8. persistent opponent damage;
9. essential resource reserve;
10. fewer actions;
11. deterministic semantic tie-break.

If every plan is losing, maximize turns until certain loss, extra opponent
resources required, and remaining comeback routes.

### Required player fundamentals

- Setup Cinderace Active and legal useful Duraludon Bench; remove setup
  `never bench`.
- Remove the blanket non-ex `-1000`.
- Generate non-ex plans for exact 120 KO, Basic prevention, one-Prize wall,
  ex-immunity bypass, stranded-Active repair, attack continuity, or improved
  Prize clock.
- Prefer ex when 220/Assemble Alloy shortens the winning route after return
  threat and Prize exposure.
- Normally take Prizes. Generate a decline-KO plan only when the KO produces a
  public forced loss or worse Prize clock and the decline preserves a concrete
  continuation.
- Treat return-to-hand/deck Pokémon as having zero persistent chip unless the
  hit is a KO.
- Boss only for terminal win, better Prize KO, ready-threat removal, or a
  certified full-turn stall.
- Use an item/supporter only for a declared plan purpose; remove the default
  `20000`.
- Bind Ultra Ball target plus both discards before play.
- Bind Night Stretcher's recovery target before play.
- Plan Turbo Flare and Assemble Alloy Energy allocation as one transaction.
- Compare FML's effect on both sides and Ice Cream healing against lost Raging
  Hammer damage.
- Unknown optional effects default to NO; unknown optional numbers use the
  minimum; mandatory contexts still return a deterministic legal selection.

### Transaction requirements

- One owner only.
- Serial/semantic binding, not option position.
- Same snapshot returns the same action without stage advance.
- Unexpected state clears the transaction and replans from the actual current
  state; it does not return to random or old scalar scoring.
- Every decision records telemetry: hard branch, combat certainty, threat
  envelope, Prize clock, comparison tuple, reason, and transaction stage.

## Required focused tests

The worker must implement and run source-only/synthetic tests for all items
below, including seat inversion and option-order permutation where applicable:

1. Setup Cinderace plus all legal useful Duraludon Bench.
2. Weakness/Resistance/FML independently and together.
3. Raging Hammer through the same modifier order.
4. Metal Defender persistence by attacker serial.
5. Coated Attack prevents Basic damage but not evolution damage.
6. Hero Cape and Prize values without double counting.
7. Unknown modifiers never certify KO/survival.
8. Ready-now, one-Energy, one-evolution, and two-resource speculative threats.
9. Generic non-Ogerpon non-ex exact KO and Basic-prevention positives.
10. ex-positive negative control where only 220 is terminal.
11. one-Prize versus two-Prize same-KO exposure.
12. safe decline-KO positive and ordinary-KO negative.
13. return-to-hand/deck chip is nonpersistent.
14. Ultra Ball full transaction positive/unsafe-discard negative.
15. Night Stretcher target-locked positive/negative.
16. purposeful/held cases for Pad, Gear, Explorer, Lillie, Ice Cream, Cape,
    and FML.
17. last essential Boss/evolution/Energy preservation.
18. Turbo Flare and Assemble Alloy multi-placement transactions.
19. duplicate callback and unexpected-state replanning.
20. unknown mandatory callback remains deterministic, legal, and respects
    min/max count.
21. static inspection: new final planner does not reference `parent_action`,
    `detect_matchup`, `_CUM_RULES`, fixed rank resolution, `random`, episode
    IDs, replay IDs, or opponent identity.
22. compile/import, legal unchanged deck, one final callable, cache-free tree.

## Engine gate

After focused tests:

- packaged/current source both-seat smoke;
- zero invalid actions;
- zero exceptions;
- zero max-step hits attributable to the candidate;
- at least one completed transaction in each seat;
- telemetry proves setup, non-ex, Prize-clock, threat, and resource-plan
  mechanisms can activate in synthetic/full-engine coverage.

Do not weaken this contract to make a test pass. Record any unimplemented TODO
explicitly rather than claiming complete coverage.
