# Rule 6 root verification

Date: 2026-08-03 JST

## Frozen identities

- Accepted parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Candidate `main.py`: `02180DB5EA65356FA85301D7978EF088725FCA241B84EE68B29E102B77655164`
- Shared deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Strategy: `428CBF0B516592AEB1BD7BABA939ADC5E2357F4D4FD53E493C30D9F5C805EBFE`
- Rule ID: `PARENT_POKE_PAD_EMPTY_BENCH_DURALUDON_ONE_METAL_READY_SUCCESSOR_TRANSACTION_V1`

The candidate changes only `main.py`. All twelve other package files are byte-identical to the accepted Rule 5 parent. The Historical-Silver scorer and deck are unchanged.

## Root-executed checks

- Focused plus inherited tests: 35/35 PASS.
- In-memory compile/import verification: PASS.
- Exactly one top-level `agent`, one `_resolve`, one static parent call, and loader-last callable `agent`: PASS.
- Legal deck: 60 cards and one ACE SPEC.
- Candidate cache directories and `.pyc`: zero.
- Both checked smoke summaries are terminal with action errors 0 and no max-step hit.

## Shadow verification

Root reran the frozen current-plus-historical shadow.

- ordered corpus: `B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004`;
- 77 readable replays, 4,262 callbacks;
- Rule 6 starts: 1;
- attributable differences: 1;
- invalid actions, exceptions, and rule faults: 0;
- ready completions: 0;
- whiff emissions/completions: 0/0.

The only difference is episode 89288308, seat 1, step 45. The accepted parent selects Duraludon serial 66 from the Poké Pad reveal, while Rule 6 deterministically selects the lower physical serial 65. Both are the intended card ID `169`. The recorded continuation follows parent serial 66; at step 46 the candidate correctly rejects that counterfactual transition, clears its owner, and returns the current parent action. This is a replay-shadow limitation rather than an illegal action, but it means the natural corpus does not prove a completed successor transaction.

Focused engine-shaped fixtures complete both the successful Pad-to-ready route and the legal empty whiff route in both seats, including retries and option permutations. The fixed160 run must now determine whether an actual candidate-controlled engine path naturally completes. If fixed160 contains no Rule 6 completion or whiff, final judgment must explicitly distinguish safe dormant behavior from an incomplete natural mechanism and must not widen the rule.

## Permitted first-difference classes

- `POKE_PAD_DURALUDON_TARGET`
- `POKE_PAD_DURALUDON_BENCH`
- `POKE_PAD_DURALUDON_READY_ATTACH`
- `POKE_PAD_DURALUDON_WHIFF_EMPTY`

Any other first difference, any loss of the saved current attack, any stale/double owner, or any execution fault rejects the candidate before adoption.

## Evaluation authorization

The candidate passes the implementation-safety gate for the immutable fixed160 schedule. This is not an adoption decision and not a strength claim.
