# H4 v2 controlling full-corpus amendment

This amendment supersedes the earlier 11-difference row-72 amendment.

## Decision

Accept all four Attack callbacks that become newly visible only after H4 v2
correctly delegates preceding setup actions. The frozen 196-replay sequential
shadow must contain exactly 14 H4 v2 action differences.

Do not add a same-turn cooldown, an "already declined" flag, a prior-card or
prior-action veto, or an episode-specific exception. A delegated non-Attack has
no H4 memory effect. Every later callback is evaluated freshly from the actual
public state.

## Exact 14-key shadow set

All keys are from corpus `historical_54927163_0530`:

1. `87670335:111`, seat 0
2. `87800215:154`, seat 0
3. `87825800:116`, seat 1
4. `87825800:124`, seat 1
5. `87953269:52`, seat 1
6. `87953269:67`, seat 1
7. `87953269:91`, seat 1
8. `87974582:72`, seat 0
9. `88010578:87`, seat 0
10. `88096059:114`, seat 1
11. `88171291:60`, seat 1
12. `88195925:167`, seat 0
13. `88399550:91`, seat 0
14. `88417236:70`, seat 1

Required split:

- retain all 10 H4 v1 differences whose inherited action was Attack;
- remove all 27 H4 v1 differences whose inherited action was non-Attack;
- add exactly four newly exposed post-setup Attack callbacks;
- total H4 v2 differences exactly 14;
- no missing retained key, changed non-Attack key, other new key, exception, or
  invalid action.

## Newly exposed certificates

| Callback | Parent Attack | Boss | Target | Yield | Stored attack |
|---|---:|---|---|---:|---:|
| `87953269:67`, seat 1 | position 7, `253` | position 0, `1182#99` | serial 12, two Prizes | `1 -> 2` | `253`, damage 220 |
| `87974582:72`, seat 0 | position 3, `253` | position 2, `1182#40` | serial 72, two Prizes | `1 -> 2` | `253`, damage 220 |
| `88010578:87`, seat 0 | position 10, `253` | position 2, `1182#38` | serial 72, two Prizes | `1 -> 2` | `253`, damage 220 |
| `88195925:167`, seat 0 | position 4, `253` | position 3, `1182#39` | serial 72, two Prizes | `1 -> 2` | `253`, damage 220 |

Option positions are frozen-row expectations only. Runtime selection must
resolve semantic options dynamically.

## Required sequential tests

1. `87953269`
   - row 66: delegate Duraludon `169#65`; transaction remains empty;
   - row 67: freshly observe inherited Attack `253`; arm Boss `#99`.
2. `87974582`
   - row 71: delegate Full Metal Lab `1244#15`; transaction remains empty;
   - row 72: freshly observe inherited Attack `253`; arm Boss `#40`.
3. `88010578`
   - row 84: delegate Pokégear `1122#25`;
   - row 85: delegate the exact parent callback;
   - row 86: delegate Metal `8#52` attachment to Duraludon `169#4`;
   - row 87: freshly observe inherited Attack `253`; arm Boss `#38`.
4. `88195925`
   - row 166: delegate Hero's Cape `1159#37` attachment to Archaludon ex
     `190#7`;
   - row 167: freshly observe inherited Attack `253`; arm Boss `#39`.

Each positive also requires repeated-callback idempotence, a fresh post-setup
snapshot, direct transaction completion, and safe clearing/delegation when the
recorded next callback follows the parent's Attack rather than the
hypothetical Boss branch.

## Controlling principle

Only an active, already-armed transaction persists. Otherwise:

1. compute the exact inherited action once for the current callback;
2. if it is non-Attack, return it unchanged and retain no H4 state;
3. on every subsequent callback, recompute from the new public observation;
4. if the inherited action is Attack, build a new H4 certificate from that
   current observation.

All other H4 v2 certificates, transaction rules, fixed-760 retention gates,
both-seat engine requirements, and exploratory-live restrictions remain
unchanged.
