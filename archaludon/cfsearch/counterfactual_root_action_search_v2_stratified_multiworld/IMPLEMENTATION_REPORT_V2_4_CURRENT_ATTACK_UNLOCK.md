# V2.4: current-turn Active attack unlock diagnostic

実行日: 2026-08-16 (JST)

## 目的

GPT PRO 指定の `T7_CURRENT_TURN_ATTACK_UNLOCK_BY_ATTACH_DIAGNOSTIC_V1` を、
accepted parent に対する診断として一度だけ実行した。検証対象は、親が同じ
Energy を Bench に付ける局面で、同じ Energy を現在の Active に付けた場合だけ
そのターンの合法 ATTACK が公開状態上で解禁されるか、である。

候補実装、holdout、ルール緩和、親変更、Kaggle 提出は行っていない。

## 固定入力

- accepted parent: `archaludon/candidates/archaludon_historical_silver_replay_repair_alakazam_lillie_v1`
- parent `main.py` SHA-256: `506E1A75062EE22BEE550C303C74D44A141EF6F8A6AD0DB6AEADBD9211085CB6`
- parent deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- discovery roots: formal discovery split `4030` rootsから、hash 順・ゲーム最大2・ターン最大1で `32` 根を選択
- selected roots SHA-256: `EAFCCF506B80F882FAF46FF15FC2AE36E6C967325943D2EF306DF943C6D3E1D1`
- engine: seeded `cynthia_v9_vs_v11_poffin_role_selection_20260713`
- branches: 各根について parent Bench attach / Active attach を同一 seed で実行
- max steps: `1000`
- holdout: 未使用

## 実行の完全性

`32 roots × 2 branches = 64` 分岐を実行し、すべて exit 0 だった。

- branch rows: `64`
- engine import shadow: `64/64 PASS`
- root public hash / legal semantic set / parent action parity: `64/64 PASS`
- action errors: `0`
- max-step: `0`
- post-attach comparable roots: `31/32`
- 除外根: `discovery_02775_kang_crustle_p1_g1_c75`。親・Activeとも同じ公開 callbackで
  `ENERGY_STATE_NOT_VISIBLE` となり、指定された比較可能性を満たさなかった。

## 診断結果（比較可能31根）

| 指標 | 値 |
| --- | ---: |
| current-turn unlock roots | 21 |
| unlock distinct games | 15 |
| opponent families | 5 |
| seats | 0, 1 |
| U1 exact KO | 0 |
| U2 positive damage | 20 |
| U3 exact zero damage | 0 |
| U4 unknown modifier/effect | 1 |
| B1 Active only | 15 |
| B2 both branches | 2 |
| B3 neither attacks | 4 |
| B4 parent only | 0 |
| game gain | 3 |
| game regression | 3 |
| game net | 0 |
| unlock-root gain | 4 |
| unlock-root regression | 3 |
| U1/U2 + B1 gain | 3 |
| U1/U2 + B1 regression | 3 |
| U1/U2 + B1 net | 0 |
| catastrophic regressions | 3 |

U4 は `Metal Defender` のように攻撃テキストがあり、base damageだけでは厳密な
効果証明にならないものを保守的に分類した。U1/U2 の候補証拠には含めていない。

## 固定ゲート

構造的には sparse ではない（unlock 21根、15ゲーム、5 family、両席）。しかし、
U1/U2+B1 の根で gain 3 / regression 3 / net 0、game でも gain 3 / regression 3、
さらに機構に直接関係する catastrophic regression が3件あった。

したがって GPT PRO の固定条件に従い、判定は **`REJECTED`**。この結果から
`HYPOTHESIS_DRAFT.md`、候補、holdout、追加の T7 診断は作成しない。

## 成果物

実行出力:

`_local_generated/analysis_outputs/archaludon_t7_current_turn_attack_unlock_diagnostic_v1/run_20260816_0112_v1/`

- `comparison_spec.json`
- `selected_roots.jsonl`
- `branch_results.jsonl`
- `analysis_outputs/root_results.csv`
- `analysis_outputs/game_results.csv`
- `analysis_outputs/unlock_classification.csv`
- `analysis_outputs/catastrophic_regressions.csv`
- `analysis_outputs/summary.json` SHA-256 `B488E4527B4B6BF52CB6321B4272FB3EF2580DAF9929E06259C5B9342A1F8C81`

主要ハッシュ:

- branch runner: `96D14872A9243B215E9B5346CB1E983EB583BDA7B882ACC290CB38FF4BC39E76`
- execution wrapper: `5FAD556A70E926B0ABAAD6D90D37A81D645865B3234922743ECE1BE7EF7CF73E`
- aggregator: `C97645319ABFD7343B91A42C52D4BDB0585B49351D4DA3855352EF44DDE20802`
- `root_results.csv` / `unlock_classification.csv`: `19DD4DC2C29C0B2468D2B55AF2A38B0912FDA77CD19DF7FD19F6181876C06800`
- `game_results.csv`: `752A713741809AC9ED730EF467A2DACB825684FB6E93B7C7A06CD7F0235CC9EF`
- `catastrophic_regressions.csv`: `6F5293A3D6D92EF1EEB617CACDDE7E53E12D911CEFF5885B0AC5138AEC66BFAF`

accepted parent のコード・deck・final は変更していない。
