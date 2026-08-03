# Rule 7 controlling amendment: final exact target release v1

This amendment controls only the Rule 7 transaction lifecycle at the real
engine's terminal callback boundary.  It does not change the frozen Rule 7
activation, supported roles, allocation priority, Energy selection, caps, or
fail-closed conditions.

## Verified engine contradiction

The real engine does not call the agent again in the same turn after the final
Turbo Flare `ATTACH_FROM` choice.  Therefore the original
`TARGET_EMITTED -> ATTACH_CONFIRMED -> CLEAR` lifecycle cannot observe the final
attachment.  Retaining the owner until the next own callback suppresses the
normal resolver on that callback and can hide Rules 1, 4, or 5.

## Controlling behavior

Rule ID: `RULE7_FINAL_EXACT_TARGET_RELEASE_UNCONFIRMED_V1`.

After emitting the last frozen, exact, legal Turbo Flare target, release the
Rule 7 owner immediately.  Record an unconfirmed terminal emission; never call
it a completed or confirmed transaction.

Immediate release is allowed only when all of the following are true:

- the owner is Rule 7 and selected a nonempty Energy set;
- the callback is an exact valid `ATTACH_FROM` prompt;
- all earlier selected Energy serials have exact log-and-board confirmation;
- the context Energy is the sole remaining unconfirmed selected serial;
- its frozen target is still exact, present, unambiguous, and legal;
- the selected option is the lowest equivalent position for that target;
- the frozen allocation still proves exact-three primary readiness, no
  overfill, at most one backup, and no third recipient.

On that callback:

- create the normal six-field proposal from the verified snapshot;
- clear the shared transaction owner before returning the target action;
- do not add the final Energy to `confirmed_energy_serials`;
- do not invoke `_turbo_completion_exact`;
- do not report `ATTACH_CONFIRMED`, `transaction_complete`, `confirmed`,
  `resolved`, or `complete`;
- report `final_target_emitted=true`,
  `resolution_status=UNCONFIRMED_ENGINE_TERMINAL_BOUNDARY`, the final Energy and
  target serials, expected post-allocation counts and caps,
  `owner_release_reason=turbo_final_target_emitted_unconfirmed`, and
  `owner_after=null`.

An identical final-prompt retry must return the same semantic target under
option reordering without reactivating a transaction owner.  Any passive replay
token must clear on the first nonmatching callback and must allow that same
callback to continue through the normal resolver.  `ZERO_EMITTED` is not
broadened and must not suppress the next own callback.

## Required evidence

Focused fixtures must cover both seats, all three roles and deficits, final
prompt retry/permutation, immediate owner release, and a next-callback Rule 4 or
Rule 5 action that is no longer suppressed.

The frozen fixed160 evaluation must verify every natural final emission against
the next engine state, exact primary readiness, caps, at most one backup, no
third recipient, no stale owner, no next-callback cleanup suppression, and all
ordinary stage gates.  A natural start without any externally verified final
emission is incomplete and rejected.  Zero natural starts remains
`DEFER-DORMANT`; conditions must not be widened.
