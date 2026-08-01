# 完全合法行動候補: 既存データgate

既存32 episode・1685局面だけを読み取り、完全行動候補の表現可能性と実用性を測定した。新規rollout、BC、PPOは実施していない。

| 指標 | 結果 |
|---|---:|
| 候補数 median / p95 / p99 / max | 4 / 11 / 15 / 25 |
| canonical化前候補総数 | 11462 |
| canonical化後候補総数 | 7478 |
| duplicate canonical action | 3984 |
| teacher canonical表現可能率 | 1685/1685 (100.00%) |
| optional surface | 164/1685 (9.73%) |
| multiple teacher action | 198/1685 (11.75%) |
| optionalまたはmultiple | 346/1685 (20.53%) |
| 候補生成 ms median / p95 / p99 / max | 0.0458 / 0.1262 / 0.3385 / 6.3482 |
| 推論可変tensor max | 0.047 MiB |
| model + 可変tensor max | 0.266 MiB |

## 判定

- gate: **PASS**
- unordered multiple selectionはsemantic identityのmultisetとしてcanonical化し、actorは選択option embeddingのsum poolingで完全行動1候補をscoreする。
- teacher actionが候補にない場合はfallbackで隠さずrepresentability failureとして数える。本データでのfailureは0件。
- 候補数・生成時間・メモリは固定閾値内であり、次は8相手・両席・分散seedの新規2,000 teacher試合へ進める。
