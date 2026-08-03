# フーディン新デッキ v0 挙動保存検証

## 結論

`alakazam_800_frozen`と`alakazam_newdeck_v0_port`を、保存済み42 replayの2,723意思決定状態へ同時に適用した。

共有51枠だけで成立する121状態を`COMPARABLE_SHARED_51`と判定し、選択actionの差は0件だった。

旧デッキ専用カードが公開領域に見える2,602状態は`NON_COMPARABLE`とし、v0の挙動保存判定へ混入させていない。

全2,723状態でも両方策のaction、Reason Code、trace分類、fallback、合法性は一致した。

この検証範囲では、v0移植に戦略変更は検出されなかった。

## 固定した入力と実装

| 項目 | 値 |
| --- | --- |
| replay入力 | `autonomous_gold_20260715/live/54895497/refresh_20260723_0003/refresh_20260723_0003_episodes.csv` |
| replay入力 SHA-256 | `B51CB730022EA9937D0EB5C145D7A957B0375FAA748B3F69CE2E444CB61E2076` |
| replay数 | 42 |
| frozen adapter | `alakazam_staged_20260729/eval_adapters/alakazam_800_frozen` |
| v0 adapter | `alakazam_staged_20260729/eval_adapters/alakazam_newdeck_v0_port` |
| frozen adapter SHA-256 | `B99DE98C53E777332B5F21036E1F634A2BBD9FD1BD22C3049F9467A953F1E8A2` |
| v0 adapter SHA-256 | `C38C357D28CB4E8401815220E385B5542B385B7AB2984719E30DBAF9503CC2AC` |
| 比較schema | `alakazam-v0-port-equivalence-v2` |

比較プログラムは、各保存stateと同じ合法手集合を両方策へ渡した。

合法手集合は正規化後にhash化し、2,723 callbackすべてで欠損なく記録した。

adapterは各callbackで自身のtarget pathと作業ディレクトリを固定し、呼び出し後に復元する。

これにより、複数agent moduleを同一processで順番にloadしたときのPython module cache混入を防いだ。

## 比較可能性の定義

`COMPARABLE_SHARED_51`は、意思決定に見えているカードが両デッキの共通51枠だけで構成され、デッキ差による直接のカード依存が観測されない状態である。

`NON_COMPARABLE`は、Genesect、Psyduck、Lucky Helmet、Handheld Fan、Battle Cageのいずれかが公開領域に見え、今回デッキでは同じstateを自然生成できない状態である。

`NON_COMPARABLE`は不一致ではなく、挙動保存の分母から除外する分類である。

比較不能状態でも診断目的で両方策を実行したが、その一致をv0の戦略保存証拠として数えていない。

## callback単位の結果

| 指標 | frozen | v0 | 差 |
| --- | ---: | ---: | ---: |
| 全callback | 2,723 | 2,723 | 0 |
| 比較可能callback | 121 | 121 | 0 |
| 比較不能callback | 2,602 | 2,602 | 0 |
| 全action差 | 0 | 0 | 0 |
| 比較可能action差 | 0 | 0 | 0 |
| Reason Code差 | 0 | 0 | 0 |
| trace分類差 | 0 | 0 | 0 |
| fallback差 | 0 | 0 | 0 |
| invalid action | 0 | 0 | 0 |
| exception | 0 | 0 | 0 |
| 記録済み次state共有 | 2,723 | 2,723 | 0 |

保存episode側のfollowing actionが存在したのは2,722 callbackだった。

両方策とも2,718 callbackで保存actionと一致した。

保存actionと異なった4 callbackはすべて`NON_COMPARABLE`であり、frozenとv0の選択action自体は同じだった。

残る1 callbackはepisode末尾の空actionであり、`FOLLOWING_ACTION_EMPTY`として明示した。

遷移後stateは、方策が選んだactionから独自engineを再実行した値ではない。

保存replay上の次observation hashを、同じstateと同じactionを選んだ両方策が共有するという証拠である。

## fallback

fallbackは両方策とも1,433 callbackで発生した。

内訳は次のとおりである。

| fallback分類 | callback |
| --- | ---: |
| `ADMISSIBILITY_REJECT` | 801 |
| setup-stopが確定Prize、終局、lethal-floor条件を満たさない | 790 |
| Run Away後に公開情報上のPokémonが残らない | 11 |
| `PLACEHOLDER_PARENT_FALLBACK` | 632 |

fallbackの有無、分類、理由はfrozenとv0で全件一致した。

新規カードの合法処理は保存replayでは発火しないため、別の7 unit testで確認した。

Lana's Aid、Xerosic's Machinations、Nighttime Mineは任意のMAIN `PLAY`で`V0_GENERIC_HOLD`となり、強制discardだけ`V0_GENERIC_FORCED_DISCARD`となる。

このhandlerは未知カード既定処理ではなく、v0で許可した明示的な最低限処理である。

## 処理時間

| 方策 | 平均 | p95 |
| --- | ---: | ---: |
| frozen | 14.186 ms | 23.401 ms |
| v0 | 14.109 ms | 22.904 ms |

時間値は同一process内で連続実行した診断値である。

OS負荷、module cache、実行順の影響を分離していないため、絶対性能や速度改善の主張には使わない。

## 証拠ファイル

| ファイル | 行数 | SHA-256 |
| --- | ---: | --- |
| `callback_comparison.csv` | 2,723 | `190EDDD7EEFF76E7205D99F257B99864B3A4F0AE9FBD8E0BB3C10FCDC3035072` |
| `replay_manifest.csv` | 42 | `32D7ECD31D63AAB21C116A6A15694B55235C60C47B05A86F8ACC8BC413FEA44B` |
| `summary.json` | 1 | `0C3A34332CDC626BA5672DE0673A726501DDCDE7B41C138B2A197B8669F94C9A` |

`callback_comparison.csv`は2,723 unique callback keyを持ち、重複は0件だった。

CSVの全38列を読み込み、式エラー相当のtoken、文字化け、必須key欠損がないことを確認した。

## v1移行ゲート

保存replayに関するゲートは通過した。

- 比較可能121状態のaction差は0件である。

- Reason Code、trace、fallback、合法性の差は0件である。

- invalid actionとexceptionは0件である。

- v0追加カードhandlerはunit testで合法かつ決定論的である。

一方、保存replayは旧デッキから生成されているため、新デッキ実戦でのtimeout、max-step、generic fallback流入を単独では証明しない。

それらは比較Aの固定scheduleで別に検査し、全条件が成立した場合だけ`alakazam_newdeck_v1_package`へ進む。

比較Aは方策だけでなく9枠のデッキ差も含むため、結果を純粋なデッキ効果とは呼ばない。

## 比較Aと正式指標による最終ゲート

保存replayとは別に、7対面、50 seed、両seatの固定scheduleで比較Aを実行した。

35 panelから700個の対応付き結果を得た。

`(opponent, seat, seed)`は一意であり、baselineとcandidateのschedule差、重複、欠損、非0 exit、action error、max-step、無効resultはすべて0件だった。

| 指標 | frozen | v0 | 差 |
| --- | ---: | ---: | ---: |
| 全700試合の勝数 | 382 | 428 | +46 |
| seat 0の勝数 | 212 | 221 | +9 |
| seat 1の勝数 | 170 | 207 | +37 |
| 対応付きgain |  | 151 |  |
| 対応付きloss |  | 105 |  |

McNemarの両側exact p値は`0.0048189135689923265`だった。

対面別の差は、フーディン同型`-2`、シロナ／ガブリアス`+10`、frozen直接対戦`+5`、Historical-Silver`+9`、ガルーラ／イワパレス`+12`、マーニー／オーロンゲ`+3`、ロケット団proxy`+9`だった。

ただし比較Aは、別の60枚、別の利用可能カード、最低限の移植処理を同時に含む実運用比較である。

したがって、この差を純粋なデッキ効果または個別カードの因果効果とは解釈しない。

v0単体の正式計測も、同じ7対面、50 seed、両seatの700試合で実行した。

checked runnerとのresult・steps結合は700/700件一致し、invalid action、例外、timeout、max-step、first-legal fallbackはすべて0件だった。

追加カードのgeneric handlerは18,395 callbackで発火し、内訳は`V0_GENERIC_HOLD`が18,180件、`V0_GENERIC_FORCED_DISCARD`が215件だった。

未知のhandler理由は0件であり、215件のgeneric fallbackはすべて明示的な強制discardだった。

新規カードが未処理fallbackへ流れた事例は検出されなかった。

正式指標CSVは、checked joinが700行、game metricsが700行、aggregateが24行であり、表計算読込後の式エラー相当tokenは0件だった。

46,519行のcallback CSVは、表計算ライブラリではメモリ上限を超えたため、生成スクリプトのschema検査、rootの行集計、SHA-256、およびaggregateとの再照合を正本とした。

## 比較A・正式指標の凍結証跡

| 証跡 | 相対path | SHA-256 |
| --- | --- | --- |
| 比較A paired rows | `alakazam_staged_20260729/evaluations/comparison_a_combined_adapterfix_v2/combined_paired_results.csv` | `E870397ED3F09D07FF1907CB281325429D035B5E95792026C5B27915B0DDCE88` |
| 比較A manifest | `alakazam_staged_20260729/evaluations/comparison_a_combined_adapterfix_v2/combined_manifest.jsonl` | `0596B13F9859546AE831CCE47586CCEFAB241F4E0BD31E12D95B2B2B8D7F49C2` |
| v0 suite manifest | `alakazam_staged_20260729/metrics/formal_v0_7opp_50seed/suite_manifest.json` | `73D40FCA981D7E35735A0D4D48A1D7575F0C55249E8AEE36F6D5BCB1506BE747` |
| v0 metric summary | `alakazam_staged_20260729/metrics/formal_v0_7opp_50seed_summary/metric_summary.json` | `57AB4DCE8D9C174F45E630A0FB6FFB64E4DF040C8F295E361FEC185337FE99D5` |
| v0 aggregates | `alakazam_staged_20260729/metrics/formal_v0_7opp_50seed_summary/metric_aggregates.csv` | `471D29F885DD726F7F0306F326CB77B07C1758D41D85CE7B80DC4854D068C0E0` |
| v0 game metrics | `alakazam_staged_20260729/metrics/formal_v0_7opp_50seed_summary/game_metrics.csv` | `D63E2D8992E558135095BFA7CE09298FA645996C35B7F22A7B2AD980680AD956` |
| v0 checked join | `alakazam_staged_20260729/metrics/formal_v0_7opp_50seed_summary/checked_join_audit.csv` | `CBED916268C01CAF95B8EE6195404D3C244AEB2F98BA2947DF63B329D064DD0C` |

Rocket行はMewtwo／Spidops agentによるproxyであり、Mewtwo ex／Ariados完全一致対面ではない。

以上から、`alakazam_newdeck_v0_port`はv1実装へ進むための安全性・挙動保存ゲートを通過した。