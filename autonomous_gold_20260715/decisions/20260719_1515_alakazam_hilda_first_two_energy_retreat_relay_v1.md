# Hypothesis freeze: Hilda-first two-Energy retreat relay v1

## Decision

Select `alakazam_hilda_first_two_energy_retreat_relay_v1` as one isolated exact-v3 sibling for a pre-implementation Phase-A feasibility audit. Do not implement, package, evaluate, or submit it unless every frozen Phase-A minimum below passes.

The candidate parent is `candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3` with source SHA-256 `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`, runtime SHA-256 `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`, and deck SHA-256 `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

## Evidence basis

- In live loss `86797929`, the live policy and exact-v3 returned identical actions on all 67 active callbacks.
- At ordinary MAIN step 32, exact-v3 attaches Telepath Psychic Energy `s119` to Active Shaymin `s82` for retreat, then promotes an unenergized Alakazam. Hilda subsequently exposes Dudunsparce `s78` and Enriching Energy `s122`; the first Powerful Hand does not occur until turn 8.
- The fixed 144 compact traces contain exactly 34 coarse rows where the evaluated exact-v3 player selects a Psychic-Energy attachment to an Active support while Hilda is visible and Bench Kadabra or Alakazam exists. This is only a census shortlist, not positive evidence.
- The prior recycle-backed draw-budget corridor failed Phase A at `0` fully certified opportunities and `0` complete chains; it must not be revived or stacked here.

## Frozen public behavior contract

At ordinary MAIN, compute exact-v3 first. Override only when all of the following are public, unique, and complete:

1. Exact-v3 uniquely finalizes attaching a visible Telepath Psychic Energy to an old, unstatused Active one-Prize support solely to pay a publicly exact retreat cost of one.
2. One unique, complete, unenergized Bench Alakazam can legally receive that Telepath; the ordinary Energy attachment is unused.
3. One unique Hilda play is legal, no exact-v3 latch or same-turn attack/terminal route exists, and every own Pokemon in play is one-Prize.
4. A conservative public damage calculation for every currently Energy-paid opposing attacker, including visible modifiers, Weakness, Resistance, and status damage, is strictly below the Active's remaining HP. Any variable or relevant unknown effect fails closed.
5. Public deck accounting proves Hilda has at least one eligible retreat-paying Energy in deck: compatible unseen copies must exceed the number that could be hidden in Prizes.

Transaction:

- Play Hilda first.
- Delegate Hilda's evolution choice to exact-v3.
- At Hilda's Energy callback, proceed only if exact-v3 publicly selects one serial-distinct Energy `e2` that can pay the Active's one-Energy retreat. Otherwise clear and delegate.
- After exact Hilda resolution, attach the recorded Telepath to the recorded Bench Alakazam.
- Across exactly one opponent turn, permit only exact-v3 actions that leave the recorded Active, Alakazam, Telepath, and `e2` unchanged; otherwise end the current turn or clear/delegate as the callback semantics require.
- On the next own turn, revalidate every serial, zone, HP/status, attachment, opponent board/damage, target, deck floor, and parent latch. Attach `e2` to the Active, pay retreat with exactly that serial, promote the Psychic-ready recorded Alakazam, and choose legal Powerful Hand.
- Enriching Energy additionally requires exact draw-count and deck-floor verification.
- Any disruption, KO, switch, Energy removal, hand loss, ambiguity, unexpected callback, or incomplete post-first-difference plan clears the relay and delegates. An incomplete exposed transaction is a semantic defect and cannot support promotion.

No hidden backup-readiness or opponent-policy claim is allowed. Corrected episode `86778139` locators 108/110, 128, and 141/143 are mandatory negatives.

## Frozen Phase-A gate

Inspect only the 34 fixed-trace coarse rows and live `86797929` step 32. Reconstruct the original fixed games on their exact engine, agents, decks, seats, and seeds; require byte/canonical equality to the checked compact traces at every reconstructed step. Phase A passes only with all of:

- at least 8 fully certified fixed starts;
- both seats, both fixed blocks, and at least 4 opponents;
- at least one Alakazam-mirror row and one Historical-Silver row;
- at least 2 starts in each seat and each block;
- at least 4 rows where the same reconstructed Hilda branch makes exact-v3 publicly select compatible serial-distinct `e2`;
- zero certified rows with an existing same-turn attack/terminal route or a publicly payable retaliation KO;
- live step 32 is one complete positive certificate.

Any failed threshold stops work before implementation. Do not relax the survival, Silver, seat, block, or completion requirements.

## Mandatory negatives

Exact-v3 identity is required when any of the following holds: ready current attacker; same-turn attack or KO; retreat cost not one; Active already Energy-ready for an attack; only Bench Kadabra; energized or ambiguous Bench attacker; any own multi-Prize Pokemon; absent/ambiguous Hilda; no publicly guaranteed compatible Hilda Energy; attachment already used; status or public retaliation KO; unknown damage/effect; any parent latch; final-Prize route; malformed serial/effect mapping; or any corrected `86778139` locator.

## Frozen Phase-0 floors if Phase A passes

- total at least `89/144`, with at least `3` paired gains and `0` paired regressions;
- P0 at least `46/72`, P1 at least `42/72`;
- known at least `45/72`, fresh at least `43/72`;
- Historical Silver at least `9/16` with a causal gain;
- Rmy at least `8/16`, combined mirrors at least `16/32` with a gain;
- no opponent decline; Great Tusk at least `4/16`; Kangaskhan at least `10/16`;
- at least 6 natural starts and 4 completed relays across both seats and blocks;
- at least 2 gains caused by one additional Powerful Hand or Prize;
- zero action errors, max-step hits, duplicate mismatches, incomplete-plan regressions, schedule/hash drift, or semantic defects.

If Phase A fails, retain exact-v3, classify the 34 rows by first failed predicate, and ask the strategy judge for one new isolated direction. Do not implement broad clock code or stack any rejected corridor.
