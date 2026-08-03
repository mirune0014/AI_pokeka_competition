# Strategy selection — parent-initiated Hero's Cape KO/Prize arbitration v1

## Decision

Authorize a read-only pre-edit actionability census only.
No candidate source edit is authorized.

Hypothesis:

`PARENT_INITIATED_HERO_CAPE_KO_PRIZE_ARBITRATION_V1`

When the once-called exact parent already selects a legal Hero's Cape
attachment, the selected target is correct only if its post-Cape KO, Prize,
public-return, survival, and attack-continuity world is not strictly dominated
by another legal target. If no legal Cape target changes a hard boundary and
one presently legal attack strictly dominates every attach-then-attack world,
the Cape should be conserved and that attack should be taken immediately.

Card identity, raw maximum HP, and the inherited `11000/8000` constants are
not purposes.

## Immutable evidence

- exact parent `main.py` SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`;
- exact deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`;
- 207-replay/209-seat manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`;
- rejected return-relevance root report SHA-256:
  `74307DB1660C13CA1BFDDA9D3A449C853006FB24003A6D5DAFE4BE5B3BFC8903`;
- rejected return-relevance independent audit SHA-256:
  `E5DCD079F492E1A7A6E2340B63CDD8116C10F1B55CFADBE2CB096E0590D86D7A`.

The fixed corpus is the exact manifest-bound
`shadow_corpus_196_prior_plus_11_new` under the 55070349 refresh.

## Scope

Trigger only at a clear ongoing `MAIN` callback where:

- the parent has been evaluated exactly once;
- no owner was live before the call and no owner is live after it;
- the returned parent action is one legal Hero's Cape `ATTACH` role;
- the physical Cape serial and every legal attachment target are public and
  unique;
- at least one actual legal `ATTACK` role exists now.

For the same physical Cape, enumerate every actual legal attachment target.
Project the exact public result: remove the Cape from hand, attach it to the
selected empty Tool slot, and increase both current HP and maximum HP by 100
without changing damage counters. For every legal current attack, recompute
the same public combat/return plan from the projected state. Also compute the
attack-now worlds from the unmodified state.

The census may emit only one of these semantic decisions:

- `APPROVE_PARENT_CAPE`;
- `RETARGET_CAPE` to one uniquely dominant legal target;
- `VETO_TO_ATTACK` when one current attack strictly dominates every Cape
  world while conserving the ACE SPEC;
- `DEFER_PARENT` when any required field is unknown, tied, incomparable, or
  not uniquely emittable.

The shadow must not initiate Cape when the parent did not select it, queue a
later attack, infer hidden opponent cards, reward HP as a scalar, use card
names/IDs as policy value, or acquire transaction ownership.

## Positive and negative boundaries

Positive boundaries:

- Cape changes a certified public return from KO to survival while preserving
  a payable attack;
- Cape changes an exact Prize or terminal-loss result;
- another target crosses such a boundary while the parent's target does not;
- all Cape targets are hard-layer equal, but a current attack wins or advances
  the same Prize result while preserving Cape.

Negative boundaries:

- only HP changes while KO, hits-to-KO, Prize, survival, and continuity do not;
- any relevant return damage/effect, Prize result, or backup is unknown;
- target worlds are tied or incomparable;
- a Tool slot is occupied, the role is not legal, an owner is live, or the
  compared attack is not currently legal;
- the benefit needs a hidden hand, hypothetical gust, or matchup identity.

## Required raw evidence

Persist one callback ledger and one target-world ledger.

Callback rows contain replay/hash, seat, step, turn, snapshot hash, callback
context and bounds, parent action/role validity, owner before/after, Cape
serial and metadata hash, all legal Cape roles, all legal attack roles,
historical public attachment transition, comparison status, hierarchy result,
predicted role, direction, emittability, first hard difference, and errors.

World rows contain callback key, world kind, Cape target identity/serial,
pre/post HP and maximum HP, Tool state, attack ID/role, exact status or
rejection reason, current damage/KO/Prize/win, return source/attack/damage,
return KO/Prize/terminal, hits-to-KO, attacker survival, forced promotion,
next payable attack, ready backup, resource ledger, and the full compact hard
vector.

## Fixed implement/stop gates

- exact 207 replays, 209 target seats, and 25,880 once-called parent
  callbacks; zero manifest mismatch, invalid parent role, duplicate raw key,
  or Cape metadata mismatch;
- at least 40 parent-selected, clear-owner Cape turns across both seats and at
  least 20 replays;
- at least 40 earliest-independent complete target-world comparisons across
  both seats;
- at least 20 uniquely classifiable and emittable turns across both seats and
  at least 12 replays;
- at least 12 predicted first-action differences across both seats and at
  least eight replays;
- at least three `RETARGET_CAPE` and three `VETO_TO_ATTACK`, with both
  directions present in both seats;
- at least three survival/Prize/continuity boundaries and three exact
  finish-or-no-purpose conservation boundaries;
- every predicted difference is later marked `GOOD_CAUSAL`, with zero illegal
  attack, owner violation, unknown-return promotion, identity-only choice, or
  unemittable role.

Any failure gives
`STOP__PARENT_CAPE_NOT_ONE_BROAD_ACTIONABLE_BOUNDARY`.
Thresholds must not be relaxed. Passing every gate authorizes one isolated
Sol-xhigh implementation only; it does not authorize adoption, packaging, or
Kaggle submission.

