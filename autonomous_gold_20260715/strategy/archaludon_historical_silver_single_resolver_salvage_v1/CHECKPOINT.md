# CHECKPOINT

Updated: 2026-08-03 JST

## Invariants

- Silver scorer unchanged.
- One final agent; one resolver; one active transaction.
- One rule at a time.
- UNKNOWN returns Silver.
- Failed rules are removed, not patched by stacking another rule.
- Existing artifacts remain read-only.

## Accepted parent

- Rule 1 accepted: `archaludon_historical_silver_single_resolver_salvage_v1`.
- `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Stored exact Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Completed rules

- Rule 1 `EXACTLY_ONE_DURALUDON_SETUP_V1`: accepted as a safe neutral rule.
  - shadow: 9/9 first differences on the intended setup boundary;
  - fixed160: Silver 100, candidate 100, G/R/T 0/0/160;
  - natural starts: 28, seat 0 = 11, seat 1 = 17;
  - execution faults: 0.

## Failed or deferred rules

- None.

## Current step

Implement Rule 2, pre-attack successor and board continuity, as the only new
behavior change from the accepted Rule 1 parent.

## Next step after acceptance

Rule 3, Ultra Ball complete route, from the last accepted Silver-based parent.
