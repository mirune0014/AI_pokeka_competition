# Strategy selection: next-turn draw-survival certificate v3

Selected: 2026-07-20 JST  
Judge: dedicated Sol-Ultra strategy worker  
Root decision: reject v2 submission; authorize one isolated v3 implementation and evaluation

## Frozen parent and sole hypothesis

- Parent: `autonomous_gold_20260715/candidates/alakazam_next_turn_draw_survival_certificate_v2`.
- Parent source/runtime/deck SHA-256:
  `D0E0DD3945547446084301B6CBC90648E46550AD7DA7949E9F4AFF59D72E5981` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Candidate:
  `autonomous_gold_20260715/candidates/alakazam_next_turn_draw_survival_certificate_v3`.
- Sole hypothesis: `ENRICHING_DRAW_ZERO_BOSS_LUCARIO_TERMINAL_OVERRIDE`.

V2 is locally clean and matches exact-v3 at `86/144`, compact `37/72`,
`0G/0R`, while recovering both v1 regressions. It is nevertheless rejected
for submission because public live episode `86909242` step 133 shows a known
dominated action: a nonterminal one-Prize KO is selected while a unique
Boss-to-three-Prize same-turn win is publicly certified.

## Strict start certificate

Activate only when every condition holds:

1. Exact MAIN envelope, complete serial-bearing public state, unresolved
   result, and no inherited v1/v2 latch active.
2. Own deck exactly 4, own Prizes exactly 2, attachment unused, supporter
   unused.
3. Frozen v2 selected the unique Powerful Hand option.
4. A state-restored exact-v3 witness selected an exact Enriching Energy
   attachment whose certified projection is `4 -> 0`.
5. Active is a complete, status-free Alakazam with Psychic Energy and
   certified Powerful Hand metadata.
6. Current opponent Active is Hariyama `674`; Powerful Hand is lethal but
   awards only one Prize, hence is nonterminal.
7. Exactly one legal Boss's Orders `1182` option exists and maps to one exact,
   unique hand serial.
8. Post-Boss projected damage is computed as `20 * (handCount - 1)`.
9. Exactly one complete, publicly clear opponent Bench target is Mega Lucario
   ex `678`, has sufficient Prize value to finish the game, and is lethal after
   the Boss hand decrement.
10. Every protected card and Pokemon serial is globally unique.

At the frozen live callback, v2 chooses `[28]` Powerful Hand for 400 into an
80-HP Hariyama. V3 must choose Boss option `[15]`, dynamically freeze Boss
serial 43 and opponent Bench index 2 Mega Lucario ex serial 76, then prove
hand 19 gives Powerful Hand 380 into 340 HP for the final two Prizes. Do not
key on episode ID or hard-code runtime serial values.

## Transaction

1. Start `await_boss_target` by playing the dynamically frozen unique Boss
   option.
2. Require the exact SWITCH prompt with `min=max=1`, the exact Boss
   hand/discard transition, supporter flag change, and otherwise conserved
   state. Select only the dynamically frozen Bench target (live option `[2]`).
3. Enter `await_attack`; require the exact Active/Bench swap log and field
   permutation, unchanged deck/hand, the frozen target now Active, and one
   unique lethal Powerful Hand. Force the attack.
4. Enter `await_resolution`; verify exact attack, damage, KO and final
   two-Prize callback, clear the v3 latch, and delegate Prize selection.

Any mismatch clears only the v3 latch and delegates to frozen v2. Parent state
must be snapshot/restored, and every changed action must pass the
filtered-parent rerun handshake.

## Minimal gates

- Checked-engine positive route reconstructed from `86909242/133` completes
  Boss -> frozen target -> Powerful Hand -> final two Prizes, preserves deck 4,
  and emits no invalid action.
- Negative controls: no Boss, supporter already used, non-Enriching exact-v3
  action, projected deck above zero, insufficient post-Boss damage, ambiguous
  Boss/target, blocked target, or already-terminal current Active are exactly
  byte-identical to v2.
- Current44 shadow: exactly 2,978 callbacks, zero invalid; exactly one v3/v2
  start difference at `86909242/133`; every other callback delegates to v2.
  Retain `86903767/127`, `86901565/153`, `86892228/155`, and `86893328/158`.
- Fixed144: v2/v3 normalized summaries and trace hashes are identical on all
  144 rows; exact-v3/v3 remains `86/144`, compact `37/72`, `0G/0R`; both
  draw-free recovery routes remain wins; all duplicate/error controls clean.

Implementation and evaluation are authorized. Packaging and Kaggle write are
not authorized until all gates are independently verified and the strategy
judge issues a later final submission judgment.
