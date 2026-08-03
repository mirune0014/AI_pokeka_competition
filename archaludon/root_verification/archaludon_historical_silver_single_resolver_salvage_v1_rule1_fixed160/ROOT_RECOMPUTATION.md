# Rule 1 固定160戦 root再計算

## 凍結入力

- 対象規則: `EXACTLY_ONE_DURALUDON_SETUP`
- 候補 `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Historical-Silver親: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- デッキ: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- 固定160仕様: `E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C`
- 生出力tree: `DB612879410B9FE53AF97B33A33212CD80C3FD24FEAD8184DA224F805616C6DD`
- 再計算スクリプト: `root_recompute_fixed160.py`

## 数値

| 指標 | Silver | 候補 | 差 |
| --- | ---: | ---: | ---: |
| 全160戦 | 100 | 100 | 0 |
| seat 0（80戦） | 47 | 47 | 0 |
| seat 1（80戦） | 53 | 53 | 0 |
| Historical-Silver（40戦） | 20 | 20 | 0 |
| Arch Peak（40戦） | 20 | 20 | 0 |
| Alakazam（40戦） | 29 | 29 | 0 |
| Marnie（40戦） | 31 | 31 | 0 |

- paired gains: 0
- paired regressions: 0
- paired ties: 160
- 一意キー: 160/160
- manifest exit error: 0
- started fault: 0
- action error: 0
- max-step: 0

## 発火と差分

- first difference: 28局
- seat 0: 11局
- seat 1: 17局
- 28/28がturn 0、`SETUP_BENCH_POKEMON`、Silver `[]`からDuraludon 1体配置への差分。
- その他の最初の差分は0。

## 段階ゲート

- 自然発火4回以上、両席発火: PASS
- gains >= regressions: PASS（0 >= 0）
- 片席・単一相手で3勝以上悪化なし: PASS
- 機械的不良0: PASS
- 全差分がRule 1へ帰属: PASS

root判定は `PASS`。独立Sol-Ultra数値監査と最終戦略判定が一致した場合だけ受理する。
