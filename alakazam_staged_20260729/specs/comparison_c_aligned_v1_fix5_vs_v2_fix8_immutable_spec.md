# Comparison C aligned v1 fix5 vs v2 fix8 immutable specification

## 比較identity

baseline:

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5`
- closure:
  `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`
- planner:
  `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v1_package_runtime_certified_fix5`

candidate:

- source:
  `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`
- closure:
  `AB4F6FD57911BAE1D5CF9FAE2013298FC1744E401E52C65855BAB127A638FD57`
- planner:
  `12266E3311F878F99C6C6924274B22288912889E3F51B4B62DBDA8A1D35DB724`
- adapter:
  `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`

両版のadapter `main.py`は
`426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC`、
deckは
`F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94`
である。

## tools

- engine tree:
  `466638706BD5C6915E25D1B3CB9E3D966390FBC263F4ED3153108E29C0194FFF`
- paired runner:
  `5EC25C98F2777FF61DE2DBD0A03A08519A7FEA4B2B4C510B5B8895BC2000E000`
- battle runner:
  `E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`
- combiner:
  `CABFB6ECB500EF1395B05EDB5A9775193B8A13578E3EDF35C0CED04214175C77`
- metric runner:
  `BCC98229B23C86FC5EB248D3F1E254337008FF4E85BD85224B3B3D6F570F1EEA`
- Python: `3.11.6`

## aligned schedule

比較A・Bと同じ7 opponents、両seat、50 seedを使う。

- seed bases:
  `202608500`, `202608510`, `202608520`, `202608530`, `202608540`
- games per cell: `10`
- paired rows: `700`
- manifest rows: `210`
- child summaries: `2,100`
- expected paired semantic schedule:
  `619BA954971C33FDC698810A58DF1E2C0786FFF16B6A0CCD2715DC33B04FD076`
- expected manifest semantic schedule:
  `9277E7463E1372FCE8095BD86A79FA35EC616177034CBEA7894BCBC5419AAAB3`

fresh outputs:

- panels:
  `alakazam_staged_20260729/evaluations/comparison_c_aligned_fix8_panels`
- combined:
  `alakazam_staged_20260729/evaluations/comparison_c_aligned_fix8_combined`
- formal v2:
  `alakazam_staged_20260729/metrics/formal_v2_fix8_aligned_7opp_50seed`
- formal summary:
  `alakazam_staged_20260729/metrics/formal_v2_fix8_aligned_7opp_50seed_summary`

## safety gate

- 700 unique paired keys、schedule差0
- 35 valid panels、manifest 210行
- baseline A/B duplicate mismatch 0
- exit、action error、timeout、max-step、invalid winner 0
- formal 70/70 blocks、700 games
- callback pair、structural、exception、fallback、abort、pendingの異常0
- paired candidateとformal v2のresult/steps差0

## mechanism completeness gate

完了transactionが次をすべて満たす。

- total `>=20`
- both seats
- at least 3 opponents
- at least 3 seed bases
- Historical-Silver `>=1`
- starts = attach verified = attacks dispatched = KO resolved

満たさなければv2を棄却し、未使用seed holdoutを実行せずfix5 v1を保持する。

満たす場合だけ、`202608600..202608649`のholdout Cを別specへ凍結する。

aligned結果とholdout結果はpoolしない。

