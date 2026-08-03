# H4 strategy selection — certified unique higher-Prize Boss KO

## Decision

Select exactly one direct historical-Silver sibling:

`H4_CERTIFIED_UNIQUE_HIGHER_PRIZE_BOSS_KO`

When the current Active already has a legal deterministic attack and exactly
one Boss-accessible Bench target is KO-able by that same attack for strictly
more immediate Prizes than the opposing Active, commit:

`Boss -> unique higher-Prize target -> same attack`.

Do not stack H1, H2, or H3.

This mechanism outranks the next alternatives because five independent public
states show the same direct prize-conversion error. Attack-completing Energy
reservation has one known natural state; the non-ex 120 breakpoint has two
states but only one clear superiority case; non-KO exposure, Bench
preservation, threat reachability, access ledgers, and explicit modes need
broader valuation.

## Frozen identities

- Formal parent:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224/main.py`.
- Parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- Deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Primary replay:
  `autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_87825800_replay.json`.
- Primary replay SHA-256:
  `9CC07DAE64B803E88CBBCB770783CE5157688C6944643521C94176588026640F`.
- Primary callback: episode `87825800`, row `116`, seat `1`, turn `10`.

## Root-verified primary positive

At the primary callback:

- our remaining Prizes: `6`; opponent remaining Prizes: `2`;
- our Active is Archaludon ex `190#69`, `300/300` HP, with Basic Metals
  `#118,#119,#112`, no Tool, and no public Special Condition;
- `supporterPlayed` is false;
- legal Boss copies are `1182#101` at option `0` and `1182#99` at option `1`;
- opposing Active Hariyama `674#6` is `30/150` HP and worth one Prize;
- opposing Bench contains Lunatone `675#7` at `110/110`, Solrock `676#11`
  at `110/110`, Mega Lucario ex `678#18` at `120/340`, and Cape-bearing
  Mega Lucario ex `678#17` at `310/440`;
- Metal Defender `253` is legal at option `3`, deals deterministic `220`,
  KOs the one-Prize Active and the first three Bench targets, and does not KO
  the `310/440` Mega;
- exactly one KO-able target has the maximum Prize value:
  Mega Lucario ex `678#18`, worth three Prizes;
- exact parent recomputation chooses Metal Defender `[3]`;
- H4 must choose the lowest-serial Boss `#99` at option `[1]`, then target
  `#18`, then Metal Defender.

The replay row's stored action is not used as a label. Row `116` stored `[0]`
belongs to the preceding promotion callback; the parent's response is stored
at row `117` as `[3]`.

## Supporting natural opportunities

All paths are under:

`autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344`.

- `87825800:124`, seat `1`, same replay: current yield `0`, unique damaged
  Mega yield `3`.
- `88417236:70`, seat `1`, replay SHA
  `8FF9C7695C88830C9FD845E1543837E9A01A39B9510B26568EFDC50A21343BC6`:
  Raging Hammer, `1 -> 2`.
- `87974582:72`, seat `0`, replay SHA
  `ADE07481B3E46A0E32CC42B8939C63FA4838165D4658AED4654F9D7DD2C484E1`:
  Metal Defender, `1 -> 2`.
- `87892692:48`, seat `0`, replay SHA
  `2BBBD6D092A3E5873CF651562F9036E533BA113F4A620244259E450B11AB9C24`:
  Metal Defender, `1 -> 2`.
- `88096059:114`, seat `1`, replay SHA
  `6A83D2CFB4B4CCEDBDBEE697820B078F096B633D3702888A3EB92F32F7B2FC40`:
  Metal Defender, `1 -> 2`.

These are repeated state-level opportunities, not match-win guarantees.

## Arm certificate

Arm only at an ordinary `MAIN` callback when every condition holds:

1. Boss is legal, `supporterPlayed` is false, and no result or mandatory
   callback is pending.
2. At least one deterministic damage attack is already legal from the current
   Active. No attachment, evolution, retreat, Ability, search, draw, discard,
   coin result, or hidden card is required.
3. Exact damage can be computed against the current Active and every publicly
   Boss-accessible Bench target, including Weakness, Resistance, Tools,
   Stadium, Special Conditions, immunity, prevention, and persistent public
   effects. Unsupported modifiers fail closed.
4. Public Prize value is exact: Mega ex `3`, ex `2`, otherwise `1`; unknown
   modifiers fail closed.
5. For each legal attack, current-Active yield is its Prize value when KO'd,
   otherwise `0`.
6. A Bench target qualifies only when the same attack deterministically KOs
   it and its Prize value is strictly greater than that attack's current yield.
7. Exactly one distinct target serial has the maximum qualifying Prize value.
   Duplicate options for that serial are equivalent; multiple distinct
   maximum serials fail closed.
8. The target is nonterminal: its Prize value is strictly below our remaining
   Prize count. Existing terminal routes have higher precedence.
9. The attack has no probabilistic, self-KO, or deterministic board-loss
   effect.
10. If multiple legal attacks certify the same unique target, choose greatest
    exact damage, then lowest attack ID.

## Precedence

1. Deck request, result, mandatory engine callbacks, and hard legality.
2. Exact historical-parent same-turn match win, including its terminal Boss
   route.
3. Public deterministic attack prohibition, immunity, or self-loss checks.
4. Complete H4 transaction.
5. Exact historical-Silver scoring.

H4 adds no future threat forecast or harmful-KO model.

## Transaction

Snapshot:

`(seat, turn, Prize counts, supporter flag, Boss serial, attacker
id/serial/HP/Energy/conditions/tools, attack id/exact damage, original Active
serial/HP/Prize yield, target id/serial/HP/Prize yield/Energy/tools, Stadium,
public modifiers, semantic option signature)`.

Stages:

1. `ARMED`: return the stored lowest-serial legal Boss.
2. `BOSS_CONFIRMED`: advance only after public observation/log proves Boss
   left hand and the Supporter was consumed.
3. `GUST_SELECT`: at the mapped opponent switch/Active-selection callback,
   choose only the stored target serial.
4. `TARGET_CONFIRMED`: after that serial is publicly Active, recompute
   legality, damage, KO, Prize value, and nonterminal status; choose the stored
   attack.
5. `DONE`: clear after attack confirmation, turn end, result, or new game.

A returned action never advances state. Repeated callbacks return the same
semantic action. Multiple Boss copies use lowest serial; duplicate stored
Boss, target, or attack options use lowest position. Multiple distinct
maximum-Prize targets fail closed.

Before Boss consumption, any mismatch clears H4 and delegates to the parent.
After Boss consumption, clear and delegate from the actual observation when
the target callback is absent, the target disappears, or attack
legality/damage changes. Clear on deck request, new game, result, seat/turn
change, attack completion, unexpected callback, or exception.

## Required positives

- Exact-engine `87825800:116`:
  `Boss #99 -> Mega #18 -> Metal Defender`.
- Independent `87825800:124`.
- At least one two-Prize Fezandipiti/other ex Metal Defender case.
- `88417236:70` using Raging Hammer.
- Both seats, changed serials, permuted option order, duplicate semantic
  options, multiple Boss copies, and repeated callbacks.

## Required negatives

- `87825800:110-114`: three distinct one-Prize KO-able Bench targets;
  fail closed on ambiguity.
- `88457867:144`, seat `1`, SHA
  `17FACDE22AFDF51F203F6100C76593AF100AF04619EEF8561E1DED21749E5879`:
  equal one-Prize values; H1 territory.
- `87892692:51`, seat `0`: Supporter already used.
- `88171291:39`, seat `1`, SHA
  `265A7B0C3F4595928807EE42490B55EFF92F2A54DF81E8B328C4BF3EE168B4B5`:
  line requires retreat from Cinderace.
- `88017509:114`, seat `1`, SHA
  `3E828609FEF02D5D8AFA240D9E1F89C27670837A03595446062EC13F7FD62908`:
  no current legal attack; H2 territory.
- `88584180:90`, seat `1`, SHA
  `047A9FC4AB682E4F9E22F0AFE8547CB7F3016D98C2021E76C36D75C46CDD27B0`:
  attack requires attachment; Energy-reservation territory.
- H3 positive `88684114:20` and every named H1, non-KO, Bench-damage, and
  non-ex example must remain parent-identical.

## Forbidden widening

Do not implement generic Boss scoring, equal-Prize threat removal, terminal
planning, retreat/evolution/attachment/Alloy setup, Energy reservation,
Bench-future valuation, opponent one-to-two-turn prediction, matchup markers,
episode/row/seed rules, hidden hand/deck/Prize access, opponent-policy proxies,
or replay-action imitation. Do not break ties among distinct equal-best
targets using threat, Energy, or investment.

## Gates and live-probe judgment

- Full current-plus-historical correct-seat shadow, zero invalid actions and
  exceptions.
- `87825800` rows `110-114` unchanged; first difference exactly row `116`.
- Every known positive satisfies the certificate and every named negative is
  parent-identical.
- Root inspects every additional natural first difference.
- Trigger-external equality `100%`.
- Exact-engine Boss/target/attack completion in both seats, with exact damage
  and Prize removal, permutations, duplicate callbacks/options, every rollback
  stage, reset, and exception fallback.
- Fixed identical-seed both-seat `200 + 560` comparison, exact keys and
  duplicate controls, zero execution faults, zero parent-win/H4-loss flips,
  no seat/panel/opponent-cell regression, and every changed trace classified.

H4 may be implemented and evaluated after H3's current execution/audit queue.
A structurally clean neutral fixed-760 result may justify one later
exploratory probe only after a separate final Sol-Ultra judgment and after the
H1/H2/H3 live queue. Neutrality is safety evidence, not strength; formal
adoption requires repeated causal H4 triggers and practical absolute strength.
