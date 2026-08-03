# Rule 7 strategy selection

Date: 2026-08-03 JST

Decision: **SELECT**

Rule ID: `PARENT_TURBO_FLARE_EXACT_PRIMARY_THEN_ONE_BACKUP_TRANSACTION_V1`

## Selected hypothesis

On Turbo Flare `965` `ATTACH_TO` and `ATTACH_FROM` callbacks only, complete exactly one currently visible Bench attacker before assigning any remaining Energy to at most one backup. Remove the old threat graph, future evolution projection, Prize evaluation, wrapper, and score logic.

## Frozen parent

- Parent: `autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`
- Parent `main.py` SHA-256: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

Only candidate `main.py` may differ. Keep one `agent`, one `_resolve`, one shared owner, one parent call per callback, and the existing six-field proposal. Silver scorer, deck, and non-`main.py` package files remain unchanged. UNKNOWN returns the current parent action.

## Exact ready roles

Only these current printed attacks count:

1. Archaludon ex `190` -> Metal Defender `253`, three Metal;
2. Archaludon `840` -> Coated Attack `1212`, three Metal;
3. Duraludon `169` -> Raging Hammer `224`, two Metal plus one Colorless, payable by three Basic Metal.

Hammer In `223` at one Metal is a legal fallback, but is not Rule 7 readiness. Duraludon is completed at three Basic Metal. Future evolution cards and draws are ignored. Benched Cinderace is not a recipient role.

## Activation

All conditions are required:

- unresolved game and shared owner empty;
- exact Turbo Flare `ATTACH_TO` context;
- effect source is the same physical Active Cinderace `666`;
- the current-turn public log contains the same serial using Turbo Flare `965`;
- Turbo Flare name, text, damage 50, and Colorless cost match frozen metadata;
- `minCount=0` and `0 <= maxCount <= 3`;
- parent action is legal for the current options;
- Bench targets, card IDs, serials, current attached Energy, and offered Energy serials are exact;
- offered Energy are unique physical Basic Metal `8` cards only;
- recipient Energy are Basic Metal only and no unknown cost modifier exists.

Do not change MAIN attack selection or arm a pre-attack watch. Any unsupported Pokémon, special Energy, unknown modifier, duplicate physical serial, or malformed binding returns the parent.

## Allocation

For each supported non-ready target, compute `deficit = 3 - current Basic Metal count`.

1. Primary candidates require `1 <= deficit <= visible offered Energy count`.
2. Choose primary by `deficit ascending`, then fixed role order `190/253`, `840/1212`, `169/224`, then target serial ascending.
3. Assign exactly `deficit` Energy to primary before any other target.
4. Only after primary is complete, choose one different backup with the same ordering.
5. Give the backup `min(remaining, backup deficit)` Energy. It may remain incomplete, but no third target may receive Energy.
6. Never exceed a target's deficit. Do not attach to an already ready target.

If Bench is empty or all supported targets are already ready, choose legal `[]`. If no primary can be completed with the visible offered Energy, do not start and return the parent.

Bind physical Energy by serial ascending: primary first, backup second. If the parent selected the same useful count, preserve its physical Energy copies. If reducing the count, prefer the lowest parent-selected serials, then the lowest exposed serials. A serial-only difference with identical count and target assignment is not allowed.

## Transaction

```text
ENERGY_SET_EMITTED
-> TARGET_EMITTED[energy_serial]
-> ATTACH_CONFIRMED[energy_serial]
-> ...
-> CLEAR_TO_CURRENT_PARENT
```

Freeze the `energy_serial -> target_serial` mapping at `ATTACH_TO`. Start the shared owner even when the selected Energy action equals the parent because target concentration still requires ownership.

Each `ATTACH_FROM` callback selects only the target mapped to `contextCard` Energy serial. Advance only after the next public callback proves that Energy moved to the expected target. At completion, recheck primary readiness and every target allocation cap, clear the owner, and use the once-computed current parent action.

For a legal zero selection, use `ZERO_EMITTED`; return `[]` on identical retries and clear only after effect resolution. Never restore a pre-effect snapshot. Never retain Rule 7 across turns.

## Duplicate and option order

- Bind Energy and targets by serial, never by option order.
- Identical semantic retry returns the same action without stage advancement.
- Equivalent UI duplicates use the lowest position.
- Conflicting meanings for one serial, duplicate physical serials, or mandatory-count conflict fail closed.
- `ATTACH_FROM` order may vary; use the context Energy serial to find its frozen target.
- Seat, turn, result, source, target, or transition discontinuity clears to the current parent.

## Focused fixtures

1. Complete each `190`, `840`, and `169` from zero, one, and two Basic Metal to three.
2. One-Metal Duraludon receives two Energy and becomes Raging Hammer ready.
3. Complete primary, then assign the remainder to exactly one backup.
4. Never allocate to a third target or beyond readiness.
5. Empty Bench and all-ready Bench select `[]` and recover.
6. Insufficient visible Energy to complete any primary returns parent.
7. Duraludon allocation is unchanged by the presence or absence of evolution cards.
8. Benched Cinderace, unsupported Pokémon, special Energy, and unknown modifier return parent.
9. Both seats, duplicate retries, option permutations, wrong source, target loss, and turn/result changes.
10. Attachment confirmation is required before progression.
11. Rule 1/4/5 tests remain passing; both-seat smoke has zero faults and no max-step hit.

## Shadow classes and rejection

Allowed differences:

- `TURBO_PRIMARY_EXACT_COMPLETION`;
- `TURBO_SINGLE_BACKUP_REMAINDER`;
- `TURBO_USEFUL_ENERGY_COUNT_REDUCED`;
- `TURBO_ZERO_NO_RECIPIENT`;
- `TURBO_TARGET_CONCENTRATION`.

Record source, Energy serial, target serial, role attack, starting Energy, deficit, allocation, and parent/candidate semantic actions.

Reject for incomplete primary allocation, overattachment, a third recipient, nonempty selection on an empty Bench, evolution-based Duraludon justification, non-Turbo difference, stale/double owner, illegal action, exception, clearly harmful first difference, fixed160 gains below regressions, or any cell three wins below the parent.

If shadow plus fixed160 has zero natural starts, record `DEFER-DORMANT` without widening. If starts exist but no candidate-controlled transaction completes, record `REJECT` as incomplete.
