# フーディン段階比較の最初の方策分岐

## 結論

比較Aではデッキ自体が異なるため、700試合を`OPERATIONAL_DECK_STATE_SPLIT`と分類し、方策単体の最初の分岐を主張しない。

比較Bでは700試合中260試合に`TRUE_POLICY_DIVERGENCE`があり、440試合には保存trace上の方策分岐がなかった。

比較Cでは700試合すべてが`NO_POLICY_DIVERGENCE`だった。

比較Cのv2は安全にv1へ戻ったが、H1の実行例を1件も作らなかった。

## 抽出方法

比較BとCでは、同じopponent、seat、seedの正式sidecarをcallback順に対応付けた。

各callbackで、事前状態、合法手集合、意味正規化した合法手集合、選択optionを比較した。

optionの物理順だけが違う場合は分岐と数えない。

最初に意味上異なるactionを選んだcallbackを固定し、後から再整列しても最初の分岐位置を変更しない。

最初の分岐と最終勝敗の対応は観測相関であり、カード単独の因果効果ではない。

## 比較A

`alakazam_800_frozen`と`alakazam_newdeck_v0_port`は、51枚を共有するが9枠が異なる。

初期手札、山札順、公開serial、合法手、以後のstate trajectoryがデッキ差から変わる。

比較Aのchecked runnerには、両deckが同一stateへ入ったことを証明するcallback traceも保存されていない。

したがって、700行すべてを次のように扱った。

| 分類 | 試合 |
| --- | ---: |
| `OPERATIONAL_DECK_STATE_SPLIT` | 700 |
| policy-level first divergence | 0件を主張 |

比較Aの382勝から428勝への差は、実運用上のデッキ・state・最低限移植処理の合成差である。

純粋なデッキ効果または特定カードの効果とは呼ばない。

## 比較B

v0とv1は同じ60枚を使う。

700試合のうち260試合で最初の意味方策分岐を検出し、47 discordant pairはすべてこの260試合に含まれた。

最初のv1選択カード別の結果は次のとおりである。

| 最初のv1選択 | 分岐試合 | 最終gain | 最終loss | 勝敗同じ |
| --- | ---: | ---: | ---: | ---: |
| Xerosic’s Machinations | 135 | 27 | 6 | 102 |
| Enhanced Hammer | 74 | 3 | 2 | 69 |
| Boss’s Orders | 25 | 2 | 0 | 23 |
| Alakazam | 13 | 1 | 4 | 8 |
| Lana’s Aid | 10 | 2 | 0 | 8 |
| cardなしのsemantic split | 3 | 0 | 0 | 3 |
| Nighttime Mine | 0 | 0 | 0 | 0 |

この集計は、最初の選択だけで最終結果を説明するものではない。

例えばXerosicはgain 27件とloss 6件の双方を含み、その後の盤面列も変化する。

### 代表例

| 対面 | seat | seed | callback / turn | v0の最初の選択 | v1の最初の選択 | 最終結果 |
| --- | ---: | ---: | --- | --- | --- | --- |
| フーディン同型 | 0 | 202608503 | 40 / 9 | Buddy-Buddy Poffin `1086` | Xerosic `1197` | loss → win |
| フーディン同型 | 1 | 202608525 | 34 / 8 | Dudunsparce `66`への進化 | Xerosic `1197` | win → loss |
| フーディン同型 | 0 | 202608540 | 40 / 9 | Telepath Psychic Energy `19`装着 | Enhanced Hammer `1081` | loss → win |
| ガルーラ／イワパレス | 1 | 202608536 | 46 / 12 | Powerful Hand `1072` | Boss’s Orders `1182` | loss → win |
| 既存frozen直接対戦 | 1 | 202608511 | 21 / 6 | Rare Candy `1079` | ActiveへのAlakazam `743`進化 | win → loss |
| フーディン同型 | 1 | 202608533 | 34 / 10 | Dudunsparce `66`退避 | Lana’s Aid `1184` | loss → win |

各例では、最初のcallbackまで事前状態と意味合法手集合が一致していた。

異なるのは、同じ合法手集合から選んだ意味actionである。

Alakazamの集計が1 gain対4 lossであっても、4枚目Alakazam規則全体を有害と断定しない。

13件という小さい分母、分岐後の連鎖、対面構成を分離できないためである。

## 比較C

v1とv2は同じ60枚、同じopponent、seat、seedを使った。

結果は次のとおりである。

| 分類 | 試合 |
| --- | ---: |
| `NO_POLICY_DIVERGENCE` | 700 |
| `TRUE_POLICY_DIVERGENCE` | 0 |

全700試合でresult、steps、callback単位の選択actionが一致した。

正式v2 traceでは45,419 callbackすべてが`V2_DEFER_V1_OWNER`と`V2_BASELINE_FALLBACK`を記録し、H1 transaction startは0件だった。

したがって、比較Cに「v2のH1が発火したが結果だけ偶然同じ」という事例はない。

v2は発火前にv1 ownerへ全件委譲した。

## 読み方

比較Bの分岐表は、実装候補を絞る診断証拠である。

特定カードを無条件に優先する根拠ではない。

比較Cの全件一致はnonfire fallbackの保存証拠である。

H1の安全性、継続性改善、対面強度を実行経路上で証明するものではない。

## 凍結証跡

| 比較 | CSV SHA-256 |
| --- | --- |
| A | `AB8607AFF4E24C8B466F3F742F3132A8C85C7C1D91F54227F52283CDD58EA541` |
| B | `127DD17D468DE5215496A41F68D27729A69DACA321C4393D1D5540A270CDA053` |
| C | `02A67E93D46FC02B31C4AD078475F4DA51C6AD2CF2C6BFBF013F027820D1FBC2` |

各CSVはheaderを除いて700行で、schedule keyの重複は0件である。
