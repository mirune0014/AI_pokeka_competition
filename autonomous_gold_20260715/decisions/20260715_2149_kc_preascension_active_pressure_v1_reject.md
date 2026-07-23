# 2026-07-15 21:49 JST - KC pre-Ascension Active pressure v1 rejected

## Decision

Reject and retire
`historical_silver_kc_preascension_active_pressure_v1`. Do not loosen,
retune, broaden, package, or submit this exact implementation. Retain
`historical_silver_kc_lone_nonex_v1` as the strongest current parent.

The final Sol-Ultra judgment agrees with the independent Sol-xhigh audit and
the root raw recomputation.

## Frozen result

| panel | parent | candidate | delta | gains | regressions |
| --- | ---: | ---: | ---: | ---: | ---: |
| reference KC policy | 114/160 | 114/160 | 0 | 0 | 0 |
| two fresh KC policies | 208/320 | 208/320 | 0 | 0 | 0 |
| combined target | 322/480 | 322/480 | 0 | 0 | 0 |

- Paired normal 95% interval: `[0, 0]`.
- All 480 parent/candidate result and step pairs were identical.
- All 480 detailed trace pairs were byte-identical.
- Exact new-rule hits: `0`; full conversion chains: `0`.
- Integrity was clean: 480 unique keys, 1,440 raw rows, 18 zero-exit
  manifests, no action errors or max-step hits.
- The first 40 reference games reproduced the accepted parent exactly at p0
  `29/40` and p1 `28/40`.

Gates 3 through 7 fail because the rule had no exposure or measurable effect.
The clean safety controls cannot promote an inert candidate. The frozen stop
clause correctly prevented Phase B.

## Evidence identity

- Candidate `main.py` SHA256:
  `D62DE46B04C514596C2961A533FD1C2846284EEE965D0300A87892B77BB32021`.
- Evaluation specification SHA256:
  `FC13836EBEDF5EB93C8BB7E95CD596D72D66BD1E0AB4D979ED4EEC273E6BA026`.
- Execution log SHA256:
  `318ED6EDF45FD29557E7599A886525A446D6621E363C2D722DA061A4E6EF45EC`.
- Independent numerical audit SHA256:
  `184C285C1B997CAA643D307A87D8A46B03868DA613570445B7794F35B0785D81`.
- Root verification: `evaluations/kc_preascension_active_pressure_v1/ROOT_PHASE_A_VERIFICATION.md`.

## Kaggle stance

No Kaggle write was made. Live submission `54710399` remains the current
agent. A remaining daily slot is not consumed without a separately selected,
independently frozen candidate that demonstrates real target exposure and
passes retention.
