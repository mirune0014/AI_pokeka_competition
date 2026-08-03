# フーディン新デッキ v1 9枠適応差分

## 結論

`alakazam_newdeck_v1_package_runtime_certified_fix5`は、v0と同じ60枚を使い、入れ替わった9枠に関係する判断だけを追加した決定論的ルールベース版である。

比較Bではv0の428/700勝からv1の451/700勝へ23勝増え、対応付き差は+3.286ポイントだった。

35 gain、12 loss、47 discordant pairに対する両側exact sign testは`p=0.0010885382064742544`で、50 seed cluster-tの95%区間は+1.31から+5.26ポイントだった。

安全性、9枠専用使用、主要対面の退行gateを通過したため、v1はv2実験のbaselineとして採用した。

その後の比較Cでv2が機構・効力gateに失敗したため、段階開発の最終ローカル候補としてv1を保持する。

これはKaggle提出またはLeaderboard上の最終デッキ採用の決定ではない。

## 正本identity

| 項目 | 値 |
| --- | --- |
| source | `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5` |
| policy closure | `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009` |
| planner | `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B` |
| raw deck | `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94` |
| normalized deck | `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` |
| evaluation adapter | `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC` |
| comparison spec | `43632474EFD532E6632A5C0C6AC45D5D958BB15FAE840EAF77A2D718BDB1733D` |

旧compliance版、fix2からfix4、各途中Comparison Bは`SUPERSEDED`証跡であり、本報告の数値へ混ぜない。

## 変更境界

v1は、raw整合性、duplicate owner、進行中transaction、終局KOを専用候補より先に評価する。

v1が発火しない場合は、v0のaction、Reason Code、fallback、core transaction、parent mutable stateを保持する。

一般的な次アタッカー最適化、対面名・seed・replay依存分岐、学習器は追加していない。

追加した候補は次の6系統に限定した。

1. 4枚目Alakazamを公開serialで証明できる進化復旧
2. 4枚目Enhanced Hammerを含む一意な特殊Energy除去
3. 3枚目Boss's Ordersを含む終局KOまたは一意な攻撃停止
4. Lana's Aidで初めて成立する現在KO
5. Xerosic's Machinations使用後も維持できる現在KO
6. Nighttime Mineで公開情報上の攻撃を停止しつつ維持する現在KO

Powerful Handに必要な最小手札は`Hreq = ceil(target_HP / 20)`で計算する。

カード使用後とchild callbackでは、最終手札、turn、action count、公開場、prize、捨て札、serial、SelectData envelopeを再検証する。

証明不能なrouteはfail closedとし、削除5 ID `{142, 858, 1156, 1161, 1264}`の自分側routeは継承ownerより前にdenylistで遮断する。

## カード別の実装

### Alakazam

同じcard IDだけで4枚目と断定しない。

他の3枚の物理serial、進化可能なKadabra、進化後3 draw、Powerful Hand成立を公開情報から一意に証明できる場合だけ使用する。

一般的な2本目作成はv1へ混ぜない。

### Enhanced Hammer

対象Energyのarea、owner、Pokémon index、energy index、id、serialを固定する。

Mist等を外して現在KOを新たに通すか、現在KOを維持しながら相手の一意なready attackerを止める場合だけ使用する。

Grow Grass EnergyのHP効果は対象がGrassの場合だけ20減る実エンジン意味論へ合わせ、非GrassとHero's Cape状態ではHPを保存する。

### Boss's Orders

終局サイド取得を最優先する。

非終局では、使用後`H-1`でも現在KOを維持し、相手の一意なready attackerを止める場合だけ使う。

Rocket ArticunoのRepelling VeilがBasic Team Rocket Pokémonへのdamage-counter効果を防ぐ局面は、使用前に遮断する。

### Lana's Aid

回収allowlistはAbra、Kadabra、Alakazam、Dunsparce、Dudunsparce、Shaymin、Basic Psychic Energyだけである。

Rule Box Pokémonと特殊Energyを除き、回収後`H-1+k`で初めて現在KOが成立する場合だけ使う。

### Xerosic's Machinations

相手手札が4枚以上で、使用後`H-1`でも現在KOを維持できる場合だけ使う。

次callbackで相手手札3枚と公開捨て札差分を検証する。

### Nighttime Mine

相手ActiveがTeraで、無色1個のcost増加により公開情報上の攻撃が未払いになり、使用後も現在KOを失わない場合だけ設置または張り替える。

formal評価では専用transactionは0件だった。

## 静的・runtime安全性

seeded engineを`PYTHONPATH`へ設定したPython 3.11.6で、candidate内の`test*.py` 146件はすべて成功した。

既知faultのHammer 60試合、Boss 20試合、smoke 140試合、formal 700試合を実行した。

formalでは700 games、70 blocks、45,419 callbackを記録し、次はすべて0だった。

- child exit、timeout、partial block、nonempty stderr
- action error、max-step、invalid winner
- structural invalid、exception
- generic fallback、first-legal fallback
- transaction abort、irreversible fault、pending transaction
- start/complete不一致、active rule switch
- unknown removed-card status、removed-card rule hit

専用transactionは437件開始し437件完了した。

開始内訳はAlakazam 31、Boss 56、Enhanced Hammer 141、Lana 14、Xerosic 195、Nighttime Mine 0だった。

## 比較Bの対応付き勝敗

7対面、50 seed、両seatの700行を、同じdeck、opponent、seed、seatで対応付けた。

| 対面 | v0 | v1 | 差 | gain / loss |
| --- | ---: | ---: | ---: | ---: |
| マーニー／オーロンゲ | 70/100 | 69/100 | -1 | 1 / 2 |
| シロナ／ガブリアス | 74/100 | 73/100 | -1 | 0 / 1 |
| フーディン同型 | 69/100 | 81/100 | +12 | 13 / 1 |
| Rocket Mewtwo／Spidops proxy | 38/100 | 38/100 | 0 | 1 / 1 |
| ガルーラ／イワパレス | 66/100 | 70/100 | +4 | 5 / 1 |
| Historical-Silver | 56/100 | 56/100 | 0 | 1 / 1 |
| 既存frozen直接対戦 | 55/100 | 64/100 | +9 | 14 / 5 |
| 全体 | 428/700 | 451/700 | +23 | 35 / 12 |

seat 0は221/350から235/350へ14勝増え、seat 1は207/350から216/350へ9勝増えた。

seed-base差は順に+6、-4、+4、+9、+8勝で、1 blockだけ負方向だった。

MarnieとCynthiaの-1は設定した大幅退行gate内だが、Rocket proxyの38%という絶対floorは解消していない。

## 行動指標

| 指標 | v0 | v1 | 差・注記 |
| --- | ---: | ---: | --- |
| first attack | 683/700、turn 4.4012 | 683/700、turn 4.4012 | 同値 |
| max consecutive attack | 5.1043 | 5.1243 | +0.0200 |
| tailを含むgap | 576/4,479、12.8600% | 543/4,447、12.2105% | -0.6495ポイント |
| 攻撃間gap | 293/4,167、7.0314% | 280/4,155、6.7389% | -0.2926ポイント |
| post-KO continuity | 701/867、80.8535% | 645/796、81.0302% | +0.1766ポイント、分母相違 |
| 2本目Alakazam系統 | 641/669、95.8146% | 638/669、95.3662% | -0.4484ポイント |
| 攻撃時手札 | 13.8350 | 13.7684 | -0.0666 |
| Powerful Hand counter | 29.4606 | 29.3241 | -0.1365 |
| new-only played / exposed | 0/3,249 | 209/3,192 | v1 6.5476% |
| generic fallback | 215/46,519 | 0/45,419 | v1は0 |
| first-legal fallback | 0 | 0 | 同値 |
| invalid / exception / timeout / max-step | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 全項目0 |
| average decision time | 16.0179ms | 13.9724ms | 別実行の診断値 |
| p95 decision time | 29.8599ms | 25.1533ms | 別実行の診断値 |

post-KO、second line、gapの分母は方策が作った内生的event数である。

したがって単純な率差を同一機会の因果効果とは解釈しない。

new-onlyの209件は`game × serial`で重複排除した観測であり、同一IDの増加copyへ自動帰属しない。

## 最初の方策分岐

700試合のうち260試合で最初のsemantic policy divergenceを検出し、440試合は保存trace上の分岐がなかった。

47 discordant pairはすべて`TRUE_POLICY_DIVERGENCE`に含まれた。

最初のcandidate card別の観測gain/lossは、Xerosic 27/6、Enhanced Hammer 3/2、Boss 2/0、Alakazam 1/4、Lana 2/0だった。

これは最初の分岐と最終勝敗の観測対応であり、カード単独の因果効果ではない。

## 凍結証跡

| 証跡 | SHA-256 |
| --- | --- |
| paired rows | `40CC9DBD57DF0826EA645FFB860BA976AD9B30E91209B337F1117073DBDCDE57` |
| combined manifest | `BE908376D654A36AFD1193C8D66D2ABA340658202E03C9B103845EF3CCAD14A5` |
| formal suite manifest | `0785538138716F87723AD0A025E375E5408F0DED5112F4309B6BD7468F9B6847` |
| formal execution summary | `B1DCA0579D43D07661EE57818FA0B258C107DB991817B53FCFE545939B85BF26` |
| formal game metrics | `A95FA44026DA8A7B4FF5D30536F3F4980CEC7BF17BED18F6DD926A92578394F4` |
| formal checked join | `7D406323FD8F9861EF35C95FAE10A81910CB6CFF949B410401966F7E57055883` |
| first-divergence CSV | `127DD17D468DE5215496A41F68D27729A69DACA321C4393D1D5540A270CDA053` |

独立数値監査とroot再計算は、700キー、schedule、勝敗、duplicate control、formal join、安全列の不一致0を確認した。
