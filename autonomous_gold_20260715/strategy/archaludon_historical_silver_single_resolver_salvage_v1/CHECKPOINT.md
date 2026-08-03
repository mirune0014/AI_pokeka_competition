# CHECKPOINT

Updated: 2026-08-03 JST

## Invariants

- Silver scorer unchanged.
- One final agent, one resolver, one active transaction.
- One rule at a time.
- UNKNOWN returns Historical-Silver.
- Failed rules are removed, not patched by another rule.
- Existing artifacts remain read-only.

## Accepted parent

- Candidate: `archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`.
- Accepted rules: 1, 4, and 5.
- `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

## Accepted rules

- Rule 1, exactly-one Duraludon setup: fixed160 `100=100`, natural starts 28,
  faults 0.
- Rule 4, exact materialization before parent Lillie: fixed160 `100=100`, two
  intended natural differences, faults 0.
- Rule 5, exact current win / unique higher-Prize Boss: fixed160 `100=100`, two
  intended direct-win differences, faults 0.  Boss route was dormant and was
  not widened.

## Failed or deferred rules

- Rule 2 continuity: `DEFER-DORMANT`; no natural fire, not integrated.
- Rule 3 Ultra Ball: `REJECT`; fixed160 `100 -> 99`, one regression.
- Rule 6 Poké Pad: `REJECT`; one start but no naturally completed route.
- Rule 7 Turbo Flare concentration: `REJECT`; fixed160 `100 -> 98`, G/R/T
  `3/5/152`, seat 1 `-3`; fixed760 forbidden.

## Current step

Implement Rule 8, exact same-Active attack dominance, as the only new behavior
from the accepted Rule 5 parent.

## Next

After Rule 8 adoption or rejection, implement Rule 9 from the last accepted
Silver-based parent.  Do not carry Rule 7 forward.
