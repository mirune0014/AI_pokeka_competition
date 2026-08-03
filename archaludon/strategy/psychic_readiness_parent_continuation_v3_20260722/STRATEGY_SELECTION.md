# Frozen strategy: Psychic readiness parent continuation v3

## Exact parent and scope

Implement one rule directly from submitted `alakazam_psychic_attack_readiness_reservation_v2`, policy SHA-256 `C289127BF6457AB3A451CE17017457103013224ED6714A78E8819B90E9F22ABD`.

Fresh destinations:

- `autonomous_gold_20260715/candidates/alakazam_psychic_readiness_parent_continuation_v3`
- `autonomous_gold_20260715/implementation/alakazam_psychic_readiness_parent_continuation_v3`

Only `planner_final_policy.py` may differ from the exact parent. Preserve the deck and all other source files byte-for-byte.

## Selected rule

Readiness owns the scarce Psychic attachment and the narrowly certified H1 mandatory promotion. Discretionary Telepath search and MAIN sequencing remain parent-owned. An intended attack may replace only an exact parent `END`.

### Initial arbitration

Leave initial H0/H1 certification, Energy selection, damage semantics, transient-defense exclusion, parent-owner precedence, and attachment arbitration unchanged.

### Optional Telepath prompt

After the reserved Telepath Energy attachment, when the exact optional Telepath prompt is present:

- return the exact once-called parent action, whether it is `[]`, one Basic, or two Basics;
- never suppress the search and never restore speculative parent state;
- for H0, move passively to `await_post_attach_main`;
- for H1, move passively to `reserved_until_exposure`.

### H0 MAIN arbitration

At the first attack-capable H0 MAIN callback, revalidate the unique reserved attacker, its exact Psychic payment, the current Active target, and the intended strict-positive attack.

- If the exact parent chose the intended attack, return it unchanged and complete the transaction.
- If the exact parent chose `END`, override with the intended attack and await resolution.
- If the exact parent chose anything else—including Boss, Dawn, evolution, Ability, Item, retreat, switch, or another attack—return it unchanged and abort/clear the readiness transaction.

This makes the attachment correction persistent while ceding the rest of the turn to the stronger cumulative parent.

### H1 exception

Retain only the existing exact mandatory-promotion override when all of the following hold:

- the original Active is gone;
- the reserved attacker remains unique and fully exact;
- the prompt is an unowned mandatory promotion;
- the current target still has a strict-positive public outcome;
- no higher-precedence parent owner exists.

If the parent already selected the reserved attacker, return the identical parent action. Once promoted, apply the same H0 MAIN arbitration above. Remove every unconditional promoted-attack continuation.

### State and rollback

- Call the exact parent once for every novel callback.
- Parent-identical pass, complete, and abort retain the complete `parent_post` state.
- Abort clears the readiness transaction.
- Only a valid `END` to intended-attack override or mandatory H1-promotion override restores the complete `parent_pre` state.
- Duplicate callbacks must return the identical cached action without an extra parent call.
- Stale, ambiguous, malformed, higher-owner, or incompletely classified states fail open to the exact parent.

## Breakage-only verification

Local strength is diagnostic and nonblocking under the user's current live-probe policy. Packaging is blocked only by structural failure.

Required focused positives:

- parent Telepath choices of zero, one, and two Basics are returned exactly;
- parent intended attack is returned exactly and completes;
- exact parent `END` becomes the intended attack;
- both-seat exact H1 mandatory promotion remains valid.

Required negatives:

- Boss, Dawn, Dudunsparce evolution, Ability, Item, retreat, switch, and another attack remain parent-identical and clear the transaction;
- stale target, stale Energy, ambiguous options, higher parent owner, transient defense, and post-promotion non-END states fail open exactly;
- duplicate replay causes no mismatch or extra parent call.

Replay all nine current public episodes plus the existing current/historical callback shadow corpus. Every listed Telepath-search, Dawn, Boss, and evolution continuation must equal the internal parent action. Only certified initial attachment forks, exact `END` to attack, and exact mandatory H1 promotion may remain.

Require compile/import, sole-and-last callable loader behavior, legal 60-card deck with one ACE SPEC, cache-free candidate/package, deterministic valid actions, source/runtime parity, both-seat exact engine H0 and H1 paths, and both-seat packaged smoke with zero exceptions, action errors, or max-step hits.

Passing authorizes an exploratory Kaggle repair, not formal adoption.
