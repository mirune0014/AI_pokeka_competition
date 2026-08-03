# Rule 3 root採否

## Decision

`SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_V1`は**REJECT**。

このtrialは最終候補へ統合せず、次規則の親にも使用しない。受理親はRule 1
`archaludon_historical_silver_single_resolver_salvage_v1`のままとする。

## Reason

- fixed160: 親`100/160`、候補`99/160`。
- paired gains / regressions / ties: `0 / 1 / 159`。
- action-observable start 3、完結した宣言transaction 0。
- Arch Peak・seat 0・seed `271958318`で唯一のmechanism-first outcomeが勝利から敗北へ反転。
- action error、例外、start fault、max-step、duplicate mismatchは0。

実装安全性は成立したが、凍結採用条件`gains >= regressions`を満たさず、明確に無害と証明できないfirst differenceがある。要件どおり補修ルールを積まず、条件も広げない。

## Independent agreement

- root再計算: `ROOT_FIXED160_RECOMPUTATION.md`
- Sol-Ultra数値監査: `SOL_ULTRA_NUMERICAL_AUDIT.md`、SHA-256
  `AE47A4291228018681C19490AC9CB9F34E14828DADFBE723DC5970650332B3EE`
- Sol-Ultra最終判定: `FINAL_JUDGMENT.md`、SHA-256
  `9A7580F9C1A1A1DFDBA2EAFFF67A955147109084479D245ACB89009D5E037BF5`

三者ともREJECTで一致した。
