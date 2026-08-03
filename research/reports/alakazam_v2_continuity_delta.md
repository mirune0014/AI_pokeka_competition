# フーディン新デッキ v2 連続攻撃差分

## 結論

`alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`は安全性を満たしたが、比較Cではv1から一度も方策分岐せず、連続攻撃ルールも一度も完了しなかった。

700試合の勝敗はv1、v2とも451勝249敗で、対応付きgain/lossは0/0、両側exact sign testは`p=1.0`だった。

正式45,419 callbackでは、transaction開始、Energy装着検証、攻撃dispatch、KO解決がすべて0件だった。

機構完全性と採用条件の双方に失敗したため、v2 fix8を棄却し、v1 fix5を最終ローカル候補として保持する。

未使用seed `202608600..202608649`のholdoutは実行せず、整列panelへ混ぜていない。

## 実装した仮説

v2では、広い連続攻撃最適化を一度に実装しなかった。

最終的に固定した単一規則は`V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO`である。

次の条件をすべて証明できる場合だけ、現在ActiveのAlakazamによる非終局Powerful Hand KOを維持しながら、既存Benchの一意なAlakazamへ一意な超Energyを手張りし、同じPowerful Handを実行する設計とした。

- 手張り後も`H - 1 >= ceil(target_HP / 20)`である。
- Bench Alakazamの不足costが超Energy1個だけである。
- Energy、対象、ATTACH option、Powerful Hand optionを物理serialで一意に束縛できる。
- v1、core、parent、duplicate callbackの既存ownerがない。
- 終局KO、既存transaction、9枠専用ruleを横取りしない。

Abra展開、一般的な進化探索、複数ターン回収、retreat、promotion、対面別分岐はこの実験へ追加していない。

初期の広い`V2_CERTIFIED_H1_CONTINUITY`案は、H0 serial再利用、不可逆action前の完全経路証明、Rare Candy child束縛、abort faultなどの静的矛盾により`SUPERSEDED_NO_GO`とした。

これは、依頼文に挙げられた広いv2機能を完成版として実装・採用したという意味ではない。

一つの解釈可能な機構を先に検証し、その機構が到達しなかったため、拡張前に停止した結果である。

## 正本identity

| 項目 | 値 |
| --- | --- |
| v1 source | `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5` |
| v1 closure | `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009` |
| v2 source | `alakazam_staged_20260729/versions/alakazam_newdeck_v2_continuity_fix8_h1_unique_attach` |
| v2 closure | `AB4F6FD57911BAE1D5CF9FAE2013298FC1744E401E52C65855BAB127A638FD57` |
| v2 planner | `12266E3311F878F99C6C6924274B22288912889E3F51B4B62DBDA8A1D35DB724` |
| raw deck | `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94` |
| normalized deck | `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` |
| comparison C spec | `715BC160D1F876C9C02C35260D93D4E049C2FA79337C28D9656AB38B8438DB2A` |

v1とv2の`deck.csv`はbyte-identicalである。

## 安全性の確定

fix5からfix7までは、owner、snapshot、duplicate callback、例外境界に残った静的欠陥を見つけるたびに棄却し、途中smokeを隔離した。

これらの途中出力は正式比較へ混ぜていない。

fix8ではactive V2 transactionの冒頭へ完全owner gateを追加し、独立静的レビューで新規P1/P2が0件となった。

seeded engineを`PYTHONPATH`へ設定したPython 3.11.6で、fix8 directoryの単体試験は192/192件成功した。

140試合smokeでは14/14 block、9,350/9,350 callbackが完了し、構造異常、例外、fallback、abort、pending transaction、action error、max-step hitは0件だった。

ただしsmokeでもH1 transactionは0件であり、強度または機構成立の証拠には使用していない。

## 比較Cの対応付き結果

比較A、Bと同じ7対面、両seat、50 seed、`202608500..202608549`を使った。

700 paired rowと210 manifest rowはすべて一意で、35 panelはすべて最初のattemptでvalidだった。

baseline duplicate A/Bは700件すべてでresult、steps、turn、context countが一致した。

| 対面 | v1 | v2 | 差 |
| --- | ---: | ---: | ---: |
| マーニー／オーロンゲ | 69/100 | 69/100 | 0 |
| シロナ／ガブリアス | 73/100 | 73/100 | 0 |
| フーディン同型 | 81/100 | 81/100 | 0 |
| Rocket Mewtwo／Spidops proxy | 38/100 | 38/100 | 0 |
| ガルーラ／イワパレス | 70/100 | 70/100 | 0 |
| Historical-Silver | 56/100 | 56/100 | 0 |
| 既存frozen直接対戦 | 64/100 | 64/100 | 0 |
| 全体 | 451/700 | 451/700 | 0 |

seat 0は両版235/350、seat 1は両版216/350だった。

全50 seed cluster、全opponent、全seat、全seed-baseで差は0だった。

全700行でresultとstepsも一致した。

Rocket proxyの絶対勝率38%は改善していない。

## 機構完全性

正式v2 suiteは70/70 block、700試合、45,419 callbackを完了した。

| 監査項目 | 結果 |
| --- | ---: |
| callback start / end | 45,419 / 45,419 |
| H1 transaction start | 0 |
| attach verified | 0 |
| attack dispatched | 0 |
| KO resolved | 0 |
| completed seat | 0 |
| completed opponent | 0 |
| completed seed-base | 0 |
| Historical-Silver complete | 0 |
| hard fault | 0 |
| pending transaction | 0 |
| structural invalid / exception | 0 / 0 |
| generic / first-legal fallback | 0 / 0 |

全callbackが`V2_BASELINE_FALLBACK`と`V2_DEFER_V1_OWNER`を記録した。

したがって、fix8は安全なno-opではあるが、H1を実行した方策ではない。

必要条件は、complete 20件以上、両seat、3対面以上、3 seed-base以上、Historical-Silver 1件以上、かつstartからKOまでの段階数一致だった。

すべて未達である。

## 行動指標

v1とv2の700 game metricsについて、結果、step、攻撃、gap、post-KO、2本目、追加枠利用、fallback、安全列の20,300 cellをrootで再比較し、不一致は0件だった。

| 指標 | v1 | v2 | 差 |
| --- | ---: | ---: | ---: |
| first attack turn | 4.401171 | 4.401171 | 0 |
| max consecutive attack turns | 5.124286 | 5.124286 | 0 |
| tailを含むgap | 12.210479% | 12.210479% | 0 |
| 攻撃間gap | 6.738869% | 6.738869% | 0 |
| post-KO continuity | 81.030151% | 81.030151% | 0 |
| 2本目Alakazam系統 | 95.366218% | 95.366218% | 0 |
| 攻撃時手札 | 13.768443 | 13.768443 | 0 |
| Powerful Hand counter | 29.324125 | 29.324125 | 0 |
| new-only played / exposed | 209 / 3,192 | 209 / 3,192 | 0 |
| generic fallback | 0 | 0 | 0 |
| first-legal fallback | 0 | 0 | 0 |
| invalid / exception / timeout / max-step | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 |
| average decision time | 13.9724 ms | 22.1342 ms | +8.1618 ms |
| p95 decision time | 25.1533 ms | 39.2193 ms | +14.0660 ms |

post-KO等の率は内生的eventを分母とする。

今回は全action列が同じため数値も同じだが、これはv2機構の効果0を推定した値ではなく、機構が発火しなかったv1 fallbackの再現値である。

decision timeだけはwrapperの追加監査により増えた。

v2 wrapper traceでは削除カードhitの明示statusを引き継がなかったため、v2行は`UNKNOWN_WRAPPER_TRACE`とし、0へ補完していない。

## 採用gate

| gate | 条件 | 結果 |
| --- | --- | --- |
| absolute wins | 441/700以上 | PASS、451 |
| paired gain | v1より10勝以上 | FAIL、0 |
| discordant direction | gain > loss | FAIL、0 > 0ではない |
| exact sign test | `p <= 0.10` | FAIL、`p=1.0` |
| Historical-Silver | 正の差 | FAIL、0 |
| Silver両seat | 非負 | PASS、0 / 0 |
| 全体両seat | 非負 | PASS、0 / 0 |
| 他対面floor | 各-2勝以上 | PASS、全て0 |
| mechanism completeness | 20件以上と分布条件 | FAIL、0件 |
| safety | fault、invalid、例外、timeout、max-step 0 | PASS |

安全性PASSは、発火経路の有効性を証明しない。

機構完全性と効力のhard gateが失敗したため、追加holdoutへ進む条件はない。

## 30分上限からの復旧

最初の正式実行は、69 blockと最終blockの9 game sidecarを生成した時点で、ホストプロセスの30分上限により停止された。

この部分blockは`quarantine_timeout_partial`へ移し、集計へ混ぜていない。

凍結launcher自身の`build_command`と`execute_block`を使って最終10 game blockを新規に再実行し、完了後だけ70件目のledger rowを追記した。

最終suiteは70 unique block、700 sidecar、700 checked joinを持ち、partial diagnostic gameは0件である。

## 凍結証跡

| 証跡 | SHA-256 |
| --- | --- |
| Comparison C paired rows | `4933BCEE122A4081CE35BF36C556A2462399633FCD0C8EC87359D6570C0D3230` |
| Comparison C manifest | `3487359E211857831DBB5364236DBA5350751319B8308B2582EE3105EDDFFC4F` |
| formal suite manifest | `A1D2B9648A0FE787E85B7E22312AE05271AA0669661BDE2C7136148CB45B2875` |
| formal block ledger | `83F4C843EC8D8C12C668482320149E2BA24011FB1EEB112517C355D37321D97C` |
| formal game metrics | `ABDB97D59E341BE516EC3C263CB499AA9E7A5AFE6A88CF76C1C38EF00161550F` |
| formal checked join | `6B2B208D1FA4624CA07DE917069EB4D6A619EA72F4180957E5F3074229E26411` |
| H1 transaction audit | `FFCC66FAC527F43495E98ABE39DAF424D98E9FB46609D01702242DD49E67B2DE` |
| first-divergence CSV | `02A67E93D46FC02B31C4AD078475F4DA51C6AD2CF2C6BFBF013F027820D1FBC2` |

独立数値監査と独立戦略判定はいずれも、`REJECT v2 fix8; RETAIN v1 fix5`と判断した。
