# Comparison C aligned fix8 execution amendment

## parent specification

- immutable spec:
  `alakazam_staged_20260729/specs/comparison_c_aligned_v1_fix5_vs_v2_fix8_immutable_spec.md`
- immutable spec SHA-256:
  `715BC160D1F876C9C02C35260D93D4E049C2FA79337C28D9656AB38B8438DB2A`

## prerequisite evidence

- independent static review: PASS
- root tests: `192/192 PASS`
- smoke:
  `alakazam_staged_20260729/metrics/smoke_v2_fix8_h1_unique_attach_seed202608570`
- smoke blocks: `14/14`
- smoke games: `140`
- smoke callback pairs: `9,350/9,350`
- smoke hard faults: `0`
- smoke V2 transaction starts: `0`

発火0件はsmokeでは診断値であり、正式なmechanism gateはaligned 700試合で
判定する。

## paired panels

35個のpanelを、checked `tools/run_seeded_paired_suite.py`で実行する。

各panel:

- baseline:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix5`
- candidate:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`
- one frozen opponent
- one frozen seed base
- both seats
- ten games per seat
- max steps `1000`

各panelは`attempt_1`から開始し、失敗時だけ同じcommandを最大
`attempt_3`まで再実行する。

失敗attemptは削除・上書き・poolしない。

## formal metrics

candidate v2だけを、同じ7 opponents、5 seed bases、両seat、10 gamesで
`tools/run_alakazam_staged_metric_suite.py`へ渡す。

fix5 v1の同一schedule formal suiteは
`metrics/formal_v1_runtime_certified_fix5_7opp_50seed`を再利用する。

paired candidate rowsとformal v2 rowsの`result`と`steps`を完全joinする。

## stop rule

安全gateまたはmechanism completeness gateのいずれかが不成立なら、
未使用seed holdoutは実行しない。

その場合、Comparison C alignedの結果を報告し、最終候補はfix5 v1とする。

