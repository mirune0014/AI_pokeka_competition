# Strategy selection — relevance-bound public return completeness v1

## Decision

Authorize a read-only cause census only.  No source edit is authorized.

Hypothesis:

`RELEVANCE_BOUND_PUBLIC_RETURN_COMPLETENESS_V1`

A public card or effect may make the return/backup graph unknown only when it
can affect an actually reachable public route or a combat/readiness consumer.
An attack-route probe that fails on unsupported attack semantics may be
classified as `EXACT_LOCAL_NO_ROUTE` only when exact energy payment proves
that the source has no attack payable now for that route tier, no attack that
becomes payable with exactly one ordinary Basic Energy attachment for the
one-attachment tier, and no unresolved global or target-wide effect.  The
shadow may turn only that failed route enumeration into an empty exact route
set.

Hidden resources, uncertain effect scope, reachable unsupported attacks,
public switch or evolution access, post-action projection failures,
non-unique replies, and backup-oracle failures remain unknown.  The shadow
adds no card semantics, assumes no Energy in hand, chooses no opponent policy,
and changes no score hierarchy.

## Immutable evidence

- parent `main.py` SHA-256:
  `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`;
- 207-replay/209-seat manifest SHA-256:
  `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`;
- frozen Jumbo opportunity CSV SHA-256:
  `093573F0C9D5E47EF6EA5E8277E6DD137078D06C07FC20BF8241606B14CCB1D9`;
- frozen Jumbo audit SHA-256:
  `1AD2E6036CCD988D478E2D6138E323D41712978FF5E564B158FAB6FEAF52C48D`;
- Neutralization root report SHA-256:
  `6BCC21DEB44E78A8ACF6E3495047DD6A62CE83C0C5C7D7822A930AAEB8462734`;
- Neutralization numerical audit SHA-256:
  `0335738B6EF85238143E834BFF62BFA66ABEE1072DFD413742E913FCC7941C39`.

## Required census

Rehydrate exactly the frozen 225 `RETURN_UNKNOWN` rows and 254 exposed attack
alternatives while replaying the exact parent once at every selectable
callback.  Preserve source identity and zone, route tier and public access
sequence, current payment, every Basic Energy type that makes the attack
payable with one attachment, skill/tool scope, exact metadata hashes, the
unaggregated threat blocker, and the direct plan fields.

Blockers must be assigned once to one of:

- reachable ready now;
- reachable after one attachment;
- reachable through free promotion or payable retreat;
- reachable through exact public evolution or switch;
- global, target-wide, or uncertain effect scope;
- exact local no-route;
- post-action projection or callback;
- backup-oracle or non-unique-reply failure.

The relevance-only shadow suppresses only exact local no-route attack-route
failures and recomputes the same plan and hard lexicographic hierarchy.

## Fixed implement/stop gates

- exactly 225 rows and 254 attack alternatives;
- 207 replays, 209 target seats, 25,880 single parent calls, with zero invalid
  action, manifest mismatch, or duplicate raw key;
- every blocker assigned exactly once with exact metadata provenance;
- one bounded cause family covers at least 40 earliest-independent turns,
  both seats, and 15 replays;
- at least 24 turns become fully exact, both seats, and 12 replays;
- at least 12 hard plan-ranking differences, both seats, and eight replays;
- at least eight predicted legal first-action differences, both seats, and six
  replays;
- at least three differences in two of current KO/Prize, terminal-return
  survival, attacker continuity, and ready-backup conversion;
- root marks every predicted difference `GOOD_CAUSAL`;
- zero relevant route suppressed, hidden-card assumption, false terminal
  certificate, or unemittable role.

Any failure gives `STOP__RETURN_UNKNOWN_NOT_ONE_ACTIONABLE_BOUNDED_CAUSE`.
Thresholds must not be relaxed.  Passing all gates authorizes one isolated
Sol-xhigh relevance-gating edit only.  Cornerstone Stance, Power Saver, draw
effects, Boss, and card-action overlays remain out of scope.

