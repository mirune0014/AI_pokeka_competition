# フーディン段階開発の最終判断

## 決定

最終ローカル候補は`alakazam_newdeck_v1_package_runtime_certified_fix5`とする。

`alakazam_newdeck_v2_continuity_fix8_h1_unique_attach`は棄却する。

既存submission `54906455`は`alakazam_800_frozen`としてidentity anchorに保持し、変更しない。

今回の作業ではKaggle提出、既存提出の差し替え、Notebook公開を行っていない。

## 採用する実体

| 項目 | 値 |
| --- | --- |
| version | `alakazam_newdeck_v1_package_runtime_certified_fix5` |
| source | `alakazam_staged_20260729/versions/alakazam_newdeck_v1_package_runtime_certified_fix5` |
| policy closure | `5FFA8776CA95E16C7030C55B5682DE42BA21C06964C790A3D6312B60FBAA5009` |
| planner | `80A9B0F88A04591D4174B21AFCC5C9019A4EFCEC02E8F9C2D1576DCFC0FC044B` |
| raw deck | `F598F5E578D0440C96DC0492EAECF2E19739B7A23225BE57114A724EF7D0FB94` |
| normalized deck | `4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69` |
| adapter `main.py` | `426F1BBB71583A691CBF39A07FA8A042CB0AB0600EB43F22F9E4DBD247E5AAEC` |

この決定は、ローカルの段階比較で最も強く、安全性を満たした版を固定する判断である。

Leaderboard全体に対する真の勝率またはKaggle提出後の得点を保証するものではない。

## 段階別の判定

| 版 | 判定 | 主な根拠 |
| --- | --- | --- |
| `alakazam_800_frozen` | 凍結 | submission archiveとsourceをSHAで固定 |
| `alakazam_newdeck_v0_port` | PASS | 共有51枠の比較可能121 stateでaction差0、安全異常0 |
| `alakazam_newdeck_v1_package` | 採用 | v0比+23勝、gain/loss 35/12、安全異常0、9枠専用利用を実行 |
| `alakazam_newdeck_v2_continuity` | 棄却 | v1比0勝、H1完了0件、全700試合で方策分岐0 |

## v0の判断

v0は、新デッキへ既存方策を移すためのbaselineとして合格した。

保存済み42 replay、2,723 callbackのうち、共有51枠だけで成立する121状態ではfrozenとv0のaction差が0件だった。

Reason Code、trace分類、fallback、合法性の差も0件だった。

比較Aではfrozen 382/700勝に対しv0は428/700勝だった。

ただし、比較Aは9枠のデッキ差、初期state差、追加カードの最低限handlerを同時に含む。

この+46勝を純粋なデッキ効果と解釈しない。

## v1を保持する理由

比較Bでは、v0の428/700勝からv1の451/700勝へ23勝増えた。

対応付きgain/lossは35/12、両側exact sign testは`p=0.0010885382064742544`、50 seed cluster-tの95%区間は+1.31から+5.26ポイントだった。

seat 0は+14勝、seat 1は+9勝で、片seatだけの改善ではなかった。

対面差は、フーディン同型+12、既存frozen直接対戦+9、ガルーラ／イワパレス+4、Rocket proxyとHistorical-Silverは0、MarnieとCynthiaは各-1だった。

MarnieとCynthiaの-1は凍結した大幅退行floor内である。

9枠専用transactionは437件開始し437件完了した。

開始内訳はAlakazam 31、Enhanced Hammer 141、Boss’s Orders 56、Lana’s Aid 14、Xerosic’s Machinations 195、Nighttime Mine 0だった。

追加された新規3 ID等の専用playは209/3,192 `game × serial`で観測され、v0の0/3,249からzero-use状態を解消した。

formal 700試合、45,419 callbackでは、invalid action、例外、timeout、max-step、generic fallback、first-legal fallback、不可逆abort、pending transaction、削除カードrule hitがすべて0だった。

146件の単体試験もすべて成功した。

## v2を棄却する理由

v2 fix8は静的レビュー、192件の単体試験、140試合smoke、安全性formal gateを通過した。

しかし、Comparison Cの700試合はv1とv2が451/700勝で同じだった。

gain/lossは0/0、`p=1.0`で、全opponent、seat、seed-baseの差が0だった。

強度gateのうち、v1比+10勝、gain > loss、`p <= 0.10`、Historical-Silver正差が失敗した。

さらに、正式45,419 callbackでH1 transaction start、Energy装着検証、攻撃dispatch、KO解決がすべて0件だった。

機構gateが求める20 complete、両seat、3対面、3 seed-base、Silver 1 completeを満たさなかった。

全700試合が`NO_POLICY_DIVERGENCE`で、行動・継続性指標20,300 cellもv1と同一だった。

これはfallback安全性の証拠であり、連続攻撃改善の証拠ではない。

v2は平均decision timeを13.9724 msから22.1342 msへ増やしながら、実行actionを変えなかった。

したがって、v2を採用する合理的根拠はない。

凍結specに従い、`202608600..202608649`のholdoutは実行していない。

## 最終候補の数値

| 指標 | v1 |
| --- | ---: |
| overall | 451/700、64.4286% |
| seat 0 | 235/350、67.1429% |
| seat 1 | 216/350、61.7143% |
| first attack turn | 4.4012 |
| tailを含むattack gap | 12.2105% |
| 攻撃間gap | 6.7389% |
| post-KO continuity | 81.0302% |
| max consecutive attack turns | 5.1243 |
| 攻撃時手札 | 13.7684 |
| Powerful Hand counter | 29.3241 |
| 2本目Alakazam系統 | 95.3662% |
| invalid / exception / timeout / max-step | 0 / 0 / 0 / 0 |

post-KO等のevent率は方策が作る内生的分母を持つ。

v0との単純率差を因果効果とは解釈しない。

## 残る重大な制約

Rocket Mewtwo／Spidops proxyは38/100勝で、全7対面の最低値だった。

これはv0、v1、v2で変わらない。

しかも評価相手はRocket Mewtwo／Spidops proxyであり、依頼時に挙げられたRocket Mewtwo ex／Ariados完全一致方策ではない。

正確なRocket／Ariados実装を得られる場合は、提出判断より前に同じseed・seatで再評価する必要がある。

Historical-Silverは56/100勝で、v1はv0から改善も悪化もしていない。

既存提出を「800版」と呼ぶ一方、リポジトリに保存されたKaggle API行で確認できる初期public scoreは1試合後の509.6だけである。

`54906455`は提出物identityのanchorであり、成熟した800点の絶対強度証拠としては扱わない。

絶対強度の主要anchorには、完全実行可能なHistorical-Silver Archaludonを使用した。

## 次の一仮説

次に連続攻撃を再検証する場合は、v1が非終局Powerful Hand KOを返し、かつ一意なBench Alakazamと一意な超Energy手張り経路がある公開stateに限って、v1のowner deferより前にH1仲裁を許す仮説を新しいspecへ固定する。

それ以外のstateはv1 actionを完全保存する。

新しいholdoutへ進む前に、整列panelだけで20件以上のstart＝attach＝attack＝KO完了、両seat、3対面、3 seed-base、Historical-Silver 1件以上、非発火state完全一致、安全fault 0を満たす必要がある。

この方向は次実験の候補であり、今回の成果物では実装または提出を承認していない。

## 最終記録

独立数値監査はComparison Bをv2実験へ進める条件付きPASS、Comparison CをFAILと判断した。

独立戦略判定は`REJECT v2 fix8; RETAIN v1 fix5`と判断した。

root再計算は、全比較のschedule、重複、勝敗mapping、runner異常、formal join、主要指標を再確認し、不一致0件だった。
