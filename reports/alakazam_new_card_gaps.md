# 追加9枠に対する既存方策の欠落と解消範囲

## 結論

新デッキでは、Alakazam、Enhanced Hammer、Boss’s Ordersが各1枚増え、Lana’s Aid 1枚、Xerosic’s Machinations 3枚、Nighttime Mine 2枚が新しく入る。

既存提出方策には、増加copyを識別して使う判断と、新規3 IDの名前付き戦略がなかった。

v0は合法性と決定性だけを補い、任意PLAYを`V0_GENERIC_HOLD`として保持した。

最終v1は9枠に直接関係する狭い証明経路を追加したが、一般的な次アタッカー最適化はv2へ残した。

## v0で残した欠落

旧方策は、名前のないnon-Pokémon PLAYへ高い既定scoreを与える。

v0はLana’s Aid、Xerosic’s Machinations、Nighttime Mineの任意PLAYを`V0_GENERIC_HOLD`へ固定し、強制DISCARDだけを`V0_GENERIC_FORCED_DISCARD`で処理する。

4枚目のAlakazam、4枚目のEnhanced Hammer、3枚目のBoss’s Ordersは、同一card IDの物理copyであるため、v0では追加copy専用の利用理由を持たない。

この処理は挙動保存移植であり、9枠パッケージへの適応ではない。

## v1で実装した範囲

### 4枚目のAlakazam

Active KadabraをAlakazamへ進化して3枚引き、現在のPowerful Hand KOを初めて成立させる厳密な復旧経路を実装した。

加えて、非終局の現在KOを維持したまま、成熟して超エネルギーを持つ唯一のBench Kadabraを進化させる`V1_ALAKAZAM_4TH_READY_BENCH`を実装した。

4枚目であることは、他の3枚のAlakazam物理serialが公開領域で一意に確認できる場合だけ証明する。

証明できない場合は`UNKNOWN_IDENTICAL_CARD_ID`として、追加copy由来とは断定しない。

### 4枚目のEnhanced Hammer

公開場の特殊エネルギーが物理的に1枚だけ存在する場合に限定した。

その1枚を除くことでMist Energy等の防止を外して現在KOが成立する場合、または`H-1`の現在KOを維持しながら相手の唯一のready backupを停止する場合だけ使用する。

子promptではarea、player、Pokémon index、energy index、energy serialをすべて再束縛する。

### 3枚目のBoss’s Orders

`H-1`で唯一のBench対象を倒して終局する経路と、非終局で相手の唯一の公開ready attackerを呼び出して停止する経路を実装した。

後者は、呼び出した対象を同じPowerful Handで倒せて、別の公開ready attackerが残らない場合だけ発火する。

特殊エネルギー、Tool、特殊状態、攻撃禁止またはcost変更効果を解決できない場合はfail-closedとする。

### Lana’s Aid

回収allowlistはAbra、Kadabra、Alakazam、Dunsparce、Dudunsparce、Shaymin、Basic Psychic Energyだけである。

Rule Box Pokémonと特殊エネルギーを除外する。

使用前は現在KO不能だが、必要最小枚数を回収した`H-1+k`で初めてKOできる場合だけ使用する。

### Xerosic’s Machinations

相手手札が4枚以上で、相手の非公開手札内容を参照せず、使用後の`H-1`でも現在のPowerful Hand KOを維持できる場合だけ使用する。

次callbackで相手手札3枚と公開捨て札差分を検証する。

### Nighttime Mine

相手ActiveがTera Pokémonで、Nighttime Mineによる無色1個のcost増加により、公開情報上すべての攻撃が未払いになる場合だけ設置または張り替える。

自分のPowerful Hand KOと`H-1`の手札床を維持できない場合は使用しない。

## 共通の安全境界

各専用routeは、既存transaction、duplicate owner、終局KO、Xerosicの既存prefixなど、上位ownerを先に処理する。

カード使用後と各子promptで、turn、action count、手札、捨て札、山札、prize、場、Stadium、status、SelectData envelope、物理serialを再確認する。

公開状態やprompt形状が変わった場合はtransactionを破棄し、同じv0 fallbackへ戻る。

削除5 IDは、継承した所有判定より前に、各関係モジュールで同値に定義したdenylistによって自分側routeを遮断する。

denylistの物理的な定義箇所は3ファイルだが、集合値と適用順序は同一である。

相手側と公開盤面の意味解釈は保持する。

## v2で検証した範囲と残存欠落

v1は、現在攻撃者を除外したH1系統の一般探索、複数ターンの回収連鎖、KO後の同一ターン復旧、retreat・promotionを含む完全経路を実装しない。

初期の広い`V2_CERTIFIED_H1_CONTINUITY`案は、H0 serialの再利用、不可逆action前の完全経路証明、child束縛、abort faultに静的矛盾があり、比較前に`SUPERSEDED_NO_GO`とした。

最終v2 fix8では、既存Benchの一意なAlakazamへ一意な超Energyを手張りし、現在の非終局Powerful Hand KOを同じターンに維持する単一仮説だけを実装した。

192件の単体試験、140試合smoke、700試合formalの安全性は通過した。

一方、正式45,419 callbackでは全件がv1 ownerへdeferし、H1 transaction start、Energy装着検証、攻撃dispatch、KO解決はすべて0件だった。

比較Cの700試合もv1と全action・結果が一致した。

したがってfix8を棄却し、一般的なH1探索、複数ターン復旧、retreat・promotionは未実装の欠落として残す。

同一IDの増加copyは公開serial証明がない限り帰属不能であり、行動ログだけから4枚目の利用率へ変換しない。

対面名、seed、保存replayの実actionを使う分岐も実装しない。

## 最終v1の静的・実行証拠

最終v1 fix5の方策closureは`5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`である。

境界変異、実カード効果、実旧route、既知fault再現、完全transactionの反復を含む146件の単体試験はすべて成功した。

formal 700試合では、追加枠が公開された3,192件の`game × serial`機会に対し209件の専用使用を記録した。

専用transactionの開始内訳は、Xerosic 195件、Enhanced Hammer 141件、Boss 56件、Alakazam 31件、Lana 14件、Nighttime Mine 0件だった。

同一IDの増加copyは物理serial証明がない限り帰属不能であり、Alakazam、Enhanced Hammer、Bossの全使用を「増加copyの利用」と呼ばない。

実対戦の勝敗差と行動指標は`alakazam_v1_package_delta.md`で別に報告する。