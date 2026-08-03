# v1 runtime transaction completion contract

## Status

This contract fixes a runtime-compliance defect in
`alakazam_newdeck_v1_package_compliance`.

It does not authorize a new strategy, a deck change, a matchup branch, or any
v2 continuity behavior.

The source candidate remains immutable.

- Source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_compliance`
- Source policy closure:
  `89F8315A4B0A8B25D8CAAF12DBBB88012DD9C5AC278E1D8455DDD0298ECDF69C`
- Destination:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified`
- Raw deck SHA-256:
  `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
- Normalized deck hash:
  `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69`

## Triggering evidence

Comparison B raw rows and all numerical aggregates are internally consistent,
but the candidate does not own its live child prompts.

- Paired rows SHA-256:
  `BF4B71412A38D65383CD48892B9E49A795CB2779DDCAF0E7CBEE0C9B8EA46008`
- Formal v1 aggregate SHA-256:
  `8D9B78D0C1070F0D8BEB412AC101F383EDC87DED0B62199B166EA65D32CBED4B`
- Formal v1 callback SHA-256:
  `EC9579E8F31B104C83F1C479474188CE9EE59752DCD89552D0E532A9D5BEB5C4`

The 45,466 callbacks contain 459 v1 transaction starts.

| route | starts | rule-owned callbacks | complete | abort |
| --- | ---: | ---: | ---: | ---: |
| Alakazam exact recovery | 31 | 93 | 31 | 0 |
| Boss terminal KO | 59 | 59 | 0 | 59 |
| Enhanced Hammer | 147 | 147 | 0 | 147 |
| Lana's Aid | 13 | 13 | 0 | 13 |
| Xerosic's Machinations | 209 | 209 | 0 | 209 |

All 428 aborts occur after an irreversible MAIN `PLAY`.

Boss, Hammer, and Lana lose ownership on the immediate child prompt.

Xerosic loses ownership on the immediate verification callback.

Therefore zero invalid actions, exceptions, timeouts, and generic fallbacks do
not satisfy the v1 compliance contract.

## Single correction hypothesis

`V1_RUNTIME_OWNED_TRANSACTION_COMPLETION`

> Preserve every certified MAIN-card selection from the source candidate, but
> handle an in-progress v1 transaction before invoking the inherited v0
> delegate. Rebind the exact live child prompt or verification state, complete
> the transaction explicitly, and call v0 only after completion or for a
> pre-irreversible fallback.

The card-selection conditions and their precedence are frozen.

The fix may only change transaction ownership, public-delta validation,
telemetry, and tests required to prove those properties.

## Required ownership order

1. Validate raw/parsed agreement and duplicate rebinding.
2. Preserve an already active inherited parent owner that predated v1.
3. If a v1 transaction is active, process its child or verification stage
   before calling the v0 delegate.
4. Return a certified v1 child action without calling v0.
5. On successful verification, close the v1 transaction, then obtain the
   current v0 action without allowing it to retroactively own the completed
   child.
6. Before any irreversible v1 action, an unprovable route may restore the
   parent state and return the exact v0 action.
7. After an irreversible v1 action, an unexpected child or verification
   failure must emit `V1_IRREVERSIBLE_ABORT_FAULT`; it must not be counted as a
   normal fallback or a completed route.

An in-progress v1 transaction must not be discarded merely because calling v0
on the same callback would create or mutate an inherited transaction.

## Exact public-delta rules

The implementation must diagnose and fix the shared live mismatch without
loosening the proof to card IDs or counts alone.

For the played card and every child:

- preserve the physical card serial;
- compare discard and hand changes as an exact one-card multiset delta while
  preserving multiplicity;
- validate turn, acting player, action-count delta, supporter/stadium flags,
  deck counts, prizes, bench limits, status flags, and protected public
  serials;
- accept only the documented engine ordering semantics;
- freeze the full `SelectData` envelope:
  context, select type, effect, contextCard, area, player, min/max, stable
  option key, and physical target serial;
- reject ambiguous option rebinding;
- verify every rule-specific postcondition before completion.

The implementation must expose a predicate-level diagnostic reason in tests,
but must not branch on opponent name, seed, replay ID, or saved action.

## Required complete chains

### Boss's Orders

`MAIN PLAY -> SWITCH child -> same frozen Powerful Hand -> post-attack verify`

The switch target must be the certified physical serial.

The promoted Active must have poison, burn, sleep, paralysis, and confusion
cleared.

### Enhanced Hammer

`MAIN PLAY -> DISCARD_ENERGY child -> current Powerful Hand or certified stop
postcondition -> verify`

The exact Pokémon serial, energy serial, energy area, energy index, and
discard delta must be checked.

### Lana's Aid

`MAIN PLAY -> TO_HAND child -> recovered serial multiset -> current Powerful
Hand -> verify`

All selected rows and serials must remain within the frozen allowlist.

### Xerosic's Machinations

`MAIN PLAY -> immediate public verification -> current Powerful Hand`

The opponent hand count, opponent discard multiset delta, own supporter delta,
and hand floor must all be verified before closing the transaction.

### Alakazam

The existing 31/31 complete live shape is the non-regression reference.

Its action, child ownership, Ability binding, attack, and completion telemetry
must remain unchanged.

## Removed-card instrumentation

The semantic denylist remains exactly:

`{142, 858, 1156, 1161, 1264}`.

Every callback must emit a known removed-rule audit result.

- `removed_rule_hit_status=KNOWN`
- an empty hit list means known false;
- a non-empty hit list must identify the owner and blocked route;
- no empty or unknown status is allowed.

The instrumentation must not change the selected action.

The existing three equal denylist definitions may be consolidated only if all
imports, behavior, and inherited tests remain exact.

## Engine provenance

The prior spec used a cache-inclusive tree hash and is not reproducible after
Python cache generation.

The authoritative source/runtime closure excludes `__pycache__`, `.pyc`, test
artifacts, and generated logs.

For the current seeded engine, the frozen 11-file source/runtime hash is:

`466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`.

The next evaluation spec and suite manifest must bind this hash and record the
exact Python executable and version.

## Required tests

- The immutable source candidate and its 106 tests remain byte-identical, and
  all 106 tests pass against that source as the historical control.
- The destination preserves every inherited test scenario. The copied shared
  call-count assertion may be parameterized only to correct the known
  contradiction: pre-irreversible/nonfire callbacks call v0 exactly once,
  while v1-owned child and verification callbacks call v0 zero times.
- The old blanket assertion that every callback calls v0 once is explicitly
  superseded because it encodes the runtime-ownership defect being repaired.
- Full engine prompt-chain tests cover at least one live-positive state for
  Boss, Hammer, Lana, Xerosic, and Alakazam.
- Each chain has a malformed-envelope negative fixture.
- The v0 delegate call count is zero on owned child callbacks.
- Every positive chain ends in `V1_TRANSACTION_COMPLETE`.
- Every positive chain has zero `V1_TRANSACTION_ABORT` and zero
  `V1_IRREVERSIBLE_ABORT_FAULT`.
- Pre-irreversible nonfire preserves v0 action, Reason Code, transaction,
  duplicate cache, and parent mutable state.
- Repeated identical callbacks rebind the same physical option.
- Removed-rule status is known on every callback.
- The destination deck is byte-identical to the source deck.
- The source candidate and all earlier frozen directories remain unchanged.

## Pre-evaluation hard gate

Comparison B may be rerun only after:

- compilation passes;
- inherited and new tests all pass;
- the five positive full chains complete;
- source-v1 nonfire equality passes;
- no post-PLAY abort is accepted as a legal fallback;
- no strategic candidate condition or precedence changed;
- a fresh destination closure and changed-file hashes are recorded;
- a fresh adapter and source-only engine provenance amendment are frozen.

