# Rule 1 採否決定

## Decision

`ACCEPT` — `EXACTLY_ONE_DURALUDON_SETUP_V1`を次段階の親として受理する。

これは安全に残せる中立採用であり、強化の主張ではない。

## Evidence

- Historical-Silver親 SHA: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- 候補 SHA: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- デッキ SHA: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- shadow: 4,262 callback、9差分、全差分が初期Duraludon 1体配置、fault 0。
- fixed160: Silver 100/160、候補100/160、G/R/T 0/0/160。
- 自然発火: 28（seat 0 = 11、seat 1 = 17）。
- invalid action、例外、max-step、duplicate mismatch: 0。
- root再計算と独立Sol-Ultra監査は全採否数値で一致。

## Gate disposition

- 自然発火4回以上・両席発火: PASS
- gains >= regressions: PASS
- 単一席・相手で3勝以上悪化なし: PASS
- 全first differenceが現在規則へ帰属: PASS
- 明確に有害なfirst difference: 0

## Residual risk

Rule 1単独では勝敗改善を観測していない。後続規則との組合せでベンチ枠やBoss対象になる可能性があるため、以降もRule 1由来のfirst differenceを追跡する。

次は、この受理親からRule 2「攻撃前の後続・盤面継続」だけを追加する。
