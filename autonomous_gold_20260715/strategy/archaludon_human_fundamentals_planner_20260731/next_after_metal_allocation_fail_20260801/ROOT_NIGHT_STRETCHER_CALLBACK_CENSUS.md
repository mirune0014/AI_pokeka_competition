# Root census: Night Stretcher callbacks

## Corpus and method

対象は固定済みの207 replay / 209 target-seat corpus:

`live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new`

`TeamNames == "rurumi"` の席だけを数えた。`select.effect.id == 1097` の callback を抽出した。Kaggle replay の `action` は一行前の observation への応答なので、callback 行の次行に保存された action を formal parent の `to_observation_class` と `option_card` で物理カードへ解決した。これは過去 agent の選択頻度であり、強さや正解ラベルではない。

## Counts

- Night Stretcher effect callbacks: `186`
- Replays: `123`
- Seats: `[0, 1]`

Historical selected recovery card ID:

| card | ID | callbacks |
|---|---:|---:|
| Duraludon | 169 | 93 |
| Archaludon ex | 190 | 53 |
| Basic Metal Energy | 8 | 34 |
| non-ex Archaludon | 840 | 4 |
| Cinderace | 666 | 2 |
| empty action | - | 0 |
| total | - | 186 |

Callback option-count distribution:

| options | callbacks |
|---:|---:|
| 1 | 6 |
| 2 | 8 |
| 3 | 10 |
| 4 | 14 |
| 5 | 28 |
| 6 | 19 |
| 7 | 22 |
| 8 | 21 |
| 9 | 10 |
| 10 | 12 |
| 11 | 12 |
| 12 | 11 |
| 13 | 5 |
| 14 | 3 |
| 15 | 3 |
| 19 | 1 |
| 20 | 1 |

## Consequence for implementation

Night Stretcher は自然頻度が十分にあり、回収対象も五種類へ分散している。全186 callback は `minCount=maxCount=1` で、合法 action は必ず一枚を選んでおり、合法な空選択は0件だった。したがって、単一カード ID の固定優先や「回収できる最大価値」を点数化するだけでは一般的な基本プレイにならず、空選択を通常案として生成してもならない。

次候補は、Stretcher を使う前に回収対象と具体的な後続目的を結ぶ必要がある。最低でも、今ターンの攻撃完成、進化から攻撃、次アタッカー形成、最終 Prize、確定 loss 回避を区別し、同じ役割が既に手札・場にある場合と将来の唯一の回収札を浪費する場合を明示的な負条件にする。

Formal parent には、最終1 Prizeで Basic Metal を回収し、Activeへ手貼りし、Bossで確定KO対象を呼び、Metal Defenderまで完遂する H2 transaction が既にある。新しい一般 rule はその owner を尊重し、H2を上書きまたは二重所有してはならない。

## Frozen row-level evidence

- generator: `freeze_night_stretcher_callback_census.py`
- generator SHA-256: `2E676D05412C1647E737EC136E73C0543F86CA09757836D52DA6F8E7FE6DCD08`
- source manifest: `night_stretcher_callback_census_raw/source_manifest.json`
- source manifest SHA-256: `90A512D5C9AE5EAD8DF92F370C32716959EC0929F9465451E7BB0926DBEB5A68`
- callback rows: `night_stretcher_callback_census_raw/callback_rows.csv`
- callback rows SHA-256: `136DE7C57BDD4582A84B2F84FA790773CE8463FE6FD67DB4BE005185BD6F1179`
- summary: `night_stretcher_callback_census_raw/summary.json`
- summary SHA-256: `3F3AD57FB2A16A502AD43E219018266FC925212ECBFF8FE9059135366BFFB355`

各行は callback observation の canonical SHA、全 option role、次行に保存された historical action/role、formal parent action/role、parent call前後のowner状態を持つ。全186 historical actionとformal parent actionは合法、全 callback は `minCount=maxCount=1`、action alignment mismatchは0だった。

Formal parent の回収先は Duraludon 92、Archaludon ex 53、Basic Metal 35、non-ex Archaludon 4、Cinderace 2だった。Historical actionとの相違は1件だけである。

- episode `88017509`, seat 1, turn 12, step 117
- historical: Duraludon `169`
- formal parent: Basic Metal `8#113`
- owner before/after: `H2_CERTIFIED_LAST_PRIZE_STRETCHER_METAL_BOSS`

全186 callbackでH2 ownerが生きていたのはこの1件だけだった。新 rule はこの行をH2 controlとして完全に親へ渡す。
