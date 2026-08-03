# v1 runtime transaction completion fixture amendment

## Status

This amendment is limited to two inherited trace-only fixtures in the
destination candidate.

The immutable source candidate and its tests remain byte-identical.

## Defect

The two destination fixtures at `test_v0_port.py` originally omitted required
`State` and `SelectData` fields, including `minCount`, `maxCount`, and physical
card serials. They could exercise trace formatting with the historical wrapper,
but they could not be parsed or certified by the stricter runtime-completion
boundary.

Treating their delegated actions as legal without those fields would weaken the
new fail-closed action contract.

## Authorized correction

The destination copy may complete only the missing observation fields:

- full `State` defaults required by the strict parser;
- full `SelectData` envelope;
- physical hand and option card IDs, serials, and owners.

The following are frozen and must not change:

- option count, type, index, and order;
- delegated action;
- Reason Code;
- relevant added-card classification;
- every assertion and scenario meaning.

This is fixture strictness, not a policy change or a weakened test.

## Verification

- immutable source tests: 106/106;
- destination tests: 120/120;
- destination `test_v0_port.py` SHA-256:
  `21229B818127FE7B62F08D915231C17485041618205AEE78D47993DE0B35EC67`;
- destination policy closure:
  `B8E4F9C50B41AE9B62FA726E7BD124E44E0A36252E80C0182576BFEB9EE2BFEF`.

