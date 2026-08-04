# 要件対応表

## 判定基準

「実装済み」は、公開情報で条件を証明できる範囲の経路が単一resolverへ接続され、対応fixtureが通る状態を指す。
未知効果を推測して動くことや、固定seedの勝率を保証することは含まない。

| 要件群 | 状態 | 実装箇所または判断 |
|---|---|---|
| 固定deck、公開情報、決定論 | 実装済み | `deck.csv`、`main.py`、`state_view.py` |
| 状態表現と公開matchup flag | 実装済み | `state_view.py`、`features.py`、`public_effects.py` |
| damage、Prize、攻撃結果 | 実装済み | `damage.py`、`attack_outcomes.py` |
| certificate、優先順位、単一resolver | 実装済み | `certificates.py`、`resolver.py` |
| Resource Ledgerと物理serial | 実装済み | `resource_ledger.py` |
| Setup ActiveとBench形成 | 実装済み | setup fallback、`enumerate_basic_bench_routes` |
| Poké Pad | 実装済み | core形成を保証付きunion検索 |
| Fighting Gong | 実装済み | attack Energy、engine、Riolu、Makuhita検索。停止局面は `Lunatone > Riolu > Energy` |
| Ultra Ball | 実装済み | 安全な2枚discardと保証targetがある経路だけ実行 |
| 初手と中盤の手貼り | 実装済み | `R_ATTACH_001_*`、後攻attack completion、`R_ATTACH_002_CONTINUITY_V1` |
| Mega Lucario exとHariyama進化 | 実装済み | 攻撃、保護、Energy継続を条件に進化 |
| Lunar Cycle | 実装済み | 公開情報で安全なprefixだけ実行 |
| JudgeとLillie | 実装済み | 相手公開手札と自分のrole rebuildで分岐 |
| 攻撃選択 | 実装済み | exact damage、Prize、継続制約、非ex壁を比較 |
| Aura Jab Energy配置 | 実装済み | 次attacker完成を優先する集中配置 |
| Premium Power Pro | 実装済み | 最小必要枚数だけ使用 |
| BossとHariyama gust | 実装済み | immediate KO、finisher、Prize、進化阻害を比較 |
| Wally | 実装済み | 3 Prize attackerの回復再起動transaction |
| Switch、Cape、昇格、retreat | 実装済み | ready attacker、生存、board-out回避を優先 |
| Transactionとfault containment | 実装済み | `transactions.py`、`fallback.py`、`main.py` |
| Telemetry | 実装済み | `telemetry.py` |
| 局面fixture | 実装済み | 446件成功 |
| ルールごとの両席比較 | 対象外 | ユーザー指示により廃止 |
| 完成後の小規模比較 | 一度実施 | 修正前40局で初動停止を発見。修正後は代表1局だけ確認 |
| fixed160、fixed760、Kaggle提出 | 未実施 | 今回は実装速度を優先し、強さ判定と外部提出を行わない |

## 境界

未登録効果や公開情報だけでは結果を確定できない経路はfail closedとする。
したがって、本実装は「合法なら広く使う」方策ではなく、「公開情報で用途を証明できた経路を使う」方策である。
実装要件の主要系統は接続済みだが、競技上の完成度は今後の実戦失敗から修正する。
