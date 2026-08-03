# H4 v3 strategy selection: exact inherited-attack lock

## Decision

Implement exactly one isolated direct child of exact historical-Silver:

`H4_V3_EXACT_INHERITED_ATTACK_LOCKED_UNIQUE_HIGHER_PRIZE_BOSS_KO`

When exact historical-Silver selects one deterministic Attack, Boss is
admissible only if that exact inherited attack ID deterministically KOs one
unique maximum-Prize Bench target for strictly more immediate, nonterminal
Prizes than the same attack earns against the current Active.

H1, H2, H3, H4 v1/v2, opponent identity, episode identity, hidden cards, and
learned behavior are not inputs.

## Immutable parent

- parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
- parent source SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- shared deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

H4 v2 source SHA
`29811BBFD174898B34FB551663DF0E8A3282C6C8675CEEDC5E97D631A1CE3041`
is evidence only and must not be the implementation parent.

## Exact certificate

Arm only on an ordinary single-choice `MAIN` callback with:

1. no active H4 transaction;
2. no pending result, effect, mandatory callback, or context card;
3. Supporter unused;
4. only supported public Stadium, Tool, Energy, condition, prevention,
   damage, and Prize modifiers;
5. one cached exact historical-Silver decision resolving to exactly one
   selected `ATTACK` option;
6. a uniquely resolvable inherited attack ID and attacker serial/fingerprint;
7. at least one legal Boss option;
8. no certified current-turn terminal route.

Store the exact inherited attack ID. Compute current-Active damage/yield and
every Bench-target damage/yield using only that ID. Never enumerate, compare,
or substitute another legal attack.

A Bench target qualifies only when:

- the stored inherited attack deterministically KOs it;
- its Prize value is strictly greater than the current Active yield of that
  same attack;
- its Prize value is below our remaining Prizes;
- all public legality, immunity, prevention, Weakness, resistance, Tool,
  Stadium, condition, and Prize checks are supported.

Select only when exactly one distinct serial has the maximum qualifying Prize
value. Multiple maximum targets, unsupported information, or ambiguity fail
closed.

## Precedence

1. Deck request, new game, result, and mandatory legality.
2. Existing active H4 transaction.
3. One cached exact historical-parent decision.
4. Parent terminal route and public attack prohibitions.
5. Certified H4 v3 transaction.
6. Cached parent action.

A delegated non-Attack creates no cooldown or memory.

## Transaction

Snapshot:

`(seat, turn, action_count, Prize counts, attacker serial/fingerprint, stored
inherited attack ID and option witness, Boss serial, original Active
serial/fingerprint/HP/yield, target serial/fingerprint/HP/Prize value, exact
damage values, board fingerprints, supported public modifiers, option
signature)`.

Stages:

1. `ARMED`: choose the lowest-serial legal Boss and lowest duplicate option.
2. `BOSS_CONFIRMED`: advance only after public Boss confirmation.
3. `GUST_SELECT`: choose the stored unique target serial.
4. `TARGET_CONFIRMED`: after that serial is Active, revalidate the same stored
   attack ID, target, damage, Prize values, and public modifiers.
5. `ATTACK_PENDING`: choose only the lowest-position legal option whose attack
   ID equals the stored inherited attack ID.
6. `DONE`: clear after attack confirmation, result, turn end, or new game.

Returning an option never advances state. Repeated callbacks are idempotent.
If the stored attack is absent, changed, unsupported, or no longer lethal,
clear and delegate from the actual observation. Never substitute another
attack.

## Frozen full-shadow expectation

On the existing 196-replay, 10,856-callback corpus, require exactly 13
differences:

- `87670335:111`
- `87825800:116`
- `87825800:124`
- `87953269:52`
- `87953269:67`
- `87953269:91`
- `87974582:72`
- `88010578:87`
- `88096059:114`
- `88171291:60`
- `88195925:167`
- `88399550:91`
- `88417236:70`

Remove the H4 v2 attack-substitution difference `87800215:154`.

Required distribution:

- retain `9/10` former inherited-Attack differences;
- retain all four post-setup Attack opportunities;
- remove all 27 inherited-non-Attack differences;
- remove the one alternate-attack substitution difference;
- zero other, missing, trigger-external, invalid, or exception differences.

## Required positives

- Every retained natural trigger must store and execute exactly the inherited
  attack ID.
- Both seats must complete Boss, target, and same-attack transactions in the
  exact engine.
- Option-order and serial permutations must preserve semantic behavior.
- Duplicate semantic Boss, target, and attack options choose the lowest legal
  position deterministically.
- Repeated callbacks, rollback after Boss, turn/seat/new-game reset, and
  exception cleanup must remain safe.

## Required negatives

Remain parent-identical at:

- `87800215:154`, where inherited `224` must not become `223`;
- fixed mirror seed `271828253`;
- ambiguous `87825800:110-114`;
- equal-Prize `88457867:144`;
- Supporter-used `87892692:51`;
- retreat-required `88171291:39`;
- no-legal-attack `88017509:114`;
- attachment-required `88584180:90`;
- every H1, H2, H3, setup, search, healing, attachment, evolution, Tool,
  Stadium, retreat, recovery, and delegated non-Attack callback.

## Forbidden generalizations

Do not implement:

- alternate-attack arbitration;
- equal-Prize Bossing;
- generic Boss or threat scoring;
- terminal planning beyond the veto;
- attachment, evolution, retreat, healing, or setup planning;
- future-board valuation;
- opponent, episode, seed, option-index, or replay-action rules;
- hidden-information access;
- learned ranking, imitation, or opponent-policy proxies;
- stacking H1, H2, H3, H4 v1, or H4 v2.

## Fixed-evaluation gates

After focused, structural, shadow, and exact-engine gates pass, freeze a new
trace-retained fixed-760 with the exact existing panels, seats, seeds, engine,
opponents, maximum steps, and direct parent.

Expected changed set:

- historical-Silver mirror, seat 0, seed `271828201`;
- `arch_shumpei`, seat 1, seed `271958328`;
- `mega_lucario_public`, seat 1, seed `271958318`.

Mirror seat 1 seed `271828253` must be byte-identical to the parent.

Require:

- 760 rows and unique schedule keys with exact equality;
- 760/760 duplicate summaries and byte traces;
- zero execution, start, action, exception, and maximum-step faults;
- exact inherited/stored/executed attack identity in every changed trace;
- all three changed routes certified `0 -> 1`;
- zero result, panel, seat, opponent, or opponent-seat regression;
- all existing absolute floors retained;
- Root inspection of every unexpected trace;
- independent numerical recomputation agreeing with Root.

A neutral `478/760` would establish semantic correctness and broad safety
only. It does not by itself authorize packaging or a live probe.
