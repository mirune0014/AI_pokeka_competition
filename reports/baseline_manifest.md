# Historical-Silver Archaludon baseline manifest

## 結論

新規ロケット団エージェントの比較基準は、Kaggle submission `54495224` の
`submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz` とする。
これは一時的な約 1072 のピーク方策や、後発の `archattach_ruleinline_20260710`
ではない。後者には RL 由来の規則が混入しており、Historical-Silver の同一物でもない。

この基準は、次の読み取り専用参照コピーと SHA-256 で固定する。

- 参照コピー:
  `analysis_outputs/reference_agents/historical_silver_archaludon_54495224`
- 評価用の同一コピー:
  `isolated_rule_agents/orbit_transfer_archaludon_20260715/baseline_exact`
- 原本アーカイブ:
  `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`
- 原本アーカイブ SHA-256:
  `69BC01010FA2963781E6CD18CBA4773E0372127763DBB7AAF5E2081E1A156809`

既存ファイルの属性・内容・配置は変更しない。今後の比較では、パスだけでなく下記の
ハッシュが一致することを毎回確認する。

## 識別情報

| 項目 | 確認結果 |
|---|---|
| Kaggle submission ID | `54495224` |
| 方策 | exact Historical-Silver Archaludon |
| 方策エントリポイント | `main.py` の `agent(obs_dict)`、行 1324 |
| デッキ | `deck.csv`、60 行 |
| 設定 | 方策内の定数と同梱 `deck.csv`。独立設定ファイルはない |
| 提出ファイル | `submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz` |
| 提出ファイルサイズ | 2,008,160 bytes |
| 依存 | 同梱 `cg/`、標準ライブラリのみ。モデル、重み、ネットワーク依存なし |
| Historical-Silver の観測ピーク | `1045.5801970820014` |
| ピーク episode | `85028839` |
| ピーク評価日時 | `2026-07-09T14:07:41.818878800Z` |
| 初動 | 12 勝 1 敗 |
| 26 公開対戦時点 | 18 勝 8 敗 |
| 元提出時の Git commit | 不明。作業当時は Git provenance がなく、ハッシュで管理 |
| 元提出時の branch | 不明 |
| 現在の取込 commit | `54f09edb2b3f6dd2def7c2c49efde16dfeda97c9` |
| 現在の branch | `main` |

同じアーカイブハッシュは後に submission `54510332`、`54600598`、
`54704652` として再提出されている。これらは同一物の再評価であり、
Historical-Silver の識別子は元の `54495224` のままとする。

## ファイルハッシュ

| ファイル | SHA-256 |
|---|---|
| `main.py` | `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E` |
| `deck.csv` | `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A` |
| `requirements.txt` | `9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47` |
| `cg/cg.dll` | `9EA2B0A751029689BFF3DDCCB5F29A98EDD46961DAD264490ED121EF704FB500` |
| `cg/api.py` | `593F1298E52A635F90F8F505A52113E9AF114F444C293404E37906F18EE06CED` |
| `cg/game.py` | `3BD3D4F4A369A11E6D2F5DA9094CF15EBC410A2221835E6417B7CFF4883F1FC2` |
| `cg/sim.py` | `1555F57F5D22BF4C09D70E0E667A916E575E68C9DD1DE9EAD34BA5E7E4968655` |
| `cg/utils.py` | `60F29665CEE0A88525D6F0383BC45959A6262D16FE35EF380AECE1E0EA13C49B` |

## デッキ

`deck.csv` のカード ID と枚数は次のとおり。

| ID | 枚数 |
|---:|---:|
| 8 | 12 |
| 169 | 4 |
| 190 | 4 |
| 666 | 4 |
| 840 | 2 |
| 1097 | 3 |
| 1121 | 4 |
| 1122 | 4 |
| 1147 | 3 |
| 1152 | 4 |
| 1159 | 1 |
| 1182 | 4 |
| 1185 | 4 |
| 1227 | 4 |
| 1244 | 3 |

合計は 60 枚である。

## 実行・評価条件

方策の通常経路は得点降順、同点時は合法手の小さい index を選ぶ。
ただし最外周の例外処理だけは `random.sample` を使う。この履歴上の挙動は基準では
変更しない。新規方策では、同じ箇所を先頭合法手へ fail-closed する。

ローカル比較の既存実績では `tools/run_seeded_paired_suite.py` と
`tools/run_local_battle.py` を使用し、両席、明示 seed、`max_steps=1000` で固定している。
新規候補の評価でも、基準・候補へ同一の opponent、seat、seed を割り当てる。

過去の不変 broad panel は 8 相手、両席、640 対戦で `520/640 = 81.25%`、
席別 `258/320` と `262/320`、action error 0、max-step hit 0 だった。
内訳は self `40/80`、exact Alakazam `50/80`、Alakazam Rmy `62/80`、
Marnie `74/80`、Mega Lucario `77/80`、Starmie `76/80`、
Dragapult `76/80`、Cornerstone Ogerpon `65/80` である。

評価用 seeded engine の canonical tree SHA-256 は
`586B92FDEA892CBB147D4C6A113575CCD98E4FC90528BABB6E8F7294D0CBEBF2`。
これは再現可能なローカル評価専用であり、提出物へ混ぜない。

## 根拠

- `analysis_outputs/cynthia_v43_v44_historical_silver_anchor_gate_20260714/SPEC.md`
- `isolated_rule_agents/orbit_transfer_archaludon_20260715/EVALUATION_SPEC.md`
- `docs/meta_deck_scouting_2026-07-03.md`
- `analysis_outputs/kaggle_live/submission_54495224_crustledeckguard/`
- `autonomous_gold_20260715/decisions/20260715_0900_exact_historical_silver_restore_submit.md`

## 変更禁止

新規開発では、この基準の `main.py`、`deck.csv`、`requirements.txt`、`cg/`、
アーカイブを編集・再圧縮しない。候補は確認後に別ディレクトリへ作り、
評価時にはこの manifest のハッシュ不一致を即時失敗とする。
