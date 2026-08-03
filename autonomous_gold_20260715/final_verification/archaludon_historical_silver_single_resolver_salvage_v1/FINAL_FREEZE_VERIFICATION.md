# Final freeze verification

Date: 2026-08-03 JST

## Scope

This freezes the only candidate allowed to enter the one final fixed-760 run
for `archaludon_historical_silver_single_resolver_salvage_v1`.  It is not a
Kaggle package or write.

## Controlling inputs

- Requirements:
  `autonomous_gold_20260715/strategy/archaludon_historical_silver_single_resolver_salvage_v1/REQUIREMENTS.md`
- Requirements SHA-256:
  `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`
- Exact Historical-Silver `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Frozen deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Frozen candidate

- Path:
  `autonomous_gold_20260715/final/archaludon_historical_silver_single_resolver_salvage_v1`
- `main.py` SHA-256:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Runtime members: 13 files.
- Cache entries: 0.
- Every runtime file is byte-identical to accepted
  `archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`.

## Accepted content

- Rule 1: exactly-one Duraludon setup.
- Rule 4: exact current materialization before parent Lillie.
- Rule 5: exact current win and unique higher-Prize Boss conversion.

Rules 2, 8, 9, and 10 were deferred dormant.  Rules 3, 6, and 7 were
rejected.  None of those rules is present in the frozen candidate.

## Structural and legality verification

- In-memory AST compile: PASS.
- One top-level `agent`: PASS.
- One `_resolve`: PASS.
- One static `_parent.agent(...)` call: PASS.
- Final top-level function is `agent`: PASS.
- Deck rows: 60.
- ACE SPEC: one Hero's Cape (`1159`).
- Existing Historical-Silver scorer and chooser remain inside the byte-exact
  `_historical_silver_parent.py`; they were not edited.
- The final candidate has one resolver and one active transaction-owner slot.
- Proposal ambiguity, unsupported evidence, and exceptions return the once-
  computed Historical-Silver action.

## Final-run authorization

The candidate satisfies the frozen-input, structure, legality, and cache gates.
It is authorized only for the single requirements-defined fixed-760 evaluation.
No other exploratory schedule is authorized before the final judgment.
