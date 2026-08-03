# Rule 9 Strategy Selection

## Frozen inputs

- Requirements SHA-256: `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`.
- Accepted Rule 5 parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Historical-Silver deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Only Rules 1, 4, and 5 are inherited. Rules 2, 3, 6, 7, and 8 are not parents.

## Selected hypothesis

`PARENT_GEAR_EXACT_LAST_PRIZE_BOSS_CONTINUATION_V1`

Only when Rule 5 already chooses a physically bound Pokégear (`1122`), Rule 9
may arm a conditional exact last-Prize Boss route. It never changes a non-Gear
parent action into Gear and never treats adding a Supporter to hand as a gain.

The top seven are hidden at entry. Physical reveal cards first become public in
the later `TO_HAND` callback. Therefore the only supported purpose is:

`parent Gear -> revealed Boss -> unique terminal target -> same attack -> win`

Explorer (`1185`) and Lillie (`1227`) are unsupported because their hidden
draw/search results prevent a complete pre-acquisition continuation proof.

## Exact entry gate

All conditions are required:

1. Exact ordinary `MAIN`; owner empty; Supporter unused; setup inactive.
2. Higher-priority Rule 5 current win, Rule 4 materialization, and Rule 5 Boss
   proposal all declined.
3. The once-called Rule 5 action is a singleton legal `PLAY` of one bound own
   Gear serial. The emitted entry action is byte-identical to Rule 5.
4. Exact Gear/Boss/Card DB metadata; no Boss is already in hand; deck count is
   positive. No reveal identity or deck order is inferred.
5. Own Active has exactly one supported, legal, payable semantic attack.
6. That attack is nonterminal against the current Active.
7. Exactly one opponent Bench serial is an exact KO with the same attack and
   takes all remaining Prizes.
8. The existing Rule 5 exact status, Tool, Stadium, ability, Energy, damage,
   board, and Prize oracle accepts every surface.

Multiple attacks or targets, UNKNOWN, malformed bindings, or owner conflict
return exact Rule 5 without arming Rule 9.

## Transaction

```text
EMPTY
-> GEAR_PLAY_EMITTED
-> GEAR_HIT_EMITTED | MISS_EMPTY_EMITTED
-> BOSS_PLAY_EMITTED
-> BOSS_TARGET_EMITTED
-> ATTACK_EMITTED
-> CLEAR
```

- Reuse the sole `_materialization_owner`; add no wrapper or second owner.
- Reveal must be exact `CARD/TO_HAND`, effect bound to the emitted Gear,
  `min=0,max=1`, with unique mapping between `current.looking` and `LOOKING`
  options. Reveal size is `min(7, entry deckCount)`.
- If one or more physical Boss copies are revealed, choose the lowest serial.
  A reveal containing Boss plus Explorer/Lillie still chooses Boss.
- A well-formed reveal without Boss emits legal `[]`; Explorer/Lillie-only is
  an unsupported miss, not a benefit. The next exact MAIN confirms the Gear
  ledger and clears without forcing another action.
- After Boss acquisition, verify hand/discard/deck/action-count changes, play
  the bound Boss, select the prebound unique target in the exact SWITCH prompt,
  re-prove target movement and the same attack's terminal certificate, then
  emit that attack.
- Same-prompt retries rebind semantic roles without advancing. Option/looking
  reordering changes positions only. Duplicate physical Boss uses minimum
  serial; duplicate semantic roles, changed attacks/targets, or ambiguity fail
  closed.
- Seat/turn drift, stale owner, metadata or ledger mismatch, missing role, or
  changed certificate clears ownership and returns that callback's exact Rule
  5 action. After an irreversible emitted step, record abort; never substitute
  another Supporter or replan.

Every proposal has only `rule_id`, `action`, `category`, `purpose`,
`exact_proof`, and `transaction`.

## Resolver precedence

1. Reset/result/deck request.
2. Continuation of the sole active Rule 4/5/9 transaction.
3. Rule 1 setup.
4. Rule 5 exact current win.
5. Rule 4 materialization.
6. Rule 5 exact Boss conversion.
7. Rule 9 parent-Gear admission.
8. Exact Rule 5 fallback.

## Focused fixtures

Both seats must cover complete Gear->Boss->target->attack for every supported
Rule 5 attack, all Boss/Explorer/Lillie reveal subsets, physical Boss
duplicates, option and looking reversal, identical retry, well-formed miss,
and owner conservation.

Negatives include non-Gear parent, Boss already in hand, current terminal,
HP one above lethal, zero/multiple attacks or targets, Supporter used, no Bench,
deck zero, unsupported modifier/status/Tool/Stadium/ability, Explorer/Lillie
only, wrong Gear/effect/serial, malformed mapping, stale ledger, changed target
or attack, and owner collision. Opponent hidden-hand identity must not affect
the action or certificate.

## Shadow and adoption gates

Allowed first-difference classes only:

- `RULE9_REVEAL_BOUND_BOSS`
- `RULE9_REVEAL_UNSUPPORTED_EMPTY`
- `RULE9_POST_ACQUISITION_BOSS_PLAY`
- `RULE9_BOUND_BOSS_TARGET`
- `RULE9_BOUND_SAME_ATTACK`

Every difference records the entry certificate, reveal multiset,
parent/candidate semantics, bound serials, exact damage/Prize proof, and stage
ledger. Any non-parent Gear entry, Explorer/Lillie acquisition, direct
Supporter change, or unexplained difference rejects the rule.

Natural activity must include at least one complete non-fixture
Gear->Boss->target->attack transaction in replay shadow or fixed160. Zero
starts, or starts with zero natural Boss-hit completion, is `DEFER-DORMANT`;
do not widen.

Fixed160 additionally requires exact schedule equality, candidate at least
`100/160`, gains at least regressions, zero execution/duplicate faults, no
opponent/seat cell three wins below Rule 5, neither seat more than two wins
below, Historical-Silver anchor non-worse, and zero harmful first differences.

## Selection decision

Selected for isolated implementation from Rule 5. The main risk is replacing
an Explorer/Lillie reveal with `[]` after a parent-chosen Gear; every such
natural miss must be inspected. Rule 9 does not add Gear use itself.
