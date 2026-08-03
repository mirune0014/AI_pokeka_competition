# 削除9枠に依存する既存ルール

## 判定

旧デッキだけに存在するカードは、Genesect 1枚、Psyduck 1枚、Lucky Helmet 1枚、Handheld Fan 2枚、Battle Cage 4枚である。

v0では共有51枠の判断同値性を優先し、識別子と分岐を残したまま自デッキ枚数を0にした。

したがって、v0の自デッキ専用分岐は到達不能だが、ソースから除去済みという意味ではない。

v1ではown-hand、own-deck、own-boardを起点とする前提だけを除去し、相手または公開盤面の意味解釈は残す。

## カード別の依存

Genesect、card ID 142は、setup順位、Hilda後のreserve、Run Away後の昇格、Lucky Helmet連携、退避先評価に使われる。

これらの自デッキrouteは除去し、相手のGenesectと保存リプレイの意味解釈用IDは残す。

Psyduck、card ID 858は、setup active、Duskull対面のbench、water threat、Hilda回収、退避先評価に使われる。

これらの自デッキrouteは除去し、公開カードとしての意味は残す。

Lucky Helmet、card ID 1156は、PLAY／ATTACH score、Genesect条件、draw clock、薄い山札で攻撃を強制するturn guardに使われる。

`P.GUARD.THIN_HELMET`を含むscore、clock、turn guardを除去する。

Handheld Fan、card ID 1161は、tool装着scoreと`I.FAN_RESPONSE`のenergy移動transactionに使われる。

このown-routeを除去し、相手toolの一般的な公開表現は壊さない。

Battle Cage、card ID 1264は、自分からのStadium PLAY、Dragapult対面の保護、張り替えscore、setup-stop protected setに使われる。

これらのown-routeは除去する。

一方、Battle Cageは相手または公開Stadiumとしてベンチへのdamage counter配置を防ぐため、`P.GUARD.FRAGILE_ABRA`などの効果判定には残す。

Nighttime Mine追加時は、旧来の「Stadiumなし、または1264だけ」というallowlistを、公開効果を比較する明示的な判定へ置き換える。

## 検証条件

v0の`deck.csv`と`runtime/deck.csv`には上記5 IDが存在しない。

この状態は`INERT_IN_V0`であり、`REMOVED_FROM_POLICY`ではない。

v1の静的テストでは、own-route参照が残っていないことと、opponent/public-state参照が残ることを別々に確認する。

## 最終v1適合結果

最終v1では、`REMOVED_OWN_CARD_IDS = {142, 858, 1156, 1161, 1264}`を意味上同一のdenylistとして各関係モジュールへ定義した。

物理的な定義箇所は3ファイルに分かれるが、集合値と適用順序は同一である。

このdenylistは、継承したtransactionや候補の所有判定より前に適用する。

したがって、Handheld Fanの既存transaction、GenesectとPsyduckの自分側役割、Lucky Helmetの薄い山札guard、Battle Cageの自分側前提へ到達しない。

強制promptで削除カードしか合法候補がない場合だけ、物理順の決定論的選択を許可し、`V1_REMOVED_CARD_FORCED_PROMPT_ONLY`を記録する。

相手のカードと公開盤面を解釈する意味論は削除していない。

最終v1 fix5の方策closureは`5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009`である。

実Handheld Fan transaction、各旧guard、既知のHammer効果、Rocket ArticunoのRepelling Veilを直接扱うfixtureを含む146件の単体試験は、すべて成功した。

formal 700試合・45,419 callbackでは、削除カードrule hitのinstrumentation statusは全件`KNOWN`で、hitは0件だった。

これは静的denylist、fixture、実行traceを組み合わせた非到達証明であり、保存replayや対面別の因果効果を推定した値ではない。
