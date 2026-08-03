# v4 C1 ポフィン判断・選択枚数 fix3 検証・採否

Date: 2026-07-30

## 結論

`alakazam_newdeck_v4_poffin_role_cardinality_fix3` は不採用とする。

実装は focused `25/25`、候補全回帰 `191/191`、親全回帰 `166/166`
を通過し、実行整合性にも異常はなかった。しかし、固定700局の候補成績が
親版を9勝下回り、絶対勝数、全体差、Historical Silver、隣接対面の
複数の必須ゲートを同時に満たさなかった。

ポフィンの役割判断と選択枚数を直接変えるこの候補は、後続候補へ継承しない。
C2の親はB0 `alakazam_newdeck_v3_exact_evolution_ko_fix2` とする。

## 凍結入力

- paired raw:
  `alakazam_staged_20260729/evaluations/v4_c1_poffin_fix3_combined_attempt2/combined_paired_results.csv`
- paired raw SHA-256:
  `BAFA80721A1095E3033B8AA82D344936A5438243EB98698838175B4EFCAF6394`
- combined manifest SHA-256:
  `DC62231788A9308087D6A40401BF063BD6E6FC58C413052516D5786583D8AA60`
- checked combined report SHA-256:
  `1E0BED06D465FDB038D6C049245A74697ACB4E056C2E739BF09EEA1D0B31BA8B`
- checked validation SHA-256:
  `03B89BF1C6A1F10D887CA7AC2DA1AC9CA26394A808374365F62F113B8F76D090`
- baseline closure:
  `DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47`
- candidate closure:
  `DE7FCD20A1B3362E845B8573DC6178E32B13F250EA8AC8619B7BA0AA704D271D`

## Rootによるraw再計算

| 項目 | 親版 | 候補 | 差 |
|---|---:|---:|---:|
| 全体 | 452/700 | 443/700 | -9 |
| Marnie | 69/100 | 72/100 | +3 |
| Cynthia | 73/100 | 75/100 | +2 |
| Alakazam mirror | 81/100 | 79/100 | -2 |
| Rocket proxy | 38/100 | 32/100 | -6 |
| Kangaskhan/Crustle | 71/100 | 71/100 | 0 |
| Historical Silver | 56/100 | 52/100 | -4 |
| Direct frozen | 64/100 | 62/100 | -2 |

Paired内訳はgain `68`、loss `77`、tie `555`。seat差はseat 0が
`-5`、seat 1が`-4`。seed-base差は順に
`-5, +8, -6, -2, -4`だった。

Historical Silverのseat差は`-1/-3`。5 seed blockは
`-1, 0, -1, 0, -2`で、正のblockは`0/5`だった。
Historical Silver以外の6対面合計は`-5/600`。

## 数値ゲート

| ゲート | 結果 |
|---|---|
| 候補勝数 `>=452` | FAIL: `443` |
| overall paired deltaが正 | FAIL: `-9` |
| Historical Silver `>=+3/100` | FAIL: `-4` |
| Silver両seatが非負 | FAIL: `-1/-3` |
| Silver正block `>=2/5` | FAIL: `0/5` |
| 隣接6対面 `>=-2/600` | FAIL: `-5` |
| 各対面 `>=-2/100` | FAIL: Rocket `-6`、Silver `-4` |
| 各対面-seat `>=-2/50` | FAIL: Direct s0 `-3`、Rocket s0 `-4`、Silver s1 `-3` |
| 実行・raw整合性 | PASS |
| 機構到達性 | 未実施 |

50 seed-clusterのone-sided 95% paired lower boundは、全体
`-4.24pp`、隣接6対面`-3.96pp`、Silver `-10.26pp`で、いずれも
閾値を下回った。per-game paired Waldでも判定は変わらない。

## 実行整合性

- paired rows: 700
- unique `(opponent, seat, seed)`: 700
- result-to-seat mapping mismatch: 0
- seed formula mismatch: 0
- selected commands: 210
- raw summary rows: 2100
- baseline A/B duplicate mismatch: 0/700
- raw summary to combined result/steps mismatch: 0
- nonzero exit: 0
- action error: 0
- max-step hit: 0
- invalid result: 0

35 panelのうち32件は`attempt_1`、3件は`attempt_2`を採用した。
無効な3件の`attempt_1`は数値poolへ入っていない。

## 機構検証を省略する理由

機構到達性は採用の必要条件であって、数値ゲート失敗を覆す条件ではない。
本候補は絶対勝数、overall、Silver、隣接対面、対面-seatの複数の独立した
必須条件に失敗したため、追加の到達性計測を行っても採用可能にならない。
したがって、計算資源をC2以降の単独候補へ移す。
