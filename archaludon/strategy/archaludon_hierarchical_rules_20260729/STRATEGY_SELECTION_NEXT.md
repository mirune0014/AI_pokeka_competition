# Next strategy: certified last-Prize recovery transaction

## Decision and parent

Implement exactly one hypothesis:

`H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS`

At one Prize remaining, reserve and execute the fully public terminal sequence:

`Night Stretcher -> Basic Metal recovery -> Active attachment -> Boss's Orders -> unique KO-able Bench target -> Metal Defender`.

H2 is a direct child of exact historical-Silver:

- `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- `deck.csv`:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

H1 submission `55064711` is an unstacked sibling and is not an implementation
input.

H2 outranks the higher-Prize Boss and non-KO candidates because it converts an
exact public same-turn win; those alternatives remain nonterminal.

## Root-verified positive

Replay:

`autonomous_gold_20260715/evidence/live_54927163_refresh_20260729_0344/episode_88017509_replay.json`

SHA-256:
`3E828609FEF02D5D8AFA240D9E1F89C27670837A03595446062EC13F7FD62908`.

At row `114`, seat `1`, turn `12`:

- both players have exactly one Prize remaining;
- our Active is evolved Archaludon ex `190#67`, 300 HP, with Basic Metal
  `8#93` and `8#118`;
- `energyAttached`, `supporterPlayed`, `retreated`, and `stadiumPlayed` are all
  false;
- hand has Boss `1182#100` and Night Stretcher `1097#89`, with no Metal;
- discard has four recoverable Basic Metal: `8#113`, `8#115`, `8#116`,
  `8#119`;
- opposing Active Mega Lucario ex `678#17` has 340 HP and is not KO-able by
  Metal Defender;
- the only opposing Bench Pokemon is Solrock `676#10`, 110 HP, one Prize;
- parent action is Poké Pad `1152#77`, option position `2`;
- Night Stretcher and Boss are legal at the relevant callbacks.

The recorded parent later recovered Duraludon, played Lillie, and lost the
held Boss route. H2 instead has a public, response-free same-turn terminal
sequence. The rule is certificate-based, not episode- or Solrock-specific.

## Public certificate

Arm H2 only at ordinary MAIN when all conditions hold:

1. Our remaining Prize count is exactly `1`.
2. Active is an already-evolved Archaludon ex `190`.
3. Metal Defender `253` lacks exactly one Basic Metal and becomes legal after
   one Basic Metal attachment.
4. Active has no public condition or effect making the attack probabilistic
   or illegal.
5. Manual attachment is unused.
6. No Basic Metal is already in hand.
7. A legal Night Stretcher `1097` is in hand.
8. At least one Basic Metal `8` is a legal Night Stretcher selection from the
   public discard.
9. Boss `1182` is in hand, is legal, and Supporter is unused.
10. The current opposing Active is not a deterministic final-Prize Metal
    Defender KO.
11. Exactly one opposing Bench Pokemon is a deterministic Metal Defender KO
    after Boss, after all public immunity, Weakness, Tool, Stadium, and damage
    modifiers.
12. That target yields the remaining Prize.
13. No retreat, evolution, Ability, search, draw, coin result, hidden card, or
    opponent action is required.
14. Every component is public and available in the current turn.

Multiple certified Bench targets fail closed in v1.

## Precedence

1. Existing immediate terminal Attack or already-complete terminal Boss route.
2. Existing hard legality, immunity, and engine-terminal rules.
3. H2 complete transaction.
4. Legacy item, recovery, attachment, Supporter, and attack scoring.

H1 and the separate direct-final-Prize overlay are absent.

## Transaction

Snapshot:

`(seat, turn, Prize counts, Active id/serial/HP/Energy, Night Stretcher serial, eligible Metal serials, Boss serial, original opposing Active serial, target serial/HP/Prize value, attack id, public modifiers)`.

Stages:

1. `ARMED`: choose stored Night Stretcher.
2. `RECOVERY_SELECT`: only after effect confirmation, choose stored Basic Metal.
3. `METAL_RECOVERED`: only after that serial is observed in hand, attach it to
   the stored Active.
4. `ATTACHED`: only after Active publicly satisfies Metal Defender, choose
   stored Boss.
5. `GUST_SELECT`: choose the stored unique target serial.
6. `TARGET_CONFIRMED`: after that serial is Active, revalidate final-Prize KO
   and choose Metal Defender.
7. `DONE`: clear on attack confirmation, terminal result, turn end, or new
   game.

A returned action never advances the stage. Only observed public state or log
confirmation advances it.

## Duplicates, reset, and rollback

- For semantically equivalent recoverable Metals, store the lowest card serial
  and then choose the lowest legal option position.
- For multiple legal Night Stretcher or Boss copies, choose lowest serial.
- For duplicate options of the stored action or serial, choose lowest legal
  position.
- Multiple distinct winning Bench targets do not arm.
- Repeated callbacks return the same semantic action without double advance.
- Reset on deck request, new game, result, turn/seat change, confirmed attack,
  or exception.
- Before Stretcher confirmation, a mismatch clears H2 and delegates to exact
  parent.
- After a card is consumed, rollback cannot undo it. Clear and delegate from
  actual current state if the recovered serial disappears, attachment fails,
  Boss becomes illegal, target changes, attack legality/damage fails, or an
  unexpected callback occurs.
- Never retain state across games, seats, or turns.

## Required positives

- Reconstruct `88017509:114` through the exact engine and finish:
  `1097 -> Metal 8 -> attach to 190#67 -> 1182 -> 676#10 -> 253`.
- Repeat with permuted option order.
- Repeat with changed serials.
- Repeat with a different unique public Bench Pokemon satisfying the same
  terminal certificate.
- Repeat every callback and prove idempotence.

## Required negatives

Remain parent-identical at:

- `88457867`: H1 ready-response threat;
- `87825800`: higher-Prize Boss arbitration;
- `88584180`: Metal already in hand without this last-Prize certificate;
- `88660007`: Alloy/non-KO continuity;
- `88507294`: promotion/investment preservation;
- `88247531`: Bench-damage evolution;
- `88643491`: remote Ogerpon hierarchy;
- `87996118` and `88602602`: non-ex 120 breakpoint.

Also fail closed when Prizes are not exactly one; attachment or Supporter is
used; Metal is already in hand; Stretcher, recoverable Metal, or Boss is
missing/illegal; Active is not evolved Archaludon ex or not exactly one Metal
short; a direct final-Prize attack exists; current Active becomes the terminal
KO without Boss; zero or multiple certified Bench targets exist; target
survives/is protected/yields insufficient Prizes; any step needs hidden
access, draw, search, evolution, retreat, or chance; or Lillie already consumed
the Supporter.

## Forbidden generalizations

Do not implement a generic last-Prize planner, generic resource reservation,
Pokemon recovery, Poke Pad/Ultra Ball/Lillie/Explorer/evolution/retreat/Alloy
planning, higher-Prize Boss arbitration, non-KO preservation, other attackers,
episode/opponent/seed/index rules, hidden-hand inference, replay imitation, or
an H1 stack.

H2 owns only the six semantic actions in its certified terminal chain.

## Verification and evaluation

- Reverify exact parent/deck hashes.
- Shadow the complete latest replay corpus.
- Primary first difference must be `88017509:114`, parent Poké Pad versus H2
  Night Stretcher.
- Reconstruct the changed continuation independently in the exact engine; do
  not imitate the recorded continuation.
- Require 100% trigger-external equality and root inspection of every natural
  trigger.
- Test both seats, option permutations, duplicates, repeated callbacks, every
  rollback stage, resets, exceptions, legality, and mandatory counts.
- Require zero invalid actions, exceptions, stale transactions, and max-step
  hits.
- Run the same frozen 200 historical-Silver plus 560 adjacent both-seat,
  identical-seed schedule used for H1.
- Require exact schedule/duplicate equality, zero command/action/max-step
  faults, zero baseline-win/H2-loss flips overall and in every seat,
  panel, and opponent/seat cell, and causal classification of every difference.

A structurally clean neutral local result may permit one exploratory live probe
only after the three-hour H1 checkpoint and full H1 causal review. It remains
safety evidence, not strength evidence. H2 must be packaged from exact
historical-Silver and use one separate slot.
