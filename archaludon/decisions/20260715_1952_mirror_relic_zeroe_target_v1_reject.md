# 2026-07-15 19:52 JST — mirror Relicanth zero-E target v1 rejected

## Decision

Reject and retire
`historical_silver_mirror_relic_zeroe_target_v1`. Do not retune, broaden,
seed-filter, reuse, package, or submit it. Retain
`historical_silver_kc_lone_nonex_v1` as the strongest current parent.

The final Sol-Ultra judgment agrees with the independent Sol-xhigh audit and
the root raw recomputation.

## Evidence identity

- Candidate `main.py` SHA-256:
  `CB436A7BF38778A0229F2EAA38F1438859268DA56F924339D29F773FB603EF28`.
- Evaluation specification SHA-256:
  `531A050B236193F4A7FB6D9C6B535C684CD6C7DC9743ECB446718A4A38CDD89C`.
- Root numerical verification SHA-256:
  `51D80788D2DD6F553467F4FC5488BEAFD6B3A3EE016ED5875B1B6680177C26D2`.
- Independent Sol-xhigh audit SHA-256:
  `898DB47A70D11AAF6D66915584AC189E1EAD416DF447838126217F5F042E463C`.

## Frozen evaluation result

| panel | parent | candidate | delta | gains | regressions |
| --- | ---: | ---: | ---: | ---: | ---: |
| reference | 145/320 | 147/320 | +2 | 5 | 3 |
| fresh | 156/320 | 157/320 | +1 | 2 | 1 |
| combined target | 301/640 | 304/640 | +3 | 7 | 4 |
| broad retention | 520/640 | 520/640 | 0 | 0 | 0 |

- Reference seat 1 regressed by two wins.
- Ozanm exact was net zero, one gain and one regression.
- Fresh delta was only `+1`, with one regression.
- Combined paired 95% interval was
  `[-0.005471108354451867, 0.014846108354451867]`.
- Broad results and steps were identical in all 640 keys.
- Integrity was clean: 1,280 unique paired keys, 3,840 raw rows, 72 manifests,
  no execution/action/max-step/duplicate/schedule errors.

Gates 3, 4, and 5 fail. The numeric-stop clause correctly prevented the trace
audit. Broad identity cannot override failed target robustness.

## Kaggle stance

No Kaggle write was made. Submission `54710399` remains complete at displayed
score `793.2`; the refresh had ten genuine new public games (`6-4`) and no
runtime failure. Today had three known submission rows at refresh time, but a
remaining slot is not consumed without a valid candidate.

Any later candidate must be a separately selected and independently frozen
hypothesis from the retained parent. It must not continue this rejected
target-scoring family.
