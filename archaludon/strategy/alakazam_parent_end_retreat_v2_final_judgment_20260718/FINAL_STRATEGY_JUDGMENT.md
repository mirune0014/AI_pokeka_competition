# Final judgment: parent-END retreat bridge v2

Date: 2026-07-18 JST  
Verdict: **B — reject v2 for packaging/live submission and build one final
strict-prize-lead successor from the exact live parent.**

## Why v2 is not the live probe

Evidence is bound by execution freeze
`C9742441ABA01BAD654867315B4F86396327CF4850C5DC7A994E0145F4E79C21`,
execution report
`F56A05DE8EFBAF28B7AED92037DC70B74BD1A0B8B7F5098E75880131698E1ACC`,
numerical audit
`68C6DB92D3CA6C8423529353877EFE8267426811AAF3C7D28B5E7E66F1246F95`,
root verification
`B58857771AFB648F69D3253FDF813AC331539354E0352CBB34347FD697859D94`,
parent raw tree
`91AFE71E7462F998A722EFAC0F55E7916EDFFD598EA4EA55A0D7567CE73E2272`,
and v2 raw tree
`1DE60F8B0C44FACAB5655B4F932E0790D0344CA45C923C76C3B469194DEFF84C`.

V2 is mechanically sound: 144 exact paired rows, zero execution/action/
max-step faults, and all ten first differences are finalized parent END to
same-turn `RETREAT -> payment -> Alakazam -> Powerful Hand KO`. It improves
`84 -> 85`, with two gains and one regression, and passes total, seat, block,
Historical-Silver, and ordinary opponent floors.

It nevertheless fails two frozen safety gates: Alakazam-Rmy is `7 -> 6`, and
the prior Rmy regression is not preserved. This is a deterministic game-plan
defect, not an unexplained fixed-panel fluctuation. At Rmy order 144 the agent
has four Prizes to the opponent's three; a one-Prize KO only reaches `3:3`,
spends retreat Energy, exposes the energized Alakazam, and starts a reply
Prize race that loses. Parent END instead wins against the opponent's visible
thin deck. Practical live evaluation does not require perfection, but it does
not justify submitting a known-broken exchange when one general public-state
certificate separates it from the live repair.

The required live `86585479` state is materially different: own/opponent
Prizes are `2:3`, and the one-Prize KO reaches a strict `1:3` lead while
preventing own imminent deck-out. The two fixed-panel gains also produce a
strict remaining-Prize lead. All other nine v2 starts satisfy the same
condition.

## Sole authorized successor

Create
`candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`
directly from the exact live parent
`candidates/alakazam_active_psychic_lone_dudunsparce_survival_v1`, whose
source/runtime/deck SHA-256 are
`FAB47771161EF7F43C9402B58D38FF240C92B6A2B77FFA6B925DFEA7F990D033` /
`9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
Do not stack onto or patch v2 in place.

Port the audited v2 END-gated atomic transaction unchanged. Add exactly one
semantic START certificate after the existing public target-Prize calculation:

`post_ko_prizes < opponent_prize_count`.

Here `post_ko_prizes = own remaining Prizes - public target Prize value`, and
`opponent_prize_count` is the opponent's current public remaining-Prize
count. Require both counts and the target Prize value to be public, integral,
and nonnegative. Freeze both counts in the latch and recheck the strict
inequality before Powerful Hand; any mismatch fails closed to the exact
parent. A game-ending KO naturally passes because `post_ko_prizes == 0` in a
live game. Add no opponent, card, episode, seat, seed, deckout, or turn
predicate.

This rule expresses the complete resource/prize trade: only spend the retreat
payment and expose the sole ready attacker when the certified KO wins the
remaining-Prize initiative. If it merely ties or leaves the agent behind,
retain parent END and its disruption/deck-clock plan.

## Focused implementation boundaries

Require all v2 compile/import/legal-60, repeated-callback, exact payment,
SWITCH/TO_ACTIVE, stale-state fail-close, inherited-latch, 707-callback live
retention, and both-seat package-smoke checks, plus:

1. `86585479`: preserve S142 Boss and S143 target; at S144 verify
   `2 - 1 = 1 < 3`, then complete the exact atomic route.
2. Rmy order 144: verify `4 - 1 = 3` is not `< 3`; return the exact parent END,
   never populate the new latch, and retain the parent win.
3. Oselcoun order 34 and Kangaskhan/Crustle order 140: the strict certificate
   must pass and both exact gain routes must complete.
4. Replay all ten v2 activation boundaries: exactly nine pass and the Rmy tie
   fails. Test equality, still-behind, malformed/negative Prize values, and a
   game-ending KO as direct fail/pass controls.
5. Every inherited Active-Psychic, lone-Dudunsparce, live-win, and ordinary
   non-END parent boundary remains unchanged.

## Evaluation and permission

The successor may reuse the exact frozen parent summaries/traces and fixed
144-key schedule SHA-256
`4271E31503F37EFE4B1BBB9ED2D3569D79D9C1E9B2A20387CCAC131F28346010`.
It must execute a fresh candidate-only 144 rows under its own frozen source;
no v2 candidate row may be reused. No 1,440-game broad run is required.

Because the new predicate is a strict subset of v2, correct isolation has a
deterministic expected boundary: 135 whole-game parent-identical traces, nine
parent-END atomic routes, `86/144` wins, P0/P1 `45/41`, known/fresh `44/42`,
two gains (orders 34 and 140), zero regressions, Rmy `7/16`, Oselcoun `8/16`,
Kangaskhan/Crustle `10/16`, and Historical-Silver `8/16`. Require those exact
results, 144/144 clean execution, zero errors/max-steps, and no unrelated
first difference.

**Permission:** v2 source `B6D1818...` is rejected and must not be packaged or
submitted. V3 is authorized for isolated implementation and fresh
candidate-only fixed-144 evaluation. If the exact boundaries above pass,
permit one user-authorized practical live probe after package verification
and the root's immediate Kaggle quota/status/replay refresh.
