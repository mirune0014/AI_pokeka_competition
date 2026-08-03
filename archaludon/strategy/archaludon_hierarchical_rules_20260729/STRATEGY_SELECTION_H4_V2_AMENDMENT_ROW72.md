# H4 v2 controlling amendment: post-setup row 72

## Decision

Accept `87974582:72` as the eleventh positive for:

`H4_V2_PARENT_ATTACK_ADMISSIBLE_UNIQUE_HIGHER_PRIZE_BOSS_KO`.

Do not add a cooldown, a previous-action veto, a one-arm-per-turn flag, or an
episode-specific exception.

## Root-verified contradiction

The original final-judgment expectation said that the 10 inherited-Attack
differences already present in the H4 v1 shadow would be the complete v2
difference set. Exact sequential replay proves one additional callback becomes
eligible only after v2 correctly delegates the preceding setup action:

- replay `87974582`, seat 0;
- row 71, turn 6, action count 14:
  - exact parent chooses Full Metal Lab `1244#15`;
  - H4 v1 incorrectly chooses Boss `1182#40`;
- row 72, turn 6, action count 15:
  - exact parent chooses Metal Defender `253`;
  - H4 v1's stale row-71 transaction clears and delegates, so v1 did not
    record a row-72 difference.

Under the selected callback-local parent-Attack gate, v2 must delegate row 71,
keep no H4 state, then evaluate row 72 from the actual post-Stadium public
state. Row 72 has both an inherited Attack and a valid H4 certificate.
Suppressing it would require an unauthorized history-dependent exception.

## Exact required behavior

At row 71:

- return the exact parent Stadium action;
- leave `_h4_transaction` empty;
- do not cache the row-71 certificate.

At row 72:

- recompute the exact parent action;
- certify and select Boss `1182#40`;
- target Fezandipiti ex serial `72`;
- target Prize value `2`;
- opposing Active immediate yield `1`;
- stored attack `253`;
- exact target damage `220`;
- snapshot the actual row-72 Stadium and action count.

Repeated row-72 callbacks return the same semantic Boss without advancing the
transaction.

## Revised immutable shadow set

H4 v2 must produce exactly these 11 first action differences:

1. `87670335:111`
2. `87800215:154`
3. `87825800:116`
4. `87825800:124`
5. `87953269:52`
6. `87953269:91`
7. `87974582:72`
8. `88096059:114`
9. `88171291:60`
10. `88399550:91`
11. `88417236:70`

Required split:

- remove all 27 H4 v1 differences whose inherited action was non-Attack,
  including `87974582:71`;
- retain the 10 inherited-Attack differences already present in H4 v1;
- add `87974582:72`;
- no other new difference;
- zero invalid actions and exceptions;
- complete parent equality outside the 11 callbacks.

## Required additional tests

1. Sequential raw test without reset:
   row 71 delegates Full Metal Lab with no transaction, then row 72 arms Boss.
2. Repeated row-72 idempotence.
3. Direct row-72 transaction completion:
   Boss confirmation, target serial 72, attack 253, KO, two-Prize removal.
4. Recorded-replay mismatch after row 72 clears safely without a stale
   transaction.

All other H4 v2 public certificates, transaction rules, and fixed-760 gates
from the final judgment remain unchanged.
